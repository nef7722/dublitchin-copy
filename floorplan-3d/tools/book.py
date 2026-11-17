# PDF photo book: rectilinear views cut from each 360° panorama + overview pages (works where interactive files can't).
import numpy as np, math
from PIL import Image, ImageDraw, ImageFont
P = 'out/pano/'
ST = [  # id, Hebrew, English, start bearing
    ('porch', 'מרפסת מקורה', 'Covered porch', 290), ('entry', 'כניסה', 'Entry', 285), ('mud', 'חדר כניסה (Mud)', 'Mud room', 180),
    ('foyer', 'מבואה', 'Foyer', 300), ('study', 'חדר עבודה', 'Study', 35), ('bsmt', 'מדרגות למרתף', 'Basement stair', 0),
    ('dining', 'חדר אוכל', 'Dining room', 260), ('dining_w', 'חדר אוכל – צד מערב', 'Dining room, west', 75),
    ('kitchen_w', 'מטבח – צד הכיריים', 'Kitchen, range wall', 120), ('kitchen', 'מטבח', 'Kitchen', 280),
    ('dinette', 'פינת אוכל', 'Dinette', 265), ('play', 'חדר משחקים', 'Play room', 170), ('living', 'סלון', 'Living room', 75),
    ('hall', 'מסדרון', 'Hallway', 180), ('landing', 'מדרגות – פודסט', 'Stair landing', 270), ('powder', 'שירותי אורחים', 'Powder room', 90)]
PITCH = {'bsmt': -25, 'landing': -12}

def view(eq, bearing, pitch, hfov, W, H):
    eh, ew = eq.shape[:2]
    b, p = math.radians(bearing), math.radians(pitch)
    f = np.array([math.sin(b) * math.cos(p), math.cos(b) * math.cos(p), math.sin(p)])
    r = np.array([math.cos(b), -math.sin(b), 0.0])
    u = np.cross(r, f)
    t = math.tan(math.radians(hfov) / 2)
    xs = (np.arange(W) + 0.5) / W * 2 - 1
    ys = 1 - (np.arange(H) + 0.5) / H * 2
    X, Y = np.meshgrid(xs * t, ys * t * H / W)
    d = f[None, None, :] + X[..., None] * r + Y[..., None] * u
    d /= np.linalg.norm(d, axis=-1, keepdims=True)
    bear = np.arctan2(d[..., 0], d[..., 1]); el = np.arcsin(np.clip(d[..., 2], -1, 1))
    uu = ((0.5 + bear / (2 * np.pi)) % 1.0) * ew - 0.5
    vv = (0.5 - el / np.pi) * eh - 0.5
    x0 = np.floor(uu).astype(int); y0 = np.clip(np.floor(vv).astype(int), 0, eh - 2)
    fx = (uu - x0)[..., None]; fy = np.clip(vv - y0, 0, 1)[..., None]
    x0 %= ew; x1 = (x0 + 1) % ew
    a = eq[y0, x0] * (1 - fx) + eq[y0, x1] * fx
    c = eq[y0 + 1, x0] * (1 - fx) + eq[y0 + 1, x1] * fx
    return Image.fromarray(np.clip(a * (1 - fy) + c * fy, 0, 255).astype(np.uint8))

PW, PH = 2480, 1754   # A4 landscape at 300 dpi
BG = (24, 26, 27); INK = (244, 241, 234); SOFT = (190, 186, 178); BRASS = (217, 169, 91)
F = '/usr/share/fonts/truetype/dejavu/'
fT = ImageFont.truetype(F + 'DejaVuSans-Bold.ttf', 78); fS = ImageFont.truetype(F + 'DejaVuSans.ttf', 38)
fK = ImageFont.truetype(F + 'DejaVuSans-Bold.ttf', 34); fC = ImageFont.truetype(F + 'DejaVuSans.ttf', 30)

def header(d, he, en, n):
    d.text((PW - 110, 90), he, font=fT, fill=INK, anchor='ra', direction='rtl')
    d.text((PW - 110, 190), en.upper(), font=fS, fill=SOFT, anchor='ra')
    d.text((110, 100), 'סיור בגובה העיניים · קומה ראשונה', font=fK, fill=BRASS, anchor='la', direction='rtl')
    if n: d.text((110, 160), n, font=fC, fill=SOFT, anchor='la')

pages = []
# cover
pg = Image.new('RGB', (PW, PH), BG); d = ImageDraw.Draw(pg)
header(d, 'הבית – סיור בתמונות', 'First floor photo tour', '')
im = Image.open('/home/user/dublitchin-copy/floorplan-3d/renders/final_main.jpg'); im.thumbnail((PW - 220, PH - 420))
pg.paste(im, ((PW - im.width) // 2, 300))
d.text((PW - 110, PH - 80), 'כל התמונות מתוך המודל התלת־ממדי שנבנה לפי התוכנית · מידות בפיט', font=fC, fill=SOFT, anchor='rd', direction='rtl')
pages.append(pg)
# plan + second overview
pg = Image.new('RGB', (PW, PH), BG); d = ImageDraw.Draw(pg)
header(d, 'תוכנית ומבט מהכניסה', 'Plan and entrance-side view', '')
mp = Image.open('/home/user/dublitchin-copy/floorplan-3d/renders/final_top_labeled.jpg'); mp.thumbnail((1050, PH - 380))
pg.paste(mp, (110, 290))
ne = Image.open('/home/user/dublitchin-copy/floorplan-3d/renders/final_ne.jpg'); ne.thumbnail((PW - 110 - 1050 - 220, PH - 380))
pg.paste(ne, (PW - 110 - ne.width, 290 + (PH - 380 - ne.height) // 2))
pages.append(pg)
# rooms
for i, (sid, he, en, b) in enumerate(ST):
    eq = np.asarray(Image.open(P + sid + '.png').convert('RGB')).astype(np.float32)
    p = PITCH.get(sid, -3)
    big = view(eq, b, p, 95, 2260, 980)
    s1 = view(eq, b + 120, p, 95, 1110, 600)
    s2 = view(eq, b - 120, p, 95, 1110, 600)
    pg = Image.new('RGB', (PW, PH), BG); d = ImageDraw.Draw(pg)
    header(d, he, en, '%d / %d' % (i + 1, len(ST)))
    pg.paste(big, (110, 270))
    pg.paste(s2, (110, 270 + 980 + 40))
    pg.paste(s1, (110 + 1110 + 40, 270 + 980 + 40))
    pages.append(pg)
    print(sid, flush=True)
out = '/home/user/dublitchin-copy/floorplan-3d/סיור-בתמונות.pdf'
pages[0].save(out, save_all=True, append_images=pages[1:], resolution=300, quality=88)
import os; print(out, os.path.getsize(out) / 1e6, 'MB')
