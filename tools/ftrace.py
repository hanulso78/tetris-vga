# 함수에 들어갈 때마다 레지스터를 원본(에뮬레이터)과 옮긴 C(hostft.exe)로 적어 첫 차이를 찾는다
#   python tools/ftrace.py 개수 "키 키 ..."
import sys, os, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import emu, scan, difftest
from unicorn import *
from unicorn.x86_const import *

HERE = os.path.dirname(os.path.abspath(__file__))
N = int(sys.argv[1])
JOY = sys.argv[3] if len(sys.argv) > 3 else 'n'
keys = difftest.parse(sys.argv[2]) if len(sys.argv) > 2 else []

# 옮긴 C 쪽
fh = os.path.join(HERE, '_ft_host.txt')
kf = os.path.join(HERE, '_ft_keys.txt')
open(kf, 'w').write(''.join('%d %x\n' % k for k in keys))
env = dict(os.environ, TTFTRACE=fh, TTFTRACEMAX=str(N))
subprocess.run([os.path.join(emu.ROOT, 'hostft.exe'), os.path.join(HERE, '_ft_tr.txt'), JOY, kf, emu.ROOT],
               env=env, timeout=1200)

# 원본 쪽
m = emu.Machine(keys=list(keys), mode=JOY)
CB = emu.LOADSEG * 16 + 0x8150
F = set(CB + f for f in scan.funcs)
out = []


def hk(mu, a, s, u):
    if a in F:
        r = mu.reg_read
        out.append('%04X %s' % (a - CB, ' '.join('%04X' % r(x) for x in (
            UC_X86_REG_AX, UC_X86_REG_BX, UC_X86_REG_CX, UC_X86_REG_DX, UC_X86_REG_SI, UC_X86_REG_DI,
            UC_X86_REG_BP, UC_X86_REG_SP, UC_X86_REG_DS, UC_X86_REG_ES))))
        if len(out) >= N:
            m.stop()


m.mu.hook_add(UC_HOOK_CODE, hk, None, CB, CB + scan.CEND)
m.run()
a = out
b = open(fh).read().splitlines()
for k in range(min(len(a), len(b))):
    if a[k] != b[k]:
        print('차이: %d 번째 함수 들어갈 때' % k)
        for j in range(max(0, k - 4), k + 1):
            print(' emu :', a[j])
            print(' host:', b[j])
        sys.exit(1)
print('같다: 함수 %d 번 (emu %d, host %d)' % (min(len(a), len(b)), len(a), len(b)))
