# Core helpers: mesh builder, plan<->world conversion, materials.
# Units: 1 Blender unit = 1 foot. Plan coords: x = east (right on drawing), y = south (down on drawing).
# World: X = x, Y = -y, Z up. Finished floor level = 0.
import bpy, bmesh, math, os
from mathutils import Vector, Matrix

MATS = {}


def W(x, y, z=0.0):
    return Vector((x, -y, z))


def Rz(a):
    return Matrix.Rotation(a, 4, 'Z')


def T(v):
    return Matrix.Translation(Vector(v))


def frame_at(px, py, face_dx, face_dy, z=0.0):
    """Local frame at plan point, local +Y = plan facing direction."""
    F = Vector((face_dx, -face_dy, 0)).normalized()
    a = math.atan2(F.y, F.x) - math.pi / 2
    return T((px, -py, z)) @ Rz(a)


class MB:
    """Accumulating mesh builder with per-face materials."""
    all = []
    REC = None   # when a list: every box / prism footprint is recorded (for walk collision maps)

    def _rec(self, pts3, m):
        if MB.REC is None:
            return
        if isinstance(m, dict):
            m = m.get('z+', m.get('all'))
        MB.REC.append((self.name, m, [(p[0], p[1]) for p in pts3], min(p[2] for p in pts3), max(p[2] for p in pts3)))

    def __init__(self, name, bevel=0.0, segs=2, angle=40):
        self.name = name
        self.bm = bmesh.new()
        self.mats = []
        self.bevel = bevel
        self.segs = segs
        self.angle = angle
        MB.all.append(self)

    def mi(self, m):
        if m not in self.mats:
            self.mats.append(m)
        return self.mats.index(m)

    def _faces_mat(self, faces, m, smooth=False):
        i = self.mi(m)
        for f in faces:
            f.material_index = i
            f.smooth = smooth

    def box(self, X0, Y0, Z0, X1, Y1, Z1, m, M=None):
        X0, X1 = min(X0, X1), max(X0, X1)
        Y0, Y1 = min(Y0, Y1), max(Y0, Y1)
        Z0, Z1 = min(Z0, Z1), max(Z0, Z1)
        if X1 - X0 < 1e-5 or Y1 - Y0 < 1e-5 or Z1 - Z0 < 1e-5:
            return
        c = [(X0, Y0, Z0), (X1, Y0, Z0), (X1, Y1, Z0), (X0, Y1, Z0),
             (X0, Y0, Z1), (X1, Y0, Z1), (X1, Y1, Z1), (X0, Y1, Z1)]
        if M is not None:
            c = [M @ Vector(p) for p in c]
        self._rec(c, m)
        v = [self.bm.verts.new(p) for p in c]
        F = {'z-': (0, 3, 2, 1), 'z+': (4, 5, 6, 7), 'y-': (0, 1, 5, 4),
             'y+': (2, 3, 7, 6), 'x-': (3, 0, 4, 7), 'x+': (1, 2, 6, 5)}
        for k, idx in F.items():
            f = self.bm.faces.new([v[i] for i in idx])
            if isinstance(m, dict):
                mm = m.get(k, m.get('all'))
            else:
                mm = m
            f.material_index = self.mi(mm)

    def pbox(self, x0, y0, x1, y1, z0, z1, m):
        """Plan-coordinate box."""
        self.box(min(x0, x1), -max(y0, y1), z0, max(x0, x1), -min(y0, y1), z1, m)

    def prism(self, pts, z0, z1, m, M=None, smooth_sides=False, mtop=None, mbot=None):
        """Extrude a world-XY polygon (list of (X,Y)) from z0 to z1."""
        n = len(pts)
        bot, top = [], []
        for (x, y) in pts:
            pb = Vector((x, y, z0)); pt = Vector((x, y, z1))
            if M is not None:
                pb = M @ pb; pt = M @ pt
            bot.append(self.bm.verts.new(pb)); top.append(self.bm.verts.new(pt))
        self._rec([v.co for v in bot] + [v.co for v in top], m)
        faces = []
        # orientation: compute signed area
        area = sum(pts[i][0] * pts[(i + 1) % n][1] - pts[(i + 1) % n][0] * pts[i][1] for i in range(n))
        ccw = area > 0
        if ccw:
            fb = self.bm.faces.new(list(reversed(bot))); ft = self.bm.faces.new(top)
        else:
            fb = self.bm.faces.new(bot); ft = self.bm.faces.new(list(reversed(top)))
        sides = []
        for i in range(n):
            j = (i + 1) % n
            q = [bot[i], bot[j], top[j], top[i]] if ccw else [bot[j], bot[i], top[i], top[j]]
            sides.append(self.bm.faces.new(q))
        self._faces_mat([fb], mbot or m)
        self._faces_mat([ft], mtop or m)
        self._faces_mat(sides, m, smooth_sides)

    def cyl(self, cx, cy, z0, z1, r, m, n=24, M=None, mtop=None):
        pts = [(cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n)) for i in range(n)]
        self.prism(pts, z0, z1, m, M=M, smooth_sides=True, mtop=mtop)

    def ellprism(self, cx, cy, rx, ry, z0, z1, m, n=32, M=None, mtop=None):
        pts = [(cx + rx * math.cos(2 * math.pi * i / n), cy + ry * math.sin(2 * math.pi * i / n)) for i in range(n)]
        self.prism(pts, z0, z1, m, M=M, smooth_sides=True, mtop=mtop)

    def rod(self, p0, p1, r, m, n=12):
        """Cylinder between two world points."""
        p0 = Vector(p0); p1 = Vector(p1)
        d = p1 - p0
        L = d.length
        q = d.normalized().to_track_quat('Z', 'Y')
        M = T(p0) @ q.to_matrix().to_4x4()
        self.cyl(0, 0, 0, L, r, m, n=n, M=M)

    def sphere(self, c, r, m, scale=(1, 1, 1), half=False, M=None, segs=24, rings=12):
        mat = Matrix.Diagonal((scale[0], scale[1], scale[2], 1))
        mat = T(c) @ mat
        if M is not None:
            mat = M @ mat
        res = bmesh.ops.create_uvsphere(self.bm, u_segments=segs, v_segments=rings, radius=r, matrix=mat)
        verts = res['verts']
        faces = list({f for v in verts for f in v.link_faces})
        self._faces_mat(faces, m, True)
        return verts

    def finish(self, coll):
        if len(self.bm.verts) == 0:
            return None
        me = bpy.data.meshes.new(self.name)
        self.bm.normal_update()
        self.bm.to_mesh(me)
        self.bm.free()
        ob = bpy.data.objects.new(self.name, me)
        coll.objects.link(ob)
        for m in self.mats:
            me.materials.append(MATS[m])
        if self.bevel > 0 and not os.environ.get('FP_NOBEVEL'):
            mod = ob.modifiers.new('bv', 'BEVEL')
            mod.width = self.bevel
            mod.segments = self.segs
            mod.limit_method = 'ANGLE'
            mod.angle_limit = math.radians(self.angle)
            mod.use_clamp_overlap = True
        return ob


