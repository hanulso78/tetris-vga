# -*- coding: utf-8 -*-
"""원판 CGA 그림(4색)을 256색으로 다시 칠한다.

   python tools/vgaart.py           -> TTVGA.DAT + tools/_vga_*.png (미리보기)

   방법: CGA 그림은 색이 넷뿐이라 그늘을 '점 뿌리기(디더)'로 낸다.  그래서 먼저
   점마다 둘레(가우스)를 보고 네 색이 각각 얼마나 덮고 있는지(0..1)를 구해 고른 밝기를
   얻고, 그림마다 정한 '무엇을 무슨 색으로' 규칙에 그 밝기를 실어 칠한다.
   가장자리는 뭉개지지 않게 원래 색 쪽으로 다시 당긴다.
"""
import os, sys, math, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pal, pics

ROOT = pics.ROOT
W, H = 320, 200


# ---- 덮임 비율 (디더 풀기) ---------------------------------------------------------
def coverage(px, sigma=1.25):
    """점마다 네 색의 덮임 비율 (가우스로 흐린 것)"""
    n = int(sigma * 2.5) + 1
    ker = [math.exp(-(k * k) / (2.0 * sigma * sigma)) for k in range(-n, n + 1)]
    s = sum(ker)
    ker = [k / s for k in ker]
    planes = []
    for c in range(4):
        a = [1.0 if v == c else 0.0 for v in px]
        b = [0.0] * (W * H)
        for y in range(H):
            row = a[y * W:(y + 1) * W]
            for x in range(W):
                t = 0.0
                for k in range(-n, n + 1):
                    xx = x + k
                    if xx < 0:
                        xx = 0
                    elif xx >= W:
                        xx = W - 1
                    t += row[xx] * ker[k + n]
                b[y * W + x] = t
        d = [0.0] * (W * H)
        for x in range(W):
            col = [b[y * W + x] for y in range(H)]
            for y in range(H):
                t = 0.0
                for k in range(-n, n + 1):
                    yy = y + k
                    if yy < 0:
                        yy = 0
                    elif yy >= H:
                        yy = H - 1
                    t += col[yy] * ker[k + n]
                d[y * W + x] = t
        planes.append(d)
    return planes


# ---- 색 고르개 ------------------------------------------------------------------
def solid(name, t):
    c = pal.ramp_color(name, t)
    return lambda x, y: c


def vgrad(name, t0, t1, y0=0, y1=H):
    def f(x, y):
        u = min(1.0, max(0.0, (y - y0) / float(y1 - y0)))
        return pal.ramp_color(name, t0 + (t1 - t0) * u)
    return f


def vmix(a, b, y0, y1):
    """위쪽은 a, 아래쪽은 b (y0..y1 에서 부드럽게 바뀐다)"""
    def f(x, y):
        u = min(1.0, max(0.0, (y - y0) / float(y1 - y0)))
        u = u * u * (3 - 2 * u)
        ca, cb = a(x, y), b(x, y)
        return tuple(ca[k] + (cb[k] - ca[k]) * u for k in range(3))
    return f


def rect(inner, outer, x0, y0, x1, y1):
    """네모 안은 inner, 밖은 outer"""
    def f(x, y):
        return inner(x, y) if x0 <= x < x1 and y0 <= y < y1 else outer(x, y)
    return f


# ---- 다시 칠하기 -----------------------------------------------------------------
def recolor(px, recipe, sharp=0.45, sigma=1.25):
    """recipe: 색 번호 0..3 -> 색 고르개.  결과: 팔레트 번호 배열"""
    cov = coverage(px, sigma)
    out = bytearray(W * H)
    cache = {}
    for y in range(H):
        for x in range(W):
            i = y * W + x
            f = [cov[c][i] for c in range(4)]
            own = px[i]
            f[own] += sharp                      # 제 색 쪽으로 당겨 가장자리를 세운다
            s = sum(f)
            r = g = b = 0.0
            for c in range(4):
                if f[c] <= 0.0005:
                    continue
                cc = recipe[c](x, y)
                w = f[c] / s
                r += cc[0] * w
                g += cc[1] * w
                b += cc[2] * w
            key = (int(r) >> 1, int(g) >> 1, int(b) >> 1)
            v = cache.get(key)
            if v is None:
                cache[key] = v = pal.quantize((r, g, b))
            out[i] = v
    return out


