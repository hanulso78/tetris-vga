# 원판 그림 파일 읽기 (BKGR0..9, SLC, TETRIS.TTL) -> 320x200 CGA 점 번호(0..3) 배열
#   BKGR/SLC : 머리 2 바이트(너비 바이트수, 줄수) + 바이트.  윗 두 비트가 11 이면
#              (아래 6 비트)번 되풀이, 다음 바이트가 그 값 (원본 04B1 과 같은 규칙)
#   TETRIS.TTL : 머리 4 바이트(너비 320, 줄수 200) + 눌리지 않은 16000 바이트
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))


def unrle(data, n):
    out = bytearray()
    i = 0
    left = n
    while left > 0 and i < len(data):
        b = data[i]
        i += 1
        left -= 1
        if (b & 0xC0) == 0xC0:
            c = b & 0x3F
            v = data[i]
            i += 1
            left -= 1
            out += bytes([v]) * c
        else:
            out.append(b)
    return bytes(out)


def load_raw(name):
    """(바이트 배열 16000, 너비 바이트수) - CGA 한 바이트에 네 점"""
    d = open(os.path.join(ROOT, name), 'rb').read()
    if name.upper().endswith('.TTL'):
        return d[4:4 + 16000], 80
    w, h = d[0], d[1]
    body = d[2:]
    if len(body) == w * h:
        return body, w
    return unrle(body, len(body))[:w * h], w


def load(name):
    """320x200 점 번호 배열 (행 우선, 값 0..3)"""
    raw, w = load_raw(name)
    px = bytearray(320 * 200)
    for y in range(200):
        row = raw[y * w:(y + 1) * w]
        for x in range(320):
            b = row[x >> 2] if (x >> 2) < len(row) else 0
            px[y * 320 + x] = (b >> (6 - 2 * (x & 3))) & 3
    return px


def save_png(px, fn, pal=((0, 0, 0), (0, 170, 170), (170, 0, 0), (170, 170, 170))):
    from PIL import Image
    im = Image.new('RGB', (320, 200))
    ip = im.load()
    for y in range(200):
        for x in range(320):
            ip[x, y] = pal[px[y * 320 + x]]
    im.save(fn)


if __name__ == '__main__':
    import sys
    for n in sys.argv[1:]:
        px = load(n)
        save_png(px, os.path.join(ROOT, 'tools', '_pic_%s.png' % n.replace('.', '_')))
        print(n, 'ok')
