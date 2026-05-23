#!/usr/bin/env python3
"""Phase 3 of the cleanroom pipeline.

Reads docs/composition.yaml (the concrete arrangement) and emits a PSID v2
file at out/friet_clean.sid. This script is the "implementation team":
it must not open any MIDI file. It only consumes the composition.

The player code mirrors the happy-hardcore design:
  V1 bass  : pulse stabs, short envelope, narrow pulse width
  V2 lead  : sawtooth, per-note filter cutoff envelope ("hoover" sweep),
             vibrato off (the filter wow does the work)
  V3 drums : noise hits with per-event ADSR; kick/snare/hat/crash
"""
import yaml, struct, subprocess, os, sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COMP_PATH = sys.argv[1] if len(sys.argv) > 1 else os.path.join(BASE, 'docs', 'composition.yaml')
OUT_SID   = sys.argv[2] if len(sys.argv) > 2 else os.path.join(BASE, 'out', 'friet_clean.sid')

PAL_CLK = 985248.0
PAL_HZ  = 50.0

WF_TRI, WF_SAW, WF_PULSE, WF_NOISE = 0x10, 0x20, 0x40, 0x80
# Bass: instant attack, hold sustain so each stab has body, fast release
V1_AD, V1_SR = 0x08, 0xC4
# Lead (triangle = vocal-ish tone): gentle 24 ms attack so legato pitch
# changes don't click, full sustain, medium release for breathy phrase tails.
V2_AD, V2_SR = 0x12, 0xF6

# Drum table: kind -> (freq_table_index, dur_frames, ad, sr)
# Long decay times (AD high nibble) so the envelope actually rings out
# instead of decaying to silence in 6 ms. Sustain=0 with release=0 means
# the envelope decays naturally toward 0 at the decay rate during gate-on.
DRUM_KIT = {
    'kick':  (2,  6, 0x09, 0x00),   # decay 720 ms — full "boom" body
    'snare': (36, 5, 0x07, 0x00),   # decay 168 ms — sharp snap
    'hat':   (78, 2, 0x02, 0x00),   # decay  24 ms — tick
    'crash': (60, 70, 0x0B, 0xC4),  # ~800 ms slow attack -> sustained at $C
                                     # -> short release. Proper SWELL: you hear
                                     # the noise *rise* into the next section
                                     # instead of a quick tick.
}

NOTE_LO, NOTE_HI = 12, 119

def midi_to_sid_freq(note):
    hz = 440.0 * 2 ** ((note - 69) / 12.0)
    return int(round(hz * (1 << 24) / PAL_CLK)) & 0xFFFF

def events_to_spans(events):
    """List of {frame, note, dur_frames} -> list of (start, end, note) spans
    with explicit rests between events."""
    if not events:
        return []
    out = []
    last_end = 0
    for ev in events:
        s = ev['frame']
        e = s + ev.get('dur_frames', 5)
        n = ev['note']
        if s > last_end:
            out.append((last_end, s, 0))  # rest
        out.append((s, e, n))
        last_end = e
    return out

def encode_voice_3byte(spans, total_frames):
    """Encode (start,end,note) spans as 3-byte events: dur_hi, dur_lo, note."""
    buf = bytearray()
    last_end = 0
    for s, e, n in spans:
        if s > last_end:
            dur = s - last_end
            while dur > 0xFFFF:
                buf += bytes([0xFF, 0xFF, 0])
                dur -= 0xFFFF
            buf += bytes([(dur >> 8) & 0xFF, dur & 0xFF, 0])
        dur = e - s
        if dur < 1: dur = 1
        while dur > 0xFFFF:
            buf += bytes([0xFF, 0xFF, n & 0x7F])
            dur -= 0xFFFF
        buf += bytes([(dur >> 8) & 0xFF, dur & 0xFF, n & 0x7F])
        last_end = e
    # Pad tail with rest to total_frames
    if total_frames > last_end:
        dur = total_frames - last_end
        while dur > 0xFFFF:
            buf += bytes([0xFF, 0xFF, 0])
            dur -= 0xFFFF
        if dur > 0:
            buf += bytes([(dur >> 8) & 0xFF, dur & 0xFF, 0])
    buf += bytes([0, 0, 0])  # loop sentinel
    return buf

