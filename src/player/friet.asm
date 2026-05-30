// Friet met Desire -- C64 player with synchronised lyrics ticker
//
// Build:    java -jar kickass/KickAss.jar src/player/friet.asm
// Run:      x64sc out/friet.prg
//
// Memory layout:
//   $0801-$080F  BASIC stub (10 SYS 2064)
//   $0810-       Player code + lyrics table
//   $1000-       SID body (loaded straight into place by the PRG)

.const SID_INIT = $1000
.const SID_PLAY = $1003

// Zero-page is dangerous territory: the SID's PLAY routine (synth.py)
// uses $02-$0F for its own counters/filter state, and $F7/$FB/$FD for
// pointers. We must NOT collide — every IRQ would clobber our variables.
// Use $90-$96 instead — KERNAL I/O scratch that's idle when we're not
// using LOAD/SAVE, and not touched by the SID player.
.var frame_lo = $90
.var frame_hi = $91
.var ly_lo    = $92
.var ly_hi    = $93
.var tmp_len  = $94
.var tmp_col  = $95
.var end_col  = $96
// Rave-visual state (beat-reactive). $97-$99 are KERNAL scratch, idle here.
.var beat_flash = $97       // 6..0 strobe decay; armed on beat / lyric onset
.var gate_prev  = $98       // previous V2 gate bit for edge-detect
.var beat_count = $99       // beats seen; nudges the banner glide phase

// ---- BASIC stub: 10 SYS 2064 ------------------------------------------
*=$0801
    .byte $0B, $08, $0A, $00, $9E
    .text "2064"
    .byte $00, $00, $00

// ---- Player code ------------------------------------------------------
*=$0810
entry:
    sei
    // Zero SID player's ZP work area ($02-$0F). SID_INIT doesn't
    // touch these — they're expected at $00 on first SID_PLAY call.
    // Clean BASIC boot has them zeroed by CLR, but when loaded as an
    // easter egg from inside a demo (copier at $0200), residue from
    // the demo's ZP causes the SID player's counters to start at
    // wrong values → lyrics desync.
    lda #0
    ldx #$0d
!zpclr:
    sta $02,x
    dex
    bpl !zpclr-
    sta frame_lo
    sta frame_hi
    sta beat_flash
    sta gate_prev
    sta beat_count
    lda #<lyric_table
    sta ly_lo
    lda #>lyric_table
    sta ly_hi

    // Switch to lowercase character set
    lda #$17
    sta $D018

    // Border + background black
    lda #$00
    sta $D020
    sta $D021

    // Clear screen
    lda #$20
    ldx #0
!loop:
    sta $0400,x
    sta $0500,x
    sta $0600,x
    sta $0700,x
    inx
    bne !loop-

    // Set screen colour to light cyan everywhere
    lda #$03
    ldx #0
!loop:
    sta $D800,x
    sta $D900,x
    sta $DA00,x
    sta $DB00,x
    inx
    bne !loop-

    // Header banner at row 1
    ldx #0
!loop:
    lda banner_top,x
    beq !done+
    sta $0400 + 40*1 + 4,x
    inx
    jmp !loop-
!done:

    // Footer credit at row 23
    ldx #0
!loop:
    lda banner_bottom,x
    beq !done+
    sta $0400 + 40*23 + 4,x
    inx
    jmp !loop-
!done:

    // Initialise the SID (subtune 0)
    lda #0
    tax
    tay
    jsr SID_INIT

    // Hook the IRQ vector
    lda #<irq
    sta $0314
    lda #>irq
    sta $0315
    // Disable CIA timer IRQs; switch to VIC raster IRQ
    lda #$7F
    sta $DC0D
    sta $DD0D
    lda $DC0D
    lda $DD0D
    lda #$01
    sta $D01A
    lda #250
    sta $D012
    lda $D011
    and #$7F
    sta $D011
    cli
!forever:
    jmp !forever-

// ---- 50 Hz IRQ: SID play + lyric ticker -------------------------------
irq:
    lda #$FF
    sta $D019
    jsr SID_PLAY
    jsr maybe_show_lyric
    jsr animate_rave
    // Increment frame counter AFTER both SID_PLAY and lyric check so
    // both see the same frame number. Previously the increment sat
    // between them, making lyrics check frame N+1 while audio played
    // frame N — a systematic 1-frame-early bias. (ADHD competitor frame)
    inc frame_lo
    bne !nh+
    inc frame_hi
!nh:
    jmp $EA81

maybe_show_lyric:
    // Sentinel: ($FFFF, *, ...) = end-of-table, stop ticking.
    ldy #0
    lda (ly_lo),y
    cmp #$FF
    bne !nx+
    iny
    lda (ly_lo),y
    cmp #$FF
    bne !nx+
    rts
