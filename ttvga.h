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

#endif
