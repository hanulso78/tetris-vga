/* ============================================================================
 *  ttvga.c  -  개선판(TETVGA): 같은 게임 코드가 그린 CGA 화면을 256색으로
 * ----------------------------------------------------------------------------
 *  게임 코드는 손대지 않는다.  대신 메모리 바이트마다 '색표' COL[] 을 두고,
 *  그림의 출처에 미리 256색을 적어 둔다:
 *    - 배경 그림 열두 장 (BKGR0..9, SLC, TETRIS.TTL): TTVGA.DAT 에 다시 칠해 둔 것을
 *      파일을 읽는 자리(또는 눌림을 푼 자리)에 그대로 적는다.
 *    - 조각 칸 여덟 개 (DS:003F..00BF): 보석처럼 그린 8x8 색.
 *  게임이 그 바이트를 옮기면(movs, lods/stos) 색표도 같이 따라간다(cpu.h).
 *  화면을 낼 때는 색표가 있는 점은 그 색으로, 없는 점은 원래 CGA 색으로 칠한다.
 * ========================================================================== */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "cpu.h"
#include "ttvga.h"
#include "ttvars.h"

uint8_t vga_pal[256][3];
uint32_t vga_ms;

#define NPIC 16
static int npic;
static char picname[NPIC][16];
static uint8_t *picdata[NPIC];          /* 320x200 팔레트 번호 */
static uint8_t tiles[8][64];            /* 조각 칸 8x8 */
static char cur_name[16];               /* 마지막으로 연 그림 파일 */

/* 색표가 없는 점: 원판 CGA 모드 5 의 네 색 */
static uint8_t fallback[4];

static uint8_t nearest(int r, int g, int b)
{
    int i, best = 1 << 30, bi = 0;

    for (i = 0; i < 256; i++) {
        int dr = vga_pal[i][0] - r, dg = vga_pal[i][1] - g, db = vga_pal[i][2] - b;
        int d = dr * dr * 3 + dg * dg * 4 + db * db * 2;
        if (d < best) {
            best = d;
            bi = i;
        }
    }
    return (uint8_t)bi;
}

/* tools/mkvga.py 의 pack() 을 되돌린다 */
static void unpack(const uint8_t *src, uint32_t n, uint8_t *dst, uint32_t dn)
{
    uint32_t i = 0, o = 0;

    while (i < n && o < dn) {
        uint8_t c = src[i++];
        if (c & 0x80) {
            uint32_t run = (uint32_t)(c - 0x80) + 3;
            uint8_t v = src[i++];
            while (run-- && o < dn)
                dst[o++] = v;
        } else {
            uint32_t k = (uint32_t)c + 1;
            while (k-- && o < dn && i < n)
                dst[o++] = src[i++];
        }
    }
}

int vga_load(const char *path)
{
    FILE *f = fopen(path, "rb");
    uint8_t hdr[8];
    int i, k;

    if (!f)
        return 0;
    if (fread(hdr, 1, 8, f) != 8 || memcmp(hdr, "TTVGA1", 6)) {
        fclose(f);
        return 0;
    }
    if (fread(hdr, 1, 2, f) != 2) {
        fclose(f);
        return 0;
    }
    npic = hdr[0] | (hdr[1] << 8);
    if (npic > NPIC)
        npic = NPIC;
    if (fread(vga_pal, 1, 768, f) != 768) {
        fclose(f);
        return 0;
    }
    if (fread(tiles, 1, sizeof tiles, f) != sizeof tiles) {
        fclose(f);
        return 0;
    }
    for (i = 0; i < npic; i++) {
        uint8_t len[4], *buf;
        uint32_t n;
        if (fread(picname[i], 1, 16, f) != 16 || fread(len, 1, 4, f) != 4)
            break;
        n = (uint32_t)len[0] | ((uint32_t)len[1] << 8) | ((uint32_t)len[2] << 16) | ((uint32_t)len[3] << 24);
        buf = (uint8_t *)malloc(n);
        picdata[i] = (uint8_t *)malloc(320 * 200);
        if (!buf || !picdata[i] || fread(buf, 1, n, f) != n) {
            free(buf);
            fclose(f);
            return 0;
        }
        unpack(buf, n, picdata[i], 320 * 200);
        free(buf);
    }
    fclose(f);
    /* 색표 없는 점에 쓸 CGA 네 색 */
    fallback[0] = nearest(0, 0, 0);
    fallback[1] = nearest(0, 42, 42);
    fallback[2] = nearest(42, 0, 0);
    fallback[3] = nearest(42, 42, 42);
    for (k = 0; k < 4; k++)
        if (fallback[k] == 0)
            fallback[k] = 16;               /* 0 번은 '색 없음' 이라 쓰지 않는다 */
    return npic > 0;
}

