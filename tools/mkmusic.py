# -*- coding: utf-8 -*-
"""TETVGA.EXE 배경음악 - 아타리판 테트리스(1988, Atari Games / Brad Fuller) 음악을
   애드립(OPL2) VGM 으로 옮겨 SOUND.DAT 하나로 묶는다.

   쓰는 법 :  python tools/mkmusic.py [--vgm]     (--vgm: 옮긴 .VGM 도 따로 남긴다)

   원본은 vgz/ 안의 POKEY VGM (2xPokey, 16비트 채널 네 성부).  tools/vgm2opl.py 가
   높이와 음량을 그대로 읽어 OPL2 채널 0..3 에 실어 준다.

   곡 (ttmusic.c 의 차례와 같다)
       TTTITLE   제목, 차례표, 판 고르기   Loginska (아타리판 주제곡, 되풀이)
       TTPLAY    놀이 중 (판 0,3,6,9)      Bradinsky
       TTPLAY2   놀이 중 (판 1,4,7)        Troika
       TTPLAY3   놀이 중 (판 2,5,8)        Kalinka
       TTOVER    끝났을 때                 Game Over
   원판 PC 판에는 배경음악이 없다 (스피커 효과음만).  효과음은 그대로 두고 음악만 얹는다.
   (손으로 지은 코로베이니키 편곡은 tools/mkmusic_korob.py 에 남겨 두었다)
"""
import os, sys, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from oplvgm import bundle
import vgm2opl

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
VGZ = os.path.join(ROOT, 'vgz')

#  (곡 이름, 원본 파일, 음량 올림)
TRACKS = [
    ('TTTITLE', '02 Loginska.vgz', 18),
    ('TTPLAY', '04 Bradinsky.vgz', 18),
    ('TTPLAY2', '08 Troika.vgz', 18),
    ('TTPLAY3', '06 Kalinka.vgz', 18),
    ('TTOVER', '11 Game Over.vgz', 18),
]


def main():
    songs = []
    for name, src, boost in TRACKS:
        data = vgm2opl.convert(vgm2opl.load(os.path.join(VGZ, src)), boost)
        n = struct.unpack('<I', data[0x18:0x1c])[0]
        loop = struct.unpack('<I', data[0x1c:0x20])[0]
        print('%-8s <- %-24s %7d bytes  %5.1f초%s' % (name, src, len(data), n / 44100.0,
                                                      '  (되풀이)' if loop else ''))
        songs.append((name, data))
        if '--vgm' in sys.argv:
            open(os.path.join(ROOT, 'tools', name + '.VGM'), 'wb').write(data)
    bundle(os.path.join(ROOT, 'SOUND.DAT'), songs)


if __name__ == '__main__':
    main()
