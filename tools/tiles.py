# -*- coding: utf-8 -*-
"""조각 칸 8x8 을 256색 보석처럼 다시 그린다 (원판은 CGA 네 색의 테두리+속).

   원판 DS:003F 부터 16 바이트씩 여덟 칸 (0 번은 지우개, 1..7 번이 조각 일곱 가지).
   여기서는 칸마다 색줄 하나를 골라 바깥 테두리(어둡게) - 위/왼쪽 빛 - 속 - 아래/오른쪽
   그늘 - 반짝이 점 순으로 칠한다.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pal

# 조각 1..7 의 색줄 (원판 테트리스의 느낌: 하늘, 금, 보라, 풀, 빨강, 파랑, 주황)
TILE_RAMP = ['night', 'ice', 'gold', 'violet', 'lime', 'red', 'sky', 'orange']
WELL_DARK = pal.idx('night', 0)          # 빈 칸 (조각이 지워진 자리)


def gem(ramp):
    """8x8 팔레트 번호"""
    t = bytearray(64)
    for y in range(8):
        for x in range(8):
            if x == 0 or y == 0 or x == 7 or y == 7:        # 바깥 테두리
                v = 0.14
            elif x == 1 or y == 1:                          # 위/왼쪽 빛
                v = 0.92
            elif x == 6 or y == 6:                          # 아래/오른쪽 그늘
                v = 0.30
            else:                                           # 속: 왼쪽 위가 밝게
                v = 0.72 - 0.10 * ((x - 2) + (y - 2)) / 6.0
            t[y * 8 + x] = pal.idx(ramp, v * (pal.NS - 1))
    t[2 * 8 + 2] = pal.idx(ramp, pal.NS - 1)                # 반짝이
    t[3 * 8 + 2] = pal.idx(ramp, pal.NS - 2)
    return t


def build():
    """여덟 칸의 8x8 색 (0 번은 빈 칸 색으로 채운다)"""
    out = [bytearray([WELL_DARK] * 64)]
    for k in range(1, 8):
        out.append(gem(TILE_RAMP[k]))
    return out


if __name__ == '__main__':
    from PIL import Image
    ts = build()
    im = Image.new('RGB', (8 * 8 * 4, 8 * 4))
    px = im.load()
    for k, t in enumerate(ts):
        for y in range(8):
            for x in range(8):
                c = pal.RGB[t[y * 8 + x]]
                for dy in range(4):
                    for dx in range(4):
                        px[(k * 8 + x) * 4 + dx, y * 4 + dy] = c
    im.save(os.path.join(os.path.dirname(os.path.abspath(__file__)), '_tiles.png'))
    print('칸 %d 개' % len(ts))
