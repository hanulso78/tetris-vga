#!/bin/sh
# 회귀 시험: test/k_*.txt 를 원본(에뮬레이터)과 옮긴 C 로 돌려 대조한다.
#   원판 빌드(hosttest.exe) 는 자판/조이스틱 둘 다, 개선판 빌드(hostvga.exe) 는 자판으로.
cd "$(dirname "$0")/.."
export PYTHONIOENCODING=utf-8
P=/c/python-3.12.10-embed-amd64/python.exe
fail=0
for f in test/k_*.txt; do
    for run in "hosttest.exe n" "hosttest.exe y" "hostvga.exe n"; do
        set -- $run
        [ -f "$1" ] || continue
        r=$(TTHOST=$1 $P tools/difftest.py $2 "$(cat $f)" x | head -1)
        printf '%-18s %-16s %s\n' "$(basename $f)" "$1 $2" "$r"
        case "$r" in 같다*) ;; *) fail=1 ;; esac
    done
done
exit $fail