# ---- 그림마다의 규칙 --------------------------------------------------------------
#  CGA 색: 0 검정, 1 청록, 2 빨강, 3 흰색 (모드 5 팔레트)
def recipes():
    R = {}

    # BKGR1 겨울 들판 (썰매, 눈 덮인 산, 마른 나무)
    R['BKGR1'] = {
        0: vmix(solid('night', 0.10), solid('brown', 0.12), 96, 150),     # 나무, 그림자
        1: vmix(vgrad('sky', 0.25, 0.62, 0, 110), solid('snow', 0.45), 110, 150),
        2: solid('crimson', 0.62),                                        # 틀, 썰매
        3: vmix(vgrad('sky', 0.55, 0.92, 0, 110), solid('snow', 0.95), 110, 150),
    }
    # BKGR2 공원 (나무, 꽃길, 멀리 성당)
    R['BKGR2'] = {
        0: solid('brown', 0.10),
        1: vmix(vgrad('sky', 0.42, 0.80, 0, 84), solid('green', 0.42), 84, 104),
        2: vmix(solid('orange', 0.60), solid('red', 0.55), 120, 150),     # 꽃, 벽돌길
        3: vmix(vgrad('sky', 0.72, 0.96, 0, 84), solid('sand', 0.80), 84, 120),
    }
    # BKGR3 초원의 기마병 (앞쪽에 코사크)
    R['BKGR3'] = {
        0: solid('brown', 0.08),
        1: vmix(vgrad('sky', 0.34, 0.74, 0, 92), solid('olive', 0.45), 92, 120),
        2: solid('crimson', 0.58),
        3: vmix(vgrad('sky', 0.70, 0.95, 0, 92), solid('sand', 0.82), 92, 130),
    }
    # BKGR4 우주 정거장 (지구 위)
    R['BKGR4'] = {
        0: solid('night', 0.04),
        1: solid('cyanmet', 0.55),
        2: solid('crimson', 0.60),       # 뼈대와 테두리의 붉은 줄
        3: solid('steel', 0.84),
    }
    # BKGR5 우주 왕복선 안 (창 밖에 지구)
    R['BKGR5'] = {
        0: solid('night', 0.05),
        1: solid('cyanmet', 0.58),
        2: solid('crimson', 0.58),
        3: solid('steel', 0.86),
    }
    # BKGR6 크렘린 / 성 바실리 성당
    R['BKGR6'] = {
        0: solid('night', 0.08),
        1: vmix(vgrad('night', 0.30, 0.55, 0, 90), solid('teal', 0.50), 90, 130),
        2: solid('crimson', 0.66),
        3: vmix(vgrad('violet', 0.55, 0.80, 0, 90), solid('sand', 0.86), 90, 140),
    }
    # BKGR7 아이스하키
    R['BKGR7'] = {
        0: solid('night', 0.10),
        1: vmix(solid('steel', 0.45), solid('ice', 0.78), 96, 130),
        2: solid('red', 0.64),
        3: vmix(solid('stone', 0.72), solid('snow', 0.96), 96, 130),
    }
    # BKGR8 발레 무대
    R['BKGR8'] = {
        0: solid('night', 0.06),
        1: vmix(solid('violet', 0.40), solid('sand', 0.55), 120, 160),
        2: solid('crimson', 0.60),
        3: vmix(solid('gold', 0.78), solid('sand', 0.90), 120, 160),
    }
    # BKGR9 경기장 (밤 경기)
    R['BKGR9'] = {
        0: solid('night', 0.06),
        1: vmix(vgrad('night', 0.25, 0.45, 0, 90), solid('lime', 0.45), 110, 150),
        2: solid('red', 0.62),
        3: vmix(vgrad('night', 0.55, 0.75, 0, 90), solid('stone', 0.86), 110, 150),
    }
    # BKGR0 붉은 벽돌 거리와 양파 지붕
    R['BKGR0'] = {
        0: solid('brown', 0.10),
        1: vmix(vgrad('sky', 0.40, 0.72, 0, 70), solid('steel', 0.45), 70, 110),
        2: vmix(solid('crimson', 0.64), solid('brown', 0.45), 110, 170),   # 벽돌
        3: vmix(vgrad('sky', 0.74, 0.94, 0, 70), solid('sand', 0.80), 70, 120),
    }
    # SLC 소련 지도 (판/높이 고르기)
    R['SLC'] = {
        0: vmix(solid('steel', 0.30), solid('night', 0.18), 40, 70),
        1: vmix(solid('steel', 0.62), solid('sky', 0.45), 40, 70),
        2: solid('crimson', 0.66),
        3: solid('stone', 0.92),
    }
    # 제목 그림: 성당은 금빛, 글자는 아래로 갈수록 붉게
    R['TETRIS.TTL'] = {
        0: vgrad('night', 0.14, 0.02, 0, 200),
        1: solid('gold', 0.80),
        2: vmix(vgrad('gold', 0.90, 0.72, 0, 120), vgrad('orange', 0.80, 0.60, 120, 200), 118, 132),
        3: solid('gold', 0.95),
    }
    return R


