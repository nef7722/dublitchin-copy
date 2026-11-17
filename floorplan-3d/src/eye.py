# Eye-level additions: ceilings, roof edge, porch roof, recessed lights, panorama stations.
import bpy, math
from mathutils import Vector
from lib import MB, W, MATS, principled
from arch import G, PORCH, BASE
from house import FOOT, R_IN, R_EX

CEIL = 9.0

# recessed ceiling lights (plan x, y, ceiling z)
LIGHTS = [
    # dining
    (5, 5), (11, 5), (17, 5), (23, 5), (5, 11.5), (11, 11.5), (17, 11.5), (23, 11.5),
    # study
    (35, 5), (40.5, 5), (35, 11.5), (40.5, 11.5),
    # kitchen
    (9, 19.2), (13.7, 19.2), (18.3, 19.4), (9, 23.6), (18.3, 23.8), (13.7, 25.0),
    # dinette
    (4.5, 28.5), (11, 28.5), (17, 28.5), (4.5, 34.5), (11, 34.5), (17, 34.5), (20.5, 31),
    # pantry, wash nook
    (2.5, 21.6), (2.5, 16.5),
    # foyer + hall
    (24.8, 18.5), (29.5, 21.0), (33.6, 18.5), (33.6, 24.2), (24.8, 24.2), (23.67, 29.5), (23.67, 34.0),
    (23.67, 38.8),
    # powder, coat closet, mud room
    (27.8, 34.1), (27.8, 30.75), (27.8, 27.9), (33.3, 29.4), (33.3, 33.3),
    # play room + closet
    (13.2, 43), (19.2, 43), (13.2, 50), (19.2, 50), (16.2, 55.2), (18.1, 38.4),
    # living room + kitchenette
    (25.5, 46), (32, 46), (25.5, 51.8), (32, 51.8), (26.2, 55.9), (32.2, 55.9),
    # stair wells
    (30.08, 9.5), (32.0, 39.3),
]
PORCH_LIGHTS = [(38.4, 21.5), (41.9, 26.5)]


def offset_poly(pts, d):
    """Outward miter offset of a simple polygon given in plan coords (y down)."""
    n = len(pts)
    area = sum(pts[i][0] * pts[(i + 1) % n][1] - pts[(i + 1) % n][0] * pts[i][1] for i in range(n))
    s = 1 if area > 0 else -1
    lines = []
    for i in range(n):
        a = Vector(pts[i]); b = Vector(pts[(i + 1) % n])
        t = (b - a).normalized()
        nrm = Vector((t.y, -t.x)) * s
        lines.append((a + nrm * d, t))
    out = []
    for i in range(n):
        p1, t1 = lines[i - 1]
        p2, t2 = lines[i]
        den = t1.x * t2.y - t1.y * t2.x
        if abs(den) < 1e-9:
            out.append((p2.x, p2.y))
            continue
        k = ((p2.x - p1.x) * t2.y - (p2.y - p1.y) * t2.x) / den
        q = p1 + t1 * k
        out.append((q.x, q.y))
    return out


def build_eye(coll):
    principled('ceiling', (0.88, 0.875, 0.85), rough=0.95, spec=0.2)
    principled('roof', (0.16, 0.16, 0.17), rough=0.9)
    m, nt, b = principled('downlight', (1, 1, 1), rough=0.4)
    b.inputs['Emission Color'].default_value = (1.0, 0.92, 0.8, 1)
    b.inputs['Emission Strength'].default_value = 12.0

    ce = MB('ceiling')
    ce.prism([(x, -y) for x, y in FOOT], CEIL, CEIL + 0.4, 'ceiling', mtop='roof')
    # roof edge / eave around the whole house (seen from the porch and through windows)
    eave = offset_poly(FOOT, 1.4)
    ce.prism([(x, -y) for x, y in eave], CEIL + 0.4, CEIL + 1.2, 'trim', mtop='roof')
    # covered porch: roof slab with ceiling, three posts
    ce.pbox(36.6, 15.9, 44.1, 28.55, CEIL, CEIL + 0.45, {'all': 'trim', 'z-': 'ceiling', 'z+': 'roof'})
    for (x, y, z0) in ((37.0, 28.05, PORCH), (43.3, 28.05, PORCH), (43.3, 16.35, PORCH - 8 * R_EX)):
        ce.pbox(x - 0.25, y - 0.25, x + 0.25, y + 0.25, z0, CEIL, 'trim')
        ce.pbox(x - 0.33, y - 0.33, x + 0.33, y + 0.33, z0, z0 + 0.5, 'trim')
        ce.pbox(x - 0.33, y - 0.33, x + 0.33, y + 0.33, CEIL - 0.35, CEIL, 'trim')
    ob = ce.finish(coll)
    MB.all.remove(ce)

    dl = MB('downlights')
    lights = [(x, y, CEIL) for x, y in LIGHTS] + [(x, y, CEIL) for x, y in PORCH_LIGHTS]
    for i, (x, y, z) in enumerate(lights):
        dl.cyl(x, -y, z - 0.03, z + 0.001, 0.28, 'nickel', n=24)
        dl.cyl(x, -y, z - 0.035, z - 0.03, 0.22, 'downlight', n=24)
        ld = bpy.data.lights.new('dl%d' % i, 'AREA')
        ld.shape = 'DISK'
        ld.size = 0.5
        ld.energy = 55.0
        ld.color = (1.0, 0.9, 0.78)
        lo = bpy.data.objects.new('dl%d' % i, ld)
        lo.location = W(x, y, z - 0.06)
        coll.objects.link(lo)
    o = dl.finish(coll)
    MB.all.remove(dl)
    o.visible_diffuse = False
    o.visible_shadow = False


# Panorama stations: id -> (plan x, plan y, floor z, Hebrew name, English name)
EYE = 5.3
STATIONS = {
    'porch':      (38.7, 26.4, PORCH, 'מרפסת מקורה', 'Covered porch'),
    'entry':      (33.3, 23.6, 0.0, 'כניסה', 'Entry'),
    'foyer':      (27.4, 20.6, 0.0, 'מבואה', 'Foyer'),
    'study':      (37.4, 11.8, 0.0, 'חדר עבודה', 'Study'),
    'bsmt':       (30.08, 14.75, -R_IN, 'מדרגות למרתף', 'Basement stair'),
    'dining':     (21.6, 12.3, 0.0, 'חדר אוכל', 'Dining room'),
    'dining_w':   (3.2, 13.4, 0.0, 'חדר אוכל – מערב', 'Dining room west'),
    'kitchen':    (12.6, 19.5, 0.0, 'מטבח', 'Kitchen'),
    'kitchen_w':  (8.8, 21.3, 0.0, 'מטבח – צד הכיריים', 'Kitchen west'),
    'dinette':    (13.2, 30.6, 0.0, 'פינת אוכל', 'Dinette'),
    'hall':       (23.65, 31.2, 0.0, 'מסדרון', 'Hallway'),
    'powder':     (26.3, 34.1, 0.0, 'שירותי אורחים', 'Powder room'),
    'mud':        (33.2, 31.2, 0.0, 'חדר כניסה', 'Mud room'),
    'landing':    (32.1, 39.3, -7 * R_IN, 'מדרגות – פודסט', 'Stair landing'),
    'play':       (16.0, 46.6, 0.0, 'חדר משחקים', 'Play room'),
    'living':     (27.6, 48.4, 0.0, 'סלון', 'Living room'),
}
