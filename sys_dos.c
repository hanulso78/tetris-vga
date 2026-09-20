/* ============================================================================
 *  sys_dos.c  -  도스(djgpp) 플랫폼: 옮긴 코드의 int / in / out 을 진짜로 한다
 * ----------------------------------------------------------------------------
 *  화면   원본은 CGA 모드 4/5 (320x200 4색) 에 그린다.  옮긴 코드는 M[] 안의
 *         B800 자리에 그리고, 여기서 그것을 VGA 모드 13h 로 풀어 보인다
 *         (키를 읽거나 시계를 볼 때, 70분의 1초에 한 번까지).
 *         시작할 때의 글자 화면(조이스틱 물음)은 진짜 BIOS/DOS 가 한다.
 *  자판   BIOS (int 16h).  게임이 BIOS 자판 버퍼를 비우면 진짜로 비운다.
 *  시계   int 1Ah 와 0040:006C 는 진짜 BIOS 틱.  게임은 이것으로 기계 속도를 잰다.
 *  소리   포트 42h/43h/61h 그대로.  "loop $" 시간 끌기는 8088 4.77MHz 만큼 기다린다.
 *  파일   DOS 파일 함수 그대로 (배경 그림, 점수표 HIGH)
 * ========================================================================== */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <signal.h>
#include <dpmi.h>
#include <go32.h>
#include <pc.h>
#include <sys/farptr.h>
#include <sys/movedata.h>
#include <time.h>
#include "cpu.h"
#include "ttcode.h"
#ifdef TTVGA
#include "ttvga.h"
#endif

static int gfx;                 /* 0 글자, 4/5 CGA */
static int vga_on;
static uint8_t vbuf[64000];
static uclock_t last_present;
static int32_t tick_ofs;
static int kbd_masked;
#ifdef TTVGA
static struct {
    char name[16];
    uint32_t pos;
} hfiles[64];
#endif

/* ---- 화면 ------------------------------------------------------------------ */
/*  원본 CGA 모드 5(흑백 팔레트, 3D9=0): 0 검정, 1 청록, 2 빨강, 3 흰색 */
static const uint8_t cgapal[4][3] = {{0, 0, 0}, {0, 42, 42}, {42, 0, 0}, {42, 42, 42}};

static void set_vga(void)
{
    __dpmi_regs r;
    int i;

    memset(&r, 0, sizeof r);
    r.x.ax = 0x0013;
    __dpmi_int(0x10, &r);
    outportb(0x3C8, 0);
#ifdef TTVGA
    for (i = 0; i < 256; i++) {
        outportb(0x3C9, vga_pal[i][0]);
        outportb(0x3C9, vga_pal[i][1]);
        outportb(0x3C9, vga_pal[i][2]);
    }
#else
    for (i = 0; i < 4; i++) {
        outportb(0x3C9, cgapal[i][0]);
        outportb(0x3C9, cgapal[i][1]);
        outportb(0x3C9, cgapal[i][2]);
    }
#endif
    vga_on = 1;
}

static void present(void)
{
    const uint8_t *v = M + 0xB8000;
    uint8_t *d = vbuf;
    int x, y;

    if (!gfx) {
        /* 글자 화면(모드 3): 게임이 B800 에 직접 글자를 적는다 (도움말, 통계).
           우리 M[] 안의 것을 진짜 화면으로 옮겨 준다.  시작할 때의 물음은 도스가
           직접 찍으므로 M[] 이 비어 있고, 그때는 건드리지 않는다. */
        int any = 0;
        for (x = 0; x < 4000; x++)
            if (v[x]) {
                any = 1;
                break;
            }
        if (any)
            dosmemput(M + 0xB8000, 4000, 0xB8000);
        last_present = uclock();
        return;
    }
#ifdef TTVGA
    vga_ms = (uint32_t)(uclock() * 1000 / UCLOCKS_PER_SEC) + 1;
    vga_render(vbuf);
    dosmemput(vbuf, sizeof vbuf, 0xA0000);
    last_present = uclock();
    return;
#endif
    for (y = 0; y < 200; y++) {
        const uint8_t *s = v + (y & 1) * 0x2000 + (y >> 1) * 80;
        for (x = 0; x < 80; x++) {
            uint8_t b = s[x];
            *d++ = (uint8_t)(b >> 6);
            *d++ = (uint8_t)((b >> 4) & 3);
            *d++ = (uint8_t)((b >> 2) & 3);
            *d++ = (uint8_t)(b & 3);
        }
    }
    dosmemput(vbuf, sizeof vbuf, 0xA0000);
    last_present = uclock();
}

