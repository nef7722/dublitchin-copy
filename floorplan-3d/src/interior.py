# Interior: kitchen cabinetry & appliances, baths, built-ins and the furniture drawn on the plan.
import bpy, bmesh, math, os
from mathutils import Vector, Matrix
from lib import MB, W, Rz, T, frame_at, MATS
from arch import B, DH

CT_CUTS = []      # (polygon world XY, z0, z1) holes for sinks in countertops
FAUCETS = []      # (world base point, world facing vector, height, reach)

DIRS = {'N': (0, -1), 'S': (0, 1), 'E': (1, 0), 'W': (-1, 0)}


class Run:
    """Local frame for a cabinet run: u along the run, v from the wall (0) to the front (depth), z up."""

    def __init__(self, x0, y0, x1, y1, front):
        fx, fy = DIRS[front]
        F = Vector((fx, -fy, 0))
        LX = Vector((F.y, -F.x, 0))
        corners = [W(x0, y0), W(x1, y0), W(x1, y1), W(x0, y1)]
        O = min(corners, key=lambda c: (round(c.dot(F), 4), round(c.dot(LX), 4)))
        self.O = O
        self.F = F
        self.LX = LX
        a = math.atan2(LX.y, LX.x)
        self.M = T(O) @ Rz(a)
        self.L = max(c.dot(LX) for c in corners) - O.dot(LX)
        self.D = max(c.dot(F) for c in corners) - O.dot(F)

    def u(self, px, py):
        return (W(px, py) - self.O).dot(self.LX)

    def world(self, u, v, z=0.0):
        return self.M @ Vector((u, v, z))


def shaker_front(M, u0, u1, z0, z1, v, mat='cab', pull='v', pull_side=None, frame=0.19, thick=0.06):
    cb = B['cab']
    cb.box(u0 + 0.01, v, z0, u1 - 0.01, v + thick, z1, mat, M)
    fw = min(frame, (u1 - u0) / 4, (z1 - z0) / 4)
    vf = v + thick
    cb.box(u0 + 0.01, vf, z0, u0 + 0.01 + fw, vf + 0.02, z1, mat, M)
    cb.box(u1 - 0.01 - fw, vf, z0, u1 - 0.01, vf + 0.02, z1, mat, M)
    cb.box(u0 + 0.01 + fw, vf, z0, u1 - 0.01 - fw, vf + 0.02, z0 + fw, mat, M)
    cb.box(u0 + 0.01 + fw, vf, z1 - fw, u1 - 0.01 - fw, vf + 0.02, z1, mat, M)
    hm = B['metal']
    vp = vf + 0.02
    if pull == 'h':
        uc = (u0 + u1) / 2
        L = min(0.55, (u1 - u0) * 0.5)
        zc = (z0 + z1) / 2
        hm.rod(M @ Vector((uc - L / 2, vp + 0.09, zc)), M @ Vector((uc + L / 2, vp + 0.09, zc)), 0.022, 'brass')
        for uu in (uc - L / 2 + 0.03, uc + L / 2 - 0.03):
            hm.rod(M @ Vector((uu, vp, zc)), M @ Vector((uu, vp + 0.09, zc)), 0.016, 'brass')
    elif pull in ('v', 'vu'):
        side = pull_side or 'r'
        uc = (u1 - 0.17) if side == 'r' else (u0 + 0.17)
        if pull == 'v':
            za, zb = z1 - 0.65, z1 - 0.18
        else:
            za, zb = z0 + 0.18, z0 + 0.65
        hm.rod(M @ Vector((uc, vp + 0.09, za)), M @ Vector((uc, vp + 0.09, zb)), 0.022, 'brass')
        for zz in (za + 0.03, zb - 0.03):
            hm.rod(M @ Vector((uc, vp, zz)), M @ Vector((uc, vp + 0.09, zz)), 0.016, 'brass')


def base_cabinets(run, u0, u1, kind='std', ct=True, mat='cab'):
    """Base cabinets between local u0..u1 (split into units)."""
    M, D = run.M, run.D
    cb = B['cab']
    cb.box(u0, 0, 0.33, u1, D - 0.06, 2.875, mat, M)
    cb.box(u0, 0, 0, u1, D - 0.3, 0.33, 'cab_in', M)
    n = max(1, round((u1 - u0) / 1.75))
    w = (u1 - u0) / n
    for i in range(n):
        a = u0 + i * w
        b = a + w
        if kind == 'sink':
            shaker_front(M, a, b, 2.27, 2.8, D - 0.06, mat, pull='none')
        else:
            shaker_front(M, a, b, 2.27, 2.8, D - 0.06, mat, pull='h')
        if b - a > 2.1:
            m = (a + b) / 2
            shaker_front(M, a, m, 0.36, 2.24, D - 0.06, mat, pull='v', pull_side='r')
            shaker_front(M, m, b, 0.36, 2.24, D - 0.06, mat, pull='v', pull_side='l')
        else:
            shaker_front(M, a, b, 0.36, 2.24, D - 0.06, mat, pull='v', pull_side='r' if i % 2 == 0 else 'l')


