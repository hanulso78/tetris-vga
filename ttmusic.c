/* ============================================================================
 *  ttmusic.c  -  개선판(TETVGA): 배경음악 (애드립 OPL2, VGM)
 * ----------------------------------------------------------------------------
 *  아타리판 테트리스(1988) 음악을 OPL2 로 옮긴 VGM 을 SOUND.DAT 에서 읽어 연주한다
 *  (sokoban/sopwith 의 것을 옮겨 왔다).
 *      TTTITLE   제목, 차례표, 판 고르기 - 코로베이니키 (되풀이)
 *      TTPLAY    놀이 중 (되풀이)
 *      TTOVER    끝났을 때 (한 번)
 *  어느 곡을 틀지는 ttvga.c 가 장면을 보고 정한다 (vga_music).  게임에서 S 로 소리를
 *  끄면(원판 [5CBC]) 음악도 멈춘다.  애드립이나 SOUND.DAT 이 없으면 조용히 넘어간다.
 *  원판 효과음(PC 스피커)은 그대로 둔다 - 애드립과 서로 다른 장치라 같이 난다.
 * ========================================================================== */
#include <stdlib.h>
#include <string.h>
#include <fcntl.h>
#include <unistd.h>
#include <time.h>
#include <pc.h>
#include "cpu.h"
#include "ttvga.h"

#define OPL_ADDR    0x388
#define OPL_DATA    0x389
#define SOUND_DAT   "sound.dat"
#define SOUND_MAGIC "SWSND10"      /* sopwith 과 같은 틀 */

static const char *const songname[MUS_COUNT] = { NULL, "TTTITLE", "TTPLAY", "TTPLAY2",
                                                 "TTPLAY3", "TTOVER" };

typedef struct {
    unsigned char *buf;
    long len, pos, loop;
    uclock_t next;
    int loaded;                     /* 0 아직, 1 읽음, -1 없음 */
} vgm_stream;

static int found = -1;              /* 애드립이 있나 (-1 아직 모른다) */
static vgm_stream track[MUS_COUNT];
static int song = MUS_NONE;         /* 지금 울리는 곡 */
static int wanted = MUS_NONE;       /* 마지막으로 청한 곡 */
static int muted;                   /* 소리를 꺼서 멈춤 */

static void wait(int n)
{
    while (n-- > 0)
        (void)inportb(OPL_ADDR);
}

long music_writes;                  /* 시험용: 칩에 쓴 횟수 */

static void wr(int reg, int val)
{
    ++music_writes;
    outportb(OPL_ADDR, (unsigned char)reg);
    wait(6);
    outportb(OPL_DATA, (unsigned char)val);
    wait(35);
}

static int detect(void)
{
    unsigned char s1, s2;

    wr(4, 0x60);
    wr(4, 0x80);
    s1 = inportb(OPL_ADDR);
    wr(2, 0xFF);
    wr(4, 0x21);
    wait(400);
    s2 = inportb(OPL_ADDR);
    wr(4, 0x60);
    wr(4, 0x80);
    return (s1 & 0xE0) == 0x00 && (s2 & 0xE0) == 0xC0;
}

static void silence(void)
{
    int i;

    for (i = 0xB0; i <= 0xB8; i++)
        wr(i, 0x00);
    wr(0xBD, 0x00);
    for (i = 0x40; i <= 0x55; i++)
        wr(i, 0x3F);
}

static void reset(void)
{
    int i;

    silence();
    for (i = 0x01; i <= 0xF5; i++)
        wr(i, 0x00);
    wr(0x01, 0x20);
}

static unsigned long le32(const unsigned char *p)
{
    return p[0] | (unsigned long)p[1] << 8 | (unsigned long)p[2] << 16 | (unsigned long)p[3] << 24;
}

static uclock_t samples(long n)
{
    return (uclock_t)((double)n * UCLOCKS_PER_SEC / 44100.0);
}

