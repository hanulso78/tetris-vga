# DOSBox 에서 도스 판을 시험 모드(TTTEST)로 돌려 저장된 화면을 한 장으로 모은다.
#   python tools/dosshot.py 스크립트.txt 결과.png [exe] [조이스틱 y/n]
# 스크립트 줄: <밀리초> key <키> / <밀리초> shot <이름> / <밀리초> quit
import os, sys, subprocess, glob, tempfile
from PIL import Image

ROOT = os.environ.get('TTDIR') or os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))   # SKBDIR = 다른 게임 폴더 (release 시험)
DOSBOX = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', 'dosbox', 'dosbox.exe'))

script, out = sys.argv[1], sys.argv[2]
exe = sys.argv[3] if len(sys.argv) > 3 else 'tetris.exe'
mode = sys.argv[4] if len(sys.argv) > 4 else 'n'
open(os.path.join(ROOT, 'TTTEST.TXT'), 'w').write(open(script).read())
for f in glob.glob(os.path.join(ROOT, '*.BMP')) + glob.glob(os.path.join(ROOT, 'TTLOG.TXT')):
    os.remove(f)
conf = os.path.join(tempfile.gettempdir(), 'ttrun.conf')
open(conf, 'w').write('''[dosbox]
machine=svga_s3
memsize=32
[cpu]
core=auto
cycles=max
[autoexec]
mount C "%s"
C:
set TTTEST=TTTEST.TXT
set TTJOY=%s
%s
exit
''' % (ROOT, mode, exe))
#  창을 띄우지 않고 돌린다 (화면을 가로채지 않게).  TTSHOW=1 이면 창을 띄운다.
env = dict(os.environ)
if not os.environ.get('TTSHOW'):
    env['SDL_VIDEODRIVER'] = 'dummy'
subprocess.run([DOSBOX, '-conf', conf, '-noconsole'], cwd=os.path.dirname(DOSBOX), timeout=900, env=env)
names = [ln.split()[2] for ln in open(script) if len(ln.split()) >= 3 and ln.split()[1] == 'shot']
imgs = []
for n in names:
    fn = os.path.join(ROOT, n.upper() + '.BMP')
    if os.path.exists(fn):
        imgs.append(Image.open(fn).convert('RGB'))
        if os.environ.get('TTKEEP'):
            Image.open(fn).convert('RGB').save(os.path.join(ROOT, 'tools', 'shot_%s.png' % n))
        os.remove(fn)
cols = 3
W = Image.new('RGB', (cols * 322, max(1, (len(imgs) + cols - 1) // cols) * 202), (60, 60, 60))
for i, im in enumerate(imgs):
    W.paste(im, ((i % cols) * 322, (i // cols) * 202))
W = W.resize((W.width * 2, W.height * 2), Image.NEAREST)
W.save(out)
print('%d shots' % len(imgs))
log = os.path.join(ROOT, 'TTLOG.TXT')
if os.path.exists(log):
    print(open(log).read().strip())
