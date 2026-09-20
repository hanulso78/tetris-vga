# 개선판 미리보기: hostvga.exe 를 키 목록으로 돌려 화면을 BMP 로 모으고 한 장으로 붙인다
#   python tools/shotvga.py "키 키 ..." [붙일파일.png] [몇 번 폴마다]
import os, sys, glob, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import emu
from difftest import parse
from PIL import Image

ROOT = emu.ROOT
HERE = os.path.dirname(os.path.abspath(__file__))
keys = parse(sys.argv[1]) if len(sys.argv) > 1 else []
out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, '_shots.png')
every = sys.argv[3] if len(sys.argv) > 3 else '250'

shots = os.path.join(HERE, 'shots')
os.makedirs(shots, exist_ok=True)
for f in glob.glob(os.path.join(shots, '*.bmp')):
    os.remove(f)
kf = os.path.join(HERE, '_kv.txt')
open(kf, 'w').write(''.join('%d %x\n' % k for k in keys))
env = dict(os.environ, TTSHOT=os.path.join(shots, 's'), TTSHOTPOLL=every)
subprocess.run([os.path.join(ROOT, 'hostvga.exe'), os.path.join(HERE, '_tr.txt'), 'n', kf, ROOT], env=env)
fs = sorted(glob.glob(os.path.join(shots, '*.bmp')))
print('%d 장' % len(fs))
if fs:
    sel = [fs[i * (len(fs) - 1) // 11] for i in range(12)] if len(fs) > 12 else fs
    cols = 3
    rows = (len(sel) + cols - 1) // cols
    W = Image.new('RGB', (cols * 322, rows * 202), (40, 40, 40))
    for i, f in enumerate(sel):
        W.paste(Image.open(f).convert('RGB'), ((i % cols) * 322, (i // cols) * 202))
    W.save(out)
    print(out)