# ---------------------------------------------------------------- materials

def _new(name):
    m = bpy.data.materials.new(name)
    try:
        m.use_nodes = True
    except Exception:
        pass
    MATS[name] = m
    nt = m.node_tree
    return m, nt, nt.nodes['Principled BSDF']


def principled(name, color, rough=0.5, metal=0.0, spec=0.5, coat=0.0, sheen=0.0):
    m, nt, b = _new(name)
    b.inputs['Base Color'].default_value = (*color, 1)
    b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = metal
    b.inputs['Specular IOR Level'].default_value = spec
    b.inputs['Coat Weight'].default_value = coat
    b.inputs['Sheen Weight'].default_value = sheen
    m.diffuse_color = (*color, 1)
    return m, nt, b


def _geo_map(nt, rot_z=0.0, scale=(1, 1, 1), loc=(0, 0, 0)):
    N, L = nt.nodes, nt.links
    geo = N.new('ShaderNodeNewGeometry')
    mp = N.new('ShaderNodeMapping')
    mp.inputs['Rotation'].default_value = (0, 0, math.radians(rot_z))
    mp.inputs['Scale'].default_value = scale
    mp.inputs['Location'].default_value = loc
    L.new(geo.outputs['Position'], mp.inputs['Vector'])
    return mp.outputs['Vector']


def _scale_vec(nt, vec, scale):
    N, L = nt.nodes, nt.links
    mp = N.new('ShaderNodeMapping')
    mp.inputs['Scale'].default_value = scale
    L.new(vec, mp.inputs['Vector'])
    return mp.outputs['Vector']


def _vmul(nt, a, b):
    N, L = nt.nodes, nt.links
    vm = N.new('ShaderNodeVectorMath'); vm.operation = 'MULTIPLY'
    L.new(a, vm.inputs[0]); L.new(b, vm.inputs[1])
    return vm.outputs[0]


