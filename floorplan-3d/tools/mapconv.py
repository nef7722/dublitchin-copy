import sys, json, numpy as np
from PIL import Image
d = sys.argv[1]
g = json.load(open(d + '/grid.json'))
h = np.load(d + '/height.npy'); b = np.load(d + '/blocked.npy')
r = np.clip((h - g['zmin']) / (g['zmax'] - g['zmin']) * 255 + 0.5, 0, 255).astype(np.uint8)
img = np.stack([r, np.where(b, 255, 0).astype(np.uint8), np.zeros_like(r)], -1)
Image.fromarray(img).save(sys.argv[2])
print(img.shape)
