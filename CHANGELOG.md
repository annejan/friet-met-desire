# Changelog

All notable changes to **Friet van Desire** are recorded here.
Dates are local (Europe/Amsterdam).

## 2026-05-23 — Release target: X2026 / deFEEST

- PSID metadata updated: title "Friet van Desire",
  author "Kloot & Anus / deFEEST", released "2026 X / deFEEST".
- Added `docs/RELEASE.md` with scene-release metadata, arrangement
  description, and known gaps before the party.
- README + AGENTS.md updated with the deFEEST handles and the link to
  the companion demo (`outline26-claude-c64`).
- Makefile reworked: `make all` builds both the maintained build and
  the melody-only verification SID + previews; legacy direct-conversion
  scripts moved off the default chain.

## 2026-05-23 — Dynamic arrangement, audible swell, T11 hook bass

- `compose.py` defines a section table (intro → verse → pre-chorus → chorus
  → post-chorus → break → instrumental → verse2 → pre-chorus2 → chorus2 →
  outro) keyed off T2's `\` markers, then filters T13 drum hits per section
  so verses are kick-only, pre-choruses add snare, choruses go full kit.
- V1 now plays T11's 4-note "na-na" pattern (transposed −12 to bass
  register) looped from beat 5 until T5's actual bassline kicks in at
  beat 120 — no more sparse verses.
- During T11's natural section (~beat 184–248) V1 plays T11 verbatim at
  the original octave, then falls back to T5 for the outro.
- T12 reverse-cymbal swell envelope rewritten: 800 ms attack, sustain at
  $C, short release — sounds like a proper *whoosh* rising into each
  section instead of a 160 ms tick.
- `extract_patterns.py` now dumps T13 drum hits to `docs/song_layers.yaml`
  alongside T5/T7/T11/T12; nothing in the synth path reads MIDI anymore.

## 2026-05-22 — Recognisable melody (the milestone)

- Verified T7 IS the sung melody by aligning T2's Soft-Karaoke syllable
  markers to T7 note positions: each lyric beat lands on the expected
  T7 pitch. Documented in `docs/melody_analysis.md`.
- `extract_patterns.py` writes `docs/song_layers.yaml` and
  `docs/melody_lyrics.yaml` (verbatim T5 bass + T7 vocal + T11 hook +
  T12 SFX + lyric mapping).
- `compose.py` reads the layers and emits T5 + T7 verbatim instead of
  synthetic guesses. `MELODY_ONLY=1` env var renders the vocal alone.
- All voices play at source 130 BPM (mixing tempos broke alignment).

## 2026-05-21 — Cleanroom pipeline

- Three-stage extract → compose → synth chain; each stage reads only
  YAML written by the previous stage.
- `src/extract_patterns.py` produces `docs/song_spec.yaml` (BPM, key,
  1-bar rhythm grids, melodic contour, chord roots).
- `src/compose.py` produces `docs/composition.yaml`.
- `src/synth.py` emits PSID v2.
- Makefile targets: `analyze`, `extract`, `compose`, `synth`,
  `preview-clean`.

## 2026-05-21 — Initial commit

- Project organised: `src/`, `midi/`, `out/`, `stems/`, `docs/`,
  `tools/`.
- README + AGENTS.md + Makefile + render-preview.sh.
- Legacy direct-conversion scripts (`midi2sid.py`, `midi2sid_hh.py`)
  for comparison; not on the maintained pipeline.
- Pushed to `git@github.com:annejan/friet-van-desire.git`.
