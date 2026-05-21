#!/usr/bin/env python3
"""Phase 1 of the cleanroom pipeline.

Reads the source MIDIs and writes an abstract specification of the song to
`docs/song_spec.yaml`. The spec describes the song musically (tempo, key,
section structure, rhythmic patterns, chord progression, drum grid) without
embedding any raw MIDI data.

After this script runs, the composer (phase 2) and synthesiser (phase 3) must
read ONLY the spec — never the MIDI. That's the cleanroom separation.
"""
import mido, yaml, os, sys, collections, statistics

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MIDI_PATH  = sys.argv[1] if len(sys.argv) > 1 else os.path.join(BASE, 'midi', 'Gala_Freed_From_Desire.mid')
SPEC_PATH  = sys.argv[2] if len(sys.argv) > 2 else os.path.join(BASE, 'docs', 'song_spec.yaml')

# Roles already established by analyze_midi.py (cross-checked against song memory)
ROLE = {
    5:  'bass',     # iconic synth bassline, D2-F3
    6:  'chord',    # 3-octave D arpeggio (chord stabs)
    7:  'melody',   # vocal substitute, A4-F5
    11: 'hook',     # chorus "na-na" Saw.Lead
    13: 'drums',
}

NOTE_NAMES = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']
def note_name(n):
    return f"{NOTE_NAMES[n % 12]}{n // 12 - 1}"

# ----------------------------- helpers --------------------------------
def tempo_us(mid):
    for t in mid.tracks:
        for m in t:
            if m.type == 'set_tempo':
                return m.tempo
    return 500000

def note_events(track):
    """List of (abs_tick, type, note) where type is 'on'/'off'."""
    out = []
    t = 0
    for m in track:
        t += m.time
        if m.type == 'note_on' and m.velocity > 0:
            out.append((t, 'on', m.note))
        elif m.type == 'note_off' or (m.type == 'note_on' and m.velocity == 0):
            out.append((t, 'off', m.note))
    return out

def detect_key(all_notes):
    """Estimate key by pitch-class histogram + Krumhansl-Schmuckler-lite.
    all_notes: iterable of MIDI note numbers (non-drum only)."""
    KEYS = {
        'major':  [6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88],
        'minor':  [6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17],
    }
    pc = [0]*12
    for n in all_notes:
        pc[n % 12] += 1
    total = sum(pc) or 1
    pc = [v/total for v in pc]
    best = None
    for mode, profile in KEYS.items():
        for root in range(12):
            score = sum(pc[(root + i) % 12] * profile[i] for i in range(12))
            if best is None or score > best[0]:
                best = (score, root, mode)
    return {'root': NOTE_NAMES[best[1]].replace('#','#'), 'mode': best[2]}

