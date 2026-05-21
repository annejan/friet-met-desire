#!/usr/bin/env python3
"""MIDI -> PSID converter with drums on V3, vibrato + PWM on lead V2,
resonant lowpass filter on V2, and a fatter bass on V1."""
import mido, struct, subprocess, sys, os, math

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MIDI_PATH = sys.argv[1] if len(sys.argv) > 1 else os.path.join(BASE, 'midi', 'Gala_Freed_From_Desire.mid')
OUT_SID   = sys.argv[2] if len(sys.argv) > 2 else os.path.join(BASE, 'out', 'friet_from_desire.sid')

# Track picks — proper roles:
#   T5 = iconic synth bassline riff (D2-F3)        -> V1 bass
#   T7 = vocal melody (A4-F5, sung lyrics)         -> V2 lead
#   T11 = chorus "na-na" hook (D3-F3, 92-124s only) -> overrides T7 in chorus
#   T13 = drums                                     -> V3
BASS_TRACK     = 5
BASS_TRANSPOSE = 0
LEAD_TRACK     = 7
LEAD2_TRACK    = 11
CHORD_TRACK    = 6
DRUM_TRACK     = 13

PAL_HZ  = 50.0
PAL_CLK = 985248.0

# Waveform/control bits (gate=$01 ORed on note-on)
WF_TRI   = 0x10
WF_SAW   = 0x20
WF_PULSE = 0x40
WF_NOISE = 0x80

# Per-voice ADSR for tonal events (drums override on V3)
V1_AD, V1_SR = 0x09, 0xA4   # bass: short attack, sustain held, short release
V2_AD, V2_SR = 0x08, 0xF9   # lead: short attack, full sustain, medium release
V3_AD, V3_SR = 0x0A, 0x68   # chord stab: short, organ-like

def midi_to_sid_freq(note):
    hz = 440.0 * 2 ** ((note - 69) / 12.0)
    return int(round(hz * (1 << 24) / PAL_CLK)) & 0xFFFF

def tempo_us(mid):
    for t in mid.tracks:
        for m in t:
            if m.type == 'set_tempo':
                return m.tempo
    return 500000

def extract_notes(mid, track_idx, pick='top'):
    """Per-note (start_frame, end_frame, midi_note); polyphony collapsed (top or bot wins)."""
    track = mid.tracks[track_idx]
    tick_to_frame = (tempo_us(mid) / mid.ticks_per_beat) * PAL_HZ / 1e6

    held = {}
    raw = []
    t = 0
    for msg in track:
        t += msg.time
        if msg.type == 'note_on' and msg.velocity > 0:
            if msg.note in held:
                raw.append((held[msg.note], t, msg.note))
            held[msg.note] = t
        elif msg.type == 'note_off' or (msg.type == 'note_on' and msg.velocity == 0):
            if msg.note in held:
                raw.append((held.pop(msg.note), t, msg.note))
    for note, s in held.items():
        raw.append((s, t, note))
    raw.sort()

    events = []
    for idx, (s, e, n) in enumerate(raw):
        sf = int(round(s * tick_to_frame))
        ef = int(round(e * tick_to_frame))
        if ef <= sf: ef = sf + 1
        events.append((sf, 0, n, idx))
        events.append((ef, 1, n, idx))
    events.sort()

    active = {}
    spans = []
    cur_idx = None
    last_frame = 0
    def winner():
        if not active: return None
        items = list(active.items())
        return (max if pick == 'top' else min)(items, key=lambda kv: (kv[1], -kv[0]))
    for frame, kind, note, idx in events:
        if cur_idx is not None and frame > last_frame:
            spans.append((last_frame, frame, active[cur_idx]))
        last_frame = frame
        if kind == 0:
            active[idx] = note
        else:
            active.pop(idx, None)
        w = winner()
        cur_idx = w[0] if w else None
    return [(s, e, n) for s, e, n in spans if e > s]

