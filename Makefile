# Friet From Desire — build SID remixes from MIDI research material
.PHONY: all clean analyze hh port preview preview-hh preview-port \
        extract compose synth clean-pipeline preview-clean

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

PREVIEW_SECONDS ?= 90

all: hh port clean-pipeline preview

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

# --- cleanroom pipeline (extract -> compose -> synth) ----
# Phase 1: read MIDIs, write abstract spec. The MIDIs are never read again.
extract: $(SPEC)
$(SPEC): $(SRC_DIR)/extract_patterns.py $(MIDI_DIR)/Gala_Freed_From_Desire.mid
	$(PYTHON) $<

# Phase 2: read spec, write concrete arrangement. No MIDI access allowed.
compose: $(COMP)
$(COMP): $(SRC_DIR)/compose.py $(SPEC)
	$(PYTHON) $<

# Phase 3: read composition, write PSID. No MIDI, no spec — only the arrangement.
synth: $(CLEAN_SID)
$(CLEAN_SID): $(SRC_DIR)/synth.py $(COMP)
	$(PYTHON) $<

clean-pipeline: $(CLEAN_SID)

preview-clean: $(CLEAN_MP3)
$(CLEAN_MP3): $(CLEAN_SID)
	$(TOOLS_DIR)/render-preview.sh $< $@ $(PREVIEW_SECONDS)

# --- preview MP3s ----
preview: preview-hh preview-port preview-clean

preview-hh: $(HH_MP3)
$(HH_MP3): $(HH_SID)
	$(TOOLS_DIR)/render-preview.sh $< $@ $(PREVIEW_SECONDS)

preview-port: $(PORT_MP3)
$(PORT_MP3): $(PORT_SID)
	$(TOOLS_DIR)/render-preview.sh $< $@ $(PREVIEW_SECONDS)

clean:
	rm -f $(OUT_DIR)/*.sid $(OUT_DIR)/*.wav $(OUT_DIR)/*.mp3
	rm -f /tmp/freed*.s /tmp/freed*.prg
