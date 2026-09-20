# TETRIS (Spectrum HoloByte, 1988) — 역어셈블 → C → VGA 256색

원판 `CTETRIS.EXE`(IBM CGA 판, MS EXEPACK 으로 눌려 있는 8086 어셈블리)를 풀어
기계적으로 C 로 옮기고, 같은 게임 코드에 256색 그림을 입힌 개선판을 더한 것이다.

| 만든 것 | 무엇 |
|---|---|
| `TETRIS.EXE` | 원판을 그대로 옮긴 것. CGA 모드 5 화면(검정/청록/빨강/흰색)을 VGA 13h 로 보인다 |
| `TETVGA.EXE` | 같은 게임 코드 + 256색 그림 (`TTVGA.DAT` 가 있어야 한다) |

두 판 모두 `CWSDPMI.EXE` 와 원판 자료 파일(`BKGR0`..`BKGR9`, `SLC`, `TETRIS.TTL`)이
같은 폴더에 있어야 한다.  바로 쓸 수 있게 묶은 것은 `release/` 에 있다.

```
release\TETVGA.EXE     256색 개선판
release\TETRIS.EXE     원판 그대로
```

## 원판 뜯어보기

* `CTETRIS.EXE` = MS EXEPACK. `tools/unexepack.py` 로 풀면 `CT_UNP.EXE`
  (자료 세그먼트 `000D`, 코드 세그먼트 `0815`, 코드 9 KB, 손으로 짠 어셈블리).
* `tools/scan.py` 가 진입점 `0014` 에서 흐름을 따라가 함수 80 개, 코드 8425 바이트를 찾는다.
  (나머지 760 바이트는 어디서도 부르지 않는 죽은 코드 — CGA/Tandy/EGA 판이 소스를 함께 쓴 흔적)
* 자판 처리는 `15DA` 의 분기표(`DS:5C8D`, 키 23 개)로 갈린다.
* 그림은 `DS:01F2` 의 그림판(320x200 CGA, 한 줄 80 바이트)에 그린 뒤
  `1385` 에서 `B800` 으로 통째로 옮긴다.  조각 칸은 8x8 (`DS:003F` 부터 16 바이트씩 여덟 개).

## 옮긴 C

* `tools/asm2c.py` → `ttcode.c` (함수마다 C 함수 하나, 레지스터는 전역, 메모리는 1 MB 평면 `M[]`).
  플래그는 쓰이는 것만 계산하고, 부르는 곳에서 넘어오는 플래그(`adc` 앞의 캐리)도 따라간다.
* `ttdata.c` = 원판 적재 이미지 (`tools/mkdata.py`), `cpu.h/cpu.c` = 8086 상태와 메모리.
* `sys_dos.c` = 도스 플랫폼(djgpp): `int 10h/16h/1Ah/21h`, 포트, 파일, 화면 내보내기.
* 기계 속도: 원판은 `0040:006C` 를 두 번 읽어 속도를 재고 그만큼 기다린다.  옮긴 C 는
  8088 클럭을 세어(`CYC()`, 문자열 명령은 길이만큼) 4.77 MHz IBM PC 와 같은 빠르기로 맞춘다
  (`TTFAST=1` 이면 맞추지 않는다).  조각은 여섯 번째 프레임마다 한 줄 내려간다.

### 원본과 대조

`tools/emu.py`(unicorn 으로 원판을 그대로 돌린다) 와 `hosttest.exe`(옮긴 C)를 같은 키로 돌려
인터럽트마다 레지스터를, 키를 읽을 때마다 메모리·화면 CRC 를 맞춰 본다.

```
sh build_host.sh              # hosttest.exe, hostvga.exe
sh tools/regress.sh           # test/k_*.txt 를 자판/조이스틱 두 갈래로
python tools/difftest.py n "50:enter 300:enter 300:enter 40:left 30:space"
python tools/ftrace.py 20000 "..."   # 첫 차이를 함수 단위로 찾기
```

`test/k_*.txt` 다섯 가지(마구잡이 키 포함)가 모두 한 줄도 다르지 않게 맞는다.

## 256색 개선판

게임 코드는 손대지 않는다.  대신 메모리 바이트마다 색표 `COL[]` 을 두고 **그림의 출처**에
256색을 미리 적어 둔다.  게임이 그 바이트를 옮기면(`movs`, `lods`/`stos`) 색표도 따라간다.

* 배경 열두 장: `tools/vgaart.py` 가 CGA 네 색 그림의 점 뿌리기(디더)를 풀어 고른 밝기를 얻고,
  그림마다 정한 규칙(하늘은 파랑 그러데이션, 벽돌은 붉은 흙빛 …)으로 다시 칠한다.
  팔레트는 `tools/pal.py` (CGA 16색 + 색줄 20 가지 x 12 단계).
* 조각 칸 일곱 가지: `tools/tiles.py` 가 보석처럼(테두리·빛·그늘·반짝이) 그린다.
* 글자: `1E3C` 는 AND/OR 로 그려 색표가 따라오지 않으므로, 그린 바로 뒤에 켠 점만 금빛으로.
* 묶음 파일 만들기: `python tools/mkvga.py` → `TTVGA.DAT`

```
python tools/mkvga.py                                  # 그림 묶음
python tools/shotvga.py "50:enter 300:enter ..." out.png   # PC 에서 미리보기
python tools/dosshot.py tools/t_game.txt out.png tetvga.exe   # DOSBox 에서 찍기
```

## 빌드

```
build.bat            TETRIS.EXE
build.bat vga        TETVGA.EXE
sh build_host.sh     PC 대조 시험판
```
