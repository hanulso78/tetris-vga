# 에뮬레이터로 돌리며 화면을 png 로 (키: difftest 와 같은 형식)
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import emu
from difftest import parse
ks = parse(sys.argv[1]) if len(sys.argv) > 1 else []
out = sys.argv[2] if len(sys.argv) > 2 else 'tools/_s'
n = [0]
m = emu.Machine(keys=ks)
def on_block(mm):
    mm.screen_png('%s%02d.png' % (out, n[0])); n[0] += 1
m.on_block = on_block
print(m.run())
m.screen_png('%s%02d.png' % (out, n[0]))
