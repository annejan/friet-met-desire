#!/bin/bash
# Render a SID to MP3 by driving vsid headlessly.
# vsid writes a corrupt WAV header (the size field is wrong because we kill it
# mid-stream) but the raw PCM data after byte 44 is valid s16le @ 48 kHz mono.
set -euo pipefail

SID="${1:?sid file required}"
MP3="${2:?output mp3 path required}"
SECONDS="${3:-60}"

PAL_CLK=985248
CYCLES=$(( SECONDS * PAL_CLK ))
WAV=$(mktemp --suffix=.wav)
trap 'rm -f "$WAV"' EXIT

vsid -sounddev wav -soundarg "$WAV" -limitcycles "$CYCLES" "$SID" >/dev/null 2>&1 &
RPID=$!
sleep $(( SECONDS + 3 ))
kill -TERM "$RPID" 2>/dev/null || true
wait 2>/dev/null || true

# Decode raw PCM (skip 44-byte WAV header) and re-encode as MP3
ffmpeg -y -f s16le -ar 48000 -ac 1 -i <(tail -c +45 "$WAV") -t "$SECONDS" "$MP3" 2>&1 | tail -3
echo "wrote $MP3 ($SECONDS s)"