static void maybe_present(void)
{
    if (uclock() - last_present > UCLOCKS_PER_SEC / 70)
        present();
}

/* ---- 원판 속도 맞추기 ---------------------------------------------------------
 *  옮긴 C 는 원판보다 훨씬 빨라서 그냥 두면 조각이 번개처럼 떨어진다.  옮긴 코드가
 *  세어 둔 8088 클럭(sim_cyc)만큼 시간이 흐르도록 기다려 4.77MHz IBM PC 와 같은
 *  빠르기로 돌린다.  (TTFAST=1 이면 기다리지 않는다)
 * ---------------------------------------------------------------------------- */
#define PC_HZ 4772727.0
static int no_pace;
static uclock_t pace_t0;
static uint32_t pace_c0;

static void pace(void)
{
    uclock_t want, now;

    if (no_pace)
        return;
    now = uclock();
    want = pace_t0 + (uclock_t)((double)(sim_cyc - pace_c0) * (double)UCLOCKS_PER_SEC / PC_HZ);
    if (want < now || want - now > UCLOCKS_PER_SEC) {   /* 너무 뒤처졌으면 새로 맞춘다 */
        pace_t0 = now;
        pace_c0 = sim_cyc;
        return;
    }
    while (uclock() < want)
        maybe_present();
}

static void text_mode(void)
{
    __dpmi_regs r;

    memset(&r, 0, sizeof r);
    r.x.ax = 0x0003;
    __dpmi_int(0x10, &r);
    vga_on = 0;
    gfx = 0;
}

/* ---- 시험 모드 ---------------------------------------------------------------
 *  TTTEST=스크립트파일 이면 자판 대신 스크립트를 읽는다 (tools/dosshot.py 가 쓴다)
 *     <밀리초> key <이름|16진>    그 시각부터 누른 것으로 친다
 *     <밀리초> shot <이름>        화면을 <이름>.BMP 로
 *     <밀리초> quit
 * -------------------------------------------------------------------------- */
static int test_on;
static struct {
    long ms;
    char what;
    unsigned key;
    char name[16];
} tev[512];
static int ntev, tpos;
static uclock_t tstart;
static FILE *tlog;

static long now_ms(void)
{
    return (long)((uclock() - tstart) * 1000 / UCLOCKS_PER_SEC);
}

static unsigned keyval(const char *s)
{
    static const struct {
        const char *n;
        unsigned v;
    } names[] = {{"enter", 0x1C0D}, {"esc", 0x011B}, {"up", 0x4800}, {"down", 0x5000}, {"left", 0x4B00},
                 {"right", 0x4D00}, {"space", 0x3920}, {"bs", 0x0E08}, {"f1", 0x3B00}, {"f2", 0x3C00},
                 {"f3", 0x3D00}, {"f4", 0x3E00}, {"home", 0x4700}, {"end", 0x4F00}};
    static const char sc[] = "..1234567890-=..qwertyuiop[]..asdfghjkl;'`.\\zxcvbnm,./";
    unsigned i;

    for (i = 0; i < sizeof names / sizeof names[0]; i++)
        if (!strcmp(s, names[i].n))
            return names[i].v;
    if (strlen(s) == 1) {
        const char *q = strchr(sc, s[0]);
        return (unsigned)(((q ? q - sc : 0) << 8) | (uint8_t)s[0]);
    }
    return (unsigned)strtoul(s, 0, 16);
}

