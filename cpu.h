/* ============================================================================
 *  cpu.h  -  옮긴 코드(ttcode.c)가 쓰는 8086 상태와 메모리
 * ----------------------------------------------------------------------------
 *  원본은 손으로 짠 어셈블리라 레지스터로 값을 주고받고 세그먼트를 수시로 바꾼다.
 *  그래서 옮긴 C 도 레지스터를 전역 변수로 두고, 메모리는 실모드 주소 그대로인
 *  평면 배열 M[] (1MB + 64KB) 로 둔다.  세그먼트:오프셋 계산, 16비트 넘침, 스택
 *  내용까지 원본과 같아서 에뮬레이터(tools/emu.py)와 메모리를 통째로 대조할 수 있다.
 *
 *  원본의 적재 세그먼트는 LOADSEG (PSP 는 그 앞 10h).  SEG(x) 는 원본 EXE 안의
 *  세그먼트 값 x 를 실제 세그먼트로 바꾼다 (재배치).
 * ========================================================================== */
#ifndef CPU_H
#define CPU_H

#include <stdint.h>

#define LOADSEG 0x1000
#define SEG(x) ((uint16_t)(LOADSEG + (x)))
#define MEMSIZE 0x110000

/* 원본의 세그먼트들 (CTETRIS.EXE, EXEPACK 을 푼 것) */
#define CSEG SEG(0x0815)        /* 코드 (9 KB) */
#define SSEG SEG(0x0000)        /* 스택 (이미지 맨 앞 80 바이트) */
#define DSEG SEG(0x000D)        /* 자료: 변수, 문자열, 그림, 화면 버퍼 */
#define CMDSEG SEG(0x0005)      /* PSP 의 명령줄을 옮겨 놓는 곳 */
#define PSPSEG ((uint16_t)(LOADSEG - 0x10))

extern uint8_t M[MEMSIZE];

typedef union {
    uint16_t x;
    struct {
        uint8_t l, h;
    } b;
} reg16_t;

extern reg16_t cpu_a, cpu_b, cpu_c, cpu_d;
extern uint16_t SI, DI, BP, SP, CS_, DS_, ES_, SS_;
extern int CF, ZF, SF, OF, DF;

/* 8088(4.77MHz) 에서 여기까지 몇 클럭 걸렸을지.  옮긴 코드는 블록마다 CYC() 로 더하고,
 * 문자열 명령은 길이만큼 더한다.  도스 판은 이 값으로 원판 속도에 맞춰 기다린다. */
extern uint32_t sim_cyc;
#define CYC(n) (sim_cyc += (n))

#define AX cpu_a.x
#define AL cpu_a.b.l
#define AH cpu_a.b.h
#define BX cpu_b.x
#define BL cpu_b.b.l
#define BH cpu_b.b.h
#define CX cpu_c.x
#define CL cpu_c.b.l
#define CH cpu_c.b.h
#define DX cpu_d.x
#define DL cpu_d.b.l
#define DH cpu_d.b.h

#define LIN(s, o) (((uint32_t)(uint16_t)(s) << 4) + (uint16_t)(o))

/* 개선판(TTVGA)은 메모리 바이트마다 그림자 색 COL[] 을 둔다: 바이트의 네 점(2비트씩,
 * 위 비트가 왼쪽)마다 256색 번호 하나씩, 0 은 "색 없음"(원래 CGA 값으로 칠한다).
 * 보통 쓰기(WB/WW)는 색을 지우고, 문자열 복사(movs)는 색도 같이 옮긴다.  lods 로 읽어
 * stos 로 바로 쓰는 것(조각 칸 그리기)도 색이 따라가도록 AX 의 색을 잠깐 들고 있는다.
 * 그림의 출처에 색을 적는 일은 ttvga.c 가 한다. */
#ifdef TTVGA
extern uint32_t COL[MEMSIZE];
extern uint32_t col_ax[2];          /* lods 가 가져온 색 (stos 가 쓴다) */
extern int col_ax_ok;
#define COL_CLR(a) (COL[a] = 0)
#define COL_CPY(d, s) (COL[d] = COL[s])
#define COL_LOD(a, n) (col_ax[0] = COL[a], col_ax[1] = (n) > 1 ? COL[(a) + 1] : 0, col_ax_ok = (n))
#define COL_STO(a, n) (col_ax_ok >= (n) ? (COL[a] = col_ax[0], (n) > 1 ? (COL[(a) + 1] = col_ax[1]) : 0) : 0,                        col_ax_ok = 0)
#else
#define COL_CLR(a) ((void)0)
#define COL_CPY(d, s) ((void)0)
#define COL_LOD(a, n) ((void)0)
#define COL_STO(a, n) ((void)0)
#endif

static inline uint8_t RB(uint16_t s, uint16_t o)
{
    return M[LIN(s, o)];
}

static inline uint16_t RW(uint16_t s, uint16_t o)
{
    return (uint16_t)(M[LIN(s, o)] | (M[LIN(s, (uint16_t)(o + 1))] << 8));
}

static inline void WB(uint16_t s, uint16_t o, uint8_t v)
{
    uint32_t a = LIN(s, o);
    M[a] = v;
    COL_CLR(a);
}

static inline void WW(uint16_t s, uint16_t o, uint16_t v)
{
    uint32_t a = LIN(s, o), b = LIN(s, (uint16_t)(o + 1));
    M[a] = (uint8_t)v;
    M[b] = (uint8_t)(v >> 8);
    COL_CLR(a);
    COL_CLR(b);
}

