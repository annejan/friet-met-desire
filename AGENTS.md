# Notes for AI agents

This project is a **happy-hardcore SID remix** of Gala's "Freed from Desire".
The MIDIs in `midi/` are *research material* — extract patterns from them,
don't try to faithfully port the song. The output should sound like a SID rave
tune, not like the original.

## Project context

- Owner: annejan (brouwer@annejan.com), openSUSE Tumbleweed, comfortable with
  6502 asm and low-level audio. Reminded me to use a Python `.venv` rather than
  `pip --user`.
- Target chip: MOS 6581/8580 (SID). PAL clock = 985 248 Hz.
- Output format: PSID v2NG (`.sid`).

## Local tools (already installed)

| Tool        | Purpose                                            |
|-------------|----------------------------------------------------|
| `xa`        | 6502 cross-assembler. Pass `-XMASM` to allow `:` in comments. Does not support `@local` labels (use unique global names). Produces RAW binary (no PRG load-address prefix); for PSID we prepend 2 load bytes ourselves. |
| `vsid`      | Part of VICE. Headless render: `vsid -sounddev wav -soundarg out.wav -limitcycles N file.sid`. WAV header is corrupt because we kill it mid-stream — recover raw PCM with `tail -c +45 out.wav`. C64 ROMs at `/usr/share/vice/C64/`. |
| `sidplayfp` | **Broken on this box** — reports `ERROR: Not enough memory.` for every file regardless of RAM. Don't bother. Use `vsid`. |
| `ffmpeg`    | Used to convert raw PCM → MP3.                     |
| Python venv | At `.venv/`. Has `mido`, `numpy`. Always activate before pip-installing. |

## PSID v2 header layout

124 bytes, big-endian: magic `PSID`, version(2), dataOffset(0x7C), loadAddr,
init, play, songs, startSong, speed(4B), name(32B), author(32B), released(32B),
flags(2B), startPage, pageLength, secondSIDAddr, thirdSIDAddr.

If `loadAddr` in header is 0, the first 2 bytes of data are interpreted as the
PRG-style load address — which is the more reliably-supported variant.

## Voice assignment

The two scripts use different strategies:

- **`src/midi2sid.py`** — port-ish: V1 = T5 bassline, V2 = T7 vocal melody
  (with T11 chorus hook overriding 92–124s), V3 = drums.
- **`src/midi2sid_hh.py`** — happy-hardcore remix: V1 = generated off-beat
  pulse bass tracking the melody octave-down, V2 = T5 melody on saw with
  per-note filter cutoff envelope (hoover-wow), V3 = programmatic 4-on-floor
  drums.

## Source-MIDI roles (from `analyze_midi.py`)

| Track | Range  | Role                                                      |
|-------|--------|-----------------------------------------------------------|
| T4    | D2–A4  | Piano comping (chord voicings, polyphony 5)               |
| T5    | D2–F3  | **Iconic synth bassline riff** — repeated D2 with octave jumps |
| T6    | D4–D6  | Chord stabs — D arpeggio across 3 octaves                 |
| T7    | A4–F5  | Vocal melody (instrument-substituted, prog 68)            |
| T8    | F3–F4  | String pad                                                |
| T11   | D3–F3  | Chorus "na-na" hook (active 92–124 s only, Saw.Lead)      |
| T13   | drumkit| Kick (36), snare (38,40), clap (39), hats (42,44,46), tambourine (54), maracas (70) |

## Common pitfalls — please *do not* re-discover

1. **Vibrato on V2 with base freq = 0 produces a constant ~3850 Hz beep.** Guard
   `apply_vibrato` with a `ora ZP_V2BASE_HI ; bne` check.
2. **V2 PW init**: write to `SID+9` (PW LO) and `SID+10` (PW HI), *not* `+10`
   and `+11`. Writing PW into `+11` sets the V2 CTRL register's TEST bit and
   silences the voice.
3. **V3 drum retrigger**: each drum hit must write ctrl with gate off, *then*
   ctrl with gate on. Writing only "noise+gate" doesn't transition gate from
   0→1 if the previous chord left gate on.
4. **Filter cutoff** $50 in `$D416` = ~400 Hz (way too dark — pulse-lead sounds
   muffled). $A0 ≈ 2.5 kHz is a good sweet spot for taming pulse harmonics
   without dulling the lead. $C0 ≈ 5 kHz lets the 6th harmonic through as a
   "beep".
5. **Polyphonic-collapse on T4 (piano comp)** produces chaotic chopped sound
   because the "max note" jumps around chord voicings. T4 is *not* a melody
   track — don't pick it as lead.
6. **Drum filter set**: tambourine (54) and maracas (70) are dense and noisy;
   keep only kick (36) + snare (38,40,39) + hats (42,44,46) for the
   foundational pattern.

## Where to start

```sh
source .venv/bin/activate
make analyze        # research dump
make hh             # build happy-hardcore SID into out/
make preview-hh PREVIEW_SECONDS=60   # render an MP3
```

The user prefers iterative feedback: build → render → listen → ask. Don't
batch many speculative tweaks; deliver something playable, ask "where does it
hurt?", iterate.
