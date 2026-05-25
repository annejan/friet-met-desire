#!/usr/bin/env python3
"""Sandbox for hearing FFD source layers (vocal + bass + drums) in a
short loop, with optional HH supplements (faster tempo, 4-on-floor
kick overlay).

The point of this iteration: stop hand-crafting beats — just play the
SOURCE-MIDI layers that already lock together (the original producer
already nailed the groove). Tweak SETTINGS at the top, run `make lab`.

Per docs/rhythm_research.md: T5 bass is a TRESILLO (3-3-2 pattern,
hits at 0, 0.75, 1.5 per half-bar) and only starts at source beat 120
(when chorus 2 / instrumental kicks in). Fragment 120-136 is 4 bars
where bass + drums + vocal all play together.
"""
import os, sys, subprocess, yaml

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LAYERS_PATH = os.path.join(BASE, 'docs', 'song_layers.yaml')
COMP_OUT    = os.path.join(BASE, 'docs', 'lab_composition.yaml')
SID_OUT     = os.path.join(BASE, 'out', 'lab.sid')
SYNTH       = os.path.join(BASE, 'src', 'synth.py')
PYTHON      = os.path.join(BASE, '.venv', 'bin', 'python')

# ============================ SETTINGS ====================================

# --- Fragment to loop (source-beat range from the karaoke MIDI) ---------
# Useful windows (verified against docs/song_layers.yaml):
#   21.5..29.5 = verse 1 first 2 bars: "My love has got no money / He's got his strong beliefs"
#                — D pedal underneath; T6 organ stab signature lives here
#   88..96     = chorus 1 first 2 bars: "Freed-from-de-si-re / Mind-and-senses-purified"
#   120..136   = na-na with the iconic T5 tresillo bass (4 bars, all layers)
SRC_START = 88.0
SRC_END   = 96.0
N_LOOPS   = 2

# --- Tempo (120 = source / 175 = HH target) ----
BPM = 175

# --- Vocal quantization (None = source timing).
# Per docs/melody_theory.md: the chorus Phrase A tresillo (0, 0.75, 1.5,
# 2, 2.75) IS the song. Quantizing to 8ths flattens it. Leave alone.
QUANTIZE_TO = None

# --- Source layers from the karaoke MIDI -------------------------------
PLAY_VOCAL = True      # T7 — the melody itself
PLAY_BASS  = False     # T5 only plays from beat 120+; we generate our own below
PLAY_DRUMS = False     # T13 is a busy house pattern; we generate clean HH instead

# --- Synthetic HH foundation -------------------------------------------
# Layer up: kick + hat first, snare for chorus only.
SYNTH_KICK  = True     # 4-on-the-floor
SYNTH_SNARE = False    # off in verse — would compete with the T6 stab
SYNTH_HAT   = True     # off-beat 8ths = HH verse shimmer

# --- Synthetic bass strategy:
#   "off"          — no synthetic bass
#   "tresillo"     — 3-3-2 (matches chorus vocal Phrase A)
#   "chord_pump"   — quarter-note chord-roots Dm-F-Bb-C (anthem foundation)
#   "t6_stab"      — T6's 5-hit verse stab rhythm at D2 (0, 4, 7, 10, 14 sixteenths)
SYNTH_BASS_MODE = "t6_stab"
# Legacy toggle (kept for backwards compat; ignored if SYNTH_BASS_MODE != "off"):
SYNTH_TRESILLO_BASS = True

# --- Click track (hat tick on every HALF-bar = once per ~1 s @ 120 BPM)
# Off by default — T13's source pattern already has 8 hats/bar (FFD's
# house shimmer); adding a click on top only made the mix denser.
# Turn ON only when comparing against a synthetic-only beat without
# source drums.
CLICK_TRACK = False

# --- Tones ------------------------------------------------------------
LEAD_CTRL = 0x40    # $40 pulse, $20 saw, $10 triangle
BASS_CTRL = 0x40

# --- Lead-in silence (frames). 0 = no shift, first note at frame 0.
LEAD_IN_FRAMES = 0

# --- PAL ----
PAL_HZ = 50.0
# ===========================================================================