static void save_bmp(const char *name)
{
    static uint8_t pal[768];
    char fn[40];
    FILE *f;
    int y, i;
    uint8_t hdr[54];
    uint32_t v;

    if (!gfx) {                                 /* 글자 화면: 진짜 화면에 들어간 글자를 적어 둔다 */
        static uint8_t tb[4000];
        sprintf(fn, "%s.TXT", name);
        f = fopen(fn, "w");
        if (!f)
            return;
        dosmemget(0xB8000, sizeof tb, tb);
        for (y = 0; y < 25; y++) {
            for (i = 0; i < 80; i++)
                fputc(tb[(y * 80 + i) * 2] ? tb[(y * 80 + i) * 2] : ' ', f);
            fputc('\n', f);
        }
        fclose(f);
        return;
    }
    sprintf(fn, "%s.BMP", name);
    f = fopen(fn, "wb");
    if (!f)
        return;
    outportb(0x3C7, 0);
    for (i = 0; i < 768; i++)
        pal[i] = inportb(0x3C9);
    memset(hdr, 0, sizeof hdr);
    hdr[0] = 'B';
    hdr[1] = 'M';
    v = 54 + 1024 + 64000;
    memcpy(hdr + 2, &v, 4);
    v = 54 + 1024;
    memcpy(hdr + 10, &v, 4);
    v = 40;
    memcpy(hdr + 14, &v, 4);
    v = 320;
    memcpy(hdr + 18, &v, 4);
    v = 200;
    memcpy(hdr + 22, &v, 4);
    hdr[26] = 1;
    hdr[28] = 8;
    fwrite(hdr, 1, 54, f);
    for (i = 0; i < 256; i++) {
        uint8_t q[4];
        q[0] = (uint8_t)(pal[i * 3 + 2] << 2);
        q[1] = (uint8_t)(pal[i * 3 + 1] << 2);
        q[2] = (uint8_t)(pal[i * 3] << 2);
        q[3] = 0;
        fwrite(q, 1, 4, f);
    }
    dosmemget(0xA0000, 64000, vbuf);
    for (y = 199; y >= 0; y--)
        fwrite(vbuf + y * 320, 1, 320, f);
    fclose(f);
}

static void test_poll(void)
{
    long t = now_ms();

    while (tpos < ntev && tev[tpos].ms <= t && tev[tpos].what != 'k') {
        if (tev[tpos].what == 's') {
            present();
            save_bmp(tev[tpos].name);
            if (tlog)
                fprintf(tlog, "%ld shot %s\n", t, tev[tpos].name);
        } else {
            outportb(0x61, (uint8_t)(inportb(0x61) & 0xFC));
            if (tlog)
                fclose(tlog);
            text_mode();
            exit(0);
        }
        tpos++;
    }
}

static int test_peek(void)
{
    test_poll();
    if (tpos < ntev && tev[tpos].what == 'k' && tev[tpos].ms <= now_ms())
        return (int)tev[tpos].key;
    return -1;
}

static unsigned test_get(void)
{
    int k;

    while ((k = test_peek()) < 0) {
        __dpmi_yield();
        present();
        if (tpos >= ntev) {
            text_mode();
            exit(0);
        }
    }
    tpos++;
    if (tlog)
        fprintf(tlog, "%ld key %04X\n", now_ms(), (unsigned)k);
    return (unsigned)k;
}

static void test_init(void)
{
    const char *fn = getenv("TTTEST");
    FILE *f;
    char ln[128], w[16], a[32];
    long ms;

    if (!fn || !(f = fopen(fn, "r")))
        return;
    while (ntev < 512 && fgets(ln, sizeof ln, f)) {
        a[0] = 0;
        if (sscanf(ln, "%ld %15s %31s", &ms, w, a) < 2)
            continue;
        tev[ntev].ms = ms;
        tev[ntev].what = w[0];
        if (w[0] == 'k')
            tev[ntev].key = keyval(a);
        else
            strncpy(tev[ntev].name, a, 15);
        ntev++;
    }
    fclose(f);
    test_on = 1;
    tlog = fopen("TTLOG.TXT", "w");
    tstart = uclock();
}