def countertop(run, u0, u1, v1=None, mat='quartz', z0=2.875, z1=3.0, ends=(0.0, 0.0)):
    v1 = run.D + 0.09 if v1 is None else v1
    B['ct'].box(u0 - ends[0], 0, z0, u1 + ends[1], v1, z1, mat, run.M)


def range_unit(run, u0, u1):
    M, D = run.M, run.D
    st, ci, mt = B['metal'], B['metal'], B['metal']
    st.box(u0 + 0.01, 0.05, 0.0, u1 - 0.01, D, 2.93, 'steel', M)
    st.box(u0 + 0.01, 0.05, 2.93, u1 - 0.01, D + 0.02, 2.97, 'cast_iron', M)
    st.box(u0 + 0.05, D, 2.6, u1 - 0.05, D + 0.04, 2.92, 'black_glass', M)
    n = 5
    for i in range(n):
        uc = u0 + 0.28 + i * (u1 - u0 - 0.56) / (n - 1)
        st.rod(M @ Vector((uc, D + 0.04, 2.76)), M @ Vector((uc, D + 0.13, 2.76)), 0.06, 'nickel', n=16)
    st.box(u0 + 0.06, D, 0.5, u1 - 0.06, D + 0.07, 2.52, 'steel', M)
    st.box(u0 + 0.38, D + 0.07, 1.2, u1 - 0.38, D + 0.075, 2.2, 'black_glass', M)
    st.box(u0 + 0.06, D, 0.08, u1 - 0.06, D + 0.07, 0.45, 'steel', M)
    st.rod(M @ Vector((u0 + 0.2, D + 0.26, 2.38)), M @ Vector((u1 - 0.2, D + 0.26, 2.38)), 0.04, 'nickel')
    for uu in (u0 + 0.25, u1 - 0.25):
        st.rod(M @ Vector((uu, D + 0.07, 2.38)), M @ Vector((uu, D + 0.26, 2.38)), 0.025, 'nickel')
    # burners and grates
    w = u1 - u0
    for uc in (u0 + w * 0.27, u0 + w * 0.73):
        for vc in (0.55, 1.45):
            r = 0.2 if vc > 1 else 0.15
            ci.cyl(0, 0, 2.97, 3.02, r, 'cast_iron', n=20, M=M @ T((uc, vc, 0)))
            ci.cyl(0, 0, 3.02, 3.05, r * 0.65, 'brass', n=20, M=M @ T((uc, vc, 0)))
    gz0, gz1 = 3.04, 3.09
    for (ga, gb) in ((u0 + 0.06, u0 + w / 2 - 0.02), (u0 + w / 2 + 0.02, u1 - 0.06)):
        for vv in (0.12, 1.0, 1.88):
            mt.box(ga, vv - 0.025, gz0, gb, vv + 0.025, gz1, 'cast_iron', M)
        for uu in (ga, (ga + gb) / 2, gb):
            mt.box(uu - 0.025, 0.12, gz0, uu + 0.025, 1.88, gz1, 'cast_iron', M)


def sink_cut(run, uc, vc, w, d, z_top=3.0, depth=0.75, mat='steel', r=0.12):
    """Undermount rectangular sink: hole in countertop + bowl."""
    M = run.M
    pts = []
    hw, hd = w / 2, d / 2
    for (cx, cy, a0) in ((hw - r, hd - r, 0), (-hw + r, hd - r, 90), (-hw + r, -hd + r, 180), (hw - r, -hd + r, 270)):
        for k in range(5):
            a = math.radians(a0 + k * 22.5)
            p = M @ Vector((uc + cx + r * math.cos(a), vc + cy + r * math.sin(a), 0))
            pts.append((p.x, p.y))
    CT_CUTS.append((pts, z_top - 0.3, z_top + 0.3))
    bw = B['metal']
    z0 = z_top - 0.13 - depth
    bw.box(uc - hw, vc - hd, z0, uc + hw, vc + hd, z0 + 0.02, mat, M)
    for (a, b, c, d2) in ((uc - hw, vc - hd, uc - hw + 0.02, vc + hd), (uc + hw - 0.02, vc - hd, uc + hw, vc + hd),
                          (uc - hw, vc - hd, uc + hw, vc - hd + 0.02), (uc - hw, vc + hd - 0.02, uc + hw, vc + hd)):
        bw.box(a, b, z0, c, d2, z_top - 0.12, mat, M)
    bw.cyl(0, 0, z0 + 0.02, z0 + 0.03, 0.12, 'nickel', n=16, M=M @ T((uc, vc, 0)))


