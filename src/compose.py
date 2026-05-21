#!/usr/bin/env python3
"""Phase 2 of the cleanroom pipeline.

Reads docs/song_spec.yaml (the abstract spec) and writes
docs/composition.yaml (a concrete arrangement in happy-hardcore style).

Cleanroom rule: this script must NEVER open or read any MIDI file. It only
sees the structured spec produced by phase 1.
"""
import yaml, os, sys, random

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPEC_PATH = sys.argv[1] if len(sys.argv) > 1 else os.path.join(BASE, 'docs', 'song_spec.yaml')
COMP_PATH = sys.argv[2] if len(sys.argv) > 2 else os.path.join(BASE, 'docs', 'composition.yaml')

# Happy hardcore target tempo (most HH tunes sit at 170–180)
HH_BPM        = 175
PAL_HZ        = 50.0

NOTE_NAMES = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']
def name_to_pc(s):
    s = s.strip().rstrip('b').upper().replace('FLAT','b')
    if s.endswith('B') and len(s) > 1: s = s[:-1] + 'b'  # tolerate "Bb" vs "B"
    if 'b' in s:
        # convert e.g. "Bb" -> A#
        base = s[0]; flat = True
    else:
        base = s[0]; flat = False
    pc = NOTE_NAMES.index(base.upper())
    if '#' in s: pc = (pc + 1) % 12
    if flat:    pc = (pc - 1) % 12
    return pc

def midi_note(name_oct):
    """E.g. 'D2' -> 38."""
    # Split letter+# from octave
    i = 1 + (1 if name_oct[1:2] == '#' else 0)
    pc = name_to_pc(name_oct[:i])
    octv = int(name_oct[i:])
    return (octv + 1) * 12 + pc

# ----- scale generators (within an octave) -----
SCALES = {
    'minor':       [0, 2, 3, 5, 7, 8, 10],
    'natural_minor': [0, 2, 3, 5, 7, 8, 10],
    'harmonic_minor': [0, 2, 3, 5, 7, 8, 11],
    'major':       [0, 2, 4, 5, 7, 9, 11],
}

def scale_pitches(root_pc, mode, octave_range=(2, 6)):
    intervals = SCALES.get(mode, SCALES['minor'])
    out = []
    for octv in range(octave_range[0], octave_range[1]):
        for i in intervals:
            out.append((octv + 1) * 12 + (root_pc + i) % 12 +
                       (0 if (root_pc + i) < 12 else 12))
    return sorted(set(out))

# ----- composition primitives -----
def pattern_to_positions(pat):
    """'X...X...X..X' -> [0,4,8,11]"""
    return [i for i, c in enumerate(pat) if c == 'X']

def beats_to_frames(beats, bpm):
    return beats * 60.0 / bpm * PAL_HZ

