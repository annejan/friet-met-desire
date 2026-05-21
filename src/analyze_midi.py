#!/usr/bin/env python3
"""Analyze each track of the MIDI and split into per-track files for identification."""
import mido, sys, os, collections
from copy import deepcopy

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(BASE, 'midi', 'Gala_Freed_From_Desire.mid')
OUTDIR = os.path.join(BASE, 'stems')
os.makedirs(OUTDIR, exist_ok=True)

mid = mido.MidiFile(SRC)
tempo = 500000
for t in mid.tracks:
    for m in t:
        if m.type == 'set_tempo':
            tempo = m.tempo
            break

sec_per_tick = (tempo / mid.ticks_per_beat) / 1e6
print(f"Source: {SRC}")
print(f"Length: {mid.length:.1f}s, tracks: {len(mid.tracks)}, tpb: {mid.ticks_per_beat}")
print(f"BPM: {60_000_000 / tempo:.1f}")
print()

NOTE_NAMES = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']
def note_name(n):
    return f"{NOTE_NAMES[n % 12]}{n // 12 - 1}"

# Write each track + meta/tempo tracks as a standalone MIDI file
def write_track_file(mid, track_idx, out_path):
    out = mido.MidiFile(ticks_per_beat=mid.ticks_per_beat, type=1)
    # Track 0 typically has tempo
    out.tracks.append(deepcopy(mid.tracks[0]))
    if track_idx != 0:
        out.tracks.append(deepcopy(mid.tracks[track_idx]))
    out.save(out_path)

for i, track in enumerate(mid.tracks):
    notes = []
    t = 0
    for m in track:
        t += m.time
        if m.type == 'note_on' and m.velocity > 0:
            notes.append((t * sec_per_tick, m.note, m.velocity))
    if not notes:
        continue
    chans = sorted(set(m.channel for m in track if hasattr(m, 'channel')))
    is_drum = 9 in chans
    progs = [m.program for m in track if m.type == 'program_change']
    name = (track.name or '').strip()

    # Range, density, mono/poly
    pitches = [n for _, n, _ in notes]
    min_p, max_p = min(pitches), max(pitches)
    duration = notes[-1][0] - notes[0][0]
    density = len(notes) / max(1, duration)

    # Polyphony estimation: count simultaneous note_on events within small windows
    active = {}
    max_poly = 0
    for m in track:
        if m.type == 'note_on' and m.velocity > 0:
            active[m.note] = True
            max_poly = max(max_poly, len(active))
        elif m.type in ('note_off',) or (m.type == 'note_on' and m.velocity == 0):
            active.pop(m.note, None)

    # Top pitches by usage
    cnt = collections.Counter(pitches)
    top = cnt.most_common(8)

    # Rhythm: gap histogram between consecutive note_ons (in seconds, rounded to 16th @ 120BPM)
    gaps = []
    for j in range(1, min(80, len(notes))):
        g = notes[j][0] - notes[j-1][0]
        gaps.append(round(g, 2))
    gap_hist = collections.Counter(gaps).most_common(5)

    print(f"=== T{i} {'[DRUM] ' if is_drum else ''}{name} ===")
    print(f"  notes={len(notes)} ch={chans} prog={progs}")
    print(f"  first_note={notes[0][0]:.1f}s last_note={notes[-1][0]:.1f}s duration={duration:.1f}s")
    print(f"  pitch range: {note_name(min_p)}({min_p}) .. {note_name(max_p)}({max_p})  span={max_p-min_p} semitones")
    print(f"  density: {density:.1f} notes/sec, max polyphony: {max_poly}")
    print(f"  top pitches: " + ", ".join(f"{note_name(n)}({c})" for n,c in top))
    print(f"  common gaps (s): {gap_hist}")
    # Print rhythmic pattern of first ~30 notes (visualize)
    if not is_drum and len(notes) > 5:
        # ASCII contour: pitches relative to median
        med = sorted(pitches)[len(pitches)//2]
        contour = ''.join(['^' if p > med + 2 else ('v' if p < med - 2 else '-') for _, p, _ in notes[:60]])
        print(f"  contour (first 60, ^=up v=down -=middle): {contour}")
    # Save per-track stem
    safe_name = (name or "unnamed").replace(' ', '_').replace('/', '_')
    prog_label = str(progs[0]) if progs else "-"
    out_path = os.path.join(OUTDIR, f'T{i:02d}_{safe_name}_prog{prog_label}.mid')
    write_track_file(mid, i, out_path)
    print(f"  stem -> {out_path}")
    print()