def oval_sink(cx, cy, rx, ry, z_top, depth=0.45):
    pts = []
    for k in range(32):
        a = 2 * math.pi * k / 32
        pts.append((cx + rx * math.cos(a), -cy + ry * math.sin(a)))
    CT_CUTS.append((pts, z_top - 0.3, z_top + 0.3))
    fn = B['fine']
    verts = fn.sphere(Vector((cx, -cy, z_top - 0.12)), 1.0, 'ceramic', scale=(rx, ry, depth), segs=32, rings=16)
    kill = [v for v in verts if v.co.z > z_top - 0.12 + 1e-4]
    bmesh.ops.delete(fn.bm, geom=kill, context='VERTS')


def faucet(base, facing, h=1.15, reach=0.75):
    FAUCETS.append((base, facing, h, reach))


def make_faucets(coll):
    for i, (base, facing, h, reach) in enumerate(FAUCETS):
        F = Vector(facing).normalized()
        cu = bpy.data.curves.new('faucet%d' % i, 'CURVE')
        cu.dimensions = '3D'
        cu.bevel_depth = 0.04
        cu.bevel_resolution = 4
        cu.use_fill_caps = True
        sp = cu.splines.new('BEZIER')
        pts = [Vector(base), Vector(base) + Vector((0, 0, h)), Vector(base) + F * reach + Vector((0, 0, h * 0.82))]
        sp.bezier_points.add(len(pts) - 1)
        for bp, p in zip(sp.bezier_points, pts):
            bp.co = p
            bp.handle_left_type = 'AUTO'
            bp.handle_right_type = 'AUTO'
        sp.bezier_points[1].handle_left_type = 'FREE'
        sp.bezier_points[1].handle_right_type = 'FREE'
        sp.bezier_points[1].handle_left = pts[1] - Vector((0, 0, 0.25))
        sp.bezier_points[1].handle_right = pts[1] + Vector((0, 0, 0.18)) + F * 0.2
        ob = bpy.data.objects.new('faucet%d' % i, cu)
        coll.objects.link(ob)
        cu.materials.append(MATS['nickel'])
        mt = B['metal']
        b = Vector(base)
        mt.cyl(b.x, b.y, b.z - 0.01, b.z + 0.08, 0.1, 'nickel', n=20)
        side = Vector((F.y, -F.x, 0))
        mt.rod(b + Vector((0, 0, 0.55)), b + Vector((0, 0, 0.55)) + side * 0.22 + Vector((0, 0, 0.05)), 0.025, 'nickel')


UP_TOP = 8.75 if os.environ.get('FP_EYE') else 8.0


def uppers(run, u0, u1, z0=4.5, z1=UP_TOP, depth=1.0, mat='cab'):
    M = run.M
    cb = B['cab']
    cb.box(u0, 0, z0, u1, depth - 0.06, z1 - 0.19, mat, M)
    n = max(1, round((u1 - u0) / 1.5))
    w = (u1 - u0) / n
    for i in range(n):
        a = u0 + i * w
        shaker_front(M, a, a + w, z0 + 0.02, z1 - 0.2, depth - 0.06, mat, pull='vu',
                     pull_side='r' if i % 2 == 0 else 'l')
    cb.box(u0 - 0.04, 0, z1 - 0.2, u1 + 0.04, depth + 0.06, z1, mat, M)
    cb.box(u0, 0, z0 - 0.06, u1, depth, z0, mat, M)


def hood(run, u0, u1, z0=5.3, z1=UP_TOP, mat='cab'):
    M = run.M
    cb = B['cab']
    cb.box(u0 - 0.15, 0, z0, u1 + 0.15, 1.75, z0 + 0.6, mat, M)
    cb.box(u0 - 0.2, 0, z0 + 0.6, u1 + 0.2, 1.8, z0 + 0.72, mat, M)
    cb.box(u0 + 0.15, 0, z0 + 0.72, u1 - 0.15, 1.25, z1 - 0.19, mat, M)
    cb.box(u0 + 0.1, 0, z1 - 0.2, u1 - 0.1, 1.32, z1, mat, M)
    B['metal'].box(u0 - 0.16, 1.751, z0 + 0.25, u1 + 0.16, 1.765, z0 + 0.33, 'brass', M)
    B['metal'].box(u0 - 0.1, 0.05, z0 - 0.01, u1 + 0.1, 1.7, z0, 'steel', M)