# ----- main composer -----
def main():
    with open(SPEC_PATH) as f:
        spec = yaml.safe_load(f)

    random.seed(42)  # reproducible

    bpm = HH_BPM
    fpbar = beats_to_frames(4, bpm)        # frames per 4/4 bar
    fpbeat = fpbar / 4
    fp16  = fpbar / 16

    root_pc = name_to_pc(spec['key']['root'])
    mode = spec['key']['mode']
    scale = SCALES.get(mode, SCALES['minor'])
    bass_root = root_pc + 12 * 3   # D3-ish for HH bass
    if bass_root < 36: bass_root = 36
    # Use Dm pentatonic-ish for lead (cleaner happy-hardcore feel)
    lead_root_pc = root_pc
    melody_octave = 5  # E5/D5 range — bright lead

    # Section plan (happy hardcore layout)
    sections = [
        # (name, bars, intensity 0..1, fill last bar)
        ('intro',     4, 0.4, False),
        ('build',     4, 0.7, True),
        ('drop_a',    8, 1.0, False),
        ('breakdown', 4, 0.5, False),
        ('build2',    4, 0.7, True),
        ('drop_b',    8, 1.0, False),
        ('outro',     4, 0.6, False),
    ]
    total_bars = sum(b for _, b, _, _ in sections)

    # Chord progression (i - VI - III - VII in natural minor)
    # In D minor: Dm - Bb - F - C
    chord_cycle = [(root_pc + 0)  % 12,  # i
                   (root_pc + 8)  % 12,  # VI
                   (root_pc + 5)  % 12,  # IV (substituting for cleaner HH)
                   (root_pc + 10) % 12]  # VII

    # ---- helpers ----
    bass_pat = pattern_to_positions(spec['elements']['bass']['rhythm_1bar_16ths'])
    # Drum patterns: kick from spec, snare on 2&4, 16th hats
    kick_pat  = pattern_to_positions(spec['elements']['drums'].get('kick',  'X...X...X...X...'))
    # Use clap (2&4) as the snare slot — closer to HH backbeat
    snare_pat = pattern_to_positions(spec['elements']['drums'].get('clap',  '....X.......X...'))
    hat_pat   = list(range(0, 16, 2))  # offbeat-style hats every 8th
    crash_pos = 0

    # Use the spec melody contour as a *seed*. Walk through it and snap to scale.
    contour = spec['elements']['melody'].get('contour_first32', [])
    # Lead starting pitch
    lead_pitch = 12 * (melody_octave + 1) + lead_root_pc + 5  # ~A4-ish for D minor (=Dm: D scale degree 5)
    # Normalize: every 16th step in the contour roughly = +1/-1 scale step

    # Output event lists with frame timing
    bass_events = []
    lead_events = []
    drum_events = []
    fx_events = []  # crashes etc.

    cur_bar = 0
    contour_idx = 0
    for sec_idx, (name, bars, intensity, fill_last) in enumerate(sections):
        for b in range(bars):
            global_bar = cur_bar + b
            chord_root = chord_cycle[global_bar % len(chord_cycle)]
            # Crash at start of each drop section
            if b == 0 and name.startswith('drop') or (b == 0 and name == 'breakdown'):
                fx_events.append({
                    'kind': 'crash',
                    'frame': int(round(global_bar * fpbar)),
                })
            # --- drums ---
            if intensity >= 0.4:
                for p in kick_pat:
                    drum_events.append({
                        'kind': 'kick',
                        'frame': int(round(global_bar * fpbar + p * fp16)),
                    })
            if intensity >= 0.5:
                for p in snare_pat:
                    drum_events.append({
                        'kind': 'snare',
                        'frame': int(round(global_bar * fpbar + p * fp16)),
                    })
            if intensity >= 0.6:
                for p in hat_pat:
                    drum_events.append({
                        'kind': 'hat',
                        'frame': int(round(global_bar * fpbar + p * fp16)),
                    })
            # Build snare roll on the last bar of a build
            if fill_last and b == bars - 1:
                for p in range(8, 16):
                    drum_events.append({
                        'kind': 'snare',
                        'frame': int(round(global_bar * fpbar + p * fp16)),
                    })
            # --- bass --- (intensity-gated; off during breakdown)
            if name != 'breakdown' and intensity >= 0.5:
                # Use spec's bass rhythm. Bass plays the chord root at bass octave.
                root_note = bass_root + ((chord_root - root_pc) % 12)
                # Octave-jump pattern: alternate root and root+12 within the bar (rave feel)
                for j, p in enumerate(bass_pat):
                    note = root_note + (12 if (j % 4) in (2, 3) else 0)
                    bass_events.append({
                        'frame': int(round(global_bar * fpbar + p * fp16)),
                        'note':  note,
                        'dur_frames': max(2, int(fp16 * 0.9)),
                    })
            # --- lead --- (only during drops; rest during intro/build/breakdown)
            if name.startswith('drop'):
                # Stepwise contour-driven melody using D-minor scale notes
                lead_root_midi = 12 * (melody_octave + 1) + lead_root_pc
                lead_scale = [lead_root_midi + i for i in scale] + \
                             [lead_root_midi + 12 + i for i in scale]
                # Place 8 notes per bar (8th-note melody)
                for sub in range(8):
                    pos16 = sub * 2
                    # Pick next scale degree using contour delta (snapped)
                    if contour_idx < len(contour):
                        delta = contour[contour_idx]
                        contour_idx += 1
                        # Snap to ±1 scale step roughly
                        step = 0
                        if delta > 1: step = 1
                        elif delta < -1: step = -1
                        idx = lead_scale.index(lead_pitch) if lead_pitch in lead_scale else 3
                        idx = max(0, min(len(lead_scale)-1, idx + step))
                        lead_pitch = lead_scale[idx]
                    lead_events.append({
                        'frame': int(round(global_bar * fpbar + pos16 * fp16)),
                        'note':  lead_pitch,
                        'dur_frames': max(2, int(fp16 * 1.8)),
                    })
        cur_bar += bars

    # Final composition
    end_frame = int(round(total_bars * fpbar)) + 50
    composition = {
        'title':       'Friet From Desire — Happy Hardcore Remix',
        'derived_from': spec.get('source_midi', 'unknown'),
        'bpm':         bpm,
        'key':         {'root': NOTE_NAMES[root_pc], 'mode': mode},
        'length_bars': total_bars,
        'length_frames': end_frame,
        'sections':    [{'name': n, 'bars': b, 'intensity': i} for n, b, i, _ in sections],
        'voices': {
            'bass':  sorted(bass_events, key=lambda e: e['frame']),
            'lead':  sorted(lead_events, key=lambda e: e['frame']),
            'drums': sorted(drum_events + fx_events, key=lambda e: e['frame']),
        }
    }
    os.makedirs(os.path.dirname(COMP_PATH), exist_ok=True)
    with open(COMP_PATH, 'w') as f:
        f.write("# Concrete arrangement (Phase 2 of cleanroom remix pipeline).\n")
        f.write("# Generated from docs/song_spec.yaml — the synth never reads the source MIDI.\n\n")
        yaml.safe_dump(composition, f, sort_keys=False, default_flow_style=False, width=120)
    print(f"Wrote {COMP_PATH}")
    print(f"  {bpm} BPM, {total_bars} bars, ~{end_frame / PAL_HZ:.1f}s")
    print(f"  bass events:  {len(bass_events)}")
    print(f"  lead events:  {len(lead_events)}")
    print(f"  drum events:  {len(drum_events) + len(fx_events)}")

if __name__ == '__main__':
    main()
