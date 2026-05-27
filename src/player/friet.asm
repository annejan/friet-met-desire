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

    // ---- Friet sprite cluster (2×2, multicolour) ----
    // 4 sprites forming a 48×42 fries-in-a-bag icon, centered on screen.
    lda #$0f
    sta $d015                 // enable sprites 0-3
    lda #$0f
    sta $d01c                 // sprites 0-3 = multicolour
    lda #$00
    sta $d017                 // no Y-expand
    sta $d01d                 // no X-expand
    sta $d01b                 // sprites in front of text
    // MC shared colours
    lda #$07
    sta $d025                 // MC1 = yellow (fries)
    lda #$09
    sta $d026                 // MC2 = brown (crispy bits)
    // Per-sprite colour = red (container)
    lda #$02
    sta $d027
    sta $d028
    sta $d029
    sta $d02a
    // Positions: centered on screen (VIC X=184 center, Y=110 top)
    // Top-left (spr0): X=148, Y=110
    lda #148
    sta $d000
    lda #110
    sta $d001
    // Top-right (spr1): X=172, Y=110
    lda #172
    sta $d002
    lda #110
    sta $d003
    // Bot-left (spr2): X=148, Y=131
    lda #148
    sta $d004
    lda #131
    sta $d005
    // Bot-right (spr3): X=172, Y=131
    lda #172
    sta $d006
    lda #131
    sta $d007
    lda #$00
    sta $d010                 // no X MSB needed (all < 256)
    // Sprite pointers (address / 64)
    lda #(spr_fries_tl / 64)
    sta $07f8
    lda #(spr_fries_tr / 64)
    sta $07f9
    lda #(spr_fries_bl / 64)
    sta $07fa
    lda #(spr_fries_br / 64)
    sta $07fb

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

// ---- 50 Hz IRQ: SID play + lyric ticker + fries animation ------------
irq:
    lda #$FF
    sta $D019
    jsr SID_PLAY
    jsr maybe_show_lyric
    jsr animate_fries
    inc frame_lo
    bne !nh+
    inc frame_hi
!nh:
    jmp $EA81

// ---- Fries animation: beat-reactive hop + sizzle shimmer -------------
// ~12 cycles per frame on calm frames, ~30 on accent frames.
.var fries_base_y  = 110           // resting Y for top sprites
.var fries_hop_frames = 6          // frames per hop event

animate_fries:
    // ---- Sizzle shimmer: rotate MC bit on one sprite per frame ----
    // Toggles $D01C bits 0-3 in round-robin so each sprite briefly
    // flashes hires (reinterprets MC pixel data = sparkle/sizzle).
    lda frame_lo
    and #$07                       // 8-frame cycle
    cmp #4
    bcs !no_sizzle+                // only sizzle on frames 0-3
    tax
    lda $d01c
    eor sizzle_mask,x              // flip one sprite's MC bit
    sta $d01c
!no_sizzle:

    // ---- Beat-reactive hop: accent detection via SID V3 gate ----
    // Read V3 control register — if gate just went ON (drum hit),
    // trigger a 6-frame hop sequence. Cheap proxy for beat detection
    // since my_music_play gates V3 on every kick/snare.
    lda $d412                      // V3 control: bit 0 = gate
    and #$01
    beq !no_trigger+
    lda hop_active
    bne !no_trigger+               // already hopping
    lda #fries_hop_frames
    sta hop_active                 // start hop
!no_trigger:

    lda hop_active
    beq !hop_done+

    // Hop sequence: quick rise (3 frames) + squash land (3 frames)
    cmp #4                         // frames 6-4 = rising
    bcs !rising+
    // Landing: X-expand ON for squash, return to base Y
    lda #$0f
    sta $d01d                      // X-expand sprites 0-3
    lda #fries_base_y
    sta $d001
    sta $d003
    lda #(fries_base_y + 21)
    sta $d005
    sta $d007
    jmp !hop_tick+
!rising:
    // Rising: X-expand OFF, shift Y up
    lda #$00
    sta $d01d
    lda hop_active
    sec
    sbc #3                         // 3,2,1 → displacement 3-6px
    asl
    sta hop_disp
    lda #fries_base_y
    sec
    sbc hop_disp
    sta $d001
    sta $d003
    lda #(fries_base_y + 21)
    sec
    sbc hop_disp
    sta $d005
    sta $d007
!hop_tick:
    dec hop_active
    bne !hop_done+
    // Hop ended: restore X-expand OFF, base Y
    lda #$00
    sta $d01d
    lda #fries_base_y
    sta $d001
    sta $d003
    lda #(fries_base_y + 21)
    sta $d005
    sta $d007
!hop_done:
    rts

sizzle_mask:
    .byte %00000001, %00000010, %00000100, %00001000
hop_active:
    .byte 0
hop_disp:
    .byte 0

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

// ---- Friet sprite shapes (multicolour, 2×2 cluster) -----------------
// MC pixels: 00=bg, 01=yellow($D025), 10=brown($D026), 11=red(spr col)
// 12 MC-pixels wide × 21 rows per sprite.
// Placed after lyric_table, before SID body. .align 64 ensures sprite
// pointer = address / 64 is clean.