/* ---- BIOS 자료 영역 --------------------------------------------------------- */
void bios_sync(uint16_t at)
{
    if (at == 0x046C) {
        uint32_t t = (uint32_t)((int32_t)_farpeekl(_dos_ds, 0x46C) + tick_ofs);
        M[0x46C] = (uint8_t)t;
        M[0x46D] = (uint8_t)(t >> 8);
        M[0x46E] = (uint8_t)(t >> 16);
        M[0x46F] = (uint8_t)(t >> 24);
    } else if (at == 0x041A) {
        M[0x41A] = _farpeekb(_dos_ds, 0x41A);
        M[0x41B] = _farpeekb(_dos_ds, 0x41B);
        M[0x41C] = _farpeekb(_dos_ds, 0x41C);
        M[0x41D] = _farpeekb(_dos_ds, 0x41D);
    } else if (at == 0x0417) {
        M[0x417] = _farpeekb(_dos_ds, 0x417);
    } else if (at == 0x0487) {
        M[0x487] = _farpeekb(_dos_ds, 0x487);
    }
}

void bios_kbflags(void)
{
    _farpokeb(_dos_ds, 0x417, M[0x417]);
}

void bios_spin(uint16_t n)
{
    tick_ofs += n;
}

/* ---- 인터럽트 ---------------------------------------------------------------- */
void int10(void)
{
    __dpmi_regs r;

    if (AH == 0x00) {
        memset(M + 0xB8000, 0, 0x8000);
#ifdef TTVGA
        memset(COL + 0xB8000, 0, 0x8000 * sizeof(uint32_t));
#endif
        if (AL == 4 || AL == 5) {
            gfx = AL;
            if (!vga_on)
                set_vga();
            present();
            return;
        }
        gfx = 0;
        vga_on = 0;
    } else if (gfx) {
        if (AH == 0x0F)
            AX = (uint16_t)(0x2800 | gfx);
        return;
    }
    memset(&r, 0, sizeof r);
    r.x.ax = AX;
    r.x.bx = BX;
    r.x.cx = CX;
    r.x.dx = DX;
    __dpmi_int(0x10, &r);
    AX = r.x.ax;
    BX = r.x.bx;
    CX = r.x.cx;
    DX = r.x.dx;
}

void int16(void)
{
    __dpmi_regs r;

    pace();
    if (test_on) {
        maybe_present();
        if (AH == 1 || AH == 0x11) {
            int k = test_peek();
            ZF = k < 0;
            if (k >= 0)
                AX = (uint16_t)k;
        } else if (AH == 0 || AH == 0x10)
            AX = (uint16_t)test_get();
        return;
    }
    if (AH == 0 || AH == 0x10) {            /* 막고 읽기: 기다리는 동안 화면을 보인다 */
        present();
        while (_farpeekw(_dos_ds, 0x41A) == _farpeekw(_dos_ds, 0x41C)) {
            __dpmi_yield();
            maybe_present();
        }
    } else
        maybe_present();
    memset(&r, 0, sizeof r);
    r.x.ax = AX;
    __dpmi_int(0x16, &r);
    AX = r.x.ax;
    ZF = (r.x.flags & 0x40) != 0;
}

void int1a(void)
{
    pace();
    if (test_on)
        test_poll();
    maybe_present();
    if (AH == 0) {
        uint32_t t = (uint32_t)((int32_t)_farpeekl(_dos_ds, 0x46C) + tick_ofs);
        CX = (uint16_t)(t >> 16);
        DX = (uint16_t)t;
        AL = 0;
    } else if (AH == 1) {
        tick_ofs = (int32_t)(((uint32_t)CX << 16) | DX) - (int32_t)_farpeekl(_dos_ds, 0x46C);
    }
}

