# ============================================================================
#  TETRIS (Spectrum HoloByte, 1988)  -  djgpp 빌드
# ----------------------------------------------------------------------------
#      make -f tt.mak            TETRIS.EXE, TETVGA.EXE
#      make -f tt.mak clean
#
#  TETRIS.EXE - 원판 CTETRIS.EXE 를 C 로 옮긴 것 (CGA 화면을 VGA 로 보인다)
#       필요한 파일 : CWSDPMI.EXE 와 원판 자료 (BKGR0..9, TETRIS.TTL, SLC)
#  TETVGA.EXE - 개선판: 같은 게임 코드에 256색 그림 (ttvga.c + TTVGA.DAT)
# ============================================================================

CC      = gcc
CFLAGS  = -O1 -Wall -Wno-unused-label -Wno-unused-variable -fno-strict-aliasing

ORIG    = ttcode.o ttdata.o cpu.o sys_dos.o
VGA     = ttcode.vo ttdata.vo cpu.vo sys_dos.vo ttvga.vo

all: tetris.exe

orig: tetris.exe
vga:  tetvga.exe

tetris.exe: $(ORIG)
	$(CC) $(CFLAGS) -o tetris.exe $(ORIG)
	strip tetris.exe

tetvga.exe: $(VGA)
	$(CC) $(CFLAGS) -o tetvga.exe $(VGA)
	strip tetvga.exe

%.o: %.c cpu.h ttcode.h ttvars.h
	$(CC) $(CFLAGS) -c $< -o $@

%.vo: %.c cpu.h ttcode.h ttvars.h ttvga.h
	$(CC) $(CFLAGS) -DTTVGA -c $< -o $@

clean:
	-del *.o
	-del *.vo
	-del tetris.exe
	-del tetvga.exe
