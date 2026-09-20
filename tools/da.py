import sys, struct
from capstone import *
f=sys.argv[1]; d=open(f,'rb').read()
if f.lower().endswith('.exe'):
    (sig,lp,pages,nrel,hdr,minal,maxal,ss,sp,csum,ip,cs,relof,ov)=struct.unpack('<2sHHHHHHHHHHHHH',d[:28])
    img=d[hdr*16:(pages-1)*512+lp]
    base=0
else:
    img=d; base=0x100
off=int(sys.argv[2],0); n=int(sys.argv[3],0) if len(sys.argv)>3 else 0x100
md=Cs(CS_ARCH_X86, CS_MODE_16); md.detail=False
for i in md.disasm(img[off:off+n], off+base):
    print('%05x  %-20s %s %s'%(i.address, i.bytes.hex(), i.mnemonic, i.op_str))
