# Polish plan — Friet van Desire

**Status:** the underlying composition (T5 verbatim bass + T7 verbatim vocal +
T12 intro swell + 4-on-floor drums, all at source 130 BPM) is finally
recognisable as "Freed from Desire". From here it's polish.

## Five axes to push, in priority order

### 1. Sound (tone & timbre of each voice)

| Voice | Now                                | Direction                              |
|-------|------------------------------------|----------------------------------------|
| V1 bass | Pulse, PW=$0800, AD=$08 SR=$C4  | Try wider/narrower PW; maybe sub-pulse with a low-pass touch |
| V2 vocal | Triangle, AD=$12 SR=$F6, filter OFF | Subtle vibrato (LFO ±$08 on freq), gentle attack so syllables phrase |
| V3 drums | Noise per-hit ADSR per kit piece | Maybe pitch-bend the kick down for thump; reduce hat brightness if it returns |

Concrete: re-enable apply_vibrato on V2 (was disabled when we removed the
filter); add small LFO depth so the vocal doesn't feel deadpan.

### 2. Balance (mix levels)

There's no per-voice volume on SID — the master volume is global. Balance comes
from envelope sustain levels and the dynamic range of each waveform. Triangle is
inherently quieter than pulse/saw; noise is loud. Current mix has all three at
sustain ≈ $F. Try:

- bass sustain $A (slightly behind)
- vocal sustain $F (front)
- drum sustain (decay-only envelopes) — already in shape

### 3. Drums (groove)

Currently kick + clap (from compose's spec-driven 1-bar grid). Options:

- **3a**: Use **T13 verbatim** kick/snare/clap events (more authentic).
- **3b**: Keep generated 4-on-floor; add open-hat on offbeats during chorus
  (was disabled to reduce density).
- **3c**: Cymbal swells at section transitions (T12 already does this for the
  intro — replicate at the chorus drop).

### 4. Tempo

We dropped to source 130 BPM to recover the melody. The user originally wanted
happy hardcore (170-180 BPM). Path forward:

- Render two builds: `friet_clean.sid` (130 BPM, song-faithful) and
  `friet_hh.sid` (175 BPM, rave). Use the same source data; only the BPM
  parameter changes.
- The vocal will sound faster (chipmunked) at 175 BPM but stays recognisable
  now that we have the right notes.

### 5. Structure / arrangement

Now we have all four MIDI sections in the data (intro, verse, pre-chorus,
chorus, post-chorus, instrumental break, outro). The current SID plays
straight through. We can:

- Trim the SID to a short single loop (intro → chorus → na-na hook → out)
- Add a build-up snare roll into each chorus
- Use V3 to ALSO play the T11 saw-lead "na-na" hook during the instrumental
  break, since drums and lead never conflict in time there

## Where each axis lives in the code

- Sound: `src/synth.py` — `V1_AD/V2_AD/V3_AD` constants and the player asm.
- Balance: same file, envelope sustain nibbles.
- Drums: `src/compose.py` — section loop's `drum_events.append(...)` paths.
  T13 verbatim path is not implemented yet; would need extending
  `extract_patterns.py` to dump T13 events to `song_layers.yaml`.
- Tempo: `src/compose.py` — `HH_BPM` / `play_bpm_*` and the MELODY_ONLY env.
- Structure: `src/compose.py` — `sections` template + the bar loop.

## Suggested order

1. ✅ **Drums verbatim from T13** (axis 3a) — done. `compose.py` now reads
   T13 events from `song_layers.yaml`, maps GM drum codes to our kit
   (kick/snare/hat — snare 38/40 and clap 39 both map onto our "snare"),
   and filters per section.
2. ✅ **T11 4-note hook as bass before T5 enters** (axis 5 variant) —
   done. V1 plays T11 (−12) looped from beat 5 until T5 takes over at
   beat 120, then T11 again at its natural octave during the instrumental
   break.
3. ✅ **Audible noise swell** — done. Crash envelope rewritten as a slow
   800 ms attack with held sustain so the rise is heard.
4. ✅ **Section-based drum dynamics** — done. Verses are kick-only,
   pre-choruses add snare, choruses go full kit (kick + snare + hat).
   The section boundaries come from T2's `\` markers, so the dynamics
   align to the song's actual structure.
5. 🟡 **Vibrato on V2 vocal** — TODO. The triangle vocal is dead-pan.
   Re-enable apply_vibrato with subtle depth (±$06 on freq) so syllables
   feel sung. Was disabled when we ripped out the filter; bring it back
   safely with the "skip when V2BASE = 0" guard.
6. 🟡 **HH tempo variant** — TODO. Render the same data at 170 BPM
   (sped up 1.3×) as `out/friet_hh.sid` while keeping `friet_clean.sid`
   at the song-faithful 130 BPM.
7. 🟡 **Reprise / dynamics push** — TODO. Once verses are light and
   choruses heavy, see if Chorus 2 should hit even harder than Chorus 1
   (e.g. crash swell preceding it, hat density up).
