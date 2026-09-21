# -*- coding: utf-8 -*-
"""아타리(POKEY) VGM 을 애드립(OPL2, YM3812) VGM 으로 옮긴다.

   python tools/vgm2opl.py "vgz/02 Loginska.vgz" out.vgm [-v 세기]

   원본은 Atari Games 테트리스(1988, Brad Fuller) 음악으로 POKEY 두 개를 쓴다.
   AUDCTL=0x78 이라 칩마다 16비트 채널 둘(1.79MHz)씩, 모두 네 성부다.
      가락 높이 : f = 1789790 / (2 * (AUDF16 + 7))          (16비트, 1.79MHz)
      소리 크기 : AUDC 아래 4비트 (0..15),  위 3비트 = 찌그러짐 (A0 이면 맑은 소리)
   이것을 OPL2 채널 0..3 에 그대로 실어, 기다림(wait)은 원본 그대로 옮긴다.
   음량은 캐리어 감쇠(40h)로, 새 음은 키 온으로 낸다 (POKEY 는 엔벨로프가 없고
   드라이버가 음량을 직접 그리므로, 소리내기 틀은 '바로 최대, 끝까지 유지' 로 둔다).
"""
import gzip, struct, sys, math

PC = 1789790.0                      # POKEY 클럭 (아케이드 기판)
OP1 = [0x00, 0x01, 0x02, 0x08, 0x09, 0x0A, 0x10, 0x11, 0x12]
OP2 = [0x03, 0x04, 0x05, 0x0B, 0x0C, 0x0D, 0x13, 0x14, 0x15]


def fnum_block(f):
    """소리 높이(Hz) -> OPL2 의 (F-Number, 블록)"""
    for blk in range(8):
        fn = int(round(f * (1 << (20 - blk)) / 49716.0))
        if fn < 1024 and (fn >= 300 or blk == 7):
            return fn, blk
    return 1023, 7


class Out:
    """OPL2 VGM 쓰기 (기다림은 원본 그대로)"""

    def __init__(self):
        self.d = bytearray()
        self.samples = 0
        self.loop = None

    def w(self, reg, val):
        self.d += bytes((0x5A, reg & 0xFF, val & 0xFF))

    def wait(self, n):
        self.samples += n
        while n > 65535:
            self.d += bytes((0x61, 0xFF, 0xFF))
            n -= 65535
        if n > 0:
            self.d += bytes((0x61, n & 0xFF, n >> 8))


#  소리틀: 캐리어만 울린다 (모듈레이터는 죽임).  물결 3 = 뾰족한 소리 (칩튠 느낌)
def patch(o, ch, noise=False):
    m, c = OP1[ch], OP2[ch]
    o.w(0x20 + m, 0x21 if not noise else 0x2F)      # EG 유지, 배음 1 (잡음은 15)
    o.w(0x40 + m, 0x3F if not noise else 0x08)      # 모듈레이터 죽임 (잡음은 살짝)
    o.w(0x60 + m, 0xF0)
    o.w(0x80 + m, 0x0F)
    o.w(0xE0 + m, 0x00)
    o.w(0x20 + c, 0x21)
    o.w(0x40 + c, 0x3F)
    o.w(0x60 + c, 0xF0)
    o.w(0x80 + c, 0x0F)
    o.w(0xE0 + c, 0x03 if not noise else 0x00)      # 3 = 뾰족한 물결
    o.w(0xC0 + ch, 0x00 if not noise else 0x0E)     # 잡음은 되먹임 크게


def level(vol, boost):
    """POKEY 음량 0..15 -> OPL 감쇠 0..63 (0 이 가장 큼)"""
    if vol <= 0:
        return 63
    db = 20.0 * math.log10(vol / 15.0)
    tl = int(round(-db / 0.75)) - boost
    return max(0, min(63, tl))


class Voice:
    def __init__(self):
        self.lo = self.hi = 0
        self.audc = 0
        self.on = False
        self.fn = self.blk = -1
        self.tl = -1
        self.noise = None