.align 64
spr_fries_tl:   // top-left: fries tips + container rim left
        .byte %00000000, %00000000, %00000000   // ............
        .byte %00000100, %01000001, %00000000   // ..1.1..1....
        .byte %00000100, %01000001, %00000000   // ..1.1..1....
        .byte %00000100, %01000101, %00000000   // ..1.1.11....
        .byte %00010100, %01000101, %00010000   // .11.1.11.1..
        .byte %00010100, %01000101, %00010000   // .11.1.11.1..
        .byte %00010101, %01000101, %01010000   // .1111.1111..
        .byte %00010101, %01100101, %01010100   // .1111211111.
        .byte %00010101, %10010101, %01010100   // .1112111111.
        .byte %00010101, %10010101, %01010100   // .1112111111.
        .byte %01010101, %10010101, %01010101   // 111121111111
        .byte %01010101, %10010101, %01010101   // 111121111111
        .byte %01010101, %01010101, %01010101   // 111111111111
        .byte %11111111, %11111111, %11111111   // 333333333333
        .byte %11111111, %11111111, %11111111   // 333333333333
        .byte %11111111, %11111111, %11110000   // 3333333333..
        .byte %11111111, %11111111, %11000000   // 333333333...
        .byte %11111111, %11111111, %00000000   // 33333333....
        .byte %11111111, %11111100, %00000000   // 3333333.....
        .byte %11111111, %11110000, %00000000   // 333333......
        .byte %11111111, %11000000, %00000000   // 33333.......
        .byte 0

.align 64
spr_fries_tr:   // top-right: fries tips + container rim right
        .byte %00000000, %00000000, %00000000   // ............
        .byte %00000000, %01000001, %00010000   // ....1..1.1..
        .byte %00000000, %01000001, %00010000   // ....1..1.1..
        .byte %00000000, %01010001, %00010000   // ....11.1.1..
        .byte %00000100, %01010001, %00010100   // ..1.11.1.11.
        .byte %00000100, %01010001, %00010100   // ..1.11.1.11.
        .byte %00000101, %01010001, %01010100   // ..1111.1111.
        .byte %00010101, %01011001, %01010000   // .111112111..
        .byte %00010101, %01011001, %01010000   // .111112111..
        .byte %00010101, %01010101, %01010000   // .111111111..
        .byte %01010101, %01011001, %01010101   // 111111211111
        .byte %01010101, %01011001, %01010101   // 111111211111
        .byte %01010101, %01010101, %01010101   // 111111111111
        .byte %11111111, %11111111, %11111111   // 333333333333
        .byte %11111111, %11111111, %11111111   // 333333333333
        .byte %00001111, %11111111, %11111111   // ..3333333333
        .byte %00000011, %11111111, %11111111   // ...333333333
        .byte %00000000, %11111111, %11111111   // ....33333333
        .byte %00000000, %00111111, %11111111   // .....3333333
        .byte %00000000, %00001111, %11111111   // ......333333
        .byte %00000000, %00000011, %11111111   // .......33333
        .byte 0

.align 64
spr_fries_bl:   // bottom-left: container taper left
        .byte %11111111, %11000000, %00000000   // 33333.......
        .byte %11111111, %00000000, %00000000   // 3333........
        .byte %11111100, %00000000, %00000000   // 333.........
        .byte %11110000, %00000000, %00000000   // 33..........
        .byte %00000000, %00000000, %00000000   // ............
        .byte %00000000, %00000000, %00000000
        .byte %00000000, %00000000, %00000000
        .byte %00000000, %00000000, %00000000
        .byte %00000000, %00000000, %00000000
        .byte %00000000, %00000000, %00000000
        .byte %00000000, %00000000, %00000000
        .byte %00000000, %00000000, %00000000
        .byte %00000000, %00000000, %00000000
        .byte %00000000, %00000000, %00000000
        .byte %00000000, %00000000, %00000000
        .byte %00000000, %00000000, %00000000
        .byte %00000000, %00000000, %00000000
        .byte %00000000, %00000000, %00000000
        .byte %00000000, %00000000, %00000000
        .byte %00000000, %00000000, %00000000
        .byte %00000000, %00000000, %00000000
        .byte 0

.align 64
spr_fries_br:   // bottom-right: container taper right
        .byte %00000000, %00000011, %11111111   // .......33333
        .byte %00000000, %00000000, %11111111   // ........3333
        .byte %00000000, %00000000, %00111111   // .........333
        .byte %00000000, %00000000, %00001111   // ..........33
        .byte %00000000, %00000000, %00000000   // ............
        .byte %00000000, %00000000, %00000000
        .byte %00000000, %00000000, %00000000
        .byte %00000000, %00000000, %00000000
        .byte %00000000, %00000000, %00000000
        .byte %00000000, %00000000, %00000000
        .byte %00000000, %00000000, %00000000
        .byte %00000000, %00000000, %00000000
        .byte %00000000, %00000000, %00000000
        .byte %00000000, %00000000, %00000000
        .byte %00000000, %00000000, %00000000
        .byte %00000000, %00000000, %00000000
        .byte %00000000, %00000000, %00000000
        .byte %00000000, %00000000, %00000000
        .byte %00000000, %00000000, %00000000
        .byte %00000000, %00000000, %00000000
        .byte %00000000, %00000000, %00000000
        .byte 0

// ---- SID body --------------------------------------------------------
*=$1000
sid_body:
    .import binary "sid_body.bin"