def extract_drum_hits(mid, track_idx):
    """Returns list of (start_frame, midi_note) for drum channel events.
    Filters to foundational kit only (kick, snare/clap, one hat sound)."""
    KEEP = {36, 35, 28,    # kicks
            38, 40, 39,    # snare + clap
            42, 44, 46}    # closed + pedal + open hat (for more pattern variety)
    track = mid.tracks[track_idx]
    tick_to_frame = (tempo_us(mid) / mid.ticks_per_beat) * PAL_HZ / 1e6
    hits = []
    t = 0
    for msg in track:
        t += msg.time
        if msg.type == 'note_on' and msg.velocity > 0 and msg.note in KEEP:
            hits.append((int(round(t * tick_to_frame)), msg.note))
    return hits

# Map a GM drum note to (noise_pitch_byte, duration_frames, ad, sr)
def drum_params(midi_note):
    # Pitch byte is an INDEX into freq table (0..95 = MIDI 24..119).
    # Lower index = lower pitch (deeper noise rumble for kick).
    if midi_note in (35, 36, 28):
        return (2,  6, 0x00, 0x09)   # kick: very low rumble, longer body
    if midi_note in (38, 39, 40, 49, 51, 57, 59):
        return (36, 4, 0x00, 0x06)   # snare/clap/cymbal: mid
    return (72, 2, 0x00, 0x04)       # hat: high, short tick

def build_v3_stream(chord_spans, drum_hits, total_frames):
    """V3 = drums only. Each drum hit becomes a short noise pulse; gaps are
    explicit gate-off events so envelopes can fully release between hits."""
    REST = (0, 0x80, V3_AD, V3_SR)   # noise no gate (rest)
    timeline = [REST] * (total_frames + 2)

    for f, dnote in drum_hits:
        if f >= total_frames: continue
        pitch, dur, ad, sr = drum_params(dnote)
        for i in range(dur):
            if f + i < total_frames:
                timeline[f + i] = (pitch, 0x81, ad, sr)
        # Explicit gate-off after hit
        if f + dur < total_frames:
            timeline[f + dur] = (pitch, 0x80, ad, sr)

    events = []
    i = 0
    while i < total_frames:
        cur = timeline[i]
        j = i + 1
        while j < total_frames and timeline[j] == cur:
            j += 1
        events.append((j - i, cur))
        i = j
    return events

def encode_v3(events):
    """V3 format: dur_hi, dur_lo, note, ctrl, ad, sr  (6 bytes per event)."""
    buf = bytearray()
    for dur, (note, ctrl, ad, sr) in events:
        if dur < 1: dur = 1
        while dur > 0xFFFF:
            buf += bytes([0xFF, 0xFF, note & 0x7F, ctrl, ad, sr])
            dur -= 0xFFFF
        buf += bytes([(dur >> 8) & 0xFF, dur & 0xFF, note & 0x7F, ctrl, ad, sr])
    buf += bytes([0, 0, 0, 0, 0, 0])  # loop sentinel
    return buf

def voice_stream_3byte(spans):
    """V1/V2 simple format: dur_hi, dur_lo, note  (3 bytes)."""
    out = []
    last_end = 0
    for s, e, n in spans:
        if s > last_end:
            out.append((s - last_end, 0))
        out.append((e - s, n))
        last_end = e
    buf = bytearray()
    for dur, note in out:
        if dur < 1: dur = 1
        while dur > 0xFFFF:
            buf += bytes([0xFF, 0xFF, note & 0x7F])
            dur -= 0xFFFF
        buf += bytes([(dur >> 8) & 0xFF, dur & 0xFF, note & 0x7F])
    buf += bytes([0, 0, 0])
    return buf

# ---- main ----
mid = mido.MidiFile(MIDI_PATH)
print(f"Loaded {MIDI_PATH}: {mid.length:.1f}s, {len(mid.tracks)} tracks")