void kbd_flush_hook(void)
{
    __dpmi_regs r;

    if (test_on) {
        while (test_peek() >= 0)
            tpos++;
        return;
    }
    for (;;) {
        memset(&r, 0, sizeof r);
        r.h.ah = 1;
        __dpmi_int(0x16, &r);
        if (r.x.flags & 0x40)
            break;
        r.h.ah = 0;
        __dpmi_int(0x16, &r);
    }
}

void int21(void)
{
    __dpmi_regs r;
    uint8_t ah = AH;
    uint32_t src = LIN(DS_, DX);

    memset(&r, 0, sizeof r);
    r.x.ax = AX;
    r.x.bx = BX;
    r.x.cx = CX;
    r.x.dx = DX;
    switch (ah) {
    case 0x09: {                            /* '$' 로 끝나는 글 */
        unsigned n = 0;
        while (n < 2000 && M[src + n] != '$')
            n++;
        dosmemput(M + src, n + 1, __tb);
        r.x.ds = __tb >> 4;
        r.x.dx = __tb & 15;
        __dpmi_int(0x21, &r);
        return;
    }
    case 0x0A: {                            /* 줄 입력 (조이스틱 물음) */
        unsigned len = M[src] + 2;
        if (test_on) {
            const char *a = getenv("TTJOY");
            M[src + 1] = 1;
            M[src + 2] = (uint8_t)(a ? a[0] : 'n');
            M[src + 3] = 13;
            return;
        }
        dosmemput(M + src, len, __tb);
        r.x.ds = __tb >> 4;
        r.x.dx = __tb & 15;
        __dpmi_int(0x21, &r);
        dosmemget(__tb, len, M + src);
        return;
    }
    case 0x3C:
    case 0x3D: {                            /* 만들기 / 열기 */
        unsigned n = 0;
        while (n < 127 && M[src + n])
            n++;
        dosmemput(M + src, n + 1, __tb);
        r.x.ds = __tb >> 4;
        r.x.dx = __tb & 15;
        __dpmi_int(0x21, &r);
        AX = r.x.ax;
        CF = r.x.flags & 1;
#ifdef TTVGA
        if (!CF && AX < 64) {
            unsigned k;
            for (k = 0; k < 15 && M[src + k]; k++)
                hfiles[AX].name[k] = (char)M[src + k];
            hfiles[AX].name[k] = 0;
            hfiles[AX].pos = 0;
        }
#endif
        return;
    }
    case 0x3F: {                            /* 읽기: 전송 버퍼를 조각조각 */
        unsigned want = CX, got = 0, chunk;
        CF = 0;
        while (got < want) {
            chunk = want - got;
            if (chunk > 0x4000)
                chunk = 0x4000;
            memset(&r, 0, sizeof r);
            r.h.ah = 0x3F;
            r.x.bx = BX;
            r.x.cx = (uint16_t)chunk;
            r.x.ds = __tb >> 4;
            r.x.dx = __tb & 15;
            __dpmi_int(0x21, &r);
            if (r.x.flags & 1) {
                AX = r.x.ax;
                CF = 1;
                return;
            }
            dosmemget(__tb, r.x.ax, M + src + got);
            got += r.x.ax;
            if (r.x.ax < chunk)
                break;
        }
        AX = (uint16_t)got;
#ifdef TTVGA
        {
            unsigned k;
            for (k = 0; k < got; k++)
                COL[src + k] = 0;
            if (BX < 64) {
                vga_file_read(hfiles[BX].name, src, hfiles[BX].pos, got);
                hfiles[BX].pos += got;
            }
        }
#endif
        return;
    }
    case 0x40: {                            /* 쓰기 */
        unsigned want = CX, put = 0, chunk;
        CF = 0;
        while (put < want) {
            chunk = want - put;
            if (chunk > 0x4000)
                chunk = 0x4000;
            dosmemput(M + src + put, chunk, __tb);
            memset(&r, 0, sizeof r);
            r.h.ah = 0x40;
            r.x.bx = BX;
            r.x.cx = (uint16_t)chunk;
            r.x.ds = __tb >> 4;
            r.x.dx = __tb & 15;
            __dpmi_int(0x21, &r);
            if (r.x.flags & 1) {
                AX = r.x.ax;
                CF = 1;
                return;
            }
            put += r.x.ax;
            if (r.x.ax < chunk)
                break;
        }
        AX = (uint16_t)put;
        return;
    }
    case 0x48: {                            /* 메모리 할당: 우리 M[] 안에서 준다 */
        static uint16_t freeseg;
        if (!freeseg)
            freeseg = (uint16_t)(PSPSEG + 0xA8C + 1);
        if ((uint32_t)freeseg + BX + 1 > 0xB000) {   /* B800 (화면) 앞까지만 */
            AX = 8;
            BX = (uint16_t)(0xB000 - freeseg);
            CF = 1;
            return;
        }
        AX = freeseg;
        freeseg = (uint16_t)(freeseg + BX + 1);
        CF = 0;
        return;
    }
    case 0x49:
    case 0x4A:
        CF = 0;
        return;
    case 0x4C:
        text_mode();
        exit(AL);
    default:                                /* 3E 닫기, 2C 시각, 42 옮기기 ... */
        __dpmi_int(0x21, &r);
        AX = r.x.ax;
        BX = r.x.bx;
        CX = r.x.cx;
        DX = r.x.dx;
        CF = r.x.flags & 1;
        return;
    }
}

