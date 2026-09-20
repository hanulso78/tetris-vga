# 마구잡이 키 시나리오 만들기 (회귀 시험용)
#   python tools/mkkeys.py 씨앗 개수 > test/k_rnd씨앗.txt
import random, sys

seed = int(sys.argv[1])
n = int(sys.argv[2]) if len(sys.argv) > 2 else 120
r = random.Random(seed)
# 놀이 중 쓰는 키들 (이름은 tools/keys.py 의 것)
PLAY = ['left', 'right', 'enter', 'space', 'down', 'up', 'j', 'l', 'k', 'm', 'i', 's', 'p',
        'f1', 'f2', 'f3', 'f4', 'esc', '1', '2']
out = ['50:enter', '300:enter', '300:enter']          # 제목 -> 만든이 -> 판 고르기
for _ in range(n):
    out.append('%d:%s' % (r.choice([8, 12, 20, 30, 45, 70]), r.choice(PLAY)))
print(' '.join(out))
