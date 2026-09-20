# -*- coding: utf-8 -*-
"""개선판(TETVGA)이 읽는 그림 묶음 TTVGA.DAT 를 만든다.

   python tools/mkvga.py

   짜임새 (모두 작은 끝 방식):
     "TTVGA1\0\0"            8 바이트
     u16 그림 수
     768                     팔레트 (r, g, b 0..63)
     8 x 64                  조각 칸 8x8 색
     그림마다: 이름 16 바이트 + 320x200 색 번호 64000  ... 눌러서 (되풀이 눌림)
"""
import os, sys, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pal, pics, tiles, vgaart

ROOT = pics.ROOT


def pack(data):
    """간단한 되풀이 눌림: 0x00..0x7F = 그대로 n+1 바이트, 0x80..0xFF = 다음 한 바이트 (n-126)번"""
    out = bytearray()
    i = 0
    n = len(data)
    while i < n:
        j = i
        while j + 1 < n and data[j + 1] == data[i] and j - i < 127:
            j += 1
        run = j - i + 1
        if run >= 3:
            out.append(0x80 + run - 3)
            out.append(data[i])
            i += run
        else:
            j = i
            lit = bytearray()
            while j < n and len(lit) < 128:
                r = 1
                while j + r < n and data[j + r] == data[j] and r < 4:
                    r += 1
                if r >= 3:
                    break
                lit.append(data[j])
                j += 1
            out.append(len(lit) - 1)
            out += lit
            i = j
    return bytes(out)


def main():
    R = vgaart.recipes()
    out = bytearray(b'TTVGA1\0\0')
    out += struct.pack('<H', len(vgaart.NAMES))
    for c in pal.PAL:
        out += bytes(c)
    for t in tiles.build():
        out += bytes(t)
    for n in vgaart.NAMES:
        px = vgaart.render(n, R)
        body = pack(bytes(px))
        out += n.encode('ascii').ljust(16, b'\0')
        out += struct.pack('<I', len(body))
        out += body
        print('%-12s %6d -> %6d' % (n, len(px), len(body)))
    open(os.path.join(ROOT, 'TTVGA.DAT'), 'wb').write(bytes(out))
    print('TTVGA.DAT %d 바이트' % len(out))


if __name__ == '__main__':
    main()
