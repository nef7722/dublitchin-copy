import sys, os, math, argparse, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
from mathutils import Vector, Matrix

ap = argparse.ArgumentParser()
ap.add_argument('--view', default='persp')
ap.add_argument('--res', type=int, default=1000)
ap.add_argument('--samples', type=int, default=24)
ap.add_argument('--out', default='out/test.png')
ap.add_argument('--no-interior', action='store_true')
ap.add_argument('--save', default='')
ap.add_argument('--el', type=float, default=52.0)
ap.add_argument('--az', type=float, default=0.0)
ap.add_argument('--dist', type=float, default=92.0)
ap.add_argument('--lens', type=float, default=35.0)
ap.add_argument('--aspect', type=float, default=1.25)
ap.add_argument('--tx', type=float, default=21.0)
ap.add_argument('--ty', type=float, default=29.0)
ap.add_argument('--tz', type=float, default=-1.0)
ap.add_argument('--crop', default='')
ap.add_argument('--sun', type=float, default=2.4)
ap.add_argument('--sun_el', type=float, default=52.0)
ap.add_argument('--sun_az', type=float, default=-38.0)
ap.add_argument('--exp', type=float, default=-0.35)
ap.add_argument('--eye', default='')
ap.add_argument('--outdir', default='out/pano')
ap.add_argument('--sky', type=float, default=0.25)
ap.add_argument('--dl', type=float, default=55.0)
ap.add_argument('--adapt', type=float, default=0.05)
args = ap.parse_args(sys.argv[1:])

t0 = time.time()
if args.eye:
    os.environ['FP_H'] = '9.0'
    os.environ['FP_EYE'] = '1'
bpy.ops.wm.read_factory_settings(use_empty=True)
import lib, arch, house
lib.make_materials()
scene = bpy.context.scene
coll = scene.collection
arch.builders()
house.build_shell(coll)
if not args.no_interior:
    import interior
    interior.build_interior(coll)
if args.eye:
    import eye
    eye.build_eye(coll)
    for o in bpy.data.objects:
        if o.type == 'LIGHT' and o.name.startswith('dl'):
            o.data.energy = args.dl
objs = {}
for b in list(lib.MB.all):
    objs[b.name] = b.finish(coll)
if not args.no_interior and objs.get('countertops') is not None:
    interior.apply_cuts(objs['countertops'], coll)
print('built in %.1fs' % (time.time() - t0))

# ------------------------------------------------------------ world & light
world = bpy.data.worlds.new('world')
scene.world = world
try:
    world.use_nodes = True
except Exception:
    pass
bg = world.node_tree.nodes['Background']
bg.inputs['Color'].default_value = (0.80, 0.86, 0.96, 1)
bg.inputs['Strength'].default_value = 0.8

sun_d = bpy.data.lights.new('sun', 'SUN')
sun_d.energy = args.sun
sun_d.angle = math.radians(4.0)
sun_d.color = (1.0, 0.96, 0.9)
sun = bpy.data.objects.new('sun', sun_d)
coll.objects.link(sun)
sun.rotation_euler = (math.radians(90 - args.sun_el), 0, math.radians(args.sun_az))
if args.eye:
    N, L = world.node_tree.nodes, world.node_tree.links
    sky = N.new('ShaderNodeTexSky')
    sky.sky_type = 'MULTIPLE_SCATTERING'
    try:
        sky.sun_disc = False
    except Exception:
        pass
    sky.sun_elevation = math.radians(args.sun_el)
    sky.sun_rotation = math.radians(180 - args.sun_az)
    L.new(sky.outputs['Color'], bg.inputs['Color'])
    bg.inputs['Strength'].default_value = args.sky

# ------------------------------------------------------------ camera
cam_d = bpy.data.cameras.new('cam')
cam = bpy.data.objects.new('cam', cam_d)
coll.objects.link(cam)
scene.camera = cam
target = Vector((args.tx, -args.ty, args.tz))
if args.eye:
    cam_d.type = 'PANO'
    cam_d.panorama_type = 'EQUIRECTANGULAR'
    cam_d.clip_start = 0.05
    cam_d.clip_end = 2000
    cam.rotation_euler = (math.pi / 2, 0, 0)
    rx = args.res
    ry = args.res // 2
elif args.view == 'top':
    cam_d.type = 'ORTHO'
    cam_d.ortho_scale = 64.0
    cam.location = Vector((21.3, -28.9, 120))
    cam.rotation_euler = (0, 0, 0)
    cam_d.clip_end = 1000
    rx = args.res
    ry = int(args.res * 1.25)
else:
    el = math.radians(args.el)
    az = math.radians(args.az)
    d = args.dist
    off = Vector((d * math.cos(el) * math.sin(az), -d * math.cos(el) * math.cos(az), d * math.sin(el)))
    cam.location = target + off
    q = (target - cam.location).to_track_quat('-Z', 'Y')
    cam.rotation_euler = q.to_euler()
    cam_d.lens = args.lens
    cam_d.sensor_width = 36
    cam_d.clip_end = 2000
    rx = args.res
    ry = int(args.res / args.aspect)

r = scene.render
r.engine = 'CYCLES'
r.resolution_x = rx
r.resolution_y = ry
r.resolution_percentage = 100
r.image_settings.file_format = 'PNG'
r.film_transparent = False
if args.crop:
    x0, y0, x1, y1 = [float(v) for v in args.crop.split(',')]
    r.use_border = True
    r.use_crop_to_border = True
    r.border_min_x, r.border_min_y, r.border_max_x, r.border_max_y = x0, y0, x1, y1
c = scene.cycles
c.device = 'CPU'
c.samples = args.samples
c.use_adaptive_sampling = True
c.adaptive_threshold = 0.02
c.use_denoising = True
try:
    c.denoiser = 'OPENIMAGEDENOISE'
except Exception:
    pass
c.max_bounces = 8
c.diffuse_bounces = 4
c.glossy_bounces = 3
c.transmission_bounces = 6
c.transparent_max_bounces = 8
c.caustics_reflective = False
c.caustics_refractive = False
c.sample_clamp_indirect = 8.0
r.threads_mode = 'FIXED'
r.threads = os.cpu_count()
scene.view_settings.view_transform = 'AgX'
scene.view_settings.look = 'AgX - Medium High Contrast'
scene.view_settings.exposure = args.exp
if args.eye:
    c.adaptive_threshold = args.adapt
    c.max_bounces = 6
    c.diffuse_bounces = 3
    c.glossy_bounces = 2
    c.transmission_bounces = 4
    c.transparent_max_bounces = 4
    c.sample_clamp_indirect = 4.0
    c.use_light_tree = True
    c.denoising_input_passes = 'RGB_ALBEDO_NORMAL'
    c.denoising_prefilter = 'ACCURATE'

if args.save:
    bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(args.save))
if args.eye:
    import eye
    ids = list(eye.STATIONS) if args.eye == 'all' else args.eye.split(',')
    os.makedirs(args.outdir, exist_ok=True)
    for sid in ids:
        x, y, z, he, en = eye.STATIONS[sid]
        cam.location = Vector((x, -y, z + eye.EYE))
        r.filepath = os.path.abspath(os.path.join(args.outdir, sid + '.png'))
        t1 = time.time()
        bpy.ops.render.render(write_still=True)
        print('rendered %s in %.1fs' % (sid, time.time() - t1), flush=True)
else:
    r.filepath = os.path.abspath(args.out)
    t1 = time.time()
    bpy.ops.render.render(write_still=True)
    print('rendered in %.1fs -> %s' % (time.time() - t1, r.filepath))
