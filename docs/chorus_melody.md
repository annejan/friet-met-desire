# Hand-transcribed chorus melody — "Freed from Desire"

Source: [pianoletternotes.blogspot.com](https://pianoletternotes.blogspot.com/2019/02/freed-from-desire-by-gala.html)
(letter-notes transcription, cross-checked against song memory).

The MIDI in `midi/` has a misleading "vocal" track (T7) — it's actually an
instrumental obligato, not the sung melody. This document captures the
**actual sung chorus** so we can play *that* as the lead.

## Notes used

In D minor (the original key): only **D, C, E, F, B♭** are needed. No "A".
That's scale degrees 1, ♭7, 2, ♭3, ♭6 — the natural-minor core.

## The 4-bar chorus phrase

(repeats 4 times = 16 bars per chorus)

```
beat:    1   1½  2   2½  3   3½  4   4½
bar 1:   d   d   c   d   d   c   d   (cd)    "freed-from-de-sire-mind-and-sen-ses"
bar 2:   d   ·   ·   ·   d   d   c   d
bar 3:   d   c   d   (cd) d   ·   ·   ·
bar 4:   d   d   c   d   d   c   d   f       "...pu-ri-fied"
                                              ← lift to F! the hook lands here
bar 5:   d   ·   d   c   d   ·   e   f       second half — "mind and..."
bar 6:   f   f   e   ·   ·   ·   ·   f       held E then up to F
bar 7:   ·   d   ·   ·   d   c   d   ·
bar 8:   ·   e   f   f   f   e   ·   ·       the "FREED!" peak in the answering phrase
```

The shape is: mostly sit on **D** with stutter-descents to C; lift to F at the
end of phrases ("…pu-ri-fied!"); the answering phrase has the descending
F-F-F-E motif (= "mind and senses pu-ri-fied" descending).

## Bb minor / harmonised version

Some phrases drop down to Bb (♭6) — gives the "soulful" colour.
The verse stutter is just `a a a a a a a a` on the dominant (A) but the
chorus avoids A entirely.

## Programmer note

Encoded as a flat note list in `src/compose.py` (see `CHORUS_MELODY`).
Each entry is `(beat_offset, duration_beats, midi_pitch)`.
