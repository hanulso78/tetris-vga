# -*- coding: utf-8 -*-
"""TETVGA.EXE 배경음악 - 애드립(OPL2) VGM 곡 셋을 SOUND.DAT 하나로 묶는다.

   쓰는 법 :  python tools/mkmusic.py [--vgm]     (--vgm: 들어 보기용 .VGM 도 남긴다)

   곡 (ttmusic.c 의 차례와 같다)
       TTTITLE   제목, 차례표, 판 고르기   '코로베이니키' (러시아 민요, 테트리스 하면 떠오르는 그 가락)
       TTPLAY    놀이 중                   같은 가락을 더 빠르고 신나게 (드럼 + 튀는 베이스)
       TTOVER    끝났을 때                 짧게 내려앉는 마침꼴
   원판에는 배경음악이 없다 (스피커 효과음만).  효과음은 그대로 두고 음악만 애드립으로 얹는다.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from oplvgm import *

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')


def chords(s, t, prog, ch, dur, oct_lo=48, n=3, vel=None):
    """prog: [(시작, 길이, 화음이름)] - 닫힌 화음을 ch, ch+1, ch+2 에"""
    for st, ln, name in prog:
        for k, m in enumerate(voicing(name, oct_lo, n)):
            s.note(t + st, ln, ch + k, m, gap=0.25)


# ---------------------------------------------------------------- 제목 ----
#  코로베이니키 (Korobeiniki, 19 세기 러시아 민요 - 테트리스 하면 떠오르는 그 가락).
#  div=4 라 한 틱은 16분음표, 한 마디(4/4)는 16 틱.
KOROB_A = ('E5/8 B4/4 C5/4 D5/8 C5/4 B4/4 '      # 1-2 마디
           'A4/8 A4/4 C5/4 E5/8 D5/4 C5/4 '      # 3-4
           'B4/12 C5/4 D5/8 E5/8 '               # 5-6
           'C5/8 A4/8 A4/8 r/8 '                 # 7-8
           'D5/12 F5/4 A5/8 G5/4 F5/4 '          # 9-10
           'E5/12 C5/4 E5/8 D5/4 C5/4 '          # 11-12
           'B4/12 C5/4 D5/8 E5/8 '               # 13-14
           'C5/8 A4/8 A4/8 r/8 ')                # 15-16  (모두 256 틱)
KOROB_B = ('E5/8 C5/8 D5/8 B4/8 '                # 17-18
           'C5/8 A4/8 G#4/8 B4/8 '               # 19-20
           'E5/8 C5/8 D5/8 B4/8 '                # 21-22
           'C5/4 E5/4 A5/8 G#5/16 ')             # 23-24  (128 틱)
BARS_A = ['Em', 'Em', 'Am', 'Em', 'Em', 'Em', 'Am', 'E7',
          'Dm', 'Dm', 'Am', 'Am', 'Em', 'Em', 'Am', 'E7']
BARS_B = ['Am', 'Em', 'Am', 'E7', 'Am', 'Em', 'Am', 'E7']
KOROB_CH = ([(16 * i, 16, n) for i, n in enumerate(BARS_A)] +
            [(256 + 16 * i, 16, n) for i, n in enumerate(BARS_B)])
KOROB_LEN = 384


def song_title():
    s = Song(bpm=150, div=4)
    s.patch(0, 0, P_PLUCK)          # 가락
    s.patch(0, 1, P_PIZZ)           # 받침 화음 셋
    s.patch(0, 2, P_PIZZ)
    s.patch(0, 3, P_PIZZ)
    s.patch(0, 4, P_BASS)
    s.melody(0, KOROB_A, 0)
    s.melody(256, KOROB_B, 0)
    for st, ln, name in KOROB_CH:
        for k, m in enumerate(voicing(name, 55, 3)):
            s.note(st + 4, 4, 1 + k, m, gap=0.3)
            s.note(st + 12, 4, 1 + k, m, gap=0.3)
        s.note(st, 8, 4, bass_root(name, 36), gap=0.15)
        s.note(st + 8, 8, 4, bass_root(name, 36) + 7, gap=0.15)
    for st in range(0, KOROB_LEN, 8):     # 가벼운 장단
        s.drum(st, BD)
        s.drum(st + 4, HH)
        if st % 16 == 8:
            s.drum(st, SD)
    s.loop_tick = 0
    s.end_tick = KOROB_LEN
    return render(s, 'TTTITLE')


# ---------------------------------------------------------------- 놀이 ----
#  같은 코로베이니키를 더 빠르게, 튀는 베이스와 드럼을 얹어 신나게
def song_play():
    s = Song(bpm=178, div=4)
    s.patch(0, 0, P_PLUCK)          # 가락 (발랄라이카 느낌)
    s.patch(0, 1, P_MUTED)          # 받침 화음
    s.patch(0, 2, P_MUTED)
    s.patch(0, 3, P_MUTED)
    s.patch(0, 4, P_BASS)
    s.patch(0, 5, P_GLOCK)          # 가락 한 옥타브 위로 살짝
    s.melody(0, KOROB_A, 0)
    s.melody(256, KOROB_B, 0)
    s.melody(0, KOROB_A, 5, shift=12, gap=0.5)      # 한 옥타브 위로 살짝 겹쳐 반짝이게
    s.melody(256, KOROB_B, 5, shift=12, gap=0.5)
    for st, ln, name in KOROB_CH:
        for k, m in enumerate(voicing(name, 55, 3)):
            s.note(st + 4, 3, 1 + k, m, gap=0.4)        # 뒷박 찌르기
            s.note(st + 12, 3, 1 + k, m, gap=0.4)
        r = bass_root(name, 36)
        for k, o in enumerate((0, 12, 7, 12)):          # 통통 튀는 베이스
            s.note(st + k * 4, 4, 4, r + o, gap=0.25)
    for st in range(0, KOROB_LEN, 4):                   # 빠른 장단
        if st % 16 == 0:
            s.drum(st, BD)
        if st % 16 == 8:
            s.drum(st, SD)
        s.drum(st, HH)
    s.loop_tick = 0
    s.end_tick = KOROB_LEN
    return render(s, 'TTPLAY')


# ---------------------------------------------------------------- 끝 ----
def song_over():
    s = Song(bpm=96, div=4)
    s.patch(0, 0, P_TROMB)
    s.patch(0, 1, P_STRINGS)
    s.patch(0, 2, P_STRINGS)
    s.patch(0, 3, P_STRINGS)
    s.patch(0, 4, P_BASS)
    s.melody(0, 'E5/8 D5/8 C5/8 B4/8 A4/16 G#4/8 A4/24', 0)
    for st, ln, name in ((0, 16, 'Am'), (16, 16, 'Dm'), (32, 16, 'E7'), (48, 24, 'Am')):
        for k, m in enumerate(voicing(name, 50, 3)):
            s.note(st, ln, 1 + k, m, gap=0.1)
        s.note(st, ln, 4, bass_root(name, 33), gap=0.1)
    s.end_tick = 76
    return render(s, 'TTOVER')


def main():
    songs = [song_title(), song_play(), song_over()]
    bundle(os.path.join(ROOT, 'SOUND.DAT'), songs)
    if '--vgm' in sys.argv:
        for name, data in songs:
            open(os.path.join(ROOT, 'tools', name + '.VGM'), 'wb').write(data)
            print('tools/%s.VGM' % name)


if __name__ == '__main__':
    main()
