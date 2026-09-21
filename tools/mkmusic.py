# -*- coding: utf-8 -*-
"""TETVGA.EXE 배경음악 - Tetris Classic (1992, Spectrum HoloByte, 음악 Paul Mogg) 의
   OPL3(YMF262) VGM 을 화면별로 골라 SOUND.DAT 하나로 묶는다.

   쓰는 법 :  python tools/mkmusic.py [--wav]      (--wav: 들어 보기용 WAV 도 뽑는다)

   원본(vgm/)이 이미 OPL3 스트림이라 고치지 않고 그대로 담는다.  ttmusic.c 가
   0x5E/0x5F (뱅크 0/1) 명령을 애드립 포트 388/389, 38A/38B 로 그대로 내보낸다.
   (아타리판 POKEY 음악을 OPL2 로 옮기던 길은 tools/vgm2opl.py 에 남아 있다)
"""
import os, sys, gzip, struct, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from oplvgm import bundle

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
SRC = os.path.join(ROOT, 'vgm')

#  (곡 이름, 원본 파일)  - ttvga.h 의 MUS_* 차례와 같아야 한다
TRACKS = [
    ('SPLASH', '01_Splash.vgm'),
    ('TITLE', '02_Title.vgm'),
    ('LEVEL1', '03_Level1.vgm'),
    ('LEVEL2', '05_Level2.vgm'),
    ('LEVEL3', '06_Level3.vgm'),
    ('LEVEL4', '07_Level4.vgm'),
    ('LEVEL5', '08_Level5.vgm'),
    ('LEVEL6', '09_Level6.vgm'),
    ('LEVEL7', '10_Level7.vgm'),
    ('LEVEL8', '11_Level8.vgm'),
    ('LEVEL9', '12_Level9.vgm'),
    ('LEVEL10', '13_Level10.vgm'),
    ('ADVANCE', '04_AdvanceLevel.vgm'),
    ('GAMEOVER', '14_GameOver.vgm'),
    ('TOP10', '15_Top10.vgm'),
    ('HIGHSC', '16_HighScore.vgm'),
]


def load(path):
    d = open(path, 'rb').read()
    if d[:2] == b'\x1f\x8b':
        d = gzip.decompress(d)
    return d


def main():
    songs = []
    for name, src in TRACKS:
        d = load(os.path.join(SRC, src))
        n = struct.unpack('<I', d[0x18:0x1c])[0]
        print('%-8s <- %-22s %6d bytes  %4.0f초' % (name, src, len(d), n / 44100.0))
        songs.append((name, d))
    bundle(os.path.join(ROOT, 'SOUND.DAT'), songs)
    if '--wav' in sys.argv:
        exe = os.path.join(ROOT, 'tools', 'vgmwav.exe')
        for name, d in songs[:3]:
            tmp = os.path.join(ROOT, 'tools', name + '.VGM')
            open(tmp, 'wb').write(d)
            subprocess.run([exe, tmp, os.path.join(ROOT, 'tools', name + '.wav'), '45'])


if __name__ == '__main__':
    main()
