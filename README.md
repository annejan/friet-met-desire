# Friet From Desire

A Commodore 64 SID remix project inspired by Gala's "Freed from Desire" (1996).

**Friet** is Dutch for fries — the name is a playful misreading of "Freed".
This project is a happy-hardcore SID remix, not a faithful port.

## Concept

The four MIDI files in `midi/` are **research material** — not source for a
direct transcription. They're studied for their patterns (drum grooves,
bassline rhythm, melodic contours, chord progressions). The output SIDs are
*remixes* that take those patterns and re-arrange them for the C64's 3-voice
SID chip in a happy-hardcore style.

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

## Source-MIDI map (researched, see `docs/midi_analysis.md`)

| Track | Range  | Role                                          |
|-------|--------|-----------------------------------------------|
| T4    | D2–A4  | Piano comping (chord voicings, 5-voice poly)  |
| T5    | D2–F3  | **The iconic synth bassline riff**            |
| T6    | D4–D6  | Chord stabs — D arpeggio across 3 octaves     |
| T7    | A4–F5  | Vocal melody (instrument-substituted)         |
| T8    | F3–F4  | String pad                                    |
| T11   | D3–F3  | Chorus "na-na" hook (only 92–124s)            |
| T13   | drumkit| Kick, snare, claps, hats, tambourine          |

## Build

```sh
source .venv/bin/activate
python src/analyze_midi.py                          # writes stems/ + prints report
python src/midi2sid.py                              # -> out/friet_from_desire.sid
python src/midi2sid_hh.py                           # -> out/friet_from_desire_hh.sid
```

Listen with VICE's `vsid out/friet_from_desire_hh.sid` (it's the SID we like
best), or render a WAV preview:

```sh
vsid -sounddev wav -soundarg out/preview.wav -limitcycles 60000000 out/friet_from_desire_hh.sid
```

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

## Status / open questions

- Track identification: confirmed via `analyze_midi.py` rhythm + range analysis;
  cross-checked against song memory (Eurodance/Italodance from 1996).
- Pattern extraction tools (rhythmic motifs, bassline shape) — TODO.
- Pad/chord rendering on SID with only 3 voices is unsolved — currently V3 is
  drums only. Possible: ring modulation for "chord shimmer".
