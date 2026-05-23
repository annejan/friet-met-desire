# Friet van Desire — build SID remixes from MIDI research material
#
# Primary target:  make preview-clean   (the maintained song-faithful build)
# Verification:    make preview-melody  (vocal alone, no bass/drums)
# Legacy:          make hh / port       (early direct-conversion experiments)
.PHONY: all clean analyze preview \
        extract compose synth clean-pipeline preview-clean preview-melody \
        hh port preview-hh preview-port melody-only

SHELL      := /bin/bash
.ONESHELL:

PYTHON     := .venv/bin/python
SRC_DIR    := src
OUT_DIR    := out
MIDI_DIR   := midi
TOOLS_DIR  := tools

HH_SID    := $(OUT_DIR)/friet_from_desire_hh.sid
HH_MP3    := $(OUT_DIR)/friet_from_desire_hh.mp3
PORT_SID  := $(OUT_DIR)/friet_from_desire.sid
PORT_MP3  := $(OUT_DIR)/friet_from_desire.mp3
SPEC      := docs/song_spec.yaml
COMP      := docs/composition.yaml
CLEAN_SID := $(OUT_DIR)/friet_clean.sid
CLEAN_MP3 := $(OUT_DIR)/friet_clean.mp3
MELODY_SID := $(OUT_DIR)/friet_melody_only.sid
MELODY_MP3 := $(OUT_DIR)/friet_melody_only.mp3
HH_NEW_SID := $(OUT_DIR)/friet_hh.sid
HH_NEW_MP3 := $(OUT_DIR)/friet_hh.mp3
LAYERS    := docs/song_layers.yaml

PREVIEW_SECONDS ?= 90

all: clean-pipeline melody-only hh-build preview-clean preview-melody preview-hh-new

# --- research ----
analyze:
	$(PYTHON) $(SRC_DIR)/analyze_midi.py

# --- assemble SIDs ----
hh: $(HH_SID)
$(HH_SID): $(SRC_DIR)/midi2sid_hh.py $(MIDI_DIR)/Gala_Freed_From_Desire.mid
	$(PYTHON) $<

port: $(PORT_SID)
$(PORT_SID): $(SRC_DIR)/midi2sid.py $(MIDI_DIR)/Gala_Freed_From_Desire.mid
	$(PYTHON) $<

# --- maintained pipeline (extract -> compose -> synth) ----
# Phase 1: MIDI -> docs/song_spec.yaml (patterns) + docs/song_layers.yaml
#          (verbatim T5/T7/T11/T12/T13 note lists). The MIDI isn't read again.
extract: $(SPEC) $(LAYERS)
$(SPEC) $(LAYERS): $(SRC_DIR)/extract_patterns.py $(MIDI_DIR)/Gala_Freed_From_Desire.mid
	$(PYTHON) $<

# Phase 2: spec + layers -> docs/composition.yaml. No MIDI access.
compose: $(COMP)
$(COMP): $(SRC_DIR)/compose.py $(SPEC) $(LAYERS)
	$(PYTHON) $<

# Phase 3: composition -> PSID. Reads only composition.yaml.
synth: $(CLEAN_SID)
$(CLEAN_SID): $(SRC_DIR)/synth.py $(COMP)
	$(PYTHON) $<

clean-pipeline: $(CLEAN_SID)

preview-clean: $(CLEAN_MP3)
$(CLEAN_MP3): $(CLEAN_SID)
	$(TOOLS_DIR)/render-preview.sh $< $@ $(PREVIEW_SECONDS)

# Vocal-only verification build — useful when the surrounding mix obscures
# the melody and you need to confirm the notes themselves.
melody-only: $(MELODY_SID)
$(MELODY_SID): $(SRC_DIR)/compose.py $(SRC_DIR)/synth.py $(SPEC) $(LAYERS)
	MELODY_ONLY=1 $(PYTHON) $(SRC_DIR)/compose.py
	$(PYTHON) $(SRC_DIR)/synth.py
	cp $(CLEAN_SID) $@
	$(PYTHON) $(SRC_DIR)/compose.py
	$(PYTHON) $(SRC_DIR)/synth.py

preview-melody: $(MELODY_MP3)
$(MELODY_MP3): $(MELODY_SID)
	$(TOOLS_DIR)/render-preview.sh $< $@ $(PREVIEW_SECONDS)

# Happy-hardcore tempo variant — same data, rendered at 170 BPM.
hh-build: $(HH_NEW_SID)
$(HH_NEW_SID): $(SRC_DIR)/compose.py $(SRC_DIR)/synth.py $(SPEC) $(LAYERS)
	HH_TEMPO=1 $(PYTHON) $(SRC_DIR)/compose.py
	$(PYTHON) $(SRC_DIR)/synth.py
	cp $(CLEAN_SID) $@
	$(PYTHON) $(SRC_DIR)/compose.py
	$(PYTHON) $(SRC_DIR)/synth.py

preview-hh-new: $(HH_NEW_MP3)
$(HH_NEW_MP3): $(HH_NEW_SID)
	$(TOOLS_DIR)/render-preview.sh $< $@ $(PREVIEW_SECONDS)

# Stand-alone C64 .prg that plays the SID and shows lyrics in sync.
# Build with KickAssembler (kickass/KickAss.jar). Run with `x64sc out/friet_player.prg`.
PLAYER_PRG := $(OUT_DIR)/friet_player.prg
.PHONY: player
player: $(PLAYER_PRG)
$(PLAYER_PRG): $(SRC_DIR)/build_player.py $(SRC_DIR)/player/friet_player.asm \
               $(CLEAN_SID) docs/melody_lyrics.yaml
	$(PYTHON) $(SRC_DIR)/build_player.py

# --- previews ----
preview: preview-clean preview-melody

preview-hh: $(HH_MP3)
$(HH_MP3): $(HH_SID)
	$(TOOLS_DIR)/render-preview.sh $< $@ $(PREVIEW_SECONDS)

preview-port: $(PORT_MP3)
$(PORT_MP3): $(PORT_SID)
	$(TOOLS_DIR)/render-preview.sh $< $@ $(PREVIEW_SECONDS)

clean:
	rm -f $(OUT_DIR)/*.sid $(OUT_DIR)/*.wav $(OUT_DIR)/*.mp3
	rm -f /tmp/freed*.s /tmp/freed*.prg
