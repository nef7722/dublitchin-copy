import numpy as np, math
from PIL import Image
a = np.array(Image.open('tour/walk/walkmap.png')).astype(float)
H = -10 + a[..., 0] / 255 * 11; B = a[..., 1] > 127
x0, y0, res = -10, -8, 0.1
def idx(x, y):
    i, j = int((x - x0) // res), int((y - y0) // res)
    return (j, i) if 0 <= i < H.shape[1] and 0 <= j < H.shape[0] else None
RING = [(math.cos(k * math.pi / 6) * .65, math.sin(k * math.pi / 6) * .65) for k in range(12)]
def free(x, y, h):
    k = idx(x, y)
    if k is None or B[k] or abs(H[k] - h) > 0.95: return False
    return all(idx(x + dx, y + dy) is not None and not B[idx(x + dx, y + dy)] for dx, dy in RING)
def walk(path, name):
    x, y = path[0]; h = H[idx(x, y)]
    if not free(x, y, h): print(name, 'START BLOCKED', x, y); 
    for (tx, ty) in path[1:]:
        for _ in range(4000):
            d = math.hypot(tx - x, ty - y)
            if d < 0.1: break
            dx, dy = (tx - x) / d * 0.08, (ty - y) / d * 0.08
            px, py = -dy, dx
            if free(x + dx, y + dy, h): x += dx; y += dy
            elif free(x + dx + px * .6, y + dy + py * .6, h): x += dx + px * .6; y += dy + py * .6
            elif free(x + dx - px * .6, y + dy - py * .6, h): x += dx - px * .6; y += dy - py * .6
            elif free(x + dx, y, h): x += dx
            elif free(x, y + dy, h): y += dy
            else: break
            h = H[idx(x, y)]
        ok = math.hypot(tx - x, ty - y) < 0.2
        print('%-10s -> (%.1f,%.1f) %s at (%.2f,%.2f) h=%.2f' % (name, tx, ty, 'OK ' if ok else 'STUCK', x, y, h))
        if not ok: return
walk([(33.3, 23.6), (37.0, 24.6), (38.7, 26.4)], 'porch')
walk([(38.7, 26.4), (41.9, 26.5), (41.9, 24.0), (41.9, 17.6), (46, 17.6)], 'porchstair')
walk([(27.4, 20.6), (29.0, 19.7), (30.08, 19.4), (30.08, 17.0), (30.08, 3.0)], 'basement')
walk([(23.65, 31.2), (23.7, 41.0), (29.5, 41.0), (32.0, 39.3), (32, 37.6), (27.2, 37.6)], 'ustair')
walk([(23.65, 31.2), (23.7, 44.5), (27.6, 48.4)], 'living')
walk([(27.6, 48.4), (22.0, 50.8), (16.0, 46.6)], 'play')
walk([(16.0, 46.6), (12.25, 40.0), (12.25, 36.0), (13.2, 30.6)], 'dinette')
walk([(13.2, 30.6), (8.8, 23.8), (8.8, 19.0), (8.85, 15.0), (3.2, 13.4)], 'kitch-din')
walk([(27.4, 20.6), (34.0, 17.0), (34.0, 14.0), (37.4, 11.8)], 'study')
walk([(33.3, 23.6), (34.1, 26.0), (34.1, 28.0), (33.2, 31.2)], 'mud')
walk([(23.65, 31.2), (26.3, 34.1), (26.5, 32.0), (27.5, 30.8)], 'powder')
walk([(3.2, 26.8), (2.9, 25.0), (2.6, 21.0)], 'pantry')
print('---')
walk([(33.0, 22.4), (36.0, 24.0), (37.5, 24.6), (38.7, 26.4)], 'porch2')
walk([(33.0, 22.4), (32.6, 24.0), (33.0, 25.8), (33.4, 27.6), (33.2, 31.2)], 'mud2')
walk([(23.65, 31.2), (26.3, 34.1), (26.4, 32.6), (26.6, 31.0), (27.0, 30.6)], 'toilet')
walk([(13.2, 30.6), (21.0, 30.0), (23.65, 31.2)], 'din-hall')
walk([(23.65, 31.2), (23.6, 26.0), (27.4, 20.6), (21.6, 12.3)], 'hall-din')
walk([(16.0, 46.6), (18.0, 41.5), (18.0, 39.0)], 'closet')
print('---2')
walk([(33.0, 22.4), (32.6, 24.0), (33.0, 25.8), (34.0, 26.2), (34.0, 27.6), (33.2, 31.2)], 'mud3')