def backsplash(x0, y0, x1, y1, z0=3.0, z1=4.5):
    B['fine'].pbox(x0, y0, x1, y1, z0, z1, 'subway_yz' if (x1 - x0) < (y1 - y0) else 'subway_xz')


# ------------------------------------------------------------------ kitchen

def kitchen():
    # K1: cooktop/range + sink run along the pantry wall (fronts face east)
    k1 = Run(4.833, 15.833, 6.833, 25.5, 'E')
    r_rng = sorted((k1.u(0, 17.25), k1.u(0, 19.75)))
    r_snk = sorted((k1.u(0, 21.35), k1.u(0, 23.85)))
    base_cabinets(k1, 0, r_rng[0])
    range_unit(k1, *r_rng)
    base_cabinets(k1, r_rng[1], r_snk[0])
    base_cabinets(k1, *r_snk, kind='sink')
    base_cabinets(k1, r_snk[1], k1.L)
    countertop(k1, 0, r_rng[0])
    countertop(k1, r_rng[1], k1.L)
    sink_cut(k1, (r_snk[0] + r_snk[1]) / 2, 1.0, 2.0, 1.45)
    p = k1.world((r_snk[0] + r_snk[1]) / 2, 0.22, 3.0)
    faucet(p, k1.F)
    uppers(k1, 0, r_rng[0] - 0.15)
    hood(k1, *r_rng)
    uppers(k1, r_rng[1] + 0.15, k1.L)
    backsplash(4.833, 15.833, 4.86, 25.5)

    # K2: peninsula with the second range (fronts face south), raised bar behind it
    k2 = Run(10.5, 15.833, 21.833, 17.833, 'S')
    a_r = sorted((k2.u(15.4, 0), k2.u(17.9, 0)))
    a_c = sorted((k2.u(19.833, 0), k2.u(10.5, 0)))   # cabinets from the corner to the open end
    base_cabinets(k2, a_c[0], a_r[0])
    range_unit(k2, *a_r)
    base_cabinets(k2, a_r[1], a_c[1])
    B['cab'].box(0, 0, 0, a_c[0], k2.D - 0.06, 2.875, 'cab', k2.M)            # corner (blind)
    countertop(k2, 0, a_r[0])
    countertop(k2, a_r[1], k2.L, ends=(0, 0.09))
    # K2b: sink leg along the foyer side (fronts face west)
    k3 = Run(19.833, 17.833, 21.833, 27.3, 'W')
    s_s = sorted((k3.u(0, 21.6), k3.u(0, 24.1)))
    base_cabinets(k3, 0, s_s[0])
    base_cabinets(k3, *s_s, kind='sink')
    base_cabinets(k3, s_s[1], k3.L)
    countertop(k3, 0, k3.L - 0.09, ends=(0.09, 0))
    sink_cut(k3, (s_s[0] + s_s[1]) / 2, 1.0, 2.0, 1.45)
    faucet(k3.world((s_s[0] + s_s[1]) / 2, 0.22, 3.0), k3.F)
    # raised bar tops on the half walls
    ct = B['ct2']
    ct.pbox(10.38, 15.22, 22.42, 15.95, 3.5, 3.62, 'quartz')
    ct.pbox(21.72, 15.95, 22.42, 25.0, 3.5, 3.62, 'quartz')

    # K3: island (waterfall top)
    cb = B['cab']
    x0, y0, x1, y1 = 10.7, 21.15, 16.7, 24.65
    cb.pbox(x0 + 0.15, y0 + 0.16, x1 - 0.15, y1 - 0.16, 0.33, 2.85, 'island')
    cb.pbox(x0 + 0.4, y0 + 0.4, x1 - 0.4, y1 - 0.4, 0, 0.33, 'cab_in')
    for front in ('S', 'N'):
        if front == 'S':
            rr = Run(x0 + 0.15, y0, x1 - 0.15, y1 - 0.16, 'S')
        else:
            rr = Run(x0 + 0.15, y0 + 0.16, x1 - 0.15, y1, 'N')
        n = 3
        w = rr.L / n
        for i in range(n):
            a = i * w
            for (za, zb) in ((2.2, 2.8), (1.35, 2.15), (0.36, 1.3)):
                shaker_front(rr.M, a, a + w, za, zb, rr.D, 'island', pull='h')
    ct.pbox(x0, y0, x1, y1, 2.85, 3.0, 'marble_ct')
    ct.pbox(x0, y0, x0 + 0.15, y1, 0, 2.85, 'marble_ct')
    ct.pbox(x1 - 0.15, y0, x1, y1, 0, 2.85, 'marble_ct')

    # K4: FRE / REF columns facing the dinette
    mt = B['metal']
    for (a, b) in ((16.167, 19.0), (19.0, 21.833)):
        cb.pbox(a, 35.15, b, 37.083, 0, 7.95, 'cab')
        mt.pbox(a + 0.03, 35.05, b - 0.03, 35.15, 0.05, 7.0, 'steel')
        mt.rod(W(b - 0.25 if a < 18 else a + 0.25, 34.85, 1.8), W(b - 0.25 if a < 18 else a + 0.25, 34.85, 6.0),
               0.04, 'nickel')
        for zz in (2.1, 5.7):
            xx = b - 0.25 if a < 18 else a + 0.25
            mt.rod(W(xx, 35.05, zz), W(xx, 34.85, zz), 0.025, 'nickel')
        rr = Run(a, 35.15, b, 37.083, 'N')
        shaker_front(rr.M, 0.02, rr.L - 0.02, 7.06, 7.8, rr.D, 'cab', pull='h')
    cb.pbox(15.98, 35.0, 16.167, 37.083, 0, 7.97, 'cab')
    cb.pbox(15.98, 35.0, 21.833, 37.083, 7.8, 7.98, 'cab')

    # K5: living-room kitchenette behind bifold doors (fronts face north)
    k5 = Run(22.167, 55.083, 36.167, 57.083, 'N')
    rg = sorted((k5.u(24.15, 0), k5.u(26.65, 0)))
    sk = sorted((k5.u(30.55, 0), k5.u(33.05, 0)))
    base_cabinets(k5, 0, rg[0])
    range_unit(k5, *rg)
    base_cabinets(k5, rg[1], sk[0])
    base_cabinets(k5, *sk, kind='sink')
    base_cabinets(k5, sk[1], k5.L)
    countertop(k5, 0, rg[0])
    countertop(k5, rg[1], k5.L)
    sink_cut(k5, (sk[0] + sk[1]) / 2, 1.0, 2.0, 1.45)
    faucet(k5.world((sk[0] + sk[1]) / 2, 0.22, 3.0), k5.F)
    uppers(k5, 0, rg[0] - 0.15, z1=7.6)
    hood(k5, *rg, z1=7.6)
    uppers(k5, rg[1] + 0.15, k5.L, z1=7.6)
    backsplash(22.167, 57.06, 36.167, 57.083)