!nx:
    // Compare frame_hi:frame_lo == lyric timestamp (hi:lo).
    // Exact match — one lyric per frame, no catch-up racing.
    ldy #0
    lda (ly_lo),y
    cmp frame_lo
    bne !not_yet+
    iny
    lda (ly_lo),y
    cmp frame_hi
    bne !not_yet+

    // Read length, compute centred starting column
    iny
    lda (ly_lo),y           // y=2, length
    sta tmp_len

    // Clear row 12
    lda #$20
    ldx #39
!clr:
    sta $0400 + 40*12,x
    dex
    bpl !clr-

    // Compute centring: tmp_col = (40 - tmp_len) / 2
    lda #40
    sec
    sbc tmp_len
    lsr
    sta tmp_col
    // end_col = tmp_col + tmp_len
    clc
    adc tmp_len
    sta end_col

    // Punch the strobe on every lyric onset — vocals are frame-synced
    // to the music by construction, so this lands the visual on the words.
    lda #6
    sta beat_flash

    // Highlight row 12 in yellow ($07) while a lyric is showing
    lda #$07
    ldx #39
!col:
    sta $D800 + 40*12,x
    dex
    bpl !col-

    // Copy text bytes to screen, starting at column tmp_col
    iny                      // y=3, first text byte
    ldx tmp_col
!cp:
    cpx end_col
    beq !cp_done+
    lda (ly_lo),y
    sta $0400 + 40*12,x
    iny
    inx
    jmp !cp-
!cp_done:
    // Advance ly_lo/hi by (3 header + tmp_len text)
    clc
    lda ly_lo
    adc tmp_len
    sta ly_lo
    lda ly_hi
    adc #0
    sta ly_hi
    clc
    lda ly_lo
    adc #3
    sta ly_lo
    lda ly_hi
    adc #0
    sta ly_hi
!not_yet:
    rts

// ---- animate_rave: beat-reactive gabber visuals -----------------------
// Two layers, one vsync IRQ, all writes at the top of the frame -> no
// raster chain, rock-solid:
//   1. ALWAYS-ALIVE: the top/bottom banners glide through an 8-colour
//      rave palette every few frames, so the screen never sits dead.
//   2. STROBE PUNCH: on every kick (V2 gate rising edge) AND on every
//      lyric onset (set from maybe_show_lyric), a 6-frame strobe fires:
//      the BORDER punches white->yellow->red->black and the LYRIC row
//      flashes white then settles to yellow. Background stays black so
//      the words never wash out.
// V2 ($D40B) is the busiest voice in the new-standard arrangement (V1
// holds its gate as the bass drone, V3 is sparse) -> driving the punch
// off V2's gate gives the tightest visible pump.
animate_rave:
    // --- layer 1: continuous banner colour glide ---
    lda frame_lo
    lsr
    lsr
    lsr                         // /8: one step every ~8 frames
    clc
    adc beat_count              // beats nudge the phase so it never loops flat
    and #$07
    tax
    lda rave_pal,x
    ldx #39
!br:
    sta $d800 + 40*1,x
    sta $d800 + 40*23,x
    dex
    bpl !br-

    // --- beat detect: V2 gate rising edge ---
    lda $d40b
    and #$01
    tax
    cmp gate_prev
    stx gate_prev
    beq !no_beat+
    txa
    beq !no_beat+               // gate fell -> ignore
    lda #6
    sta beat_flash              // (re)arm the strobe
    inc beat_count
!no_beat:

    // --- layer 2: border strobe ---
    ldx beat_flash
    lda border_pal,x
    sta $d020

    // --- lyric row ($0400+40*12) colour: flash white, settle yellow ---
    ldx beat_flash
    lda lyric_pal,x
    ldx #39
!lr:
    sta $d800 + 40*12,x
    dex
    bpl !lr-

    // --- decay the strobe ---
    lda beat_flash
    beq !done+
    dec beat_flash
!done:
    rts

// Strobe palettes, indexed by beat_flash (6 = freshest kick, 0 = idle).
border_pal:                     //  0    1    2    3    4    5    6
    .byte $00, $0b, $02, $08, $0a, $07, $01   // black..white
lyric_pal:                      // readable: yellow base, white on the hit
    .byte $07, $07, $07, $07, $07, $01, $01
rave_pal:                       // 8-colour gabber cycle for the banners
    .byte $01, $07, $0a, $02, $04, $0e, $03, $05

// ---- Static banners (screen-code bytes generated by src/build_player.py) --
banner_top:
    .import binary "banner_top.bin"
    .byte 0
banner_bottom:
    .import binary "banner_bottom.bin"
    .byte 0

lyric_table:
    .import binary "lyric_table.bin"
    .byte $FF, $FF, $00       // sentinel

// ---- SID body --------------------------------------------------------
*=$1000
sid_body:
    .import binary "sid_body.bin"
