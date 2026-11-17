import sys
from PIL import Image, ImageDraw, ImageFont
src, dst = sys.argv[1], sys.argv[2]
im = Image.open(src).convert('RGBA')
W, H = im.size
ppf = H / 64.0
def px(x, y):
    return (W / 2 + (x - 21.3) * ppf, H / 2 + (y - 28.9) * ppf)
he_font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', int(W * 0.0125))
en_font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', int(W * 0.0085))
labels = [
    (14.3, 13.4, 'חדר אוכל', 'DINING RM'),
    (37.6, 12.6, 'חדר עבודה', 'STUDY'),
    (13.7, 19.6, 'מטבח', 'KITCHEN'),
    (2.5, 22.0, 'מזווה', 'W.I.P.'),
    (13.8, 31.0, 'פינת אוכל', 'DINETTE'),
    (31.0, 20.6, 'מבואה', 'FOYER'),
    (38.3, 25.9, 'מרפסת מקורה', 'COVERED PORCH'),
    (33.3, 31.0, 'חדר כניסה', 'MUD RM'),
    (27.8, 30.75, 'שירותים', 'POWDER'),
    (15.6, 48.5, 'חדר משחקים', 'PLAY RM'),
    (28.3, 49.5, 'סלון', 'LIVING RM'),
    (29.2, 53.6, 'מטבחון', 'KITCHENETTE'),
    (30.1, 2.6, 'מדרגות למטה', 'DN'),
    (31.9, 37.6, 'מדרגות למטה', 'DN'),
]
ov = Image.new('RGBA', im.size, (0, 0, 0, 0))
d = ImageDraw.Draw(ov)
for x, y, he, en in labels:
    cx, cy = px(x, y)
    he_v = he  # raqm handles RTL shaping
    b1 = d.textbbox((0, 0), he_v, font=he_font)
    b2 = d.textbbox((0, 0), en, font=en_font)
    w = max(b1[2] - b1[0], b2[2] - b2[0]) + int(W * 0.012)
    h = (b1[3] - b1[1]) + (b2[3] - b2[1]) + int(W * 0.011)
    d.rounded_rectangle((cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2), radius=int(W * 0.006), fill=(255, 255, 255, 215),
                        outline=(40, 40, 45, 160), width=2)
    d.text((cx - (b1[2] - b1[0]) / 2 - b1[0], cy - h / 2 + int(W * 0.004) - b1[1]), he_v, font=he_font, fill=(25, 25, 30, 255))
    d.text((cx - (b2[2] - b2[0]) / 2 - b2[0], cy + h / 2 - (b2[3] - b2[1]) - int(W * 0.004) - b2[1]), en, font=en_font,
           fill=(90, 90, 95, 255))
out = Image.alpha_composite(im, ov).convert('RGB')
out.save(dst, quality=92)
print('saved', dst, out.size)