# ------------------------- pattern extraction -------------------------
def rhythm_grid(events_on_ticks, ticks_per_bar, bar_subdiv=16):
    """Find the most-common single-bar rhythmic pattern.
    Convert each bar's note_on positions into a bit-tuple, then return the
    bit-tuple that appears most often. This produces a true representative
    bar rather than a union of all positions ever hit."""
    if not events_on_ticks:
        return [0] * bar_subdiv
    step = ticks_per_bar / bar_subdiv
    by_bar = collections.defaultdict(set)
    for t in events_on_ticks:
        bar = int(t // ticks_per_bar)
        pos = int(round((t % ticks_per_bar) / step)) % bar_subdiv
        by_bar[bar].add(pos)
    # Skip empty bars
    bar_patterns = [tuple(sorted(positions)) for positions in by_bar.values() if positions]
    if not bar_patterns:
        return [0] * bar_subdiv
    most_common, _ = collections.Counter(bar_patterns).most_common(1)[0]
    return [1 if i in most_common else 0 for i in range(bar_subdiv)]

def pattern_to_string(pattern):
    """[1,0,0,0,1,...] -> 'X...X...X...X...'"""
    return ''.join('X' if x else '.' for x in pattern)

def melodic_contour(events, max_notes=32):
    """Reduce a sequence of pitches to relative-interval contour."""
    pitches = [n for _, kind, n in events if kind == 'on'][:max_notes]
    if len(pitches) < 2:
        return []
    return [pitches[i] - pitches[i-1] for i in range(1, len(pitches))]

def chord_roots_per_bar(events, ticks_per_bar, n_bars):
    """Given chord-arpeggio events, take the LOWEST note within each bar
    as the implied chord root. Returns list of note names (octave-stripped)."""
    by_bar = collections.defaultdict(list)
    for t, kind, n in events:
        if kind == 'on':
            bar = int(t // ticks_per_bar)
            by_bar[bar].append(n)
    roots = []
    for b in range(n_bars):
        if by_bar[b]:
            lo = min(by_bar[b])
            roots.append(NOTE_NAMES[lo % 12])
        else:
            roots.append(None)
    return roots

def compress_chord_progression(roots):
    """Find the shortest repeating chord cycle within the bar-by-bar root list."""
    clean = [r for r in roots if r is not None]
    if not clean:
        return []
    # Try cycle lengths 1..16; pick shortest that explains >= 75% of bars
    best_cycle = clean[:8]
    best_score = 0
    for L in range(1, min(17, len(clean)//2 + 1)):
        seed = clean[:L]
        matches = sum(1 for i, r in enumerate(clean) if r == seed[i % L])
        score = matches / len(clean)
        if score > 0.75 and L <= len(best_cycle):
            best_cycle = seed
            best_score = score
            break
    return best_cycle

# ------------------------- drum pattern ------------------------------
GM_DRUMS = {
    35: 'kick', 36: 'kick', 28: 'kick',
    38: 'snare', 40: 'snare', 39: 'clap',
    42: 'hat',  44: 'hat',  46: 'open_hat',
    49: 'crash', 51: 'ride',
    54: 'tambourine', 70: 'shaker',
}

def drum_patterns(track, ticks_per_bar, bar_subdiv=16):
    by_kind_ticks = collections.defaultdict(list)
    t = 0
    for m in track:
        t += m.time
        if m.type == 'note_on' and m.velocity > 0:
            kind = GM_DRUMS.get(m.note, f'gm{m.note}')
            by_kind_ticks[kind].append(t)
    patterns = {}
    for kind, ticks in by_kind_ticks.items():
        patterns[kind] = pattern_to_string(rhythm_grid(ticks, ticks_per_bar, bar_subdiv))
    return patterns

# ------------------------- main ----------------------------------------
def main():
    mid = mido.MidiFile(MIDI_PATH)
    tempo = tempo_us(mid)
    bpm = round(60_000_000 / tempo, 2)
    tpb = mid.ticks_per_beat
    ticks_per_bar = tpb * 4   # assume 4/4

    # Total bars from the last note in any track
    last_tick = 0
    for tr in mid.tracks:
        t = 0
        for m in tr:
            t += m.time
            if m.type == 'note_on':
                if t > last_tick:
                    last_tick = t
    n_bars = (last_tick + ticks_per_bar - 1) // ticks_per_bar

    spec = {
        'source_midi': os.path.basename(MIDI_PATH),
        'bpm': bpm,
        'time_signature': '4/4',
        'length_bars': int(n_bars),
        'length_seconds': round(mid.length, 1),
    }

    # Collect all non-drum pitches for key detection
    all_pitches = []
    for i, track in enumerate(mid.tracks):
        if i not in ROLE: continue
        if ROLE[i] == 'drums': continue
        for _, kind, n in note_events(track):
            if kind == 'on':
                all_pitches.append(n)
    spec['key'] = detect_key(all_pitches)

    # Per-element patterns
    elements = {}
    for ti, role in ROLE.items():
        if ti >= len(mid.tracks): continue
        track = mid.tracks[ti]
        events = note_events(track)
        if role == 'drums':
            elements['drums'] = drum_patterns(track, ticks_per_bar, bar_subdiv=16)
            continue
        on_ticks = [t for t, kind, _ in events if kind == 'on']
        pitches = [n for _, kind, n in events if kind == 'on']
        if not pitches:
            continue
        first_bar = on_ticks[0] // ticks_per_bar if on_ticks else 0
        last_bar  = on_ticks[-1] // ticks_per_bar if on_ticks else 0
        info = {
            'first_bar': int(first_bar),
            'last_bar':  int(last_bar),
            'span':      f'{note_name(min(pitches))}..{note_name(max(pitches))}',
            'avg_pitch': round(statistics.mean(pitches), 1),
            'note_count': len(pitches),
            'rhythm_1bar_16ths': pattern_to_string(rhythm_grid(on_ticks, ticks_per_bar, 16)),
            'contour_first32': melodic_contour(events, 32),
        }
        # Chord roots if this is the chord track
        if role == 'chord':
            roots = chord_roots_per_bar(events, ticks_per_bar, n_bars)
            info['chord_progression'] = compress_chord_progression(roots)
        elements[role] = info

    spec['elements'] = elements

    os.makedirs(os.path.dirname(SPEC_PATH), exist_ok=True)
    with open(SPEC_PATH, 'w') as f:
        f.write("# Abstract song specification (Phase 1 of cleanroom remix pipeline).\n")
        f.write("# The composer and synthesiser MUST read ONLY this file, never the MIDI.\n\n")
        yaml.safe_dump(spec, f, sort_keys=False, default_flow_style=False)
    print(f"Wrote {SPEC_PATH}")
    print(f"  {bpm} BPM, key {spec['key']['root']} {spec['key']['mode']}, {n_bars} bars")
    for k, v in elements.items():
        if k == 'drums':
            print(f"  drums kit: {list(v.keys())}")
        else:
            print(f"  {k}: {v['rhythm_1bar_16ths']}  ({v['span']})")

if __name__ == '__main__':
    main()
