# Architecture: walls, openings, floors, foundation, stairs, porch.
# All dimensions in feet, taken from the drawing (labels honoured; unlabeled items scaled off the drawing).
import math, os
from mathutils import Vector, Matrix
from lib import MB, W, Rz, T, frame_at

H = float(os.environ.get('FP_H', '8.0'))   # wall height: 8' cut for the dollhouse views, 9' ceiling for eye level
DH = 6.667     # door head (6'-8")
SILL = 2.167   # window sill  (3046 / 2046 windows are 4'-6" tall, head 6'-8")
WH = 6.667
TE = 0.5       # exterior wall
TI = 0.333     # interior wall (4")
ZW0 = -0.06
G = -6.4375    # grade (11 exterior risers of 6.75" below porch landing)
ZB = -9.8
BASE = -9.0    # basement floor
PORCH = -0.25

B = {}


def builders():
    B['walls'] = MB('walls')
    B['trim'] = MB('trim', bevel=0.012, segs=1)
    B['frames'] = MB('frames', bevel=0.01, segs=1)
    B['glass'] = MB('glass')
    B['floors'] = MB('floors')
    B['found'] = MB('foundation')
    B['stairs'] = MB('stairs', bevel=0.01, segs=1)
    B['doors'] = MB('doors', bevel=0.008, segs=1)
    B['hard'] = MB('furn_hard', bevel=0.02, segs=2)
    B['fine'] = MB('furn_fine', bevel=0.006, segs=1)
    B['soft'] = MB('furn_soft', bevel=0.09, segs=3)
    B['round'] = MB('furn_round')
    B['metal'] = MB('metal', bevel=0.004, segs=1)
    B['cab'] = MB('cabinets', bevel=0.006, segs=1)
    B['ct'] = MB('countertops', bevel=0.012, segs=2)
    B['ct2'] = MB('countertops_solid', bevel=0.012, segs=2)
    B['porch'] = MB('porch', bevel=0.01, segs=1)
    return B


EXTN = {'N': Vector((0, 1, 0)), 'S': Vector((0, -1, 0)), 'E': Vector((1, 0, 0)), 'W': Vector((-1, 0, 0))}


def wall_seg(p0, p1, t, openings=(), ext=None, h=H, capmat='cap', bb=True, extend=(0.0, 0.0), nobb=()):
    """Wall along the plan centre-line p0->p1 (plan coords), thickness t.
    openings: list of (u0, u1, kind, opts) with u measured along the wall from p0."""
    wa, wb, tr, fr, gl = B['walls'], B['trim'], B['trim'], B['frames'], B['glass']
    P0 = W(*p0); P1 = W(*p1)
    d = P1 - P0
    Lw = d.length
    a = math.atan2(d.y, d.x)
    M = T(P0) @ Rz(a)
    ly = Vector((-math.sin(a), math.cos(a), 0))
    ext_side = None
    if ext is not None:
        n = EXTN[ext] if isinstance(ext, str) else ext
        ext_side = 'y+' if n.dot(ly) > 0 else 'y-'

    def fm(top):
        dm = {'all': 'wall'}
        if top >= h - 1e-4:
            dm['z+'] = capmat
        if ext_side:
            dm[ext_side] = 'ext'
        return dm

    int_sides = [s for s in (1, -1) if (('y+' if s > 0 else 'y-') != ext_side)]
    bb_sides = [s for s in int_sides if not any(EXTN[k].dot(ly) * s > 0.5 for k in nobb)]
    ops = sorted(openings, key=lambda o: o[0])
    cur = -extend[0]
    floor_parts = []
    end = Lw + extend[1]
    for op in ops:
        u0, u1, kind = op[0], op[1], op[2]
        o = op[3] if len(op) > 3 else {}
        if u0 > cur:
            wa.box(cur, -t / 2, ZW0, u0, t / 2, h, fm(h), M)
            floor_parts.append((cur, u0))
        head = o.get('head', DH)
        if kind in ('door', 'slide', 'cased'):
            if head < h:
                wa.box(u0, -t / 2, head, u1, t / 2, h, fm(h), M)
            if kind == 'door' and o.get('casing', True):
                for s in int_sides:
                    _door_casing(M, u0, u1, head, t, s)
            if kind == 'slide':
                _slider(M, u0, u1, head, t, ext_side)
                for s in int_sides:
                    _door_casing(M, u0, u1, head, t, s)
        elif kind == 'win':
            sill = o.get('sill', SILL)
            wa.box(u0, -t / 2, ZW0, u1, t / 2, sill, fm(sill), M)
            if head < h:
                wa.box(u0, -t / 2, head, u1, t / 2, h, fm(h), M)
            floor_parts.append((u0, u1))
            _window(M, u0, u1, sill, head, t, o.get('units', 1), ext_side, int_sides)
        cur = u1
    if cur < end:
        wa.box(cur, -t / 2, ZW0, end, t / 2, h, fm(h), M)
        floor_parts.append((cur, end))
    if bb:
        for s in bb_sides:
            for (a0, a1) in floor_parts:
                tr.box(a0, s * t / 2, 0, a1, s * (t / 2 + 0.05), 0.42, 'trim', M)
    return M