static inline void PUSH(uint16_t v)
{
    SP -= 2;
    WW(SS_, SP, v);
}

static inline uint16_t POP(void)
{
    uint16_t v = RW(SS_, SP);
    SP += 2;
    return v;
}

/* 한 바이트 복사 (movs): 색도 같이 */
static inline void CPB(uint16_t ds, uint16_t so, uint16_t es, uint16_t eo)
{
    uint32_t d = LIN(es, eo), a = LIN(ds, so);
    M[d] = M[a];
    COL_CPY(d, a);
}

/* 방향 플래그(DF)대로 SI/DI 가 늘거나 준다 */
static inline void MOVSB(uint16_t sseg)
{
    CPB(sseg, SI, ES_, DI);
    if (DF) { SI--; DI--; } else { SI++; DI++; }
}

static inline void MOVSW(uint16_t sseg)
{
    CPB(sseg, SI, ES_, DI);
    CPB(sseg, (uint16_t)(SI + 1), ES_, (uint16_t)(DI + 1));
    if (DF) { SI -= 2; DI -= 2; } else { SI += 2; DI += 2; }
}

static inline void STOSB(void)
{
    WB(ES_, DI, AL);
    COL_STO(LIN(ES_, DI), 1);
    DI += DF ? -1 : 1;
}

static inline void STOSW(void)
{
    WW(ES_, DI, AX);
    COL_STO(LIN(ES_, DI), 2);
    DI += DF ? -2 : 2;
}

static inline void LODSB(uint16_t sseg)
{
    AL = RB(sseg, SI);
    COL_LOD(LIN(sseg, SI), 1);
    SI += DF ? -1 : 1;
}

static inline void LODSW(uint16_t sseg)
{
    AX = RW(sseg, SI);
    COL_LOD(LIN(sseg, SI), 2);
    SI += DF ? -2 : 2;
}

/* rep 문자열 명령 */
static inline void rep_movsb(uint16_t sseg)
{
    sim_cyc += (uint32_t)CX * 18;
    while (CX) {
        MOVSB(sseg);
        CX--;
    }
}

static inline void rep_movsw(uint16_t sseg)
{
    sim_cyc += (uint32_t)CX * 26;
    while (CX) {
        MOVSW(sseg);
        CX--;
    }
}

static inline void rep_stosb(void)
{
    sim_cyc += (uint32_t)CX * 11;
    while (CX) {
        WB(ES_, DI, AL);
        DI += DF ? -1 : 1;
        CX--;
    }
}

static inline void rep_stosw(void)
{
    sim_cyc += (uint32_t)CX * 15;
    while (CX) {
        WW(ES_, DI, AX);
        DI += DF ? -2 : 2;
        CX--;
    }
}

/* ---- 개선판 갈고리 (ttvga.c): 원본 동작은 그대로 두고 256색 그림자만 다룬다 ---- */
#ifdef TTVGA
void vga_enter(uint16_t fn);
void vga_leave(uint16_t fn);
void vga_text_pix(void);            /* 글자 한 줄을 그린 뒤 색표를 적는다 */
void vga_text_save(void);           /* 그리기 전 그 자리 색표를 챙겨 둔다 */
#define VGA_ENTER(fn) vga_enter(fn)
#define VGA_LEAVE(fn) vga_leave(fn)
#define VGA_TEXT() vga_text_pix()
#define VGA_TEXT_SAVE() vga_text_save()
extern int vga_fast;                /* 도스 개선판: 원판의 긴 기다림을 줄인다 */
#define VGA_FAST(stmt) if (vga_fast) { stmt }
#else
#define VGA_FAST(stmt)
#define VGA_ENTER(fn)
#define VGA_LEAVE(fn)
#define VGA_TEXT()
#define VGA_TEXT_SAVE()
#endif

/* ---- 플랫폼 (sys_dos.c / tools/hosttest.c) ---- */
void int10(void);
void int16(void);
void int1a(void);
void int21(void);
uint8_t port_in(uint16_t port);
void port_out(uint16_t port, uint8_t v);
void delay_loop(uint16_t n);        /* 8088 의 "loop $" n 번만큼 시간 끌기 */
void kbd_flush_hook(void);          /* 게임이 BIOS 자판 버퍼를 비웠다 */
void bios_sync(uint16_t at);        /* 0040:xxxx (시계, 자판 상태) 를 읽기 앞서 */
void bios_kbflags(void);            /* 게임이 0040:0017 (NumLock) 을 바꿨다 */
void bios_spin(uint16_t ticks);     /* 속도 재기 되돌이: 그만큼 시간이 간 것으로 */
void far_return(void);              /* 주 프로그램 끝 (retf) */
void div_error(uint16_t at);
void jump_error(uint16_t at);      /* 분기표에 없는 값 */

/* 함수에 들어갈 때 레지스터 기록 (tools/ftrace.py 로 원본과 대조할 때만) */
#ifdef TTFTRACE
void ftrace_log(uint16_t a);
#define FTRACE(a) ftrace_log(a)
#else
#define FTRACE(a) ((void)0)
#endif

void cpu_reset(void);               /* 적재: M[] 를 채우고 레지스터를 시작 값으로 */
extern const uint8_t tt_image[];    /* ttdata.c: 적재 이미지 (tools/mkdata.py) */
extern const unsigned tt_image_size;

#endif
