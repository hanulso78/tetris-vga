/* OPL2 VGM 을 WAV 로 뽑는다 (귀로 확인하려고).  Nuked OPL3 코어를 쓴다.
 *   gcc -O2 -o vgmwav.exe tools/vgmwav.c <adplug>/src/nukedopl.c -I<adplug>/src -lm
 *   vgmwav 노래.vgm 나올파일.wav [초]
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include "nukedopl.h"

#define SR 44100

static unsigned long le32(const unsigned char *p)
{
    return p[0] | ((unsigned long)p[1] << 8) | ((unsigned long)p[2] << 16) | ((unsigned long)p[3] << 24);
}

int main(int argc, char **argv)
{
    FILE *f;
    unsigned char *b;
    long n, pos, len, loop, want;
    opl3_chip chip;
    short *buf;
    long nbuf = 0, cap;
    double secs = argc > 3 ? atof(argv[3]) : 30.0;
    unsigned char hdr[44];
    unsigned long v;

    if (argc < 3) {
        fprintf(stderr, "vgmwav in.vgm out.wav [seconds]\n");
        return 1;
    }
    f = fopen(argv[1], "rb");
    if (!f)
        return 1;
    fseek(f, 0, SEEK_END);
    len = ftell(f);
    fseek(f, 0, SEEK_SET);
    b = malloc(len);
    if (fread(b, 1, len, f) != (size_t)len)
        return 1;
    fclose(f);

    v = le32(b + 0x34);
    pos = v ? (long)(0x34 + v) : 0x40;
    v = le32(b + 0x1C);
    loop = v ? (long)(0x1C + v) : 0;
    cap = (long)(secs * SR) + SR;
    buf = malloc(sizeof(short) * cap * 2);
    OPL3_Reset(&chip, SR);

    while (pos < len && nbuf < cap) {
        unsigned char c = b[pos];
        if (c == 0x5A || c == 0x5E) {
            OPL3_WriteReg(&chip, b[pos + 1], b[pos + 2]);
            pos += 3;
        } else if (c == 0x5F) {
            OPL3_WriteReg(&chip, 0x100 | b[pos + 1], b[pos + 2]);
            pos += 3;
        } else if (c == 0x61 || c == 0x62 || c == 0x63 || (c >= 0x70 && c <= 0x7F)) {
            if (c == 0x61) {
                want = b[pos + 1] | (b[pos + 2] << 8);
                pos += 3;
            } else if (c == 0x62) {
                want = 735;
                pos += 1;
            } else if (c == 0x63) {
                want = 882;
                pos += 1;
            } else {
                want = (c & 15) + 1;
                pos += 1;
            }
            if (nbuf + want > cap)
                want = cap - nbuf;
            if (want > 0) {
                OPL3_GenerateStream(&chip, buf + nbuf * 2, (unsigned)want);
                nbuf += want;
            }
        } else if (c == 0x66) {
            if (!loop)
                break;
            pos = loop;
        } else if (c >= 0x51 && c <= 0x5F) {
            pos += 3;
        } else if (c == 0x50 || c == 0x4F) {
            pos += 2;
        } else {
            pos += 1;
        }
    }

    memcpy(hdr, "RIFF", 4);
    v = 36 + nbuf * 4;
    memcpy(hdr + 4, &v, 4);
    memcpy(hdr + 8, "WAVEfmt ", 8);
    v = 16;
    memcpy(hdr + 16, &v, 4);
    hdr[20] = 1;
    hdr[21] = 0;
    hdr[22] = 2;
    hdr[23] = 0;
    v = SR;
    memcpy(hdr + 24, &v, 4);
    v = SR * 4;
    memcpy(hdr + 28, &v, 4);
    hdr[32] = 4;
    hdr[33] = 0;
    hdr[34] = 16;
    hdr[35] = 0;
    memcpy(hdr + 36, "data", 4);
    v = nbuf * 4;
    memcpy(hdr + 40, &v, 4);
    f = fopen(argv[2], "wb");
    fwrite(hdr, 1, 44, f);
    fwrite(buf, 4, nbuf, f);
    fclose(f);
    {   /* 소리가 나긴 하는지 (평균 크기) */
        double s = 0;
        long i;
        for (i = 0; i < nbuf * 2; i++)
            s += (double)buf[i] * buf[i];
        printf("%s: %.1f초, RMS %.0f\n", argv[2], nbuf / (double)SR, nbuf ? sqrt(s / (nbuf * 2)) : 0);
    }
    return 0;
}
