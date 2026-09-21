/* ttvga.h - 개선판(TETVGA): CGA 화면을 256색으로 보이게 하는 부분 */
#ifndef TTVGA_H
#define TTVGA_H

#include <stdint.h>

extern uint8_t vga_pal[256][3];     /* 팔레트 (0..63) */
extern uint32_t vga_ms;             /* 지금 시각(밀리초) - 반짝이는 것에 쓴다 */

int vga_load(const char *path);     /* TTVGA.DAT 읽기 (0 이면 없음) */
void vga_reset(void);               /* 조각 칸 색표 붙이기 */
void vga_file_read(const char *name, uint32_t lin, uint32_t pos, uint32_t n);
void vga_render(uint8_t *out);      /* B800 의 CGA 화면 + 색표 -> 320x200 256색 */

/* ---- 배경음악 (ttmusic.c, 애드립 OPL2 + VGM) ---- */
enum { MUS_NONE = 0, MUS_TITLE, MUS_PLAY, MUS_PLAY2, MUS_PLAY3, MUS_OVER, MUS_COUNT };

int vga_music(void);                /* 지금 장면에 맞는 곡 */
int music_muted(void);              /* 게임에서 소리를 껐나 (S 키) */
void music_want(int which);
void music_poll(void);
void music_off(void);
int music_found(void);
int music_done(int which);
extern long music_writes;           /* 시험용: 애드립에 쓴 횟수 */
extern long music_us, music_polls;

#endif