def _ramp(nt, fac, stops):
    N, L = nt.nodes, nt.links
    cr = N.new('ShaderNodeValToRGB')
    els = cr.color_ramp.elements
    els[0].position, els[0].color = stops[0][0], (*stops[0][1], 1)
    els[1].position, els[1].color = stops[-1][0], (*stops[-1][1], 1)
    for p, c in stops[1:-1]:
        e = els.new(p); e.color = (*c, 1)
    L.new(fac, cr.inputs['Fac'])
    return cr.outputs['Color']


def _noise(nt, vec, scale=1.0, detail=4.0, rough=0.5):
    N, L = nt.nodes, nt.links
    nz = N.new('ShaderNodeTexNoise')
    nz.inputs['Scale'].default_value = scale
    nz.inputs['Detail'].default_value = detail
    nz.inputs['Roughness'].default_value = rough
    L.new(vec, nz.inputs['Vector'])
    return nz.outputs['Fac']


def _bump(nt, b, height, strength=0.3, dist=0.01, invert=False):
    N, L = nt.nodes, nt.links
    bp = N.new('ShaderNodeBump')
    bp.inputs['Strength'].default_value = strength
    bp.inputs['Distance'].default_value = dist
    bp.invert = invert
    L.new(height, bp.inputs['Height'])
    L.new(bp.outputs['Normal'], b.inputs['Normal'])


def wood_planks(name, c1, c2, mortar, plank_w=0.42, plank_l=4.5, rot=90, rough=0.32, grain=0.35):
    m, nt, b = principled(name, c1, rough=rough)
    N, L = nt.nodes, nt.links
    vec = _geo_map(nt, rot_z=rot)
    br = N.new('ShaderNodeTexBrick')
    br.offset = 0.5; br.offset_frequency = 2
    br.inputs['Color1'].default_value = (*c1, 1)
    br.inputs['Color2'].default_value = (*c2, 1)
    br.inputs['Mortar'].default_value = (*mortar, 1)
    br.inputs['Scale'].default_value = 1.0
    br.inputs['Mortar Size'].default_value = 0.006
    br.inputs['Bias'].default_value = 0.0
    br.inputs['Brick Width'].default_value = plank_l
    br.inputs['Row Height'].default_value = plank_w
    L.new(vec, br.inputs['Vector'])
    gv = _scale_vec(nt, vec, (0.35, 9.0, 1.0))
    g = _noise(nt, gv, scale=3.0, detail=4, rough=0.6)
    gr = _ramp(nt, g, [(0.25, (1 - grain, 1 - grain, 1 - grain)), (0.75, (1.0, 1.0, 1.0))])
    col = _vmul(nt, br.outputs['Color'], gr)
    L.new(col, b.inputs['Base Color'])
    _bump(nt, b, br.outputs['Fac'], strength=0.35, dist=0.004, invert=True)
    return m


def tiles(name, c1, c2, mortar, w=2.0, h=2.0, offset=0.0, rough=0.3, vein=False, rot=0, mortar_size=0.008, plane='xy',
          noise_amt=0.06):
    m, nt, b = principled(name, c1, rough=rough)
    N, L = nt.nodes, nt.links
    vec = _geo_map(nt, rot_z=rot, loc=(0.37, 0.21, 0))
    if plane != 'xy':
        sep = nt.nodes.new('ShaderNodeSeparateXYZ')
        com = nt.nodes.new('ShaderNodeCombineXYZ')
        nt.links.new(vec, sep.inputs[0])
        nt.links.new(sep.outputs['Y' if plane == 'yz' else 'X'], com.inputs['X'])
        nt.links.new(sep.outputs['Z'], com.inputs['Y'])
        vec = com.outputs[0]
    br = N.new('ShaderNodeTexBrick')
    br.offset = offset; br.offset_frequency = 2
    br.inputs['Color1'].default_value = (*c1, 1)
    br.inputs['Color2'].default_value = (*c2, 1)
    br.inputs['Mortar'].default_value = (*mortar, 1)
    br.inputs['Scale'].default_value = 1.0
    br.inputs['Mortar Size'].default_value = mortar_size
    br.inputs['Brick Width'].default_value = w
    br.inputs['Row Height'].default_value = h
    L.new(vec, br.inputs['Vector'])
    col = br.outputs['Color']
    nzf = _noise(nt, vec, scale=0.8, detail=3, rough=0.55)
    nzc = _ramp(nt, nzf, [(0.3, (1 - noise_amt,) * 3), (0.7, (1.0, 1.0, 1.0))])
    col = _vmul(nt, col, nzc)
    if vein:
        wv = N.new('ShaderNodeTexWave')
        wv.wave_type = 'BANDS'; wv.bands_direction = 'DIAGONAL'
        wv.inputs['Scale'].default_value = 0.45
        wv.inputs['Distortion'].default_value = 9.0
        wv.inputs['Detail'].default_value = 3.0
        wv.inputs['Detail Scale'].default_value = 1.2
        L.new(vec, wv.inputs['Vector'])
        vr = _ramp(nt, wv.outputs['Fac'], [(0.0, (0.78, 0.78, 0.79)), (0.035, (1, 1, 1)), (1.0, (1, 1, 1))])
        col = _vmul(nt, col, vr)
    L.new(col, b.inputs['Base Color'])
    _bump(nt, b, br.outputs['Fac'], strength=0.4, dist=0.004, invert=True)
    return m


