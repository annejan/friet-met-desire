# Friet van Desire

A Commodore 64 SID remix project inspired by Gala's "Freed from Desire" (1996).

**Friet** is Dutch for fries — the name is a playful misreading of "Freed".
This project is a happy-hardcore SID remix, not a faithful port.

## Concept

The four MIDI files in `midi/` are **research material** — not source for a
direct transcription. They're studied for their patterns (drum grooves,
bassline rhythm, melodic contours, chord progressions). The output SIDs are
*remixes* that take those patterns and re-arrange them for the C64's 3-voice
SID chip in a happy-hardcore style.

### Pipeline

The build is a three-stage extract → compose → synth chain. Each stage
writes a YAML file the next stage reads, so a tweak at one level doesn't
require redoing the others.

```
midi/*.mid  ──>  extract_patterns.py  ──>  docs/song_spec.yaml    (patterns)
                                       \──>  docs/song_layers.yaml (verbatim notes)
                                                  │
                                                  ▼
                                            compose.py  ──>  docs/composition.yaml
                                                                       │
                                                                       ▼
                                                                 synth.py  ──>  out/friet_clean.sid
```

| Phase | Tool                        | Reads                                | Writes              |
|-------|-----------------------------|--------------------------------------|---------------------|
| 1     | `src/extract_patterns.py`   | the MIDI                             | `docs/song_spec.yaml` (BPM, key, 1-bar rhythm grids, contour, chord roots) AND `docs/song_layers.yaml` (verbatim T5/T7/T11/T12 note lists + lyric markers) |
| 2     | `src/compose.py`            | spec + layers (no MIDI)              | `docs/composition.yaml` (sectioned event list) |
| 3     | `src/synth.py`              | composition only                     | `out/friet_clean.sid` (PSID v2) |

Set `MELODY_ONLY=1` before running compose to render the vocal alone (no
bass, no drums) — handy for verifying the melody is recognisable in
isolation.

The legacy `midi2sid.py` and `midi2sid_hh.py` are early direct conversions
kept for comparison.

## Layout

```
friet/
├── README.md               this file
├── midi/                   source MIDIs (Karaoke transcriptions of FFD)
├── stems/                  per-track MIDI stems for inspecting individual parts
├── src/                    tools
│   ├── analyze_midi.py     dump structure + extract per-track stems
│   ├── midi2sid.py         straight-ish port (V1 bass + V2 vocal + V3 drums)
│   └── midi2sid_hh.py      happy-hardcore remix (sped up, hoover lead, programmatic drums)
├── out/                    generated .sid + .mp3 preview
├── docs/                   notes on the SID chip, the song structure, etc.
└── .venv/                  Python venv (mido)
```

## Source-MIDI map (verified against lyrics — see `docs/melody_analysis.md`)

| Track | Inst (GM)          | Range  | Role                                                        |
|-------|--------------------|--------|-------------------------------------------------------------|
| T2    | (lyric track)      | —      | Soft-Karaoke `\My love` etc., syllables aligned to T7 notes |
| T4    | BrtAcoust (1)      | D2–A4  | Piano comp (chord voicings, polyphony 5)                    |
| T5    | 5ths Bass (87)     | D2–F3  | **Iconic synth bassline riff**                              |
| T6    | Perc Organ (17)    | D4–D6  | Chord stabs — D arpeggio across 3 octaves                   |
| T7    | Oboe (68)          | A4–F5  | **Vocal melody substitute** (the singer)                    |
| T8    | Syn Strings (50)   | F3–F4  | String pad                                                  |
| T9    | Strings (48)       | D6–D7  | High strings countermelody                                  |
| T10   | Halo Pad (95)      | D4–D5  | Pad                                                         |
| T11   | Saw Lead (81)      | D3–F3  | **Chorus "na-na" hook** (instrumental break, 92–124s)       |
| T12   | Reverse Cymbal (119)| A2    | **Intro noise swell** (beat 5 + section transitions)        |
| T13   | drumkit            | —      | Kick, snare, clap, hats, tambourine, maracas                |

We verified T7 IS the sung melody by aligning T2's syllable markers to T7's
note positions: every "Freed", "from", "de", "si", "re" lyric event lands
exactly on the corresponding F5, F5, D5, D5, C5 in T7.

## Build

```sh
source .venv/bin/activate

# Cleanroom pipeline — read MIDI once, produce a fresh remix:
make extract compose synth          # -> out/friet_clean.sid
make preview-clean                   # -> out/friet_clean.mp3

# Legacy direct conversions (for comparison):
make hh                              # -> out/friet_from_desire_hh.sid
make port                            # -> out/friet_from_desire.sid
make preview                         # render all .mp3 previews

# Research:
make analyze                         # dump per-track stems + a textual report
```

Listen interactively: `vsid out/friet_clean.sid`.

## Tools required

- `xa` — Andre Fachat's 6502 cross-assembler (with `-XMASM` flag to allow `:` in comments)
- `vsid` from VICE (uses C64 ROMs at `/usr/share/vice/C64/`)
- Python venv with `mido` (and `numpy` for FFT analysis)
- `ffmpeg` to convert raw vsid output → MP3

Note: `sidplayfp` is *broken* on the development box (reports "Not enough
memory" for every SID regardless of file). `vsid` works fine.

## Copyright / Fair use

"Freed from Desire" is © 1996 written by Gala Rizzatto, Maurizio Molella,
Filippo Carmeni, published by Do It Yourself Music Records (and others). The
MIDIs in `midi/` are karaoke transcriptions whose own copyright belongs to
their (unnamed) creators.

This project is a **transformative remix** for personal / educational / fan
use. The generated SIDs are not byte-for-byte ports — they take rhythmic and
melodic *patterns* from the research MIDIs and re-arrange them in a
happy-hardcore style for the SID chip. No commercial distribution is intended.

If a rights-holder objects, please open an issue and the offending material
will be removed.

## Status

- ✅ **Melody recognisable** as "Freed from Desire" — T7 verbatim vocal +
  T5 verbatim bass + drums + intro noise swell, all at source 130 BPM.
- ✅ Lyrics aligned to T7 notes (every syllable has a verified pitch in
  `docs/song_layers.yaml` and `docs/melody_lyrics.yaml`).
- 🟡 **Polish pending** — see `docs/polish_plan.md`:
  1. T13 drums verbatim (replace generated kick + clap)
  2. T11 saw-lead "na-na" hook layered during the instrumental break
  3. Vibrato on V2 so the vocal feels human
  4. Tempo split — produce both a 130-BPM "song-faithful" build and a
     170-BPM "happy hardcore" build from the same source data
- 🟡 Pads / chord rendering with only 3 voices remains unsolved — V3 is
  drums only. Possible: ring-modulate V1 against V3 for "chord shimmer".
