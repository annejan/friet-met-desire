#!/usr/bin/env python3
"""Happy Hardcore SID from a MIDI file.

Takes the melody + timing from a MIDI (default: Freed From Desire) and
re-arranges as a happy-hardcore-style SID tune:
  V1 bass  : stabby pulse, off-beat 8th-note bouncy bass tracking melody root
  V2 lead  : sawtooth with per-note filter cutoff envelope for hoover-ish wow,
             high resonance, vibrato + PWM doesn't apply (saw has no PW)
  V3 drums : programmatic 4-on-floor kick + snare on 2&4 + 16th hats
"""
import mido, struct, subprocess, sys, os, math

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MIDI_PATH = sys.argv[1] if len(sys.argv) > 1 else os.path.join(BASE, 'midi', 'Gala_Freed_From_Desire.mid')
OUT_SID   = sys.argv[2] if len(sys.argv) > 2 else os.path.join(BASE, 'out', 'friet_from_desire_hh.sid')

LEAD_TRACK   = 5         # iconic FFD riff
PAL_HZ       = 50.0
PAL_CLK      = 985248.0

# Happy hardcore tempo
HH_BPM       = 170
ORIG_BPM     = 120
SPEEDUP      = HH_BPM / ORIG_BPM     # ~1.417x

# Frame counts for the rave drum pattern at HH_BPM
FRAMES_PER_BEAT = PAL_HZ * 60.0 / HH_BPM   # ~17.65
FRAMES_PER_8TH  = FRAMES_PER_BEAT / 2
FRAMES_PER_16TH = FRAMES_PER_BEAT / 4

# Waveform bits
WF_TRI, WF_SAW, WF_PULSE, WF_NOISE = 0x10, 0x20, 0x40, 0x80

# Voice envelopes
V1_AD, V1_SR = 0x05, 0x82   # bass: instant attack, fast decay, low sustain, short release — stabby
V2_AD, V2_SR = 0x07, 0xF8   # lead: short attack, sustained
V3_AD, V3_SR = 0x00, 0x09   # default drum env (overridden per-hit)

def midi_to_sid_freq(note):
    hz = 440.0 * 2 ** ((note - 69) / 12.0)
    return int(round(hz * (1 << 24) / PAL_CLK)) & 0xFFFF

def tempo_us(mid):
    for t in mid.tracks:
        for m in t:
            if m.type == 'set_tempo':
                return m.tempo
    return 500000

def extract_notes(mid, track_idx, pick='top', transpose=0):
    """Returns (start_frame, end_frame, midi_note), already sped up by SPEEDUP."""
    track = mid.tracks[track_idx]
    tick_to_frame = (tempo_us(mid) / mid.ticks_per_beat) * PAL_HZ / 1e6 / SPEEDUP

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
    spans = [(s, e, max(0, n + transpose)) for s, e, n in spans if e > s]
    return spans

# ---- Bouncy off-beat bass: derive from melody by playing root on every 8th gap ----
def build_bouncy_bass(lead_spans, total_frames):
    """Generate a happy-hardcore bouncy bass pattern.
    Each off-beat 8th note plays the current melody's root pitch (octave-down).
    Each stab is a short pulse hit (4 frames) then rest until next stab.
    """
    spans = []
    stab_len = max(3, int(round(FRAMES_PER_16TH * 0.9)))
    # Walk every 8th note tick and pick the melody note that's active there
    f = 0
    step = FRAMES_PER_8TH
    n_steps = int(total_frames / step) + 1
    for k in range(n_steps):
        # Off-beat 8ths only — skip the on-beat 8ths so the kick has room
        if k % 2 == 0:
            continue
        frame = int(round(k * step))
        if frame >= total_frames:
            break
        # Find which melody note is active at this frame
        active_note = 0
        for s, e, n in lead_spans:
            if s <= frame < e:
                active_note = n
                break
        if active_note == 0:
            continue
        # Bass = melody octave down (note - 12)
        bass_note = max(0, active_note - 12)
        spans.append((frame, frame + stab_len, bass_note))
    return spans