def convert(data, boost=6, chans=4):
    ver = struct.unpack('<I', data[8:12])[0]
    dstart = 0x40 if ver < 0x150 else 0x34 + struct.unpack('<I', data[0x34:0x38])[0]
    loop_rel = struct.unpack('<I', data[0x1C:0x20])[0]
    loop_pos = 0x1C + loop_rel if loop_rel else 0
    loop_samples = struct.unpack('<I', data[0x20:0x24])[0]

    o = Out()
    o.w(0x01, 0x20)                 # 물결 고르기 켜기
    o.w(0x08, 0x00)
    o.w(0xBD, 0x00)
    for ch in range(chans):
        patch(o, ch)
    vs = [Voice() for _ in range(chans)]
    audctl = [0x78, 0x78]

    def flush():
        for i, v in enumerate(vs):
            vol = v.audc & 0x0F
            noise = (v.audc & 0xE0) != 0xA0
            if noise != v.noise:
                patch(o, i, noise)
                v.noise = noise
                v.tl = -1
            if vol == 0:
                if v.on:
                    o.w(0xB0 + i, (v.blk << 2) | (v.fn >> 8) if v.fn >= 0 else 0)
                    v.on = False
                continue
            n = v.lo | (v.hi << 8)
            f = PC / (2.0 * (n + 7))
            if f < 20 or f > 8000:
                continue
            fn, blk = fnum_block(f)
            tl = level(vol, boost)
            if tl != v.tl:
                o.w(0x40 + OP2[i], tl)
                v.tl = tl
            if not v.on or fn != v.fn or blk != v.blk:
                o.w(0xA0 + i, fn & 0xFF)
                o.w(0xB0 + i, 0x20 | (blk << 2) | (fn >> 8))
                v.fn, v.blk, v.on = fn, blk, True

    p = dstart
    while p < len(data):
        if loop_pos and o.loop is None and p >= loop_pos:
            flush()
            o.loop = len(o.d)
        c = data[p]
        if c == 0xBB:                                   # POKEY 쓰기
            a, val = data[p + 1], data[p + 2]
            chip = 1 if (a & 0x80) else 0
            r = a & 0x0F
            base = chip * 2
            if r == 0x00:
                vs[base].lo = val
            elif r == 0x02:
                vs[base].hi = val
            elif r == 0x03:
                vs[base].audc = val
            elif r == 0x04:
                vs[base + 1].lo = val
            elif r == 0x06:
                vs[base + 1].hi = val
            elif r == 0x07:
                vs[base + 1].audc = val
            elif r == 0x08:
                audctl[chip] = val
            p += 3
        elif c == 0x61:
            flush()
            o.wait(data[p + 1] | (data[p + 2] << 8))
            p += 3
        elif c == 0x62:
            flush()
            o.wait(735)
            p += 1
        elif c == 0x63:
            flush()
            o.wait(882)
            p += 1
        elif 0x70 <= c <= 0x7F:
            flush()
            o.wait((c & 15) + 1)
            p += 1
        elif c == 0x66:
            break
        elif c in (0x4F, 0x50):
            p += 2
        elif 0x51 <= c <= 0x5F:
            p += 3
        elif c == 0xA0:
            p += 3
        elif 0x80 <= c <= 0x8F:
            p += 1
        elif c == 0xE0:
            p += 5
        else:
            p += 1
    flush()
    for i in range(chans):                              # 끝: 모두 키 오프
        o.w(0xB0 + i, 0x00)
    o.d += b'\x66'

    DATA = 0x100
    hdr = bytearray(DATA)
    hdr[0:4] = b'Vgm '
    struct.pack_into('<I', hdr, 0x04, DATA + len(o.d) - 4)
    struct.pack_into('<I', hdr, 0x08, 0x151)
    struct.pack_into('<I', hdr, 0x18, o.samples)
    if o.loop is not None:
        struct.pack_into('<I', hdr, 0x1C, DATA + o.loop - 0x1C)
        struct.pack_into('<I', hdr, 0x20, loop_samples)
    struct.pack_into('<I', hdr, 0x34, DATA - 0x34)
    struct.pack_into('<I', hdr, 0x50, 3579545)          # YM3812 클럭
    return bytes(hdr) + bytes(o.d)


def load(path):
    d = open(path, 'rb').read()
    if d[:2] == b'\x1f\x8b':
        d = gzip.decompress(d)
    return d


if __name__ == '__main__':
    src = sys.argv[1]
    dst = sys.argv[2]
    boost = int(sys.argv[4]) if len(sys.argv) > 4 else 6
    out = convert(load(src), boost)
    open(dst, 'wb').write(out)
    print('%s -> %s  %d bytes' % (src, dst, len(out)))