def wall_rect(x0, y0, x1, y1, opens=(), ext=None, **kw):
    """Axis aligned wall given by its plan rectangle; openings in absolute plan coords along the run."""
    if (x1 - x0) >= (y1 - y0):
        ym = (y0 + y1) / 2
        ops = [(o[0] - x0, o[1] - x0, *o[2:]) for o in opens]
        return wall_seg((x0, ym), (x1, ym), y1 - y0, ops, ext, **kw)
    xm = (x0 + x1) / 2
    ops = [(o[0] - y0, o[1] - y0, *o[2:]) for o in opens]
    return wall_seg((xm, y0), (xm, y1), x1 - x0, ops, ext, **kw)


def _door_casing(M, u0, u1, head, t, s, cw=0.29, ct=0.06):
    tr = B['trim']
    v0, v1 = s * t / 2, s * (t / 2 + ct)
    tr.box(u0 - cw, v0, 0, u0, v1, head + cw, 'trim', M)
    tr.box(u1, v0, 0, u1 + cw, v1, head + cw, 'trim', M)
    tr.box(u0 - cw, v0, head, u1 + cw, v1, head + cw, 'trim', M)
    # jamb liners
    tr.box(u0, -t / 2, 0, u0 + 0.06, t / 2, head, 'trim', M)
    tr.box(u1 - 0.06, -t / 2, 0, u1, t / 2, head, 'trim', M)
    tr.box(u0, -t / 2, head - 0.06, u1, t / 2, head, 'trim', M)


def _window(M, u0, u1, sill, head, t, units, ext_side, int_sides, fw=0.15):
    fr, gl, tr = B['frames'], B['glass'], B['trim']
    dv = 0.13
    # outer frame
    fr.box(u0, -dv, sill, u0 + fw, dv, head, 'frame', M)
    fr.box(u1 - fw, -dv, sill, u1, dv, head, 'frame', M)
    fr.box(u0, -dv, head - fw, u1, dv, head, 'frame', M)
    fr.box(u0, -dv, sill, u1, dv, sill + fw, 'frame', M)
    uw = (u1 - u0) / units
    for k in range(1, units):
        c = u0 + k * uw
        fr.box(c - 0.1, -dv, sill, c + 0.1, dv, head, 'frame', M)
    zm = (sill + head) / 2 + 0.25
    for k in range(units):
        a = u0 + k * uw
        b = a + uw
        fr.box(a, -0.09, zm - 0.06, b, 0.09, zm + 0.06, 'frame', M)
        # sash frames
        for (za, zb) in ((sill + fw, zm), (zm, head - fw)):
            fr.box(a + 0.05, -0.07, za, b - 0.05, 0.07, za + 0.08, 'frame', M)
            fr.box(a + 0.05, -0.07, zb - 0.08, b - 0.05, 0.07, zb, 'frame', M)
            fr.box(a + 0.05, -0.07, za, a + 0.16, 0.07, zb, 'frame', M)
            fr.box(b - 0.16, -0.07, za, b - 0.05, 0.07, zb, 'frame', M)
    gl.box(u0 + fw, -0.012, sill + fw, u1 - fw, 0.012, head - fw, 'glass', M)
    # interior casing, stool and apron
    for s in int_sides:
        v0 = s * t / 2
        cw = 0.29
        tr.box(u0 - cw, v0, sill, u0, v0 + s * 0.06, head + cw, 'trim', M)
        tr.box(u1, v0, sill, u1 + cw, v0 + s * 0.06, head + cw, 'trim', M)
        tr.box(u0 - cw, v0, head, u1 + cw, v0 + s * 0.06, head + cw, 'trim', M)
        tr.box(u0 - cw - 0.08, s * dv, sill - 0.07, u1 + cw + 0.08, v0 + s * 0.16, sill, 'trim', M)
        tr.box(u0 - cw, v0, sill - 0.42, u1 + cw, v0 + s * 0.05, sill - 0.07, 'trim', M)
        # jamb extensions
        tr.box(u0, s * dv, sill, u0 + 0.05, v0, head, 'trim', M)
        tr.box(u1 - 0.05, s * dv, sill, u1, v0, head, 'trim', M)
        tr.box(u0, s * dv, head - 0.05, u1, v0, head, 'trim', M)
    if ext_side:
        s = 1 if ext_side == 'y+' else -1
        v0 = s * t / 2
        tr.box(u0 - 0.12, s * dv, sill - 0.1, u1 + 0.12, v0 + s * 0.14, sill, 'trim', M)
        tr.box(u0 - 0.3, v0, sill - 0.1, u0, v0 + s * 0.05, head + 0.3, 'trim', M)
        tr.box(u1, v0, sill - 0.1, u1 + 0.3, v0 + s * 0.05, head + 0.3, 'trim', M)
        tr.box(u0 - 0.3, v0, head, u1 + 0.3, v0 + s * 0.05, head + 0.3, 'trim', M)


