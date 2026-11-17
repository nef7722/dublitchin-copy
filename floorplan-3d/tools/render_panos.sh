#!/bin/bash
cd "$(dirname "$0")"
./bvenv/bin/python fp/main.py --eye entry,foyer,dining,kitchen,kitchen_w,dinette,living,play,study,hall,powder,mud,landing,bsmt,dining_w,porch --res 3200 --samples 22 --exp 0.4 --outdir out/pano 2>&1 | grep --line-buffered -E "rendered|rror|Trace"
echo ALLDONE
