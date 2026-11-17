#!/bin/bash
cd "$(dirname "$0")"
PID=$(pgrep -f "fp/main.py --eye" | head -1)
[ -n "$PID" ] && kill -STOP $PID
./bvenv/bin/python fp/export_walk.py --lm 4096 --samples 40 --out out/walkfinal 2>&1 | grep -E "built|removed|area|baked|exported|rror|Trace"
[ -n "$PID" ] && kill -CONT $PID
echo BAKEDONE