bass_raw = extract_notes(mid, BASS_TRACK, pick='bot')
bass = [(s, e, max(0, n + BASS_TRANSPOSE)) for s, e, n in bass_raw if n > 0]
lead1 = extract_notes(mid, LEAD_TRACK,  pick='top')   # vocal
lead2 = extract_notes(mid, LEAD2_TRACK, pick='top')   # chorus hook
chord = extract_notes(mid, CHORD_TRACK, pick='top')
drums = extract_drum_hits(mid, DRUM_TRACK)

# During chorus, T11 ("na-na" hook) substitutes for T7 (vocal). Outside that
# window, T7 plays. T11 plays from ~92s to ~124s.
def substitute_chorus(primary, secondary):
    """Where secondary has notes, secondary wins. Otherwise primary plays."""
    if not secondary:
        return primary
    end = max([e for _, e, _ in primary + secondary], default=0)
    sec_active = [None] * (end + 2)
    for s, e, n in secondary:
        for f in range(s, e):
            sec_active[f] = n
    pri_active = [None] * (end + 2)
    for s, e, n in primary:
        for f in range(s, e):
            pri_active[f] = n
    merged = []
    cur_n, cur_start = None, None
    for f in range(end):
        winner = sec_active[f] if sec_active[f] is not None else pri_active[f]
        if winner != cur_n:
            if cur_n is not None:
                merged.append((cur_start, f, cur_n))
            cur_n = winner
            cur_start = f
    if cur_n is not None:
        merged.append((cur_start, end, cur_n))
    return merged

lead = substitute_chorus(lead1, lead2)

# Extend lead notes slightly so phrase endings have a tail before the rest hits.
# For each note, extend its end up to the next note's start (or by EXTEND frames
# if there's a gap longer than that). This gives a more legato feel.
def extend_for_legato(spans, extend=10):
    out = []
    for i, (s, e, n) in enumerate(spans):
        if i + 1 < len(spans):
            next_s = spans[i + 1][0]
            new_e = min(e + extend, next_s)
        else:
            new_e = e + extend
        out.append((s, max(new_e, e + 1), n))
    return out

lead = extend_for_legato(lead, extend=1)

total_f = max(e for _,e,_ in (bass + lead + chord)) + 50
v1_data = voice_stream_3byte(bass)
v2_data = voice_stream_3byte(lead)
v3_events = build_v3_stream(chord, drums, total_f)
v3_data = encode_v3(v3_events)

print(f"  bass  T{BASS_TRACK}: {len(bass)} spans, {len(v1_data)}B")
print(f"  lead  T{LEAD_TRACK}: {len(lead)} spans, {len(v2_data)}B")
print(f"  chord+drum T{CHORD_TRACK}+T{DRUM_TRACK}: {len(v3_events)} events, {len(v3_data)}B")

# ---- frequency table (MIDI 24..119) ----
NOTE_LO = 24
NOTE_HI = 119
freq_lo = []
freq_hi = []
for n in range(NOTE_LO, NOTE_HI + 1):
    f = midi_to_sid_freq(n)
    freq_lo.append(f & 0xFF)
    freq_hi.append((f >> 8) & 0xFF)

# Vibrato LFO table — 16-entry signed-ish, applied to lead freq lo (+ carry)
# zigzag with peak amplitude 12 freq units
VIB_DEPTH = 14
vib_pattern = [0, 4, 8, 12, 14, 12, 8, 4, 0, -4, -8, -12, -14, -12, -8, -4]
vib_table = [(v & 0xFF) for v in vib_pattern]   # signed 8-bit in two's complement
# We also need to know the sign for hi-byte correction; encode sign as a parallel table
vib_signhi = [0xFF if v < 0 else 0x00 for v in vib_pattern]