# ------------------------------------------------------------------ furniture

def chair(M, mat='chair', wood='walnut'):
    hd, sf = B['hard'], B['soft']
    for (x, y) in ((-0.62, -0.62), (0.62, -0.62), (-0.62, 0.66), (0.62, 0.66)):
        hd.box(x - 0.07, y - 0.07, 0, x + 0.07, y + 0.07, 1.42, wood, M)
    sf.box(-0.8, -0.78, 1.36, 0.8, 0.82, 1.64, mat, M)
    sf.box(-0.78, -0.86, 1.55, 0.78, -0.6, 3.25, mat, M)


def sofa(M, Wd, D, nseats, arms=(True, True), back=True, mat='sofa', aw=0.5, seat_from=None):
    sf, hd = B['soft'], B['hard']
    x0, x1 = -Wd / 2, Wd / 2
    y0, y1 = -D / 2, D / 2
    ia = x0 + (aw if arms[0] else 0)
    ib = x1 - (aw if arms[1] else 0)
    sf.box(ia, y0, 0.32, ib, y1, 1.12, mat, M)
    for (x, y) in ((x0 + 0.2, y0 + 0.2), (x1 - 0.2, y0 + 0.2), (x0 + 0.2, y1 - 0.2), (x1 - 0.2, y1 - 0.2)):
        hd.box(x - 0.08, y - 0.08, 0, x + 0.08, y + 0.08, 0.34, 'walnut', M)
    ia = x0 + (aw if arms[0] else 0)
    ib = x1 - (aw if arms[1] else 0)
    if arms[0]:
        sf.box(x0, y0, 0.32, x0 + aw, y1, 2.05, mat, M)
    if arms[1]:
        sf.box(x1 - aw, y0, 0.32, x1, y1, 2.05, mat, M)
    if back:
        sf.box(ia, y0, 1.12, ib, y0 + 0.55, 2.7, mat, M)
    sb = y0 + (0.55 if back else 0)
    w = (ib - ia) / nseats
    for i in range(nseats):
        a = ia + i * w
        sf.box(a + 0.02, sb, 1.12, a + w - 0.02, y1 - 0.02, 1.58, mat, M)
        if back:
            sf.box(a + 0.04, sb - 0.1, 1.5, a + w - 0.04, sb + 0.45, 2.85, mat, M)