# ---- Drum pattern: 4-on-floor + snare 2&4 + 16th hats ----
def build_hh_drums(total_frames):
    """Returns list of (start_frame, drum_type) where drum_type is one of
    'kick','snare','hat'."""
    hits = []
    n_beats = int(total_frames / FRAMES_PER_BEAT) + 1
    for beat in range(n_beats):
        bf = int(round(beat * FRAMES_PER_BEAT))
        if bf >= total_frames: break
        hits.append((bf, 'kick'))
        # Snare on beats 2 and 4 (beat % 4 in 2 or 0... actually 1 and 3 in 0-indexed)
        if beat % 4 in (1, 3):
            hits.append((bf, 'snare'))
        # 16th hats — 4 per beat, but skip the one that's on the kick
        for sub in (1, 2, 3):
            hf = bf + int(round(sub * FRAMES_PER_16TH))
            if hf < total_frames:
                hits.append((hf, 'hat'))
    return hits

def drum_params(kind):
    # (freq_table_index, dur_frames, ad, sr)
    if kind == 'kick':
        return (2,  5, 0x00, 0x09)
    if kind == 'snare':
        return (36, 4, 0x00, 0x06)
    return (78, 2, 0x00, 0x04)  # hat: high, short

def build_v3_stream(drum_hits, total_frames):
    REST = (0, 0x80, V3_AD, V3_SR)
    timeline = [REST] * (total_frames + 2)
    for f, kind in drum_hits:
        if f >= total_frames: continue
        pitch, dur, ad, sr = drum_params(kind)
        for i in range(dur):
            if f + i < total_frames:
                timeline[f + i] = (pitch, 0x81, ad, sr)
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
    buf = bytearray()
    for dur, (note, ctrl, ad, sr) in events:
        if dur < 1: dur = 1
        while dur > 0xFFFF:
            buf += bytes([0xFF, 0xFF, note & 0x7F, ctrl, ad, sr])
            dur -= 0xFFFF
        buf += bytes([(dur >> 8) & 0xFF, dur & 0xFF, note & 0x7F, ctrl, ad, sr])
    buf += bytes([0, 0, 0, 0, 0, 0])
    return buf

def voice_stream_3byte(spans):
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
print(f"Loaded {MIDI_PATH}  ({mid.length:.1f}s @ orig BPM, target {HH_BPM} BPM)")
print(f"Speedup factor {SPEEDUP:.3f}x, FRAMES_PER_BEAT={FRAMES_PER_BEAT:.2f}")

lead = extract_notes(mid, LEAD_TRACK, pick='top')
total_f = max((e for _,e,_ in lead), default=0) + 100
bass = build_bouncy_bass(lead, total_f)
drums = build_hh_drums(total_f)
v3_events = build_v3_stream(drums, total_f)

v1_data = voice_stream_3byte(bass)
v2_data = voice_stream_3byte(lead)
v3_data = encode_v3(v3_events)

print(f"  lead T{LEAD_TRACK}: {len(lead)} spans, {len(v2_data)}B (covers {total_f/PAL_HZ:.1f}s)")
print(f"  bass: {len(bass)} stabs, {len(v1_data)}B")
print(f"  drums: {len(drums)} hits, {len(v3_data)}B")

# Frequency table
NOTE_LO, NOTE_HI = 12, 119
freq_lo, freq_hi = [], []
for n in range(NOTE_LO, NOTE_HI + 1):
    f = midi_to_sid_freq(n)
    freq_lo.append(f & 0xFF)
    freq_hi.append((f >> 8) & 0xFF)

def bytes_to_asm(name, data, per_line=16):
    out = [f"{name}:"]
    for i in range(0, len(data), per_line):
        chunk = data[i:i+per_line]
        out.append("    .byt " + ",".join(f"${b:02X}" for b in chunk))
    return "\n".join(out)

# ---- 6502 player ----
# V2 lead uses sawtooth with per-note filter cutoff envelope:
#   On new note: cutoff = $E0 (open)
#   Each frame: cutoff decays by FILT_DECAY toward $30 (closed)
# This produces the "wow" hoover sweep characteristic of happy hardcore.