def fabric(name, color, rough=0.95, sheen=0.35, bump=0.15):
    m, nt, b = principled(name, color, rough=rough, sheen=sheen, spec=0.3)
    vec = _geo_map(nt)
    if bump > 0 and False:
        nz = _noise(nt, vec, scale=180.0, detail=2, rough=0.5)
        _bump(nt, b, nz, strength=bump, dist=0.002)
    return m


def wood_solid(name, c1, c2, rough=0.4, rot=0, scale=(0.25, 12, 1)):
    m, nt, b = principled(name, c1, rough=rough, coat=0.15)
    vec = _geo_map(nt, rot_z=rot)
    gv = _scale_vec(nt, vec, scale)
    g = _noise(nt, gv, scale=2.5, detail=4, rough=0.62)
    col = _ramp(nt, g, [(0.3, c2), (0.7, c1)])
    nt.links.new(col, b.inputs['Base Color'])
    return m


def siding(name, color):
    m, nt, b = principled(name, color, rough=0.75)
    N, L = nt.nodes, nt.links
    vec = _geo_map(nt)
    wv = N.new('ShaderNodeTexWave')
    wv.wave_type = 'BANDS'; wv.bands_direction = 'Z'; wv.wave_profile = 'SAW'
    wv.inputs['Scale'].default_value = 0.54
    wv.inputs['Distortion'].default_value = 0.0
    wv.inputs['Detail'].default_value = 0.0
    L.new(vec, wv.inputs['Vector'])
    _bump(nt, b, wv.outputs['Fac'], strength=0.25, dist=0.02)
    return m


def stucco(name, color, rough=0.9):
    m, nt, b = principled(name, color, rough=rough)
    vec = _geo_map(nt)
    nz = _noise(nt, vec, scale=6.0, detail=3, rough=0.7)
    c = _ramp(nt, nz, [(0.3, tuple(x * 0.9 for x in color)), (0.7, color)])
    nt.links.new(c, b.inputs['Base Color'])
    _bump(nt, b, nz, strength=0.15, dist=0.02)
    return m


def glass(name='glass'):
    m = bpy.data.materials.new(name)
    try:
        m.use_nodes = True
    except Exception:
        pass
    MATS[name] = m
    nt = m.node_tree
    N, L = nt.nodes, nt.links
    for n in list(N):
        N.remove(n)
    out = N.new('ShaderNodeOutputMaterial')
    gb = N.new('ShaderNodeBsdfPrincipled')
    gb.inputs['Base Color'].default_value = (0.86, 0.92, 0.94, 1)
    gb.inputs['Roughness'].default_value = 0.0
    gb.inputs['Transmission Weight'].default_value = 1.0
    gb.inputs['IOR'].default_value = 1.45
    try:
        gb.inputs['Thin Wall'].default_value = True
    except Exception:
        pass
    tr = N.new('ShaderNodeBsdfTransparent')
    lp = N.new('ShaderNodeLightPath')
    mx = N.new('ShaderNodeMixShader')
    L.new(lp.outputs['Is Shadow Ray'], mx.inputs['Fac'])
    L.new(gb.outputs[0], mx.inputs[1])
    L.new(tr.outputs[0], mx.inputs[2])
    L.new(mx.outputs[0], out.inputs['Surface'])
    m.diffuse_color = (0.7, 0.8, 0.85, 0.3)
    return m