NAMES = ['BKGR0', 'BKGR1', 'BKGR2', 'BKGR3', 'BKGR4', 'BKGR5', 'BKGR6', 'BKGR7', 'BKGR8', 'BKGR9',
         'SLC', 'TETRIS.TTL']


# ---- 원판 글꼴로 글씨 넣기 (DS:7C6C 부터 글자마다 16 바이트, 8x8) ----------------
def font_glyphs():
    import struct
    d = open(os.path.join(ROOT, 'CT_UNP.EXE'), 'rb').read()
    h = struct.unpack('<14H', d[:28])
    img = d[h[4] * 16:]
    return img[0x0D * 16 + 0x7C6C:]


def draw_text(out, x0, y0, text, col, shadow=None):
    """다시 칠한 그림(팔레트 번호 배열) 위에 글씨를 얹는다"""
    g = font_glyphs()
    for n, ch in enumerate(text.upper()):
        k = ord(ch) - 0x20
        if k < 0:
            continue
        for row in range(8):
            b = g[k * 16 + row * 2:k * 16 + row * 2 + 2]
            for j in range(8):
                v = (b[j >> 2] >> (6 - 2 * (j & 3))) & 3
                if not v:
                    continue
                x, y = x0 + n * 8 + j, y0 + row
                if 0 <= x < W and 0 <= y < H:
                    out[y * W + x] = col
                    if shadow is not None and x + 1 < W and y + 1 < H:
                        if out[(y + 1) * W + x + 1] != col:
                            out[(y + 1) * W + x + 1] = shadow


WELL = (118, 8, 202, 172)       # 조각이 떨어지는 칸 (10x20 칸, 8x8 점): 늘 어둡게


def render(name, R):
    px = pics.load(name)
    r = dict(R[name])
    if name not in ('TETRIS.TTL', 'SLC'):
        r[0] = rect(solid('night', 0.02), r[0], *WELL)
    out = recolor(px, r)
    if name == 'TETRIS.TTL':                      # 256색으로 다시 그린 사람
        draw_text(out, 56, 168, 'VGA REMASTER BY IN-HAK MIN', pal.idx('gold', 9), pal.idx('brown', 1))
    return out


def save_png(out, fn):
    from PIL import Image
    im = Image.new('RGB', (W, H))
    ip = im.load()
    for y in range(H):
        for x in range(W):
            ip[x, y] = pal.RGB[out[y * W + x]]
    im.save(fn)


if __name__ == '__main__':
    R = recipes()
    want = sys.argv[1:] or NAMES
    for n in want:
        out = render(n, R)
        save_png(out, os.path.join(ROOT, 'tools', '_vga_%s.png' % n.replace('.', '_')))
        print(n, 'ok')