# GM drum-pitch -> our kit-kind mapping (same as compose.py).
GM_DRUMS = {35:'kick', 36:'kick', 28:'kick',
            38:'snare', 40:'snare', 39:'snare',
            46:'hat', 44:'hat', 42:'hat'}


def main():
    with open(LAYERS_PATH) as f:
        layers = yaml.safe_load(f)

    fbeat = 60.0 * PAL_HZ / BPM
    fbar  = fbeat * 4
    frag_beats = SRC_END - SRC_START
    frag_bars  = int(round(frag_beats / 4))
    total_bars = frag_bars * N_LOOPS
    total_frames = int(round(total_bars * fbar)) + 50

    print(f"Fragment: src beats {SRC_START}–{SRC_END}  ({frag_bars} bars × {N_LOOPS} loops)")
    print(f"Tempo: {BPM} BPM  → {fbeat:.2f} frames/beat  → {total_bars * fbar / PAL_HZ:.1f} s body")

    def pull(layer_name, transform=lambda b, d, p: (b, d, int(p))):
        """Yield (rel_beat, dur_beats, pitch) for source-layer events
        falling inside [SRC_START, SRC_END)."""
        for b, d, p in layers['layers'].get(layer_name, []):
            if SRC_START <= b < SRC_END:
                yield transform(b - SRC_START, d, p)

    # --- Lead (T7 vocal) ----
    lead_events = []
    for loop in range(N_LOOPS):
        for rel_b, dur_b, pitch in pull('vocal'):
            out_b = rel_b + loop * frag_beats
            if QUANTIZE_TO:
                out_b = round(out_b / QUANTIZE_TO) * QUANTIZE_TO
            lead_events.append({
                'frame':      int(round(out_b * fbeat)),
                'note':       pitch,
                'dur_frames': max(4, int(round(max(0.2, dur_b) * fbeat))),
                'ctrl':       LEAD_CTRL,
            })
    print(f"Lead: {len(lead_events)} vocal events")

    # --- Bass --------------------------------------------------------------
    bass_events = []
    if PLAY_BASS:
        src_bass = list(pull('bass'))
        for loop in range(N_LOOPS):
            for rel_b, dur_b, pitch in src_bass:
                out_b = rel_b + loop * frag_beats
                bass_events.append({
                    'frame':      int(round(out_b * fbeat)),
                    'note':       pitch,
                    'dur_frames': max(3, int(round(max(0.15, dur_b) * fbeat))),
                    'ctrl':       BASS_CTRL,
                })
        print(f"Bass: {len(bass_events)} T5 source events")
    if SYNTH_BASS_MODE != "off":
        # Chord roots for the Dm-F-Bb-C cycle (chorus uses them; verse
        # holds D pedal regardless).
        CHORD_ROOTS = [38, 41, 34, 36]   # D2 (Dm), F2 (F), Bb1 (Bb), C2 (C)
        CHORUS_ANCHOR = 88.0
        for bar in range(total_bars):
            lab_bar_in_frag = bar % frag_bars
            src_beat_at_bar_start = SRC_START + lab_bar_in_frag * 4
            chord_idx = int((src_beat_at_bar_start - CHORUS_ANCHOR) // 4) % 4
            chord_pitch = CHORD_ROOTS[chord_idx]
            if SYNTH_BASS_MODE == "t6_stab":
                # T6's iconic stab rhythm: 5 hits at sixteenths 0, 4,
                # 7, 10, 14 = beat positions 0, 1, 1.75, 2.5, 3.5.
                # Pitch follows the chord root (D in verse / Dm-F-Bb-C
                # in chorus) so the stab stays harmonically correct
                # while keeping the groove pattern.
                for off in (0.0, 1.0, 1.75, 2.5, 3.5):
                    bass_events.append({
                        'frame':      int(round((bar * 4 + off) * fbeat)),
                        'note':       chord_pitch,
                        'dur_frames': max(4, int(round(0.4 * fbeat))),
                        'ctrl':       BASS_CTRL,
                    })
            elif SYNTH_BASS_MODE == "tresillo":
                # D2 / A2 tresillo (3-3-2 per half-bar)
                D2, A2 = 38, 45
                for half in (0, 2):
                    pitch = D2 if half == 0 else A2
                    for off in (0, 0.75, 1.5):
                        bass_events.append({
                            'frame':      int(round((bar * 4 + half + off) * fbeat)),
                            'note':       pitch,
                            'dur_frames': max(3, int(round(0.5 * fbeat))),
                            'ctrl':       BASS_CTRL,
                        })
            elif SYNTH_BASS_MODE == "chord_pump":
                # Quarter-note chord-root pump
                for beat in range(4):
                    bass_events.append({
                        'frame':      int(round((bar * 4 + beat) * fbeat)),
                        'note':       chord_pitch,
                        'dur_frames': max(6, int(round(0.9 * fbeat))),
                        'ctrl':       BASS_CTRL,
                    })
        print(f"Bass: {len(bass_events)} events (mode={SYNTH_BASS_MODE})")

    # --- Drums --------------------------------------------------------------
    drum_events = []
    if PLAY_DRUMS:
        src_drums = []
        for b, _, pitch in layers['layers'].get('drums', []):
            if not (SRC_START <= b < SRC_END): continue
            kind = GM_DRUMS.get(int(pitch))
            if kind:
                src_drums.append((b - SRC_START, kind))
        for loop in range(N_LOOPS):
            for rel_b, kind in src_drums:
                out_b = rel_b + loop * frag_beats
                drum_events.append({
                    'kind':  kind,
                    'frame': int(round(out_b * fbeat)),
                })
        print(f"Drums: {len(drum_events)} T13 source events")
    # Synthetic HH foundation. V3 is mono — kick/snare/hat at the same
    # frame would collide, so we choose offsets that don't overlap.
    for bar in range(total_bars):
        bar_start = bar * 4.0
        if SYNTH_KICK:
            for off in (0, 1, 2, 3):
                drum_events.append({'kind': 'kick',
                    'frame': int(round((bar_start + off) * fbeat))})
        if SYNTH_SNARE:
            for off in (1, 3):
                drum_events.append({'kind': 'snare',
                    'frame': int(round((bar_start + off) * fbeat))})
        if SYNTH_HAT:
            for off in (0.5, 1.5, 2.5, 3.5):
                drum_events.append({'kind': 'hat',
                    'frame': int(round((bar_start + off) * fbeat))})

    # --- Lead-in shift ----
    if LEAD_IN_FRAMES > 0:
        for ev in lead_events:  ev['frame'] += LEAD_IN_FRAMES
        for ev in drum_events:  ev['frame'] += LEAD_IN_FRAMES
        for ev in bass_events:  ev['frame'] += LEAD_IN_FRAMES
        total_frames += LEAD_IN_FRAMES

    # --- Click track (after shift so it covers the lead-in too) ----
    # Tick on every HALF-BAR (beats 1 and 3) — at 120 BPM that's
    # one tick per second, slow enough to feel like a metronome and
    # not compete with the melody for rhythmic attention.
    if CLICK_TRACK:
        click_events = []
        bar = 0
        while True:
            done = False
            for off in (0, 2):
                f = int(round((bar * 4.0 + off) * fbeat))
                if f >= total_frames - 5:
                    done = True; break
                click_events.append({'kind': 'hat', 'frame': f})
            if done: break
            bar += 1
        # Click first so source/HH drums on the same frame win.
        drum_events = click_events + drum_events

    composition = {
        'title':         'Friet van Desire — Lab',
        'derived_from':  f'lab.py {SRC_START}-{SRC_END} @ {BPM} BPM',
        'bpm':           BPM,
        'key':           {'root': 'D', 'mode': 'minor'},
        'length_bars':   total_bars,
        'length_frames': total_frames,
        'sections':      [{'name': 'lab', 'bars': total_bars, 'intensity': 1.0}],
        'voices': {
            'bass':  sorted(bass_events,  key=lambda e: e['frame']),
            'lead':  sorted(lead_events,  key=lambda e: e['frame']),
            'drums': drum_events,
        },
    }
    with open(COMP_OUT, 'w') as f:
        yaml.safe_dump(composition, f, sort_keys=False)
    print(f"Wrote {COMP_OUT}")

    r = subprocess.run([PYTHON, SYNTH, COMP_OUT, SID_OUT])
    if r.returncode != 0:
        sys.exit(r.returncode)


if __name__ == '__main__':
    main()