/* ---- 포트 ------------------------------------------------------------------ */
uint8_t port_in(uint16_t port)
{
    return inportb(port);
}

void port_out(uint16_t port, uint8_t v)
{
    /* 우리는 VGA 모드 13h 로 보이므로 CGA/EGA 화면 레지스터는 건드리지 않는다 */
    if (port == 0x3D8 || port == 0x3D9 || (port >= 0x3B0 && port <= 0x3BF) ||
        (port >= 0x3C0 && port <= 0x3CF))
        return;
    if (port == 0x21) {
        int m = (v & 2) != 0;
        if (kbd_masked && !m)
            kbd_flush_hook();
        kbd_masked = m;
        return;
    }
    outportb(port, v);
}

/* 8088 4.77MHz 에서 "loop $" 한 번 = 17 클럭.  소리는 이 기다림으로 높이가 정해지므로
   클럭만 세지 말고 진짜로 기다린다 (기다린 만큼 pace() 가 덜 기다린다) */
void delay_loop(uint16_t n)
{
    uclock_t end = uclock() + (uclock_t)((double)n * 17.0 * UCLOCKS_PER_SEC / PC_HZ);

    sim_cyc += (uint32_t)n * 17;
    while (uclock() < end)
        ;
}

void far_return(void)
{
    text_mode();
    exit(0);
}

void div_error(uint16_t at)
{
    text_mode();
    printf("divide error at %04X\n", at);
    exit(1);
}

void jump_error(uint16_t at)
{
    text_mode();
    printf("bad jump table at %04X\n", at);
    exit(1);
}

static void on_break(int sig)
{
    (void)sig;
    outportb(0x61, (uint8_t)(inportb(0x61) & 0xFC));
    text_mode();
    exit(1);
}

int main(int argc, char **argv)
{
    (void)argc;
    (void)argv;
    signal(SIGINT, on_break);
    uclock();
    no_pace = getenv("TTFAST") != 0;
    test_init();
    pace_t0 = uclock();
    cpu_reset();
#ifdef TTVGA
    if (!vga_load("TTVGA.DAT")) {
        printf("TTVGA.DAT not found\n");
        return 1;
    }
    vga_reset();
#endif
    tt_main();
    text_mode();
    return 0;
}