def make_materials():
    principled('wall', (0.86, 0.85, 0.82), rough=0.9, spec=0.3)
    principled('cap', (0.05, 0.05, 0.055), rough=0.85, spec=0.2)
    siding('ext', (0.74, 0.74, 0.72))
    stucco('found', (0.46, 0.45, 0.43))
    principled('trim', (0.9, 0.9, 0.88), rough=0.35)
    principled('door', (0.91, 0.91, 0.89), rough=0.32)
    principled('cab', (0.9, 0.9, 0.88), rough=0.3)
    principled('cab_in', (0.75, 0.74, 0.72), rough=0.6)
    principled('quartz', (0.88, 0.88, 0.86), rough=0.12, spec=0.6)
    tiles('marble_ct', (0.94, 0.94, 0.93), (0.92, 0.92, 0.91), (0.94, 0.94, 0.93), w=200, h=200, rough=0.08,
          vein=True, mortar_size=0.0)
    principled('steel', (0.78, 0.78, 0.78), rough=0.22, metal=1.0)
    principled('nickel', (0.82, 0.8, 0.77), rough=0.18, metal=1.0)
    principled('brass', (0.83, 0.62, 0.32), rough=0.28, metal=1.0)
    principled('blackm', (0.03, 0.03, 0.03), rough=0.35, metal=0.6)
    principled('black_glass', (0.01, 0.01, 0.012), rough=0.04, spec=0.8)
    principled('cast_iron', (0.025, 0.025, 0.025), rough=0.55, metal=0.4)
    principled('ceramic', (0.93, 0.93, 0.92), rough=0.04, spec=0.7)
    principled('mirror', (0.95, 0.95, 0.95), rough=0.01, metal=1.0)
    principled('frame', (0.05, 0.05, 0.05), rough=0.4)
    m, nt, b = principled('ground', (0.20, 0.30, 0.12), rough=0.95, spec=0.25)
    vec = _geo_map(nt)
    n1 = _noise(nt, vec, scale=0.08, detail=3, rough=0.6)
    c = _ramp(nt, n1, [(0.3, (0.16, 0.25, 0.09)), (0.5, (0.22, 0.32, 0.12)), (0.7, (0.27, 0.35, 0.15))])
    n2 = _noise(nt, vec, scale=25.0, detail=2, rough=0.5)
    c2 = _ramp(nt, n2, [(0.3, (0.8, 0.8, 0.8)), (0.7, (1.0, 1.0, 1.0))])
    nt.links.new(_vmul(nt, c, c2), b.inputs['Base Color'])

    principled('concrete', (0.42, 0.42, 0.41), rough=0.95)
    principled('bulb', (1, 1, 1), rough=0.5)
    glass()
    wood_planks('oak', (0.56, 0.38, 0.22), (0.68, 0.49, 0.30), (0.2, 0.13, 0.08))
    wood_planks('oak_tread', (0.5, 0.33, 0.19), (0.6, 0.42, 0.25), (0.5, 0.33, 0.19), plank_w=50, plank_l=50, rot=0)
    tiles('tile', (0.55, 0.53, 0.49), (0.51, 0.49, 0.455), (0.40, 0.385, 0.36), w=2.0, h=2.0, offset=0.0, rough=0.28)
    tiles('marble', (0.92, 0.92, 0.91), (0.88, 0.88, 0.87), (0.72, 0.72, 0.71), w=2.0, h=2.0, rough=0.06,
          vein=True)
    tiles('slate', (0.24, 0.25, 0.26), (0.30, 0.31, 0.32), (0.18, 0.18, 0.18), w=1.5, h=1.5, rough=0.7,
          offset=0.5)
    tiles('paver', (0.42, 0.45, 0.48), (0.50, 0.52, 0.53), (0.33, 0.33, 0.33), w=2.0, h=1.33, rough=0.8,
          offset=0.5)
    for pl in ('yz', 'xz'):
        tiles('subway_' + pl, (0.94, 0.94, 0.93), (0.92, 0.92, 0.91), (0.78, 0.78, 0.77), w=0.5, h=0.25,
              rough=0.06, offset=0.5, mortar_size=0.012, noise_amt=0.02, plane=pl)
    fabric('sofa', (0.53, 0.50, 0.45))
    fabric('sofa_dark', (0.30, 0.31, 0.33))
    fabric('chair', (0.80, 0.76, 0.68))
    fabric('cushion_acc', (0.62, 0.42, 0.28))
    principled('leather', (0.06, 0.045, 0.035), rough=0.45, coat=0.1)
    wood_solid('walnut', (0.28, 0.16, 0.09), (0.18, 0.10, 0.06))
    wood_solid('oakwood', (0.62, 0.45, 0.28), (0.5, 0.35, 0.2))
    wood_solid('rail_wood', (0.30, 0.18, 0.10), (0.22, 0.12, 0.07))
    wood_solid('front_door', (0.20, 0.11, 0.06), (0.13, 0.07, 0.04))
    principled('island', (0.10, 0.15, 0.15), rough=0.35)
    principled('appliance_dark', (0.04, 0.04, 0.04), rough=0.3)