def build_drum_timeline(drum_events, total_frames):
    """List of {frame, kind} -> RLE-compressed (dur, note, ctrl, ad, sr) events."""
    REST = (0, 0x80, 0x00, 0x09)
    timeline = [REST] * (total_frames + 2)
    for ev in sorted(drum_events, key=lambda e: e['frame']):
        kind = ev.get('kind', 'hat')
        if kind not in DRUM_KIT: continue
        pitch, dur, ad, sr = DRUM_KIT[kind]
        f = ev['frame']
        for i in range(dur):
            if f + i < total_frames:
                timeline[f + i] = (pitch, 0x81, ad, sr)
        if f + dur < total_frames:
            timeline[f + dur] = (pitch, 0x80, ad, sr)
    # RLE
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
    """6-byte events: dur_hi, dur_lo, note, ctrl, ad, sr."""
    buf = bytearray()
    for dur, (note, ctrl, ad, sr) in events:
        if dur < 1: dur = 1
        while dur > 0xFFFF:
            buf += bytes([0xFF, 0xFF, note & 0x7F, ctrl, ad, sr])
            dur -= 0xFFFF
        buf += bytes([(dur >> 8) & 0xFF, dur & 0xFF, note & 0x7F, ctrl, ad, sr])
    buf += bytes([0, 0, 0, 0, 0, 0])  # loop sentinel
    return buf