# PWM table — narrower sweep $07..$09 (close to 50% duty, gentle movement)
pwm_table = []
for i in range(32):
    if i < 16:
        pwm_table.append(0x07 + (i // 8))
    else:
        pwm_table.append(0x07 + ((31 - i) // 8))

def bytes_to_asm(name, data, per_line=16):
    out = [f"{name}:"]
    for i in range(0, len(data), per_line):
        chunk = data[i:i+per_line]
        out.append("    .byt " + ",".join(f"${b:02X}" for b in chunk))
    return "\n".join(out)

asm = f"""
NOTE_LO = {NOTE_LO}
SID = $D400

; Zero-page work area
ZP_V0   = $FB
ZP_V1   = $FD
ZP_V2   = $F7
ZP_CNT0 = $02
ZP_CNT1 = $04
ZP_CNT2 = $06
ZP_V2BASE_LO = $08
ZP_V2BASE_HI = $09
ZP_VIB_IDX   = $0A
ZP_PWM_IDX   = $0B

*=$1000
    jmp init_routine    ; $1000 PSID init entry
    jmp play_routine    ; $1003 PSID play entry

; ================================================================
; INIT
; ================================================================
init_routine:
    sei
    lda #0
    ldx #$18
init_clr:
    sta SID,x
    dex
    bpl init_clr

    ; ADSR per voice (V3 ADSR is updated per-event for drum vs chord)
    lda #${V1_AD:02X}
    sta SID+5
    lda #${V1_SR:02X}
    sta SID+6
    lda #${V2_AD:02X}
    sta SID+12
    lda #${V2_SR:02X}
    sta SID+13
    lda #${V3_AD:02X}
    sta SID+19
    lda #${V3_SR:02X}
    sta SID+20

    ; Default pulse width for V2 (lead)
    lda #$00
    sta SID+9           ; V2 PW LO ($D409)
    lda #$08
    sta SID+10          ; V2 PW HI ($D40A)

    ; Filter — lowpass on V2 with cutoff around 2.5kHz; passes the lead body
    ; (fundamentals 440-740Hz + first few harmonics) while attenuating the
    ; "beepy" 6th+ harmonics that pulse waves naturally produce.
    lda #$00
    sta SID+21          ; FC LO
    lda #$A0
    sta SID+22          ; FC HI
    lda #$12
    sta SID+23          ; RES/FILT — res=1, V2 routed
    lda #$1F
    sta SID+24          ; MODE/VOL — LP + vol max

    ; Reset pointers and counters
    lda #<v0_data
    sta ZP_V0
    lda #>v0_data
    sta ZP_V0+1
    lda #<v1_data
    sta ZP_V1
    lda #>v1_data
    sta ZP_V1+1
    lda #<v2_data
    sta ZP_V2
    lda #>v2_data
    sta ZP_V2+1

    lda #0
    sta ZP_CNT0
    sta ZP_CNT0+1
    sta ZP_CNT1
    sta ZP_CNT1+1
    sta ZP_CNT2
    sta ZP_CNT2+1
    sta ZP_V2BASE_LO
    sta ZP_V2BASE_HI
    sta ZP_VIB_IDX
    sta ZP_PWM_IDX
    cli
    rts

; ================================================================
; PLAY (50Hz)
; ================================================================
play_routine:
    jsr tick0
    jsr tick1
    jsr tick2
    jsr apply_vibrato
    jsr apply_pwm
    rts

; ---- Voice 0 (bass) -- 3-byte events ----
tick0:
    lda ZP_CNT0
    bne d0lo
    lda ZP_CNT0+1
    bne d0hi
    jmp fetch0
d0hi:
    dec ZP_CNT0+1
    dec ZP_CNT0
    rts
d0lo:
    dec ZP_CNT0
    rts

fetch0:
    ldy #0
    lda (ZP_V0),y
    sta ZP_CNT0+1
    iny
    lda (ZP_V0),y
    sta ZP_CNT0
    iny
    lda (ZP_V0),y
    pha
    lda ZP_CNT0
    ora ZP_CNT0+1
    bne f0go
    pla
    lda #<v0_data
    sta ZP_V0
    lda #>v0_data
    sta ZP_V0+1
    rts
f0go:
    pla
    pha
    cmp #0
    beq f0rest
    sec
    sbc #NOTE_LO
    tax
    lda freq_lo,x
    sta SID+0
    lda freq_hi,x
    sta SID+1
    lda #${WF_TRI:02X}        ; bass = triangle (round body)
    sta SID+4
    lda #${WF_TRI|1:02X}
    sta SID+4
    jmp f0adv
f0rest:
    lda #${WF_TRI:02X}
    sta SID+4
f0adv:
    pla
    clc
    lda ZP_V0
    adc #3
    sta ZP_V0
    bcc f0done
    inc ZP_V0+1
f0done:
    rts

; ---- Voice 1 (lead) -- 3-byte events ----
tick1:
    lda ZP_CNT1
    bne d1lo
    lda ZP_CNT1+1
    bne d1hi
    jmp fetch1
d1hi:
    dec ZP_CNT1+1
    dec ZP_CNT1
    rts
d1lo:
    dec ZP_CNT1
    rts

fetch1:
    ldy #0
    lda (ZP_V1),y
    sta ZP_CNT1+1
    iny
    lda (ZP_V1),y
    sta ZP_CNT1
    iny
    lda (ZP_V1),y
    pha
    lda ZP_CNT1
    ora ZP_CNT1+1
    bne f1go
    pla
    lda #<v1_data
    sta ZP_V1
    lda #>v1_data
    sta ZP_V1+1
    rts
f1go:
    pla
    pha
    cmp #0
    beq f1rest
    sec
    sbc #NOTE_LO
    tax
    lda freq_lo,x
    sta ZP_V2BASE_LO    ; store base freq; vibrato applies it each frame
    lda freq_hi,x
    sta ZP_V2BASE_HI
    lda #${WF_PULSE:02X}
    sta SID+11
    lda #${WF_PULSE|1:02X}
    sta SID+11
    jmp f1adv
f1rest:
    ; Do NOT reset ZP_V2BASE — keep last note's freq so vibrato during release
    ; doesn't wrap toward 0 and produce a beep.
    lda #${WF_PULSE:02X}
    sta SID+11
f1adv:
    pla
    clc
    lda ZP_V1
    adc #3
    sta ZP_V1
    bcc f1done
    inc ZP_V1+1
f1done:
    rts

; ---- Voice 2 (chord+drums) -- 6-byte events: dur_hi,dur_lo,note,ctrl,ad,sr ----
tick2:
    lda ZP_CNT2
    bne d2lo
    lda ZP_CNT2+1
    bne d2hi
    jmp fetch2
d2hi:
    dec ZP_CNT2+1
    dec ZP_CNT2
    rts
d2lo:
    dec ZP_CNT2
    rts

fetch2:
    ldy #0
    lda (ZP_V2),y
    sta ZP_CNT2+1
    iny
    lda (ZP_V2),y
    sta ZP_CNT2
    iny
    lda (ZP_V2),y       ; note
    pha
    lda ZP_CNT2
    ora ZP_CNT2+1
    bne f2go
    pla
    lda #<v2_data
    sta ZP_V2
    lda #>v2_data
    sta ZP_V2+1
    rts
f2go:
    pla
    pha                ; note on stack
    iny
    lda (ZP_V2),y      ; ctrl byte
    pha                ; ctrl on stack
    iny
    lda (ZP_V2),y      ; AD
    sta SID+19
    iny
    lda (ZP_V2),y      ; SR
    sta SID+20
    ; Decide freq lookup first (using "note" still on stack below ctrl)
    pla                ; A = ctrl (preserve)
    pha
    and #$80           ; bit 7 = noise waveform => drum
    bne f2_drum
    ; Tonal: look up freq from table
    tsx
    lda $0102,x        ; peek note (under ctrl) — stack layout: [note][ctrl][...]
    cmp #0
    beq f2_freq_done
    sec
    sbc #NOTE_LO
    tax
    lda freq_lo,x
    sta SID+14
    lda freq_hi,x
    sta SID+15
f2_freq_done:
    jmp f2_gate
f2_drum:
    ; Drum: use note value as DIRECT INDEX into freq table for noise pitch
    tsx
    lda $0102,x        ; peek note under ctrl
    tax
    cpx #96
    bcc f2_drum_ok
    ldx #95            ; clamp
f2_drum_ok:
    lda freq_lo,x
    sta SID+14
    lda freq_hi,x
    sta SID+15
f2_gate:
    pla                ; ctrl
    pha                ; keep for second write
    and #$FE           ; gate off
    sta SID+18
    pla                ; ctrl (gate on)
    sta SID+18
    pla                ; pop note (discard now)
f2adv:
    clc
    lda ZP_V2
    adc #6
    sta ZP_V2
    bcc f2done
    inc ZP_V2+1
f2done:
    rts

; ---- Vibrato: add table[idx] (signed) to V2 base freq, write to $D407/$D408 ----
apply_vibrato:
    ; Skip entirely if base freq is zero (before any note played) — otherwise
    ; the vibrato offset would wrap to a high freq and produce a constant tone.
    lda ZP_V2BASE_LO
    ora ZP_V2BASE_HI
    bne vib_active
    rts
vib_active:
    inc ZP_VIB_IDX
    lda ZP_VIB_IDX
    and #$0F
    tay
    lda vib_lo,y
    clc
    adc ZP_V2BASE_LO
    sta SID+7
    lda vib_hi,y
    adc ZP_V2BASE_HI
    sta SID+8
    rts

; ---- PWM: sweep V2 pulse width hi ($D40B) ----
apply_pwm:
    inc ZP_PWM_IDX
    lda ZP_PWM_IDX
    and #$1F
    tay
    lda pwm_table,y
    sta SID+10         ; $D40A PW lo (use as part of width)
    rts

; ================================================================
; Data tables
; ================================================================
{bytes_to_asm('freq_lo', freq_lo)}
{bytes_to_asm('freq_hi', freq_hi)}
{bytes_to_asm('vib_lo', vib_table)}
{bytes_to_asm('vib_hi', vib_signhi)}
{bytes_to_asm('pwm_table', pwm_table)}

{bytes_to_asm('v0_data', v1_data)}
{bytes_to_asm('v1_data', v2_data)}
{bytes_to_asm('v2_data', v3_data)}
"""

asm_path = '/tmp/freed.s'
prg_path = '/tmp/freed.prg'
with open(asm_path, 'w') as f:
    f.write(asm)

r = subprocess.run(['xa', '-XMASM', '-o', prg_path, asm_path], capture_output=True, text=True)
if r.returncode != 0:
    print("xa failed:")
    print(r.stdout)
    print(r.stderr)
    sys.exit(1)

with open(prg_path, 'rb') as f:
    prg = f.read()

load_addr = 0x1000
prg = bytes([load_addr & 0xFF, (load_addr >> 8) & 0xFF]) + prg
print(f"Code load=${load_addr:04X} size={len(prg)-2} bytes")

init_addr = 0x1000
play_addr = 0x1003

def pad32(s):
    b = s.encode('ascii')[:31]
    return b + b'\0' * (32 - len(b))

header = b'PSID'
header += struct.pack('>H', 2)
header += struct.pack('>H', 0x7C)
header += struct.pack('>H', 0)
header += struct.pack('>H', init_addr)
header += struct.pack('>H', play_addr)
header += struct.pack('>H', 1)
header += struct.pack('>H', 1)
header += struct.pack('>I', 0)
header += pad32('Freed From Desire')
header += pad32('Gala (MIDI to SID)')
header += pad32('2026')
header += struct.pack('>H', 0x0000)
header += bytes([0, 0, 0, 0])
assert len(header) == 0x7C

with open(OUT_SID, 'wb') as f:
    f.write(header + prg)
print(f"Wrote {OUT_SID} ({len(header) + len(prg)} bytes)")
