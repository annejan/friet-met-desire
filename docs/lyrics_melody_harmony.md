# Lyrics × Melody × Harmony — how TL-Buis maps onto FFD

This document maps each Dutch lyric line onto its melodic phrase,
chord context, and section role. Use it to verify that the parody
lyrics "fit" the original melody's phrasing and emotional arc.

## Structure match

The TL-Buis lyrics follow the exact same **call-and-response** structure
as the original English:

| Original structure | Original lyric | TL-Buis lyric | Melodic phrase |
|--------------------|---------------|---------------|----------------|
| Verse line A (×4)  | "My love has got no money" | "Mijn crew die heeft geen centen" | V-X: E5 stutter → F5 → D5 |
| Verse line B (×4)  | "He's got his strong beliefs" | "maar wel een zieke scroll" | V-Y: D5 → C5 stutter → B♭4 |
| Pre-chorus A (×4)  | "Want more and more" | "Meer en meer" | PC-X: A4 → C5 → D5 pickup |
| Pre-chorus B (×4)  | "People just want more..." | "iedereen wil meer en meer" | PC-Y: D5-C5 weaving |
| Chorus A (×4)      | "Freed from desire" | "Friet van Desire" | C-A: F5 → D5 → C5 **tresillo** |
| Chorus B (×3)      | "Mind and senses purified" | "SID en VIC slaan door" | C-B: F5×4 → E5×4 straight 8ths |
| Na-na A (×4)       | "Na na na na na..." | "Na-na-na-na-na-na-na" | V-X (same as verse!) |
| Na-na B (×4)       | "na na na na na..." | "na-na-na door de zaal" | V-Y (same as verse!) |

## Syllable-fit notes

### Verse — good fit
- "Mijn crew die heeft geen centen" = 7 syllables on 7 notes (E5×5 + F5 + D5)
- "maar wel een zieke scroll" = 6 syllables on 6 notes (D5 + C5×4 + B♭4)
- Original: "My love has got no money" = 7 syllables ✓

### Pre-chorus — good fit  
- "Meer en meer" = 3 syllables on 4 notes (A4 + C5 + D5 + D5). The held
  D5 at the end can sustain under "meer". ✓
- "iedereen wil meer en meer" = 7 syllables on 7 notes. ✓

### Chorus — excellent fit
- "Friet van Desire" = 4 syllables on 5 notes (F5 + D5 + D5 + C5 + C5).
  "De-si-re" maps to D5-C5-C5 with the last C5 as sustain. ✓
  **Pun alignment**: "Friet" hits on F5 (the peak) just like "Freed". 🍟
- "SID en VIC slaan door" = 5 syllables on 8 notes (F5×4 + E5×4).
  The straight 8ths carry the words "SID en VIC slaan door" with each
  syllable spanning ~2 notes. ✓

### Na-na — direct match
- "Na-na-na-na-na-na-na" = same syllable count as V-X stutter. ✓
- "na-na-na door de zaal" = V-Y descent. ✓

### Chorus 2 — alternative lyrics
- "SID en VIC staan rood" replaces "slaan door" — same syllable count. ✓
- "heel de sporthal sloopt zichzelf" = 7 syllables on 8 notes. ✓
- "alle scanlines zwaar verstoord" = 7 on 8. ✓

### Chorus 3 — callback + greeting
- Reuses chorus 1 lyrics for bars 1-6.
- Final bar: "groetjes van TL-Buis" replaces "Friet van Desire" —
  4 syllables on 5 notes, same fit. The C-A tresillo carries the greet.

## Chord context per section

| Section | Chord cycle | Bass behaviour |
|---------|------------|----------------|
| Verse (21.5-54.5) | Dm pedal throughout | V1 interleaving D2 stab |
| Pre-chorus (54.5-88) | Dm pedal | V1 interleaving D2 stab |
| Chorus (88-117.5) | Dm → F → B♭ → C per bar | V1 interleaving D2 stab (no chord-follow yet) |
| Na-na (117.5-149.5) | C → Dm → F → B♭ (continues cycle) | V1 interleaving D2 stab |
| Chorus 2/3 reprises | Same as Chorus 1 | Same |

Note: V1 currently plays D2 pedal throughout (no chord-following). The
harmonic colour comes entirely from V2's melody notes sitting on
different chord tones per bar. The D2 pedal acts as a drone.

## Open questions for TL-Buis

1. **Verse 2 lyrics exist** ("Mijn code draait op floppies...") but our
   arrangement has NO verse 2 segment. If we extend the song, these
   lines slot into bars at output beats ~192+.
2. **Pre-chorus 2** lyrics ("Meer en meer / meer MHz / maar die code
   compileert niet eens") — also cut from our arrangement. Same issue.
3. **Lyric line lengths**: some Dutch lines are longer than their English
   counterparts. The to_screen() word-wrap handles overflow (splits into
   multiple 40-col events) but fast-scrolling text might feel rushed at
   175 BPM.

