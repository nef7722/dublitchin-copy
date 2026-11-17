#!/bin/bash
# copy final walk assets + converted panoramas into the tour folder
cd "$(dirname "$0")"
set -e
python3 lmconv.py out/walkfinal/lightmap.npy tour/walk/lightmap.jpg 4 2
cp out/walkfinal/house.glb tour/walk/house.glb
python3 mapconv.py out/walkfinal tour/walk/walkmap.png
python3 conv.py
ls -la tour/walk tour/pano | head -40
du -sh tour
