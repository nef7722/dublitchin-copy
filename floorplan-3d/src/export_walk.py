# Build the eye-level house, bake a lighting map (Cycles) and export a GLB + walk/height maps for the web walkthrough.
import sys, os, math, time, json, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ['FP_H'] = '9.0'
os.environ['FP_EYE'] = '1'
os.environ['FP_NOBEVEL'] = '1'
os.environ['FP_WALK'] = '1'
import bpy, bmesh
import numpy as np
from mathutils import Vector

ap = argparse.ArgumentParser()
ap.add_argument('--out', default='out/walk')
ap.add_argument('--lm', type=int, default=2048)
ap.add_argument('--samples', type=int, default=64)
ap.add_argument('--nobake', action='store_true')
ap.add_argument('--dl', type=float, default=55.0)
args = ap.parse_args(sys.argv[1:])
os.makedirs(args.out, exist_ok=True)
t0 = time.time()

bpy.ops.wm.read_factory_settings(use_empty=True)
import lib
lib.MB.REC = []
import arch, house, interior, eye
lib.make_materials()
scene = bpy.context.scene
coll = scene.collection
arch.builders()
house.build_shell(coll)
interior.build_interior(coll)
eye.build_eye(coll)
objs = {}
for b in list(lib.MB.all):
    objs[b.name] = b.finish(coll)
interior.apply_cuts(objs['countertops'], coll)
for o in bpy.data.objects:
    if o.type == 'LIGHT' and o.name.startswith('dl'):
        o.data.energy = args.dl
print('built %.1fs, records %d' % (time.time() - t0, len(lib.MB.REC)), flush=True)

# ------------------------------------------------------------------ walk + height maps
GX0, GY0, GX1, GY1, RES = -10.0, -8.0, 56.0, 66.0, 0.1   # plan-coordinate bounds (ft) and cell size
nx, ny = int((GX1 - GX0) / RES), int((GY1 - GY0) / RES)
xs = GX0 + (np.arange(nx) + 0.5) * RES
ys = GY0 + (np.arange(ny) + 0.5) * RES
height = np.full((ny, nx), -100.0, dtype=np.float32)       # walkable top surface (filled below)
WALK_B = {'floors', 'stairs', 'porch'}
WALK_M = {'oak', 'tile', 'marble', 'slate', 'oak_tread', 'paver'}
OBST_SKIP = {'ground', 'downlights', 'floors'}


def cells(poly):
    """Boolean mask of grid cells inside a convex polygon given in world XY."""
    P = np.array([(x, -y) for x, y in poly])   # -> plan coords
    x0, y0 = P.min(0); x1, y1 = P.max(0)
    i0 = max(0, int((x0 - GX0) / RES)); i1 = min(nx, int(math.ceil((x1 - GX0) / RES)))
    j0 = max(0, int((y0 - GY0) / RES)); j1 = min(ny, int(math.ceil((y1 - GY0) / RES)))
    if i1 <= i0 or j1 <= j0:
        return None
    X, Y = np.meshgrid(xs[i0:i1], ys[j0:j1])
    # convex hull of the points
    pts = sorted(set((round(p[0], 4), round(p[1], 4)) for p in P))
    if len(pts) < 3:
        return None

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lower, upper = [], []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    hull = lower[:-1] + upper[:-1]
    if len(hull) < 3:
        return None
    inside = np.ones(X.shape, bool)
    n = len(hull)
    for k in range(n):
        a, b = hull[k], hull[(k + 1) % n]
        inside &= ((b[0] - a[0]) * (Y - a[1]) - (b[1] - a[1]) * (X - a[0])) >= -1e-9
    return (slice(j0, j1), slice(i0, i1), inside)


recs = lib.MB.REC
for (bn, m, poly, z0, z1) in recs:
    if bn in WALK_B and m in WALK_M:
        c = cells(poly)
        if c is None:
            continue
        sj, si, ins = c
        sub = height[sj, si]
        sub[ins] = np.maximum(sub[ins], z1)
        height[sj, si] = sub
nosurf = height < -50
height[nosurf] = arch.G                                     # lawn
blocked = np.zeros((ny, nx), bool)
for (bn, m, poly, z0, z1) in recs:
    if bn in OBST_SKIP or bn.startswith('cut') or bn.startswith('ctcut'):
        continue
    if bn in WALK_B and m in WALK_M:
        continue
    if z1 - z0 < 0.05:
        continue
    c = cells(poly)
    if c is None:
        continue
    sj, si, ins = c
    h = height[sj, si]
    if bn == 'foundation_block':
        continue
    else:
        hit = ins & (z1 > h + 0.45) & (z0 < h + 5.6)
    blocked[sj, si] |= hit
