#!/usr/bin/env python3
"""Build the stand-alone C64 .prg that plays out/friet_clean.sid with a
synchronised lyrics ticker.

Pipeline:
  1. Extract the raw SID body from out/friet_clean.sid (drop the PSID
     header and the PRG load-address prefix).
  2. Build a binary lyric table from docs/melody_lyrics.yaml, lyric
     lines remapped onto the OUTPUT timeline via the same SEGMENTS
     table compose.py uses.
  3. Drop those binaries plus two banner strings next to
     src/player/friet_player.asm and invoke KickAssembler.

Output: out/friet_player.prg (loads at $0801, runs via SYS 2064).
"""
import os, sys, struct, subprocess, yaml

BASE         = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SID_PATH     = os.path.join(BASE, 'out', 'friet_clean.sid')
LYRICS_PATH  = os.path.join(BASE, 'docs', 'melody_lyrics.yaml')
ASM_PATH     = os.path.join(BASE, 'src', 'player', 'friet_player.asm')
PLAYER_DIR   = os.path.dirname(ASM_PATH)
OUT_PRG      = os.path.join(BASE, 'out', 'friet_player.prg')
KICKASS_JAR  = os.path.join(BASE, 'kickass', 'KickAss.jar')

# ---- 1. SID body ------------------------------------------------------
with open(SID_PATH, 'rb') as f:
    sid = f.read()
assert sid[:4] == b'PSID', "not a PSID file"
psid_data_offset = struct.unpack('>H', sid[6:8])[0]
psid_load_addr   = struct.unpack('>H', sid[8:10])[0]
sid_init = struct.unpack('>H', sid[10:12])[0]
sid_play = struct.unpack('>H', sid[12:14])[0]
body = sid[psid_data_offset:]
if psid_load_addr == 0:
    sid_load_addr = body[0] | (body[1] << 8)
    sid_code      = body[2:]
else:
    sid_load_addr = psid_load_addr
    sid_code      = body
assert sid_load_addr == 0x1000, f"SID expects $1000 load addr, got ${sid_load_addr:04X}"
print(f"SID load=${sid_load_addr:04X} size={len(sid_code)} bytes "
      f"(init=${sid_init:04X} play=${sid_play:04X})")
with open(os.path.join(PLAYER_DIR, 'sid_body.bin'), 'wb') as f:
    f.write(sid_code)

# ---- 2. Lyrics table --------------------------------------------------
SEGMENTS = [
    (  0.0,  21.5, 'intro'),
    ( 21.5,  54.5, 'verse1'),
    ( 54.5,  88.0, 'prechorus1'),
    ( 88.0, 117.5, 'chorus1'),
    (117.5, 149.5, 'postchorus_nana'),
    (149.5, 153.5, 'breathe1'),
    ( 88.0, 117.5, 'chorus2'),
    (149.5, 153.5, 'breathe2'),
    ( 88.0, 117.5, 'chorus3'),
]
out_offsets = []
cur = 0.0
for s, e, _ in SEGMENTS:
    out_offsets.append(cur)
    cur += e - s

def remap(src_beat):
    for (s, e, _), out_s in zip(SEGMENTS, out_offsets):
        if s <= src_beat < e:
            yield out_s + (src_beat - s)

with open(LYRICS_PATH) as f:
    ly = yaml.safe_load(f)
syls = ly['lyrics_aligned']
src_bpm = ly.get('source_bpm', 120)
FRAMES_PER_BEAT = 50.0 * 60 / src_bpm   # 25 fr/beat at 120 BPM

# Group syllables into lines using inter-syllable gaps > 1.5 beats.
LINE_GAP_BEATS = 1.5
lines = []
cur_syls, cur_start = [], None
for s in syls:
    if s['pitch'] is None: continue
    if not cur_syls:
        cur_syls, cur_start = [s], s['beat']
        continue
    if s['beat'] - cur_syls[-1]['beat'] > LINE_GAP_BEATS:
        lines.append((cur_start, cur_syls))
        cur_syls, cur_start = [s], s['beat']
    else:
        cur_syls.append(s)
if cur_syls:
    lines.append((cur_start, cur_syls))

events = []   # (frame, text)
for line_beat, ss in lines:
    text = ''.join(s['syllable'] for s in ss).strip()
    for out_beat in remap(line_beat):
        events.append((int(round(out_beat * FRAMES_PER_BEAT)), text))
events.sort()
print(f"{len(syls)} syllables -> {len(lines)} lyric lines -> "
      f"{len(events)} on-screen lyric updates")

# ---- Text -> C64 screen codes -----------------------------------------
def to_screen(s, width=40):
    out = []
    for c in s.upper()[:width]:
        o = ord(c)
        if 0x41 <= o <= 0x5A:
            out.append(o - 0x40)            # A-Z -> $01-$1A
        elif o == 0x20:
            out.append(0x20)
        elif 0x30 <= o <= 0x39:
            out.append(o)
        elif o in (44, 46, 33, 39, 47, 45):  # , . ! ' / -
            out.append(o)
        else:
            out.append(0x20)
    return bytes(out)

# Banners
with open(os.path.join(PLAYER_DIR, 'banner_top.bin'), 'wb') as f:
    f.write(to_screen("FRIET VAN DESIRE -- DEFEEST AT X2026"))
with open(os.path.join(PLAYER_DIR, 'banner_bottom.bin'), 'wb') as f:
    f.write(to_screen("KLOOT & ANUS / DEFEEST / 2026"))

# Lyric table — sequence of (frame_lo, frame_hi, len, screen_bytes...)
buf = bytearray()
for frame, text in events:
    codes = to_screen(text)
    buf += bytes([frame & 0xFF, (frame >> 8) & 0xFF, len(codes)]) + codes
with open(os.path.join(PLAYER_DIR, 'lyric_table.bin'), 'wb') as f:
    f.write(buf)
print(f"Lyric table: {len(buf)} bytes")

# ---- 3. Invoke KickAssembler ------------------------------------------
if not os.path.exists(KICKASS_JAR):
    print(f"KickAss.jar not found at {KICKASS_JAR}")
    sys.exit(1)
r = subprocess.run(
    ['java', '-jar', KICKASS_JAR, ASM_PATH, '-o', OUT_PRG],
    capture_output=True, text=True,
)
print(r.stdout)
if r.returncode != 0:
    print(r.stderr)
    sys.exit(1)
size = os.path.getsize(OUT_PRG)
print(f"Wrote {OUT_PRG} ({size} bytes)")
