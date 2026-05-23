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

1. **Drums verbatim from T13** (axis 3a) — the karaoke MIDI already has the
   actual drum pattern; using it should improve the groove and authenticity.
2. **Add T11 saw-lead hook on V3 during instrumental break** (axis 5).
3. **Vibrato on V2** (axis 1) so the vocal feels human.
4. **Two-build tempo split** (axis 4) — produce both versions.
5. Iterate on balance & structure based on listening.