# the house body (concave footprint) blocks lawn cells under it; stair wells have their own tread heights
FPP = house.FOOT
XX, YY = np.meshgrid(xs, ys)
insideF = np.zeros((ny, nx), bool)
for k in range(len(FPP)):
    x1, y1 = FPP[k]; x2, y2 = FPP[(k + 1) % len(FPP)]
    if y1 == y2:
        continue
    cond = (y1 > YY) != (y2 > YY)
    xint = (x2 - x1) * (YY - y1) / (y2 - y1) + x1
    insideF ^= cond & (XX < xint)
blocked |= insideF & nosurf
# keep visitors near the house outside
yy, xx = np.meshgrid(ys, xs, indexing='ij')
far = (xx < -6) | (xx > 52) | (yy < -4) | (yy > 62)
blocked |= far
np.save(os.path.join(args.out, 'height.npy'), height)
np.save(os.path.join(args.out, 'blocked.npy'), blocked)
json.dump({'x0': GX0, 'y0': GY0, 'res': RES, 'nx': nx, 'ny': ny, 'zmin': -10.0, 'zmax': 1.0},
          open(os.path.join(args.out, 'grid.json'), 'w'))
print('maps %.1fs' % (time.time() - t0), flush=True)

# ------------------------------------------------------------------ prepare meshes
view = bpy.context.view_layer


def desel():
    for ob_ in bpy.data.objects:
        try:
            ob_.select_set(False)
        except Exception:
            pass

for o in list(bpy.data.objects):
    if o.name.startswith('cut') or o.name.startswith('ctcut'):
        continue
    if o.type in ('MESH', 'CURVE') and (o.modifiers or o.type == 'CURVE'):
        desel()
        view.objects.active = o
        o.select_set(True)
        bpy.ops.object.convert(target='MESH')
for o in list(bpy.data.objects):
    if o.name.startswith('cut') or o.name.startswith('ctcut'):
        bpy.data.objects.remove(o, do_unlink=True)
ground = bpy.data.objects['ground']
meshes = [o for o in bpy.data.objects if o.type == 'MESH' and o is not ground]
desel()
for o in meshes:
    o.select_set(True)
view.objects.active = meshes[0]
bpy.ops.object.join()
house_ob = view.objects.active
house_ob.name = 'house'
me = house_ob.data
print('joined: verts %d faces %d (%.1fs)' % (len(me.vertices), len(me.polygons), time.time() - t0), flush=True)

# drop faces that can never be seen: the underside of the foundation and of floor slabs
bm = bmesh.new()
bm.from_mesh(me)
bm.normal_update()
GL = arch.G - 0.05
bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=(0, 0, GL), plane_no=(0, 0, 1))
bm.normal_update()
FP = house.FOOT


def in_foot(x, y):
    c = False
    n = len(FP)
    for i in range(n):
        x1, y1 = FP[i]; x2, y2 = FP[(i + 1) % n]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            c = not c
    return c


kill = []
for f in bm.faces:
    n = f.normal
    c = f.calc_center_median()
    if n.z < -0.9 and (c.z < 0.05):
        kill.append(f)                       # undersides resting on floors / slabs / below grade
    elif n.z > 0.9 and (abs(c.z - 9.0) < 0.02 or c.z > 9.3 or abs(c.z + 0.05) < 0.012):
        kill.append(f)                       # wall tops under the ceiling, roof tops, slab top under floors
    elif c.z < GL and abs(n.z) < 0.3:
        p = c + n * 0.25
        if not in_foot(p.x, -p.y):
            kill.append(f)                   # outside faces below the lawn
bmesh.ops.delete(bm, geom=kill, context='FACES')
print('removed hidden faces: %d' % len(kill), flush=True)
# planar world UVs (feet) for the procedural surface textures (drop any UV layers that came with joined curves)
for _l in list(bm.loops.layers.uv):
    bm.loops.layers.uv.remove(_l)
uv0 = bm.loops.layers.uv.new('UVMap')
for f in bm.faces:
    n = f.normal
    ax, ay, az = abs(n.x), abs(n.y), abs(n.z)
    for l in f.loops:
        co = l.vert.co
        if az >= ax and az >= ay:
            l[uv0].uv = (co.x, co.y)
        elif ax >= ay:
            l[uv0].uv = (co.y if n.x > 0 else -co.y, co.z)
        else:
            l[uv0].uv = (-co.x if n.y > 0 else co.x, co.z)