asm = f"""
NOTE_LO = {NOTE_LO}
SID = $D400

ZP_V0   = $FB
ZP_V1   = $FD
ZP_V2   = $F7
ZP_CNT0 = $02
ZP_CNT1 = $04
ZP_CNT2 = $06
ZP_FILT_CUR = $08   ; current filter cutoff (FC HI)
ZP_FILT_TGT = $09   ; target (settle here)

*=$1000
    jmp init_routine
    jmp play_routine

; ================================================================
init_routine:
    sei
    lda #0
    ldx #$18
init_clr:
    sta SID,x
    dex
    bpl init_clr

    ; ADSRs
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

    ; V1 pulse width — narrow for stabby bass
    lda #$00
    sta SID+2
    lda #$04
    sta SID+3

    ; Filter — V2 routed, high resonance for hoover
    lda #$00
    sta SID+21          ; FC LO
    lda #$E0
    sta SID+22          ; FC HI — start open
    lda #$92
    sta SID+23          ; res=9, V2 routed
    lda #$1F
    sta SID+24          ; LP + vol max

    lda #$E0
    sta ZP_FILT_CUR
    lda #$40
    sta ZP_FILT_TGT

    ; Reset pointers/counters
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
    cli
    rts

; ================================================================
play_routine:
    jsr tick0
    jsr tick1
    jsr tick2
    jsr filter_env
    rts

; ---- Filter envelope: decay cutoff each frame toward target ----
filter_env:
    lda ZP_FILT_CUR
    cmp ZP_FILT_TGT
    beq fe_done
    bcc fe_up
    sec
    sbc #2
    cmp ZP_FILT_TGT
    bcs fe_store
    lda ZP_FILT_TGT
    jmp fe_store
fe_up:
    clc
    adc #1
fe_store:
    sta ZP_FILT_CUR
    sta SID+22
fe_done:
    rts

; ---- Voice 0 (bouncy bass) — pulse ----
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
    lda #${WF_PULSE:02X}
    sta SID+4
    lda #${WF_PULSE|1:02X}
    sta SID+4
    jmp f0adv
f0rest:
    lda #${WF_PULSE:02X}
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

; ---- Voice 1 (lead, saw + filter env reset on each note) ----
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
    sta SID+7
    lda freq_hi,x
    sta SID+8
    lda #${WF_SAW:02X}
    sta SID+11
    lda #${WF_SAW|1:02X}
    sta SID+11
    ; Reset filter cutoff to open — creates hoover sweep on each note
    lda #$E0
    sta ZP_FILT_CUR
    jmp f1adv
f1rest:
    lda #${WF_SAW:02X}
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

; ---- Voice 2 (drums, 6-byte events) ----
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
    lda (ZP_V2),y
    pha                ; push note
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
    iny
    lda (ZP_V2),y      ; ctrl
    pha                ; push ctrl
    iny
    lda (ZP_V2),y      ; ad
    sta SID+19
    iny
    lda (ZP_V2),y      ; sr
    sta SID+20
    ; Set freq from note (note is used as INDEX into freq table directly for drums)
    tsx
    lda $0102,x        ; note (below ctrl on stack)
    cmp #96
    bcc f2_note_ok
    lda #95
f2_note_ok:
    tax
    lda freq_lo,x
    sta SID+14
    lda freq_hi,x
    sta SID+15
    ; Gate-off, then gate-on for retrigger
    pla                ; ctrl
    pha
    and #$FE
    sta SID+18
    pla
    sta SID+18
    pla                ; discard note
    clc
    lda ZP_V2
    adc #6
    sta ZP_V2
    bcc f2done
    inc ZP_V2+1
f2done:
    rts

; ================================================================
{bytes_to_asm('freq_lo', freq_lo)}
{bytes_to_asm('freq_hi', freq_hi)}
{bytes_to_asm('v0_data', v1_data)}
{bytes_to_asm('v1_data', v2_data)}
{bytes_to_asm('v2_data', v3_data)}
"""

asm_path = '/tmp/freedhh.s'
prg_path = '/tmp/freedhh.prg'
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

def pad32(s):
    b = s.encode('ascii')[:31]
    return b + b'\0' * (32 - len(b))

header = b'PSID'
header += struct.pack('>H', 2)
header += struct.pack('>H', 0x7C)
header += struct.pack('>H', 0)
header += struct.pack('>H', 0x1000)
header += struct.pack('>H', 0x1003)
header += struct.pack('>H', 1)
header += struct.pack('>H', 1)
header += struct.pack('>I', 0)
header += pad32('FFD Happy Hardcore')
header += pad32('Gala / SID Rave Remix')
header += pad32('2026')
header += struct.pack('>H', 0x0000)
header += bytes([0, 0, 0, 0])
assert len(header) == 0x7C

with open(OUT_SID, 'wb') as f:
    f.write(header + prg)
print(f"Wrote {OUT_SID} ({len(header) + len(prg)} bytes)")
