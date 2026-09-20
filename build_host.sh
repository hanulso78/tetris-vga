#!/bin/sh
# PC(MSYS2 mingw)용 대조 시험판
export PATH=/c/MSYS2/mingw64/bin:$PATH
cd "$(dirname "$0")"
gcc -O1 -w -o hosttest.exe tools/hosttest.c cpu.c ttcode.c ttdata.c "$@"
# 개선판 미리보기 (같은 게임 코드 + 256색 색표, TTSHOT=경로접두 면 화면을 BMP 로)
gcc -O1 -w -DTTVGA -o hostvga.exe tools/hosttest.c cpu.c ttcode.c ttdata.c ttvga.c "$@"