def _slider(M, u0, u1, head, t, ext_side, fw=0.15):
    fr, gl = B['frames'], B['glass']
    dv = 0.16
    fr.box(u0, -dv, 0, u0 + fw, dv, head, 'frame', M)
    fr.box(u1 - fw, -dv, 0, u1, dv, head, 'frame', M)
    fr.box(u0, -dv, head - fw, u1, dv, head, 'frame', M)
    fr.box(u0, -dv, 0, u1, dv, 0.06, 'frame', M)
    mid = (u0 + u1) / 2
    for (a, b, v) in ((u0 + fw, mid + 0.1, 0.07), (mid - 0.1, u1 - fw, -0.07)):
        pw = 0.2
        fr.box(a, v - 0.05, 0.06, a + pw, v + 0.05, head - fw, 'frame', M)
        fr.box(b - pw, v - 0.05, 0.06, b, v + 0.05, head - fw, 'frame', M)
        fr.box(a, v - 0.05, 0.06, b, v + 0.05, 0.3, 'frame', M)
        fr.box(a, v - 0.05, head - fw - pw, b, v + 0.05, head - fw, 'frame', M)
        gl.box(a + pw, v - 0.01, 0.3, b - pw, v + 0.01, head - fw - pw, 'glass', M)
    # pull
    B['metal'].box(mid - 0.35, 0.13, 3.0, mid - 0.31, 0.16, 4.2, 'blackm', M)


# ------------------------------------------------------------------ door leaves

def door_leaf(hinge, direction, w, h=DH, t=0.146, mat='door', handle=True, handle_mat='brass', panels=2,
              knob=False):
    """hinge: plan (x,y) ; direction: plan unit vector the open leaf points to."""
    dx, dy = direction
    Dw = Vector((dx, -dy, 0)).normalized()
    a = math.atan2(Dw.y, Dw.x)
    M = T(W(*hinge)) @ Rz(a)
    dr = B['doors']
    dr.box(0.03, -t / 2, 0.04, w, t / 2, h - 0.02, mat, M)
    sw = 0.36 if w > 2.2 else 0.3
    for s in (1, -1):
        v0, v1 = s * t / 2, s * (t / 2 + 0.018)
        dr.box(0.03, v0, 0.04, 0.03 + sw, v1, h - 0.02, mat, M)
        dr.box(w - sw, v0, 0.04, w, v1, h - 0.02, mat, M)
        dr.box(0.03 + sw, v0, h - 0.4, w - sw, v1, h - 0.02, mat, M)
        dr.box(0.03 + sw, v0, 0.04, w - sw, v1, 0.75, mat, M)
        if panels == 2:
            dr.box(0.03 + sw, v0, 3.05, w - sw, v1, 3.45, mat, M)
        if panels == 3:
            dr.box(0.03 + sw, v0, 2.6, w - sw, v1, 2.95, mat, M)
            dr.box(0.03 + sw, v0, 4.4, w - sw, v1, 4.75, mat, M)
        if handle:
            hm = B['metal']
            uh = w - 0.24
            hm.rod(M @ Vector((uh, v0, 3.0)), M @ Vector((uh, v1 + s * 0.03, 3.0)), 0.085, handle_mat, n=16)
            if knob:
                hm.sphere(Vector((uh, v1 + s * 0.12, 3.0)), 0.09, handle_mat, M=M, segs=16, rings=8)
                hm.rod(M @ Vector((uh, v1, 3.0)), M @ Vector((uh, v1 + s * 0.08, 3.0)), 0.03, handle_mat)
            else:
                hm.rod(M @ Vector((uh, v1, 3.0)), M @ Vector((uh, v1 + s * 0.13, 3.0)), 0.03, handle_mat)
                hm.rod(M @ Vector((uh, v1 + s * 0.13, 3.0)), M @ Vector((uh - 0.42, v1 + s * 0.13, 3.0)), 0.035,
                       handle_mat)
    # hinges
    for z in (0.75, 3.3, h - 0.75):
        B['metal'].box(-0.02, -t / 2 - 0.01, z, 0.05, t / 2 + 0.01, z + 0.33, handle_mat, M)
    return M


