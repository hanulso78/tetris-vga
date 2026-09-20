import sys, struct
from capstone import *
d=open('CT_UNP.EXE','rb').read(); h=struct.unpack('<14H',d[:28]); img=d[h[4]*16:]
CB=h[11]*16
off=int(sys.argv[1],0); n=int(sys.argv[2],0) if len(sys.argv)>2 else 0x100
md=Cs(CS_ARCH_X86, CS_MODE_16); md.detail=False
for i in md.disasm(bytes(img[CB+off:CB+off+n]), off):
    print('%04x  %-16s %s %s'%(i.address, i.bytes.hex(), i.mnemonic, i.op_str))