/* ---- 색표 붙이기 -------------------------------------------------------------- */
#define PIXCOL(c, k) (uint32_t)((uint32_t)(c) << (8 * (k)))

/* 조각 칸 여덟 개 (DS:003F 부터 16 바이트씩) */
void vga_reset(void)
{
    int t, y, b, k;

    for (t = 0; t < 8; t++) {
        uint32_t base = LIN(DSEG, (uint16_t)(tile_blank + 16 * t));
        for (y = 0; y < 8; y++)
            for (b = 0; b < 2; b++) {
                uint32_t c = 0;
                for (k = 0; k < 4; k++)
                    c |= PIXCOL(tiles[t][y * 8 + b * 4 + k], k);
                COL[base + y * 2 + b] = c;
            }
    }
}

static int find_pic(const char *name)
{
    int i, k;
    char up[16];

    for (k = 0; k < 15 && name[k]; k++)
        up[k] = (name[k] >= 'a' && name[k] <= 'z') ? (char)(name[k] - 32) : name[k];
    up[k] = 0;
    for (i = 0; i < npic; i++)
        if (!strcmp(picname[i], up))
            return i;
    return -1;
}

/* 그림 한 장(16000 바이트, 한 줄 80 바이트)을 lin 자리에 색표로 적는다 */
static void tag_pic(uint32_t lin, int p)
{
    const uint8_t *s;
    int y, x;

    if (p < 0 || !picdata[p])
        return;
    s = picdata[p];
    for (y = 0; y < 200; y++)
        for (x = 0; x < 80; x++) {
            const uint8_t *q = s + y * 320 + x * 4;
            COL[lin + y * 80 + x] = PIXCOL(q[0], 0) | PIXCOL(q[1], 1) | PIXCOL(q[2], 2) | PIXCOL(q[3], 3);
        }
}

void vga_file_read(const char *name, uint32_t lin, uint32_t pos, uint32_t n)
{
    int k;

    (void)lin;
    if (pos == 0) {
        for (k = 0; k < 15 && name[k]; k++)
            cur_name[k] = name[k];
        cur_name[k] = 0;
    }
    /* 눌리지 않은 그림(BKGR0, SLC, TETRIS.TTL)은 바로 그림판(DS:01F2)에 들어간다 */
    if (n >= 16000)
        tag_pic(LIN(DSEG, screen_buf), find_pic(cur_name));
}

/* 눌림 풀기(04B1) 가 끝나면 ES:0000 에 배경 그림 한 장이 들어 있다 */
void vga_enter(uint16_t fn)
{
    (void)fn;
}

void vga_leave(uint16_t fn)
{
    if (fn == 0x04B1)
        tag_pic(LIN(ES_, 0), find_pic(cur_name));
}

/* 글자(1E3C)는 AND/OR 로 그려서 색표가 따라오지 않는다.  한 줄(2 바이트 = 8 점)을
   그린 바로 뒤에 불러, 글자가 된 점만 색을 적는다.  원판이 쓰던 CGA 색(마스크
   DS:5CD0)에 맞춰 금빛/붉은빛/푸른빛을 고른다. */
void vga_text_pix(void)
{
    uint32_t a = LIN(ES_, DI);
    uint16_t mask = RW(DS_, 0x5CD0);
    uint8_t col;
    int b, k;

    if (mask == 0x5555)
        col = 16 + 3 * 12 + 9;                  /* ice: 푸른 글자 */
    else if (mask == 0xAAAA)
        col = 16 + 8 * 12 + 9;                  /* orange: 따뜻한 호박빛 글자 */
    else
        col = 16 + 9 * 12 + 10;                 /* gold: 밝은 금빛 (보통 글자) */
    for (b = 0; b < 2; b++) {
        uint8_t v = b ? AH : AL;                /* 방금 켠 점들 (글자 모양 & 색 마스크) */
        uint32_t c = COL[a + b];
        for (k = 0; k < 4; k++) {
            int p = (v >> (6 - 2 * k)) & 3;
            if (p)
                c = (c & ~(uint32_t)(0xFFu << (8 * k))) | PIXCOL(col, k);
        }
        COL[a + b] = c;
    }
}

/* ---- 화면 내기 ---------------------------------------------------------------- */
void vga_render(uint8_t *out)
{
    int y, x, k;

    for (y = 0; y < 200; y++) {
        uint32_t base = 0xB8000 + (uint32_t)(y & 1) * 0x2000 + (uint32_t)(y >> 1) * 80;
        uint8_t *d = out + y * 320;
        for (x = 0; x < 80; x++) {
            uint8_t b = M[base + x];
            uint32_t c = COL[base + x];
            for (k = 0; k < 4; k++) {
                uint8_t v = (uint8_t)(c >> (8 * k));
                *d++ = v ? v : fallback[(b >> (6 - 2 * k)) & 3];
            }
        }
    }
}
