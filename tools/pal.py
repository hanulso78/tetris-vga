# 256색 판(팔레트) 한 벌.  개선판(TETVGA)이 쓰는 색은 모두 여기서 나온다.
#   0..15   CGA 16색 (색표가 없는 점의 대비용)
#   16..255 20 가지 색줄(ramp) x 12 단계 (어두운 쪽 -> 밝은 쪽)
# 값은 VGA 판 그대로 0..63.

CGA16 = [(0, 0, 0), (0, 0, 42), (0, 42, 0), (0, 42, 42), (42, 0, 0), (42, 0, 42), (42, 21, 0), (42, 42, 42),
         (21, 21, 21), (21, 21, 63), (21, 63, 21), (21, 63, 63), (63, 21, 21), (63, 21, 63), (63, 63, 21),
         (63, 63, 63)]

# (이름, 어두운 끝, 밝은 끝, 가운데 색(없으면 곧은 사이값))
RAMPS = [
    ('gray',    (2, 2, 3),    (60, 60, 62),  None),
    ('steel',   (3, 5, 9),    (54, 58, 63),  (26, 32, 40)),
    ('sky',     (2, 6, 20),   (54, 62, 63),  (16, 34, 56)),
    ('ice',     (2, 12, 16),  (56, 63, 63),  (10, 40, 48)),
    ('night',   (0, 0, 6),    (34, 40, 63),  (6, 8, 26)),
    ('violet',  (6, 0, 14),   (54, 40, 63),  (26, 12, 42)),
    ('pink',    (14, 0, 10),  (63, 46, 56),  (44, 14, 34)),
    ('red',     (10, 0, 0),   (63, 40, 34),  (44, 6, 6)),
    ('orange',  (12, 3, 0),   (63, 52, 28),  (50, 22, 4)),
    ('gold',    (14, 8, 0),   (63, 60, 34),  (48, 34, 6)),
    ('olive',   (8, 8, 2),    (56, 58, 30),  (30, 32, 10)),
    ('green',   (0, 8, 2),    (40, 63, 36),  (6, 32, 10)),
    ('lime',    (4, 12, 0),   (50, 63, 30),  (20, 40, 8)),
    ('teal',    (0, 8, 8),    (36, 63, 58),  (4, 30, 28)),
    ('brown',   (8, 4, 2),    (54, 42, 30),  (28, 17, 9)),
    ('sand',    (14, 9, 5),   (63, 56, 44),  (42, 30, 19)),
    ('stone',   (7, 6, 6),    (60, 58, 54),  (32, 30, 27)),
    ('crimson', (8, 0, 2),    (63, 26, 30),  (40, 2, 8)),
    ('cyanmet', (0, 6, 10),   (44, 63, 63),  (8, 34, 44)),
    ('snow',    (8, 12, 20),  (63, 63, 63),  (34, 42, 52)),
]
NR = len(RAMPS)
NS = 12                                     # 색줄 한 줄의 단계 수
RAMP = {r[0]: k for k, r in enumerate(RAMPS)}


def _mix(a, b, t):
    return tuple(a[k] + (b[k] - a[k]) * t for k in range(3))


def build():
    """256 색 (R, G, B) 목록 (0..63)"""
    pal = [tuple(c) for c in CGA16]
    for name, lo, hi, mid in RAMPS:
        for s in range(NS):
            t = s / (NS - 1.0)
            if mid is None:
                c = _mix(lo, hi, t)
            elif t < 0.5:
                c = _mix(lo, mid, t * 2)
            else:
                c = _mix(mid, hi, (t - 0.5) * 2)
            pal.append(tuple(min(63, max(0, int(round(v)))) for v in c))
    return pal


PAL = build()
RGB = [(r * 255 // 63, g * 255 // 63, b * 255 // 63) for r, g, b in PAL]


def idx(ramp, shade):
    """색줄 이름과 단계(0..11) -> 팔레트 번호"""
    s = min(NS - 1, max(0, int(round(shade))))
    return 16 + RAMP[ramp] * NS + s


def ramp_color(ramp, t):
    """색줄 위의 실수 자리 t(0..1) -> (r, g, b) 0..255"""
    f = t * (NS - 1)
    k = min(NS - 2, max(0, int(f)))
    a, b = RGB[16 + RAMP[ramp] * NS + k], RGB[16 + RAMP[ramp] * NS + k + 1]
    u = f - k
    return tuple(a[i] + (b[i] - a[i]) * u for i in range(3))


def darken(i, n=5):
    """같은 색줄에서 n 단계 어두운 색 (테두리 그림자용)"""
    if i < 16:
        return 16
    r, sh = (i - 16) // NS, (i - 16) % NS
    return 16 + r * NS + max(0, sh - n)


def quantize(rgb, lut={}):
    """(r, g, b) 0..255 -> 가장 가까운 팔레트 번호 (0 번은 '색 없음' 이라 쓰지 않는다)"""
    key = (int(rgb[0]) >> 2, int(rgb[1]) >> 2, int(rgb[2]) >> 2)
    v = lut.get(key)
    if v is None:
        r, g, b = key[0] * 4 + 2, key[1] * 4 + 2, key[2] * 4 + 2
        best, bi = 1 << 30, 1
        for i in range(1, 256):
            pr, pg, pb = RGB[i]
            d = (pr - r) ** 2 * 3 + (pg - g) ** 2 * 4 + (pb - b) ** 2 * 2
            if d < best:
                best, bi = d, i
        lut[key] = v = bi
    return v


if __name__ == '__main__':
    from PIL import Image
    im = Image.new('RGB', (16 * 20, 16 * 16))
    px = im.load()
    for i in range(256):
        for y in range(16):
            for x in range(20):
                px[(i % 16) * 20 + x, (i // 16) * 16 + y] = RGB[i]
    im.save('tools/_pal.png')
    print('팔레트 %d 색' % len(PAL))