# -------------------- main --------------------
def main():
    with open(COMP_PATH) as f:
        comp = yaml.safe_load(f)
    total_frames = comp['length_frames']
    title = comp.get('title', 'Friet From Desire')[:31]
    bpm   = comp.get('bpm', 175)

    bass_spans = events_to_spans(comp['voices']['bass'])
    lead_spans = events_to_spans(comp['voices']['lead'])

    v1_data = encode_voice_3byte(bass_spans, total_frames)
    v2_data = encode_voice_3byte(lead_spans, total_frames)
    v3_data = encode_v3(build_drum_timeline(comp['voices']['drums'], total_frames))

    print(f"  bass : {len(comp['voices']['bass']):4d} events -> {len(v1_data)}B")
    print(f"  lead : {len(comp['voices']['lead']):4d} events -> {len(v2_data)}B")
    print(f"  drums: {len(comp['voices']['drums']):4d} events -> {len(v3_data)}B")

    # Frequency table
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

    asm = f"""
NOTE_LO = {NOTE_LO}
SID = $D400

ZP_V0   = $FB
ZP_V1   = $FD
ZP_V2   = $F7
ZP_CNT0 = $02
ZP_CNT1 = $04
ZP_CNT2 = $06
ZP_FILT_CUR = $08
ZP_FILT_TGT = $09
ZP_V2_LAST = $0A         ; last lead note played (0 = rest); drives legato

*=$1000
    jmp init_routine
    jmp play_routine

init_routine:
    sei
    lda #0
    ldx #$18
init_clr:
    sta SID,x
    dex
    bpl init_clr
    lda #${V1_AD:02X}
    sta SID+5
    lda #${V1_SR:02X}
    sta SID+6
    lda #${V2_AD:02X}
    sta SID+12
    lda #${V2_SR:02X}
    sta SID+13
    ; V1 pulse width — wider for fatter bass body
    lda #$00
    sta SID+2
    lda #$08
    sta SID+3
    ; V2 pulse width — 50% duty for a chirpy square-wave chiptune lead
    lda #$00
    sta SID+9           ; V2 PW LO
    lda #$08
    sta SID+10          ; V2 PW HI
    ; Filter — completely OFF. The lead is a clean triangle ("singer" tone)
    ; and the bass is pulse; neither benefits from the resonant LP that was
    ; previously eating the vocal.
    lda #$00
    sta SID+21
    sta SID+22
    sta SID+23
    lda #$0F
    sta SID+24          ; volume max, no filter mode
    lda #$00
    sta ZP_FILT_CUR
    sta ZP_FILT_TGT
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
    sta ZP_V2_LAST
    cli
    rts

play_routine:
    jsr tick0
    jsr tick1
    jsr tick2
    jsr filter_env
    rts

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
    lda (ZP_V1),y         ; A = note (0 means rest)
    pha                   ; preserve note across sentinel check
    lda ZP_CNT1
    ora ZP_CNT1+1
    bne f1go
    pla                   ; sentinel: discard note, loop pointer
    lda #<v1_data
    sta ZP_V1
    lda #>v1_data
    sta ZP_V1+1
    rts
f1go:
    pla                   ; A = note
    cmp #0
    beq f1rest_path

    ; NOTE event — always set frequency
    tax                   ; X = note (preserve raw note for compare/stash)
    sec
    sbc #NOTE_LO
    tay
    lda freq_lo,y
    sta SID+7
    lda freq_hi,y
    sta SID+8

    ; Legato decision:
    ;   - same pitch as last  -> retrigger gate (articulate "stutter")
    ;   - last was rest       -> retrigger gate (phrase entry)
    ;   - else (pitch change) -> LEGATO: keep gate on, only freq changes
    cpx ZP_V2_LAST
    beq f1retrig
    lda ZP_V2_LAST
    beq f1retrig
    jmp f1stash
f1retrig:
    lda #${WF_TRI:02X}
    sta SID+11
    lda #${WF_TRI|1:02X}
    sta SID+11
f1stash:
    stx ZP_V2_LAST
    jmp f1adv

f1rest_path:
    ; Drop gate so the envelope releases between phrases.
    lda #${WF_TRI:02X}
    sta SID+11
    lda #0
    sta ZP_V2_LAST
f1adv:
    clc
    lda ZP_V1
    adc #3
    sta ZP_V1
    bcc f1done
    inc ZP_V1+1
f1done:
    rts

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
    iny
    lda (ZP_V2),y      ; ctrl
    pha
    iny
    lda (ZP_V2),y      ; ad
    sta SID+19
    iny
    lda (ZP_V2),y      ; sr
    sta SID+20
    tsx
    lda $0102,x        ; peek note (under ctrl)
    cmp #96
    bcc f2_note_ok
    lda #95
f2_note_ok:
    tax
    lda freq_lo,x
    sta SID+14
    lda freq_hi,x
    sta SID+15
    pla                ; ctrl
    pha
    and #$FE
    sta SID+18
    pla
    sta SID+18
    pla                ; pop note
    clc
    lda ZP_V2
    adc #6
    sta ZP_V2
    bcc f2done
    inc ZP_V2+1
f2done:
    rts

{bytes_to_asm('freq_lo', freq_lo)}
{bytes_to_asm('freq_hi', freq_hi)}
{bytes_to_asm('v0_data', v1_data)}
{bytes_to_asm('v1_data', v2_data)}
{bytes_to_asm('v2_data', v3_data)}
"""
    asm_path = '/tmp/friet_clean.s'
    prg_path = '/tmp/friet_clean.prg'
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
    prg = bytes([0x00, 0x10]) + prg
    print(f"Code load=$1000 size={len(prg)-2} bytes")

    def pad32(s):
        b = s.encode('ascii', errors='replace')[:31]
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
    # PSID metadata for the deFEEST / X2026 release.
    # Title is the song title (≤31 chars); Author = scene handles; Released
    # is "YYYY <PARTY>". Truncated automatically by pad32.
    header += pad32('Friet van Desire')
    header += pad32('Kloot & Anus / deFEEST')
    header += pad32('2026 X / deFEEST')
    header += struct.pack('>H', 0x0000)
    header += bytes([0, 0, 0, 0])
    assert len(header) == 0x7C
    os.makedirs(os.path.dirname(OUT_SID), exist_ok=True)
    with open(OUT_SID, 'wb') as f:
        f.write(header + prg)
    print(f"Wrote {OUT_SID} ({len(header) + len(prg)} bytes)")

if __name__ == '__main__':
    main()