def dining():
    hd = B['hard']
    # table 12'-6" x 4'-3"
    x0, x1, y0, y1 = 4.25, 16.75, 6.375, 10.625
    hd.pbox(x0, y0, x1, y1, 2.35, 2.52, 'walnut')
    hd.pbox(x0 + 0.3, y0 + 0.3, x1 - 0.3, y1 - 0.3, 2.15, 2.35, 'walnut')
    for xx in (x0 + 0.5, (x0 + x1) / 2, x1 - 0.5):
        for yy in (y0 + 0.45, y1 - 0.45):
            hd.pbox(xx - 0.13, yy - 0.13, xx + 0.13, yy + 0.13, 0, 2.15, 'walnut')
    for i in range(6):
        xx = 5.5 + 2.0 * i
        chair(frame_at(xx, 5.85, 0, 1))      # north side, facing south
        chair(frame_at(xx, 11.15, 0, -1))    # south side, facing north
    chair(frame_at(3.45, 8.5, 1, 0))
    chair(frame_at(17.55, 8.5, -1, 0))
    # sofa against the stair wall
    sofa(frame_at(26.8, 8.2, -1, 0), 7.2, 2.5, 3)


def dinette():
    hd = B['hard']
    cx, cy = 5.6, 31.3
    hd.cyl(cx, -cy, 2.36, 2.5, 2.25, 'walnut', n=48)
    hd.cyl(cx, -cy, 0.12, 2.36, 0.28, 'walnut', n=24)
    hd.cyl(cx, -cy, 0.0, 0.12, 1.05, 'walnut', n=36)
    for k in range(8):
        a = math.radians(90 + 45 * k)
        px, py = cx + 2.95 * math.cos(a), cy + 2.95 * math.sin(a)
        chair(frame_at(px, py, -math.cos(a), -math.sin(a)))


def study():
    hd, sf, mt = B['hard'], B['soft'], B['metal']
    # bow-front desk, user sits on the north side
    xa, xb, yb, ys, yf = 35.34, 41.68, 6.86, 8.6, 9.4
    pts = [(xa, yb), (xb, yb), (xb, ys)]
    cxm = (xa + xb) / 2
    half = (xb - xa) / 2
    # circular arc through (xa,ys), (cxm,yf), (xb,ys)
    s = yf - ys
    R = (half ** 2 + s ** 2) / (2 * s)
    cyc = yf - R
    a0 = math.atan2(ys - cyc, xb - cxm)
    a1 = math.atan2(ys - cyc, xa - cxm)
    for k in range(1, 24):
        a = a0 + (a1 - a0) * k / 24
        pts.append((cxm + R * math.cos(a), cyc + R * math.sin(a)))
    pts.append((xa, ys))
    wpts = [(x, -y) for x, y in pts]
    hd.prism(wpts, 2.36, 2.52, 'walnut')
    for (a, b) in ((xa + 0.1, xa + 1.6), (xb - 1.6, xb - 0.1)):
        hd.pbox(a, yb + 0.1, b, ys - 0.05, 0, 2.36, 'walnut')
        for (za, zb) in ((1.65, 2.3), (0.95, 1.6), (0.1, 0.9)):
            B['cab'].pbox(a + 0.05, yb + 0.02, b - 0.05, yb + 0.1, za, zb, 'walnut')
            mt.rod(W((a + b) / 2 - 0.25, yb - 0.05, (za + zb) / 2), W((a + b) / 2 + 0.25, yb - 0.05, (za + zb) / 2),
                   0.02, 'brass')
    hd.pbox(xa + 1.6, ys - 0.25, xb - 1.6, ys - 0.15, 0.5, 2.36, 'walnut')
    # executive chair north of the desk, facing south
    M = frame_at(38.5, 6.0, 0, 1)
    sf.box(-0.85, -0.8, 1.45, 0.85, 0.85, 1.78, 'leather', M)
    sf.box(-0.8, -0.95, 1.7, 0.8, -0.65, 3.7, 'leather', M)
    sf.box(-1.0, -0.6, 1.9, -0.82, 0.6, 2.35, 'leather', M)
    sf.box(0.82, -0.6, 1.9, 1.0, 0.6, 2.35, 'leather', M)
    mt.cyl(0, 0, 0.35, 1.45, 0.09, 'nickel', M=M)
    for k in range(5):
        a = 2 * math.pi * k / 5
        mt.rod(M @ Vector((0, 0, 0.3)), M @ Vector((1.05 * math.cos(a), 1.05 * math.sin(a), 0.22)), 0.06, 'blackm')
        mt.sphere(M @ Vector((1.05 * math.cos(a), 1.05 * math.sin(a), 0.1)), 0.1, 'blackm', segs=12, rings=6)


