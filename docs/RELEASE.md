# Release notes — *Friet van Desire*

## Scene metadata

- **Title:** Friet van Desire
- **Group:** deFEEST
- **Composer / coder:** Kloot/deFEEST (Claude AI pair-programmer) +
  Anus/deFEEST (annejan)
- **Target party:** **X2026** (Dutch Commodore demoparty)
- **Format:** PSID v2 / `out/friet_clean.sid`
- **Chip:** MOS 6581/8580 (PAL, 985 248 Hz)
- **Player:** 50 Hz IRQ, init at $1000, play at $1003
- **Length:** **1:48** clean build (120 BPM), **1:14** HH build (175 BPM);
  loops on reaching the end. See "Structure" below.

## Companion demo

This SID will sound in deFEEST's X2026 demo, *"Kloten met de
broodtrommel"* — see <https://github.com/annejan/outline26-claude-c64>.

## Structure

Compose-time segment map (`SEGMENTS` in `src/compose.py`) re-orders the
source MIDI to fit a happy-hardcore arrangement:

| #  | Segment            | Source-beat range  | Beats |
|----|--------------------|--------------------|-------|
| 1  | Intro              | 0.0 → 21.5         | 21.5  |
| 2  | Verse 1            | 21.5 → 54.5        | 33.0  |
| 3  | Pre-chorus 1       | 54.5 → 88.0        | 33.5  |
| 4  | Chorus 1           | 88.0 → 117.5       | 29.5  |
| 5  | Post-chorus (Na-na)| 117.5 → 149.5      | 32.0  |
| 6  | **Breathe 1**      | 149.5 → 153.5      |  4.0  |
| 7  | Chorus 2 reprise   | 88.0 → 117.5       | 29.5  |
| 8  | **Breathe 2**      | 149.5 → 153.5      |  4.0  |
| 9  | Chorus 3 reprise   | 88.0 → 117.5       | 29.5  |
|    | **Total**          |                    | **216.5** |

Breathe segments are 4-beat instrumental gaps (drums + T11 hook bass keep
going, no vocal) so each chorus reprise gets room to breathe before the
next one hits. Total loop: **1:48** at 120 BPM clean build, **1:14** at
175 BPM HH build.

Each chorus reprise (#6 and #7) replays the same source range as Chorus 1,
so the vocal + bass + drum events are bar-for-bar identical. A synthetic
crash-riser fires 3 beats before each chorus's output position so each
one hits as a "drop". Verses 2 / Pre-chorus 2 / Instrumental break /
Outro of the original arrangement are NOT used — they don't fit the HH
form factor.

## Arrangement (current build)

Three SID voices, all running at the song's native 130 BPM:

| Voice | What it plays                                                       |
|-------|---------------------------------------------------------------------|
| V1    | T11 "na-na" 4-note hook (D2/F2, octave-down) looped from beat 5 until T5's real synth bassline takes over at beat 120. T11 returns at its natural octave during the instrumental break (~beat 184) before T5 resumes for the outro. |
| V2    | T7 vocal melody verbatim — Oboe substitute, verified by aligning T2's `\My`, `\Freed`, `\Na` syllable markers note-for-note to T7 pitches. The actual singer. |
| V3    | T13 drums verbatim, mapped to a SID kick/snare/hat kit and **filtered per section** so verses are kick-only, pre-choruses add snare, choruses go full kit. Plus T12's reverse-cymbal swells at the intro and at each section transition. |

## Tones

- V1 bass: pulse waveform, PW $0800, sustained envelope.
- V2 vocal: triangle waveform, slow attack so syllables phrase, full
  sustain.
- V3 drums: noise with per-kit-piece ADSR; reverse-cymbal has an 800 ms
  slow attack so the swell is *heard*, not ticked.

## How to verify before the party

```sh
make all                 # rebuild both SIDs + previews
vsid out/friet_clean.sid # listen on VICE
xxd out/friet_clean.sid | head -8   # confirm PSID header reads
                                    #   'PSID' v2, Kloot & Anus / deFEEST
```

## Known gaps before release

See [`polish_plan.md`](polish_plan.md). Open items:

1. Vibrato on V2 (vocal currently dead-pan).
2. HH-tempo variant `friet_hh.sid` at 170 BPM alongside the 130 BPM
   song-faithful build.
3. Possible bigger Chorus 2 hit relative to Chorus 1 (extra crash, more
   hats) to give the song a proper "second drop" reprise.

## Sources used

- Karaoke MIDI: `midi/Gala_Freed_From_Desire.mid` — T2 lyric markers
  cross-validated against T7 to establish that T7 is the vocal melody.
- [Hooktheory](https://www.hooktheory.com/theorytab/view/gala/freed-from-desire):
  key D minor, i-III-VI-VII chord progression.
- [ChordU](https://chordu.com/chords-tabs-gala-freed-from-desire-official-video--id_p3l7fgvrEKM):
  tempo 128.85 BPM, chords Dm-F-B♭-C.
- [pianoletternotes.blogspot.com](https://pianoletternotes.blogspot.com/2019/02/freed-from-desire-by-gala.html):
  cross-reference for the verse "a-a-a" stutter and the chorus "d-d-c-d"
  descending pattern.
