# CTETRIS 코드 세그먼트 흐름 따라가기
import struct, sys
from capstone import *
from capstone.x86 import *

E = open('CT_UNP.EXE', 'rb').read()
H = struct.unpack('<14H', E[:28])
IMG = E[H[4] * 16:]
CB = H[11] * 16                 # 코드 세그먼트 시작(이미지 오프셋)
CODE = IMG[CB:]
CEND = len(CODE)
ENTRY = H[10]
DB = 0x0D * 16                  # 자료 세그먼트(이미지 오프셋)
# 15DA 의 간접 분기: 자판 처리표 DS:5C8D (키 23 개)
JT = 0x5C8D
JUMPTAB = {0x15DA: [struct.unpack('<H', IMG[DB + JT + 2 * k:DB + JT + 2 * k + 2])[0] for k in range(23)]}

md = Cs(CS_ARCH_X86, CS_MODE_16); md.detail = True
code = {}; funcs = set(); labels = set(); indirect = []
EXTRA = []
try:
    for ln in open('tools/roots.txt'):
        ln = ln.split('#')[0].strip()
        if ln:
            EXTRA.append(int(ln.split()[0], 16))
except FileNotFoundError:
    pass


def dis(a):
    return next(md.disasm(bytes(CODE[a:a + 16]), a), None)


def run(roots):
    work = list(roots)
    while work:
        a = work.pop()
        while 0 <= a < CEND and a not in code:
            ins = dis(a)
            if ins is None:
                print('bad at %04x' % a, file=sys.stderr); break
            code[a] = ins
            g = ins.groups; op = ins.operands; m = ins.mnemonic
            if m == 'call' and op[0].type == X86_OP_IMM:
                t = op[0].imm & 0xffff; funcs.add(t); work.append(t)
            elif m == 'call':
                indirect.append(a)
            elif (X86_GRP_JUMP in g or m.startswith('loop') or m == 'jcxz') and op[0].type == X86_OP_IMM:
                t = op[0].imm & 0xffff; labels.add(t); work.append(t)
                if m == 'jmp': break
            elif m == 'jmp' and a in JUMPTAB:
                for t in JUMPTAB[a]:
                    labels.add(t); work.append(t)
                break
            elif m in ('jmp', 'ljmp'):
                indirect.append(a); break
            elif m in ('ret', 'retf', 'iret'):
                break
            elif m == 'lcall':
                indirect.append(a)
            a += ins.size


roots = [ENTRY] + EXTRA
funcs |= set(roots)
run(roots)

if __name__ == '__main__':
    cov = set()
    for a, i in code.items(): cov.update(range(a, a + i.size))
    gaps = []; a = 0
    while a < CEND:
        if a not in cov:
            s = a
            while a < CEND and a not in cov: a += 1
            gaps.append((s, a))
        else: a += 1
    print('code size %04x  funcs %d  code bytes %d' % (CEND, len(funcs), len(cov)))
    print('funcs:', ' '.join('%04x' % f for f in sorted(funcs)))
    for a in sorted(set(indirect)):
        print('indirect %04x: %s %s' % (a, code[a].mnemonic, code[a].op_str))
    for s, e in gaps:
        if e - s > 2:
            print('gap %04x-%04x (%d) %s' % (s, e, e - s, bytes(CODE[s:min(e, s + 24)]).hex()))