def living_play():
    # play room sofa against the south wall (faces north)
    sofa(frame_at(16.25, 55.75, 0, -1), 7.0, 2.6, 3)
    # living room L-sectional: long leg on the east wall, return along the stair wall
    sofa(frame_at(34.85, 46.6, -1, 0), 6.9, 2.5, 3, arms=(True, False))
    sofa(frame_at(32.35, 44.45, 0, 1), 2.5, 2.5, 1, arms=(False, True))
    B['soft'].box(33.6, -44.0, 1.12, 35.54, -43.15, 2.69, 'sofa')
    B['soft'].box(33.7, -44.4, 1.5, 35.5, -43.65, 2.85, 'sofa')
    # dashed wall unit on the play-room side of the wall
    cb = B['cab']
    cb.pbox(19.97, 45.65, 21.833, 47.05, 4.4, 6.6, 'cab')
    rr = Run(19.97, 45.65, 21.833, 47.05, 'W')
    shaker_front(rr.M, 0.02, rr.L - 0.02, 4.42, 6.58, rr.D - 0.06, 'cab', pull='vu', pull_side='r')


def baths():
    fn, ct, cb, mt = B['fine'], B['ct'], B['cab'], B['metal']
    # Toilet in the powder room, tank on the east wall, facing west
    M = frame_at(29.35, 30.75, -1, 0)
    fn.ellprism(0, 0.15, 0.36, 0.55, 0.0, 1.0, 'ceramic', M=M)
    fn.ellprism(0, 0.35, 0.68, 0.95, 0.95, 1.28, 'ceramic', M=M)
    fn.ellprism(0, 0.36, 0.7, 0.97, 1.28, 1.34, 'ceramic', M=M)
    fn.ellprism(0, 0.36, 0.69, 0.96, 1.34, 1.4, 'ceramic', M=M)
    fn.box(-0.85, -0.78, 1.3, 0.85, -0.2, 2.45, 'ceramic', M)
    fn.box(-0.9, -0.82, 2.45, 0.9, -0.15, 2.55, 'ceramic', M)
    mt.cyl(0.0, -0.45, 2.55, 2.58, 0.07, 'nickel', M=M)
    # Powder vanity (open to the hall) against the east wall
    v = Run(28.5, 32.583, 30.167, 35.583, 'W')
    cb.box(0, 0, 0.33, v.L, v.D - 0.06, 2.75, 'walnut', v.M)
    cb.box(0, 0, 0, v.L, v.D - 0.3, 0.33, 'cab_in', v.M)
    shaker_front(v.M, 0.0, v.L / 2, 0.36, 2.7, v.D - 0.06, 'walnut', pull='v', pull_side='r')
    shaker_front(v.M, v.L / 2, v.L, 0.36, 2.7, v.D - 0.06, 'walnut', pull='v', pull_side='l')
    ct.pbox(28.42, 32.583, 30.167, 35.583, 2.75, 2.875, 'marble_ct')
    oval_sink(29.3, 34.08, 0.62, 0.45, 2.875)
    faucet(W(29.95, 34.08, 2.875), Vector((-1, 0, 0)), h=0.85, reach=0.5)
    mt.pbox(30.1, 33.15, 30.167, 35.0, 3.5, 6.2, 'brass')
    mt.pbox(30.07, 33.25, 30.167, 34.9, 3.6, 6.1, 'mirror')
    # Wash nook off the dining room (oval sink, open to the north)
    v = Run(0.5, 15.55, 4.5, 17.5, 'N')
    cb.box(0, 0, 0.33, v.L, v.D - 0.06, 2.75, 'cab', v.M)
    cb.box(0, 0, 0, v.L, v.D - 0.3, 0.33, 'cab_in', v.M)
    shaker_front(v.M, 0.0, v.L / 2, 0.36, 2.7, v.D - 0.06, 'cab', pull='v', pull_side='r')
    shaker_front(v.M, v.L / 2, v.L, 0.36, 2.7, v.D - 0.06, 'cab', pull='v', pull_side='l')
    ct.pbox(0.5, 15.45, 4.5, 17.5, 2.75, 2.875, 'marble_ct')
    oval_sink(2.6, 16.45, 0.85, 0.5, 2.875)
    faucet(W(2.6, 17.25, 2.875), Vector((0, 1, 0)), h=0.85, reach=0.5)
    mt.pbox(1.4, 17.43, 3.8, 17.5, 3.5, 6.2, 'brass')
    mt.pbox(1.5, 17.40, 3.7, 17.5, 3.6, 6.1, 'mirror')
    backsplash(0.5, 17.48, 4.5, 17.5, 2.875, 3.4)


