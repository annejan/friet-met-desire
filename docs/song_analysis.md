# "Freed from Desire" — Music Theory Analysis

Compiled from external sources (Hooktheory, chord/tab sites, sheet music) and
cross-checked against the MIDI in `midi/`. This document is the
**authoritative spec** for what the song actually is — the cleanroom
composer should be informed by this, not by guesses from the MIDI alone.

## Key facts

| Property         | Value                                                |
|------------------|------------------------------------------------------|
| Key              | **D minor** (Aeolian; some sources also note F major as the relative major) |
| Tempo (original) | **130 BPM** (the karaoke MIDI in `midi/` is at 120 BPM, slower) |
| Time signature   | 4/4                                                  |
| Writers          | Gala (Rizzatto), Maurizio Molella ("Molella"), Phil Jay |
| Released         | 1996                                                 |

## Chord progression — i – III – VI – VII

The entire song revolves around a four-bar minor loop:

```
| Dm  | F   | Bb  | C   |
| i   | III | VI  | VII |
```

In D-minor Roman-numeral terms: **i – ♭III – ♭VI – ♭VII** (natural minor).

This is the "minor 1-3-6-7 anthemic loop" found in countless dance and rock
tracks. It avoids the minor v and minor iv, picks up the major III, VI, and
VII from natural minor / Aeolian, and substitutes ♭VII (C) for the dominant —
no leading tone, no tritone resolution, just modal stepwise movement.

## Bassline — two distinct behaviours

**Verse**: a **D pedal tone** is held throughout. The upper voicings move
(Dm → F/D → B♭/D → C/D — slash chords with D in the bass), but the bass
itself stays on D. This creates the hypnotic "stuck-on-one-note" verse feel.

**Chorus** (and the iconic full-band sections): the bass **follows the root
motion** — D → F → B♭ → C. Stepwise-ish movement: down a major third, up a
fourth, up a tone, back down to D. This is what gives the chorus its
"anthemic" lift compared to the verses.

The bass synth itself is an aggressive 16th-note-driven pulse pattern, not a
sustained line — the bassist plays the same rhythmic figure over each chord,
varying only the pitch.

## Sections (from the original 1996 mix)

```
0:00  Intro       — drums + bass D-pedal + chord stab on D arpeggio
0:15  Verse 1     — vocals enter over D-pedal bass
0:45  Pre-chorus  — bass starts moving, build with claps/snare
1:00  Chorus 1    — "Freed from desire, mind and senses purified"
                     bass follows Dm–F–B♭–C
1:30  Verse 2     — same as verse 1 with denser arrangement
2:00  Pre-chorus
2:15  Chorus 2
2:45  Breakdown / bridge — "na na na na na na, na-na-naaa" hook
3:00  Chorus 3+   — repeat with extra energy
```

The "na-na-na" hook (Track 11 in the karaoke MIDI: 128 notes, only between
1:32 and 2:04 in MIDI time, range D3–F3) is in fact a *low-octave* synth
counter-melody that doubles the chorus — not the main melodic content.

## Source-MIDI track roles (re-confirmed against this analysis)

| Track | Range | What it is                                                |
|-------|-------|-----------------------------------------------------------|
| T4    | D2–A4 | Piano comping — plays the Dm/F/B♭/C chord *voicings*      |
| T5    | C2–F3 | Synth bass — rhythmic 16th-note pattern, NOT the iconic "doo-doo" we may remember; the recognisable bassline is the *pedal* in verses |
| T6    | D4–D6 | Chord stab arpeggio (D in three octaves — D pedal layer) |
| T7    | A4–F5 | **Vocal melody** (sung lyrics, instrument substitute)     |
| T8    | F3–F4 | String pad                                                |
| T11   | D3–F3 | The "na-na" counter-melody hook (only during one section) |
| T13   | drums | Kick (4-on-floor), clap on 2 & 4, dense 16th hats         |

## Implications for the cleanroom remix

For the happy-hardcore version we want:

1. **Use the right chord cycle order**: Dm → F → B♭ → C. Earlier our composer
   used Dm → B♭ → F → C (i–VI–III–VII), which is technically valid but not
   what the song actually does.
2. **Two bass modes**: verse = D pedal (every off-beat 8th plays D regardless
   of chord); chorus = root motion (off-beat 8ths play D, F, B♭, C per bar).
3. **Lead arpeggios in chorus** should follow the chord tones of the current
   chord — not just always-D triads.
4. **Tempo**: target 170–180 BPM for happy hardcore (sped up from 130).

## Sources

- [Freed From Desire — Hooktheory Theorytab](https://www.hooktheory.com/theorytab/view/gala/freed-from-desire)
- [Freed From Desire — Ultimate-Guitar chords](https://tabs.ultimate-guitar.com/tab/gala/freed-from-desire-chords-1465989)
- [ChordZone analysis](https://www.chordzone.org/2023/11/gala-freed-from-desire-chords-and-tabs-for-guitar-and-piano-sheet-music-tabs.html)
- [BoiteAChansons chords](https://www.boiteachansons.net/en/partitions/gala/freed-from-desire)