/* SOUND.DAT 목차에서 이름을 찾아 읽는다 */
static int load(vgm_stream *s, const char *name)
{
    unsigned char head[10], entry[20];
    unsigned long off = 0, size = 0;
    int fd, count, i, ok = 0;

    s->loaded = -1;
    if ((fd = open(SOUND_DAT, O_RDONLY | O_BINARY)) == -1)
        return 0;
    if (read(fd, head, 10) != 10 || memcmp(head, SOUND_MAGIC, 8) != 0) {
        close(fd);
        return 0;
    }
    count = head[8] | head[9] << 8;
    for (i = 0; i < count && !ok; i++) {
        if (read(fd, entry, 20) != 20)
            break;
        if (strncmp((char *)entry, name, 12) == 0) {
            off = le32(entry + 12);
            size = le32(entry + 16);
            ok = 1;
        }
    }
    if (!ok || size < 0x40 || size > 1024L * 1024L
        || lseek(fd, off, SEEK_SET) != (off_t)off || (s->buf = malloc(size)) == NULL) {
        close(fd);
        return 0;
    }
    s->len = read(fd, s->buf, size);
    close(fd);
    if (s->len < 0x40 || memcmp(s->buf, "Vgm ", 4) != 0) {
        free(s->buf);
        s->buf = NULL;
        return 0;
    }
    s->loaded = 1;
    return 1;
}

static void rewind_(vgm_stream *s)
{
    unsigned long loop = le32(s->buf + 0x1C), data = le32(s->buf + 0x34);

    s->loop = loop ? (long)(0x1C + loop) : 0;
    if (s->loop >= s->len)
        s->loop = 0;
    s->pos = data ? (long)(0x34 + data) : 0x40;
    s->next = uclock();
}

/* 시각이 된 명령을 칩에 보낸다.  곡이 끝나면 0 */
static int step(vgm_stream *s)
{
    uclock_t now = uclock();
    const unsigned char *b = s->buf;
    unsigned char c;

    if (now > s->next + UCLOCKS_PER_SEC / 4)    /* 오래 못 불렸으면 따라잡지 않는다 */
        s->next = now;
    while (now >= s->next) {
        if (s->pos >= s->len) {
            if (!s->loop)
                return 0;
            s->pos = s->loop;
        }
        c = b[s->pos];
        if (c == 0x5A) {
            wr(b[s->pos + 1], b[s->pos + 2]);
            s->pos += 3;
        } else if (c == 0x61) {
            s->next += samples(b[s->pos + 1] | b[s->pos + 2] << 8);
            s->pos += 3;
        } else if (c == 0x62) {
            s->next += samples(735);
            s->pos++;
        } else if (c == 0x63) {
            s->next += samples(882);
            s->pos++;
        } else if (c >= 0x70 && c <= 0x7F) {
            s->next += samples((c & 15) + 1);
            s->pos++;
        } else if (c == 0x66) {
            if (!s->loop)
                return 0;
            s->pos = s->loop;
        } else if (c >= 0x51 && c <= 0x5F) {
            s->pos += 3;
        } else {
            s->pos++;
        }
        now = uclock();
    }
    return 1;
}

static void play(int which)
{
    vgm_stream *s;

    if (found < 0 && (found = detect()) != 0)
        reset();
    if (!found)
        return;
    if (song != MUS_NONE)
        silence();
    song = MUS_NONE;
    if (which <= MUS_NONE || which >= MUS_COUNT)
        return;
    s = &track[which];
    if (!s->loaded)
        load(s, songname[which]);
    if (s->loaded < 0)
        return;
    rewind_(s);
    wr(0x01, 0x20);
    song = which;
    muted = 0;
}

/* 곡 청하기 - 같은 곡을 거듭 청하면 그대로 둔다 (끝난 짧은 곡도 다시 틀지 않는다) */
void music_want(int which)
{
    if (which == wanted)
        return;
    wanted = which;
    play(which);
}

/* 기다리는 곳마다 */
long music_us, music_polls;         /* 시험용: 여기서 보낸 시간과 횟수 */

void music_poll(void)
{
    uclock_t t0 = uclock();

    ++music_polls;
    if (found != 1 || song == MUS_NONE)
        return;
    if (music_muted()) {
        if (!muted) {
            muted = 1;
            silence();
        }
        return;
    }
    if (muted) {                    /* 소리를 다시 켜면 그 곡 처음부터 */
        play(song);
        return;
    }
    if (!step(&track[song])) {
        silence();
        song = MUS_NONE;
    }
    music_us += (long)((uclock() - t0) * 1000000 / UCLOCKS_PER_SEC);
}

void music_off(void)
{
    if (found == 1)
        reset();
    song = wanted = MUS_NONE;
}


int music_found(void)
{
    return found == 1;
}

/* 이 곡이 끝까지 다 울렸나 (끝 곡을 한 번만 틀려고) */
int music_done(int which)
{
    return wanted == which && song == MUS_NONE;
}