bm.to_mesh(me)
bm.free()
area = sum(p.area for p in me.polygons)
print('area %.0f sq ft' % area, flush=True)

lm_uv = me.uv_layers.new(name='LM')
me.uv_layers.active = lm_uv
desel()
house_ob.select_set(True)
view.objects.active = house_ob
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.smart_project(angle_limit=math.radians(60), island_margin=0.0015, area_weight=0.0, scale_to_bounds=False)
bpy.ops.object.mode_set(mode='OBJECT')
print('lightmap uv %.1fs' % (time.time() - t0), flush=True)

# ------------------------------------------------------------------ bake lighting
world = bpy.data.worlds.new('world')
scene.world = world
world.use_nodes = True
bg = world.node_tree.nodes['Background']
sky = world.node_tree.nodes.new('ShaderNodeTexSky')
sky.sky_type = 'MULTIPLE_SCATTERING'
try:
    sky.sun_disc = False
except Exception:
    pass
sky.sun_elevation = math.radians(52)
sky.sun_rotation = math.radians(180 + 38)
world.node_tree.links.new(sky.outputs['Color'], bg.inputs['Color'])
bg.inputs['Strength'].default_value = 0.25
sun_d = bpy.data.lights.new('sun', 'SUN')
sun_d.energy = 2.4
sun_d.angle = math.radians(4.0)
sun_d.color = (1.0, 0.96, 0.9)
sun = bpy.data.objects.new('sun', sun_d)
coll.objects.link(sun)
sun.rotation_euler = (math.radians(38), 0, math.radians(-38))

if not args.nobake:
    img = bpy.data.images.new('lightmap', args.lm, args.lm, float_buffer=True, alpha=False)
    for mat in me.materials:
        nt = mat.node_tree
        n = nt.nodes.new('ShaderNodeTexImage')
        n.image = img
        nt.nodes.active = n
    scene.render.engine = 'CYCLES'
    c = scene.cycles
    c.device = 'CPU'
    c.samples = args.samples
    c.use_denoising = False
    c.max_bounces = 6
    c.diffuse_bounces = 3
    c.glossy_bounces = 2
    c.transmission_bounces = 4
    c.transparent_max_bounces = 4
    c.sample_clamp_indirect = 4.0
    scene.render.threads_mode = 'FIXED'
    scene.render.threads = os.cpu_count()
    scene.render.bake.margin = 6
    scene.render.bake.use_pass_direct = True
    scene.render.bake.use_pass_indirect = True
    scene.render.bake.use_pass_color = False
    desel()
    house_ob.select_set(True)
    view.objects.active = house_ob
    tb = time.time()
    bpy.ops.object.bake(type='DIFFUSE', pass_filter={'DIRECT', 'INDIRECT'}, margin=6, use_clear=True)
    print('baked in %.1fs' % (time.time() - tb), flush=True)
    px = np.array(img.pixels[:], dtype=np.float32).reshape(args.lm, args.lm, 4)
    np.save(os.path.join(args.out, 'lightmap.npy'), px)
    for mat in me.materials:
        nt = mat.node_tree
        for n in [n for n in nt.nodes if n.type == 'TEX_IMAGE']:
            nt.nodes.remove(n)

# ------------------------------------------------------------------ export
gm = ground.data
if not gm.uv_layers:
    gb = bmesh.new(); gb.from_mesh(gm)
    guv = gb.loops.layers.uv.new('UVMap')
    for f in gb.faces:
        for l in f.loops:
            l[guv].uv = (l.vert.co.x, l.vert.co.y)
    gb.to_mesh(gm); gb.free()
me.uv_layers.active = me.uv_layers['UVMap']
desel()
house_ob.select_set(True)
ground.select_set(True)
mats = sorted(set(m.name for m in me.materials))
json.dump(mats, open(os.path.join(args.out, 'materials.json'), 'w'))
bpy.ops.export_scene.gltf(filepath=os.path.abspath(os.path.join(args.out, 'house.glb')), export_format='GLB',
                          use_selection=True, export_texcoords=True, export_normals=True, export_apply=True,
                          export_materials='EXPORT', export_image_format='NONE', export_yup=True)
print('exported, total %.1fs' % (time.time() - t0), flush=True)