def bifold(hinge, sign, panel_w=3.0, ang=43.5, h=DH):
    """Two-panel bifold folded into a V pointing north (into the living room)."""
    a = math.radians(ang)
    x, y = hinge
    d1 = (sign * math.cos(a), -math.sin(a))
    apex = (x + d1[0] * panel_w, y + d1[1] * panel_w)
    d2 = (sign * math.cos(a), math.sin(a))
    door_leaf((x, y), d1, panel_w - 0.03, h=h, t=0.1, handle=False)
    M = door_leaf(apex, d2, panel_w - 0.03, h=h, t=0.1, handle=False)
    hm = B['metal']
    for s in (1, -1):
        hm.sphere(Vector((0.25, s * 0.13, 3.2)), 0.07, 'brass', M=M, segs=12, rings=6)
    # track
    B['trim'].box(min(x, x + sign * 2 * panel_w * math.cos(a)), -y - 0.08, h, max(x, x + sign * 2 * panel_w * math.cos(a)),
                  -y + 0.08, h + 0.05, 'blackm')


# ------------------------------------------------------------------ stairs

def flight(x0, y0, x1, y1, direction, n, z_top, riser, zbot=ZB, tread_mat='oak_tread', nos=0.09,
           body_mat='trim', tread_t=0.09):
    """Straight flight of n treads descending in plan 'direction' ('N','S','E','W') inside plan rect.
    Tread i top = z_top - i*riser."""
    st = B['stairs']
    if direction in ('N', 'S'):
        L0, L1 = (y0, y1)
    else:
        L0, L1 = (x0, x1)
    run = (L1 - L0) / n
    for i in range(1, n + 1):
        ztop = z_top - i * riser
        if direction == 'N':      # descending toward smaller y, nosing projects downhill
            a, b = L1 - i * run, L1 - (i - 1) * run
            body = (x0, a, x1, b); tread = (x0, a - nos, x1, b)
        elif direction == 'S':
            a, b = L0 + (i - 1) * run, L0 + i * run
            body = (x0, a, x1, b); tread = (x0, a, x1, b + nos)
        elif direction == 'E':
            a, b = L0 + (i - 1) * run, L0 + i * run
            body = (a, y0, b, y1); tread = (a, y0, b + nos, y1)
        else:  # 'W'
            a, b = L1 - i * run, L1 - (i - 1) * run
            body = (a, y0, b, y1); tread = (a - nos, y0, b, y1)
        st.pbox(body[0], body[1], body[2], body[3], zbot, ztop - tread_t, body_mat)
        st.pbox(tread[0], tread[1], tread[2], tread[3], ztop - tread_t, ztop, tread_mat)
    return run


def balustrade(p0, p1, z, height=3.0, post=0.3, spacing=0.36, newel=(True, True), z1=None):
    """Guard rail between plan points p0 and p1 (base z, optional sloped end z1)."""
    tr = B['stairs']
    z1 = z if z1 is None else z1
    P0 = W(*p0, z); P1 = W(*p1, z1)
    d = P1 - P0
    Lh = Vector((d.x, d.y, 0)).length
    n = max(1, int(Lh / spacing))
    for i in range(1, n):
        f = i / n
        p = P0 + d * f
        tr.box(p.x - 0.055, p.y - 0.055, p.z, p.x + 0.055, p.y + 0.055, p.z + height, 'trim')
    for f, flag in ((0.0, newel[0]), (1.0, newel[1])):
        if flag:
            p = P0 + d * f
            tr.box(p.x - post / 2, p.y - post / 2, p.z, p.x + post / 2, p.y + post / 2, p.z + height + 0.35, 'trim')
            tr.box(p.x - post / 2 - 0.04, p.y - post / 2 - 0.04, p.z + height + 0.35, p.x + post / 2 + 0.04,
                   p.y + post / 2 + 0.04, p.z + height + 0.45, 'rail_wood')
    # handrail (sloped prism along the run)
    _rail(P0 + Vector((0, 0, height)), P1 + Vector((0, 0, height)), 0.24, 0.16, 'rail_wood')
    _rail(P0 + Vector((0, 0, 0.0)), P1 + Vector((0, 0, 0.0)), 0.16, 0.12, 'trim')


def _rail(Pa, Pb, w, hgt, mat):
    st = B['stairs']
    d = Pb - Pa
    L = d.length
    q = d.normalized().to_track_quat('X', 'Z')
    M = T(Pa) @ q.to_matrix().to_4x4()
    st.box(0, -w / 2, -hgt / 2, L, w / 2, hgt / 2, mat, M)
