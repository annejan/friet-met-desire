# How the "Freed from Desire" lead actually works

Transcribed from MIDI track T7 (the vocal-substitute "shakuhachi" line) and
cross-checked against the song memory. All pitch names are in D minor.

## Scale-degree palette

The whole vocal melody uses only six pitches, all from the **D natural minor**
scale (no chromatic notes):

| Note | Scale degree | Count in T7 | Role                |
|------|--------------|-------------|---------------------|
| **E5**   | 2  (supertonic) | 124 | the verse "stutter" pitch |
| **C5**   | ♭7 (subtonic)   | 108 | the descending tail       |
| **D5**   | 1  (tonic)      | 104 | settles every phrase here |
| **F5**   | ♭3 (mediant)    |  52 | the *peak* — "FREED!"     |
| **B♭4**  | ♭6 (submediant) |  26 | the soulful suspension    |
| **A4**   | 5  (dominant)   |   8 | rare pickup               |

Range: **A4 → F5** (8 semitones, just under an octave). Stays squarely in
chest-voice register — that's what makes it singable.

## The two phrases that build everything

T7 is constructed from **two 1-bar building blocks** repeated and swapped.

### Phrase **A** — "FREED from de-sire" (the descending hook)

```
beat 1.00 :  F5     ← peak, lands on downbeat, holds ~½ beat
beat 1.75 :  D5     ← lift "from"
beat 2.50 :  D5
beat 3.00 :  C5
beat 3.50 :  C5     ← stutters down to ♭7
beat 3.75 :  C5
```

Shape: **F – D – D – C – C** = ♭3 → 1 → 1 → ♭7 → ♭7. Lands hard on the
mediant, falls a 4th, settles on ♭7. Then either resolves up to E5 (next
phrase) or down to B♭4 ("…purified-").

### Phrase **B** — the E5 stutter ("…mind and senses …")

```
beat 1.50 :  E5  (or  B♭4 → E5 in the chorus)
beat 2.00 :  E5
beat 2.50 :  E5
beat 3.00 :  E5
beat 3.50 :  E5
```

Five **even 8th-note E5s** on the back half of the bar. The first half is
either silent (verse) or held on B♭4 (chorus). The repetition makes the
"and-and-and-and-and" feel.

## Bar map of the whole song

```
bars 1– 4   intro (no vocal)
bars 5–12   VERSE 1 — sequence: B, A, B, A, B, A, B, A
              (B = stutter 5×E5;  A = F D D C C C Bb4)
bars 13–21  PRE-CHORUS — long sustained D5s with a 1-bar "C5 D5 D5 C5 D5
              A4 C5 D5" ornament every other bar (the "(my love has got no)
              money" sustained-line section)
bars 22–28  CHORUS 1   — A', B': new variant where A' = F D D C C and
              B' = F F F F E E E E  (the "FREED from desire, MIND and SENSES"
              uplift — quarter-note descending eighths)
bars 29–37  CHORUS 1 continued — back to A, B alternation, four times
bars 38–60  VERSE 2 / PRE-CHORUS 2 (mirrors 5–21)
bars 61–69  CHORUS 2  (mirrors 22–37)
bars 70–93  CHORUS 3 / outro — A, B repeats with a fade
```

The whole song is just **two bars** of melody used 40-something times in
different orderings, plus the pre-chorus "long D5" sections. That's the
secret of its earworm quality.

## Rhythm

- Every phrase fits inside one bar of 4/4.
- Note onsets sit on **off-beats** — most notes start on the "and" of a
  beat, not the beat itself. The downbeat-F5 in phrase A is the one
  exception, and that's what gives the hook its weight ("FREED!").
- Note durations are ~0.2 beats (a 16th-ish) for the stutters, ~0.6 beats
  for the held downbeats. Mostly 8th-note feel.

## What this means for the SID remix

1. **The hook to be obvious**: phrase A's F5 → D5 → C5 → Bb4 descent must
   land on the downbeat with the F5 *clearly louder/longer* than the
   surrounding notes.
2. **The E5 stutter is the hypnotic part**: keep its 5-note even spacing.
   Don't quantise it onto every 16th — the syncopation matters.
3. **Pre-chorus = sustained D5**: a near-static held note is the contrast
   that makes the chorus hit. Don't fill it with extra notes.
4. **Tempo**: at 175 BPM the stutters become very rapid (each E5 = ~85 ms).
   For HH that's correct — it becomes a buzz. At 130 BPM (original) the
   stutters are clearly singable ~115 ms apart. We can choose either.
5. **Octave**: A4–F5 sits in the C64 SID's prime range; no transposition
   needed.

## Source

T7 of `midi/Gala_Freed_From_Desire.mid` is the karaoke arrangement's
substitute for the singer (program 68 = shakuhachi). I cross-referenced the
phrase shapes against the published Hooktheory analysis (D minor, i-III-VI-VII)
and the chord-tab community transcriptions to make sure the scale degrees
match the original studio recording.