def builtins():
    tr, cb, mt, hd = B['trim'], B['cab'], B['metal'], B['hard']
    # walk-in pantry shelving (west and north walls)
    for z in (1.5, 3.0, 4.5, 6.0, 7.3):
        tr.pbox(0.5, 17.833, 1.75, 25.45, z, z + 0.07, 'trim')
        tr.pbox(1.75, 17.833, 4.5, 18.9, z, z + 0.07, 'trim')
    # pantry contents (jars / boxes) for scale
    import random
    rnd = random.Random(3)
    cols = ['oakwood', 'cab_in', 'brass', 'ceramic', 'sofa', 'cushion_acc']
    for z in (1.57, 3.07, 4.57, 6.07):
        y = 18.1
        while y < 25.0:
            h = rnd.uniform(0.45, 0.95)
            w = rnd.uniform(0.35, 0.7)
            hd.pbox(0.7, y, 0.7 + rnd.uniform(0.5, 0.9), y + w, z, z + h, rnd.choice(cols))
            y += w + rnd.uniform(0.15, 0.5)
    # coat closet: shelf + rod
    tr.pbox(25.5, 26.917, 30.167, 28.0, 5.6, 5.67, 'trim')
    mt.rod(W(25.5, 27.8, 5.35), W(30.167, 27.8, 5.35), 0.05, 'nickel')
    # play-room closet shelves
    for z in (1.0, 2.5, 4.0, 5.5):
        tr.pbox(14.333, 37.417, 21.833, 39.3, z, z + 0.07, 'trim')
    for x in (16.8, 19.3):
        tr.pbox(x, 37.417, x + 0.07, 39.3, 0, 6.2, 'trim')
    # mud room bench with lockers along the south wall
    m0, m1 = 30.5, 36.167
    cb.pbox(m0, 34.583, m1, 35.583, 0, 1.4, 'cab')
    hd.pbox(m0, 34.5, m1, 35.583, 1.4, 1.55, 'oakwood')
    cb.pbox(m0, 35.45, m1, 35.583, 1.55, 6.0, 'cab')
    cb.pbox(m0, 34.75, m1, 35.583, 6.0, 6.15, 'cab')
    cb.pbox(m0, 34.6, m1, 35.583, 7.0, 7.12, 'cab')
    n = 3
    w = (m1 - m0) / n
    for i in range(n + 1):
        x = m0 + i * w
        cb.pbox(x - 0.04, 34.75, x + 0.04, 35.583, 1.55, 7.0, 'cab')
    for i in range(n):
        xc = m0 + (i + 0.5) * w
        for dx in (-0.35, 0.35):
            mt.rod(W(xc + dx, 35.45, 5.2), W(xc + dx, 35.2, 5.35), 0.03, 'brass')
    rr = Run(m0, 34.583, m1, 35.583, 'N')
    for i in range(n):
        shaker_front(rr.M, i * w + 0.03, (i + 1) * w - 0.03, 0.15, 1.35, rr.D, 'cab', pull='h')


def build_interior(coll):
    kitchen()
    dining()
    dinette()
    study()
    living_play()
    baths()
    builtins()
    make_faucets(coll)


def apply_cuts(ct_obj, coll):
    """Sink holes; self-intersection mode because the countertop pieces touch each other."""
    for i, (pts, z0, z1) in enumerate(CT_CUTS):
        cm = MB('ctcut%d' % i)
        cm.prism(pts, z0, z1, 'quartz')
        co = cm.finish(coll)
        MB.all.remove(cm)
        co.hide_render = True
        co.display_type = 'WIRE'
        mod = ct_obj.modifiers.new('cut%d' % i, 'BOOLEAN')
        mod.operation = 'DIFFERENCE'
        mod.solver = 'EXACT'
        mod.use_self = True
        mod.use_hole_tolerant = True
        mod.object = co
