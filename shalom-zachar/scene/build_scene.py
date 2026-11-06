"""
Shalom Zachar table – photoreal background rendered with Blender/Cycles.

Units: 1 Blender unit = 1 cm.  The camera looks straight down and frames a
48 x 64 cm piece of table (3:4), which maps 1:1 onto the 1200 x 1600 poster
(25 px per cm).  The middle of the table is left empty for the text.

Usage:
    python build_scene.py --out table.png [--preview] [--samples N] [--scale PCT]
"""
import argparse
import math
import random
import sys

import bpy
import bmesh
import numpy as np
from mathutils import Vector, Matrix, Euler, noise

ap = argparse.ArgumentParser()
ap.add_argument('--out', default='table.png')
ap.add_argument('--preview', action='store_true')
ap.add_argument('--samples', type=int, default=128)
ap.add_argument('--scale', type=int, default=200)  # % of 1200x1600
ap.add_argument('--blend', default='')
ap.add_argument('--border', type=float, nargs=4, default=None)  # x0 y0 x1 y1 (0..1, y from bottom)
args = ap.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:])

rng = random.Random(5787)
R = rng.uniform

# ---------------------------------------------------------------- reset
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
col = scene.collection


# ---------------------------------------------------------------- helpers
def srgb(h, a=1.0):
    h = h.lstrip('#')
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(((x + 0.055) / 1.055) ** 2.4 if x > 0.04045 else x / 12.92 for x in c) + (a,)


def new_mat(name):
    m = bpy.data.materials.new(name)
    try:
        m.use_nodes = True
    except Exception:
        pass
    nt = m.node_tree
    b = nt.nodes.get('Principled BSDF')
    if b is None:
        for n in list(nt.nodes):
            nt.nodes.remove(n)
        b = nt.nodes.new('ShaderNodeBsdfPrincipled')
        o = nt.nodes.new('ShaderNodeOutputMaterial')
        nt.links.new(b.outputs[0], o.inputs['Surface'])
    return m, nt, b


def node(nt, t, **kw):
    n = nt.nodes.new(t)
    for k, v in kw.items():
        setattr(n, k, v)
    return n


def link(nt, a, b):
    nt.links.new(a, b)


def ramp(nt, stops):
    n = nt.nodes.new('ShaderNodeValToRGB')
    cr = n.color_ramp
    cr.elements[0].position = stops[0][0]
    cr.elements[0].color = stops[0][1]
    cr.elements[1].position = stops[-1][0]
    cr.elements[1].color = stops[-1][1]
    for p, c in stops[1:-1]:
        e = cr.elements.new(p)
        e.color = c
    return n


def noise_tex(nt, vec, scale, detail=3.0, rough=0.55, distortion=0.0):
    n = nt.nodes.new('ShaderNodeTexNoise')
    n.inputs['Scale'].default_value = scale
    n.inputs['Detail'].default_value = detail
    n.inputs['Roughness'].default_value = rough
    n.inputs['Distortion'].default_value = distortion
    if vec is not None:
        link(nt, vec, n.inputs['Vector'])
    return n


def mapping(nt, vec, scale=(1, 1, 1), loc=(0, 0, 0), rot=(0, 0, 0)):
    n = nt.nodes.new('ShaderNodeMapping')
    n.inputs['Scale'].default_value = scale
    n.inputs['Location'].default_value = loc
    n.inputs['Rotation'].default_value = rot
    link(nt, vec, n.inputs['Vector'])
    return n


def math_node(nt, op, a, b=None, c=None):
    n = nt.nodes.new('ShaderNodeMath')
    n.operation = op
    for i, v in enumerate((a, b, c)):
        if v is None:
            continue
        if isinstance(v, (int, float)):
            n.inputs[i].default_value = v
        else:
            link(nt, v, n.inputs[i])
    return n


def bump(nt, height, strength, distance, normal=None):
    n = nt.nodes.new('ShaderNodeBump')
    n.inputs['Strength'].default_value = strength
    n.inputs['Distance'].default_value = distance
    link(nt, height, n.inputs['Height'])
    if normal is not None:
        link(nt, normal, n.inputs['Normal'])
    return n


def setin(b, name, v):
    if name in b.inputs:
        b.inputs[name].default_value = v


def obj_from_bm(name, bm, mats=(), smooth=True, link_to=col):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    if smooth:
        for p in me.polygons:
            p.use_smooth = True
    for m in mats:
        me.materials.append(m)
    ob = bpy.data.objects.new(name, me)
    if link_to is not None:
        link_to.objects.link(ob)
    return ob


def param_surface(bm, fn, nu, nv, mat=0):
    vs = [[bm.verts.new(fn(i / nu, j / nv)) for j in range(nv + 1)] for i in range(nu + 1)]
    for i in range(nu):
        for j in range(nv):
            try:
                f = bm.faces.new((vs[i][j], vs[i + 1][j], vs[i + 1][j + 1], vs[i][j + 1]))
                f.material_index = mat
            except ValueError:
                pass


def finish(bm, merge=1e-4):
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=merge)
    # drop faces that collapsed at the poles
    bad = [f for f in bm.faces if f.calc_area() < 1e-9]
    if bad:
        bmesh.ops.delete(bm, geom=bad, context='FACES')
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)


def lathe(name, profile, mats, steps=128, subsurf=2):
    bm = bmesh.new()
    vs = [bm.verts.new((r, 0, z)) for r, z in profile]
    es = [bm.edges.new((vs[i], vs[i + 1])) for i in range(len(vs) - 1)]
    bmesh.ops.spin(bm, geom=vs + es, cent=(0, 0, 0), axis=(0, 0, 1), angle=2 * math.pi, steps=steps, use_duplicate=False)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    ob = obj_from_bm(name, bm, mats)
    if subsurf:
        md = ob.modifiers.new('sub', 'SUBSURF')
        md.levels = 1
        md.render_levels = subsurf
    return ob


# ---------------------------------------------------------------- materials
def mat_table():
    m, nt, b = new_mat('table')
    tc = node(nt, 'ShaderNodeTexCoord')
    big = noise_tex(nt, tc.outputs['Object'], 0.045, 10, 0.62)
    mid = noise_tex(nt, tc.outputs['Object'], 0.35, 6, 0.6)
    fine = noise_tex(nt, tc.outputs['Object'], 4.0, 4, 0.5)
    f1 = math_node(nt, 'MULTIPLY_ADD', big.outputs['Fac'], 0.75, math_node(nt, 'MULTIPLY', mid.outputs['Fac'], 0.25).outputs[0])
    cr = ramp(nt, [(0.30, srgb('#120c09')), (0.45, srgb('#241911')), (0.55, srgb('#33241b')), (0.66, srgb('#433024')), (0.78, srgb('#54402f'))])
    link(nt, f1.outputs[0], cr.inputs['Fac'])
    link(nt, cr.outputs['Color'], b.inputs['Base Color'])
    rr = ramp(nt, [(0.3, (0.62, 0.62, 0.62, 1)), (0.7, (0.86, 0.86, 0.86, 1))])
    link(nt, mid.outputs['Fac'], rr.inputs['Fac'])
    link(nt, rr.outputs['Color'], b.inputs['Roughness'])
    h = math_node(nt, 'MULTIPLY_ADD', fine.outputs['Fac'], 0.6, math_node(nt, 'MULTIPLY', mid.outputs['Fac'], 0.4).outputs[0])
    bp = bump(nt, h.outputs[0], 0.35, 0.05)
    link(nt, bp.outputs['Normal'], b.inputs['Normal'])
    setin(b, 'Specular IOR Level', 0.35)
    return m


def mat_wood(name, tones, grain_scale=0.42, seed_loc=(0, 0, 0)):
    m, nt, b = new_mat(name)
    tc = node(nt, 'ShaderNodeTexCoord')
    mp = mapping(nt, tc.outputs['Object'], scale=(0.35, 1.0, 0.35), loc=seed_loc)
    wv = node(nt, 'ShaderNodeTexWave', wave_type='RINGS', rings_direction='Y')
    wv.inputs['Scale'].default_value = grain_scale * 0.32
    wv.inputs['Distortion'].default_value = 5.0
    wv.inputs['Detail'].default_value = 3.0
    wv.inputs['Detail Scale'].default_value = 0.8
    link(nt, mp.outputs['Vector'], wv.inputs['Vector'])
    nz = noise_tex(nt, mp.outputs['Vector'], 0.6, 6, 0.6)
    f = math_node(nt, 'MULTIPLY_ADD', wv.outputs['Fac'], 0.7, math_node(nt, 'MULTIPLY', nz.outputs['Fac'], 0.3).outputs[0])
    cr = ramp(nt, [(0.05, srgb(tones[0])), (0.35, srgb(tones[1])), (0.65, srgb(tones[2])), (0.95, srgb(tones[3]))])
    link(nt, f.outputs[0], cr.inputs['Fac'])
    link(nt, cr.outputs['Color'], b.inputs['Base Color'])
    b.inputs['Roughness'].default_value = 0.55
    setin(b, 'Coat Weight', 0.08)
    setin(b, 'Coat Roughness', 0.35)
    setin(b, 'Specular IOR Level', 0.35)
    pores = noise_tex(nt, mapping(nt, tc.outputs['Object'], scale=(1, 0.08, 1)).outputs['Vector'], 18, 2, 0.5)
    hb = math_node(nt, 'MULTIPLY_ADD', wv.outputs['Fac'], 0.5, math_node(nt, 'MULTIPLY', pores.outputs['Fac'], 0.5).outputs[0])
    bp = bump(nt, hb.outputs[0], 0.18, 0.03)
    link(nt, bp.outputs['Normal'], b.inputs['Normal'])
    return m


def mat_chickpea():
    m, nt, b = new_mat('arbes')
    tc = node(nt, 'ShaderNodeTexCoord')
    oi = node(nt, 'ShaderNodeObjectInfo')
    nz = noise_tex(nt, tc.outputs['Object'], 2.2, 3, 0.5)
    f = math_node(nt, 'MULTIPLY_ADD', nz.outputs['Fac'], 0.5, math_node(nt, 'MULTIPLY', oi.outputs['Random'], 0.5).outputs[0])
    cr = ramp(nt, [(0.15, srgb('#a8742f')), (0.4, srgb('#c38f45')), (0.62, srgb('#d4a75c')), (0.85, srgb('#e1bd78'))])
    link(nt, f.outputs[0], cr.inputs['Fac'])
    link(nt, cr.outputs['Color'], b.inputs['Base Color'])
    b.inputs['Roughness'].default_value = 0.38
    setin(b, 'Subsurface Weight', 0.15)
    setin(b, 'Subsurface Radius', (0.1, 0.05, 0.02))
    setin(b, 'Subsurface Scale', 1.0)
    setin(b, 'Coat Weight', 0.2)
    setin(b, 'Coat Roughness', 0.25)
    wr = noise_tex(nt, tc.outputs['Object'], 9.0, 6, 0.62, 0.4)
    bp = bump(nt, wr.outputs['Fac'], 0.32, 0.025)
    link(nt, bp.outputs['Normal'], b.inputs['Normal'])
    return m


def mat_peanut_shell():
    m, nt, b = new_mat('peanut_shell')
    tc = node(nt, 'ShaderNodeTexCoord')
    oi = node(nt, 'ShaderNodeObjectInfo')
    mp = mapping(nt, tc.outputs['Object'], scale=(1.1, 3.0, 3.0))
    vo = node(nt, 'ShaderNodeTexVoronoi', feature='DISTANCE_TO_EDGE')
    vo.inputs['Scale'].default_value = 1.6
    vo.inputs['Randomness'].default_value = 0.85
    link(nt, mp.outputs['Vector'], vo.inputs['Vector'])
    er = ramp(nt, [(0.0, (0, 0, 0, 1)), (0.045, (1, 1, 1, 1))])
    link(nt, vo.outputs['Distance'], er.inputs['Fac'])
    nz = noise_tex(nt, tc.outputs['Object'], 3.0, 4, 0.55)
    a = math_node(nt, 'MULTIPLY', er.outputs['Color'], 0.25)
    bb = math_node(nt, 'MULTIPLY_ADD', oi.outputs['Random'], 0.3, a.outputs[0])
    c = math_node(nt, 'MULTIPLY_ADD', nz.outputs['Fac'], 0.45, bb.outputs[0])
    cr = ramp(nt, [(0.12, srgb('#6e4a28')), (0.4, srgb('#94693c')), (0.62, srgb('#b48650')), (0.85, srgb('#c99d66'))])
    link(nt, c.outputs[0], cr.inputs['Fac'])
    link(nt, cr.outputs['Color'], b.inputs['Base Color'])
    b.inputs['Roughness'].default_value = 0.82
    fine = noise_tex(nt, tc.outputs['Object'], 14, 4, 0.6)
    h = math_node(nt, 'MULTIPLY_ADD', er.outputs['Color'], 0.8, math_node(nt, 'MULTIPLY', fine.outputs['Fac'], 0.2).outputs[0])
    bp = bump(nt, h.outputs[0], 0.45, 0.04)
    link(nt, bp.outputs['Normal'], b.inputs['Normal'])
    return m


def mat_pistachio_shell():
    m, nt, b = new_mat('pist_shell')
    tc = node(nt, 'ShaderNodeTexCoord')
    oi = node(nt, 'ShaderNodeObjectInfo')
    mp = mapping(nt, tc.outputs['Object'], scale=(1.2, 9, 9))
    st = noise_tex(nt, mp.outputs['Vector'], 1.5, 5, 0.6)
    blot = noise_tex(nt, tc.outputs['Object'], 1.6, 3, 0.5)
    f = math_node(nt, 'MULTIPLY_ADD', oi.outputs['Random'], 0.45, math_node(nt, 'MULTIPLY_ADD', st.outputs['Fac'], 0.3, math_node(nt, 'MULTIPLY', blot.outputs['Fac'], 0.25).outputs[0]).outputs[0])
    cr = ramp(nt, [(0.15, srgb('#8a6a48')), (0.4, srgb('#a68660')), (0.6, srgb('#b99c78')), (0.75, srgb('#b8957f')), (0.9, srgb('#cbb291'))])
    link(nt, f.outputs[0], cr.inputs['Fac'])
    link(nt, cr.outputs['Color'], b.inputs['Base Color'])
    b.inputs['Roughness'].default_value = 0.55
    setin(b, 'Subsurface Weight', 0.1)
    setin(b, 'Subsurface Radius', (0.05, 0.04, 0.03))
    bp = bump(nt, st.outputs['Fac'], 0.25, 0.02)
    link(nt, bp.outputs['Normal'], b.inputs['Normal'])
    return m


def mat_pistachio_kernel():
    m, nt, b = new_mat('pist_kernel')
    tc = node(nt, 'ShaderNodeTexCoord')
    nz = noise_tex(nt, tc.outputs['Object'], 2.5, 5, 0.6, 0.8)
    cr = ramp(nt, [(0.3, srgb('#5d3a4a')), (0.44, srgb('#7a5a4c')), (0.52, srgb('#7f9a34')), (0.66, srgb('#a8bf4c')), (0.8, srgb('#c7d36a'))])
    link(nt, nz.outputs['Fac'], cr.inputs['Fac'])
    link(nt, cr.outputs['Color'], b.inputs['Base Color'])
    b.inputs['Roughness'].default_value = 0.5
    setin(b, 'Subsurface Weight', 0.2)
    setin(b, 'Subsurface Radius', (0.05, 0.08, 0.03))
    return m


def mat_glass(name='glass', tint='#f4faf7', rough=0.0):
    m, nt, b = new_mat(name)
    b.inputs['Base Color'].default_value = srgb(tint)
    b.inputs['Roughness'].default_value = rough
    b.inputs['IOR'].default_value = 1.5
    setin(b, 'Transmission Weight', 1.0)
    return m


def mat_liquid(name, color, absorb, density):
    m, nt, b = new_mat(name)
    b.inputs['Base Color'].default_value = srgb(color)
    b.inputs['Roughness'].default_value = 0.0
    b.inputs['IOR'].default_value = 1.33
    setin(b, 'Transmission Weight', 1.0)
    out = [n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL'][0]
    va = node(nt, 'ShaderNodeVolumeAbsorption')
    va.inputs['Color'].default_value = srgb(absorb)
    va.inputs['Density'].default_value = density
    link(nt, va.outputs[0], out.inputs['Volume'])
    return m


def mat_foam():
    m, nt, b = new_mat('foam')
    tc = node(nt, 'ShaderNodeTexCoord')
    hs = []
    for sc, w in ((6.0, 0.5), (2.6, 0.5)):
        v = node(nt, 'ShaderNodeTexVoronoi', feature='SMOOTH_F1')
        v.inputs['Scale'].default_value = sc
        if 'Smoothness' in v.inputs:
            v.inputs['Smoothness'].default_value = 0.15
        link(nt, tc.outputs['Object'], v.inputs['Vector'])
        r_ = ramp(nt, [(0.0, (1, 1, 1, 1)), (0.62, (0, 0, 0, 1))])
        link(nt, v.outputs['Distance'], r_.inputs['Fac'])
        hs.append((r_.outputs['Color'], w))
    h = math_node(nt, 'MULTIPLY', hs[0][0], hs[0][1])
    for out, w in hs[1:]:
        h = math_node(nt, 'MULTIPLY_ADD', out, w, h.outputs[0])
    nz = noise_tex(nt, tc.outputs['Object'], 0.7, 3, 0.5)
    f = math_node(nt, 'MULTIPLY_ADD', nz.outputs['Fac'], 0.35, math_node(nt, 'MULTIPLY', h.outputs[0], 0.65).outputs[0])
    cr = ramp(nt, [(0.1, srgb('#d2bc94')), (0.4, srgb('#e9dcc2')), (0.65, srgb('#f3ebdc')), (0.9, srgb('#f9f4ea'))])
    link(nt, f.outputs[0], cr.inputs['Fac'])
    link(nt, cr.outputs['Color'], b.inputs['Base Color'])
    b.inputs['Roughness'].default_value = 0.35
    setin(b, 'Subsurface Weight', 0.5)
    setin(b, 'Subsurface Radius', (0.2, 0.16, 0.1))
    setin(b, 'Subsurface Scale', 1.0)
    bp = bump(nt, h.outputs[0], 0.35, 0.05)
    link(nt, bp.outputs['Normal'], b.inputs['Normal'])
    return m


def mat_glow(name, color, strength):
    """soft elliptical decal that emits light – stands in for the caustic a glass of whisky throws."""
    m, nt, b = new_mat(name)
    tc = node(nt, 'ShaderNodeTexCoord')
    mp = mapping(nt, tc.outputs['Generated'], scale=(2, 2, 1), loc=(-1, -1, 0))
    gr = node(nt, 'ShaderNodeTexGradient', gradient_type='SPHERICAL')
    link(nt, mp.outputs['Vector'], gr.inputs['Vector'])
    fr = ramp(nt, [(0.0, (0, 0, 0, 1)), (0.55, (0.35, 0.35, 0.35, 1)), (1.0, (1, 1, 1, 1))])
    link(nt, gr.outputs['Fac'], fr.inputs['Fac'])
    b.inputs['Base Color'].default_value = srgb(color)
    setin(b, 'Emission Color', srgb(color))
    em = math_node(nt, 'MULTIPLY', fr.outputs['Color'], strength)
    link(nt, em.outputs[0], b.inputs['Emission Strength'])
    link(nt, fr.outputs['Color'], b.inputs['Alpha'])
    return m


def mat_ceramic():
    m, nt, b = new_mat('ceramic')
    tc = node(nt, 'ShaderNodeTexCoord')
    nz = noise_tex(nt, tc.outputs['Object'], 0.8, 4, 0.5)
    cr = ramp(nt, [(0.35, srgb('#e6dccb')), (0.65, srgb('#f3ece0'))])
    link(nt, nz.outputs['Fac'], cr.inputs['Fac'])
    link(nt, cr.outputs['Color'], b.inputs['Base Color'])
    b.inputs['Roughness'].default_value = 0.18
    setin(b, 'Coat Weight', 0.5)
    setin(b, 'Coat Roughness', 0.05)
    return m


def mat_flat(name, color, rough=0.6):
    m, nt, b = new_mat(name)
    b.inputs['Base Color'].default_value = srgb(color)
    b.inputs['Roughness'].default_value = rough
    return m


M_TABLE = mat_table()
M_WOOD1 = mat_wood('wood1', ['#4a2a15', '#6e4425', '#8c5a32', '#a26c3e'], 0.42, (3, 1, 0))
M_WOOD2 = mat_wood('wood2', ['#42260f', '#633d1f', '#83552d', '#9c6738'], 0.38, (11, 7, 0))
M_WOOD3 = mat_wood('wood3', ['#4d2d17', '#734a29', '#93633a', '#ac7746'], 0.46, (21, 3, 0))
M_ARBES = mat_chickpea()
M_PSHELL = mat_peanut_shell()
M_PIST = mat_pistachio_shell()
M_KERNEL = mat_pistachio_kernel()
M_GLASS = mat_glass()
M_BEER = mat_liquid('beer', '#ffe08a', '#f0b03a', 0.05)
M_WHISKY = mat_liquid('whisky', '#ffd590', '#e0942e', 0.16)
M_GLOW = mat_glow('glow', '#ffb04a', 1.3)
M_FOAM = mat_foam()
M_CERAMIC = mat_ceramic()
M_FILL_ARBES = mat_flat('fill_arbes', '#6b4a22', 0.6)
M_FILL_NUT = mat_flat('fill_nut', '#5a4128', 0.8)
M_FILL_PIST = mat_flat('fill_pist', '#6e5a40', 0.7)
M_PEPPER = mat_flat('pepper', '#17110c', 0.7)
M_SALT = mat_glass('salt', '#ffffff', 0.25)


# ---------------------------------------------------------------- item meshes
def chickpea_mesh(k):
    bm = bmesh.new()
    off = Vector((k * 7.1, k * 3.3, k * 1.7))
    r0 = 0.45 * R(0.94, 1.06)

    def fn(u, v):
        U, V = math.pi * u, 2 * math.pi * v
        d = Vector((math.cos(U), math.sin(U) * math.cos(V), math.sin(U) * math.sin(V)))
        s = 1 + 0.05 * noise.noise(d * 1.6 + off)
        p = d * r0 * s
        p.z *= 0.9
        p.y *= 0.97
        t = max(0.0, d.x - 0.72) / 0.28           # beak
        p.x += 0.11 * t ** 2
        p.y *= 1 - 0.45 * t
        p.z *= 1 - 0.45 * t
        g = math.exp(-(d.y / 0.09) ** 2) * (1.0 if d.z > 0 and d.x > -0.3 else 0.0)  # groove from the beak
        p -= d * 0.03 * g
        return p

    param_surface(bm, fn, 20, 28)
    finish(bm)
    return obj_from_bm(f'pea{k}', bm, [M_ARBES], link_to=None).data


def peanut_mesh(k):
    bm = bmesh.new()
    L, B, C = R(1.45, 1.65), R(0.64, 0.72), R(0.6, 0.66)
    off = Vector((k * 5.3, 2.1, k * 0.7))
    lobe = R(0.9, 0.98)

    def fn(u, v):
        U, V = math.pi * u, 2 * math.pi * v
        x = math.cos(U)
        w = 1 - 0.2 * math.exp(-((x - 0.05) / 0.26) ** 2)
        if x < 0:
            w *= lobe
        w *= 1 + 0.035 * noise.noise(Vector((x * 2, math.cos(V), math.sin(V))) + off)
        X = L * x + 0.1 * max(0.0, x) ** 10
        return Vector((X, B * math.sin(U) * math.cos(V) * w, C * math.sin(U) * math.sin(V) * w))

    param_surface(bm, fn, 30, 24)
    finish(bm)
    return obj_from_bm(f'peanut{k}', bm, [M_PSHELL], link_to=None).data


def pistachio_mesh(k, theta):
    bm = bmesh.new()
    A, B, C = R(1.05, 1.18), R(0.7, 0.78), R(0.6, 0.68)

    def taper(x):
        return 1 - 0.22 * max(0.0, x) ** 2

    for side in (1, -1):
        rot = Matrix.Rotation(-side * theta, 4, 'X')

        def fn(u, v, side=side, rot=rot):
            U, V = math.pi * u, -math.pi / 2 + math.pi * v
            x = math.cos(U)
            tp = taper(x)
            p = Vector((A * x + 0.06 * max(0.0, x) ** 8, side * B * math.sin(U) * math.cos(V) * tp, C * math.sin(U) * math.sin(V) * tp))
            # hinge at the bottom seam
            p = rot @ (p - Vector((0, 0, -C))) + Vector((0, 0, -C))
            return p

        param_surface(bm, fn, 22, 12, mat=0)
    # kernel
    def kf(u, v):
        U, V = math.pi * u, 2 * math.pi * v
        x = math.cos(U)
        tp = taper(x)
        return Vector((A * 0.84 * x, B * 0.8 * math.sin(U) * math.cos(V) * tp, C * 0.84 * math.sin(U) * math.sin(V) * tp + 0.02))

    param_surface(bm, kf, 18, 16, mat=1)
    finish(bm)
    return obj_from_bm(f'pist{k}', bm, [M_PIST, M_KERNEL], link_to=None).data


def pepper_mesh(k):
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=1, radius=R(0.025, 0.05))
    for v in bm.verts:
        v.co *= R(0.6, 1.3)
    return obj_from_bm(f'pep{k}', bm, [M_PEPPER], smooth=False, link_to=None).data


def salt_mesh(k):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=R(0.04, 0.08))
    return obj_from_bm(f'salt{k}', bm, [M_SALT], smooth=False, link_to=None).data


PEAS = [chickpea_mesh(k) for k in range(8)]
PEANUTS = [peanut_mesh(k) for k in range(6)]
PISTS = [pistachio_mesh(k, th) for k, th in enumerate([0.0, 0.07, 0.11, 0.15, 0.19, 0.13, 0.09, 0.0])]
PEPPERS = [pepper_mesh(k) for k in range(4)]
SALTS = [salt_mesh(k) for k in range(3)]

ITEMS = bpy.data.collections.new('items')
col.children.link(ITEMS)


def place(mesh, x, y, z, rot):
    ob = bpy.data.objects.new('it', mesh)
    ob.location = (x, y, z)
    ob.rotation_euler = rot
    ITEMS.objects.link(ob)
    return ob


# item footprint (a, b) and half-height c in cm
SPEC = {
    'pea': (0.47, 0.45, 0.41),
    'peanut': (1.55, 0.68, 0.62),
    'pist': (1.12, 0.74, 0.64),
}


def make_item(kind, x, y, z, yaw):
    if kind == 'pea':
        return place(rng.choice(PEAS), x, y, z, Euler((R(0, 6.28), R(-0.5, 0.5), yaw)))
    if kind == 'peanut':
        return place(rng.choice(PEANUTS), x, y, z, Euler((R(-0.6, 0.6), R(-0.18, 0.18), yaw)))
    if kind == 'pist':
        roll = R(-0.35, 0.35) if rng.random() < 0.8 else R(1.2, 1.6) * rng.choice([-1, 1])
        return place(rng.choice(PISTS), x, y, z, Euler((roll, R(-0.15, 0.15), yaw)))


# ---------------------------------------------------------------- heightfield drop (natural piles, no overlaps)
class HeightField:
    def __init__(self, cx, cy, half, res, base_fn):
        self.cx, self.cy, self.res = cx, cy, res
        n = int(2 * half / res)
        self.x0, self.y0 = cx - half, cy - half
        xs = self.x0 + (np.arange(n) + 0.5) * res
        ys = self.y0 + (np.arange(n) + 0.5) * res
        self.X, self.Y = np.meshgrid(xs, ys)
        self.H = base_fn(self.X - cx, self.Y - cy)
        self.n = n

    def drop(self, x, y, a, b, c, yaw, zmax=40.0):
        rmax = max(a, b)
        i0 = max(0, int((x - rmax - self.x0) / self.res))
        i1 = min(self.n, int((x + rmax - self.x0) / self.res) + 2)
        j0 = max(0, int((y - rmax - self.y0) / self.res))
        j1 = min(self.n, int((y + rmax - self.y0) / self.res) + 2)
        X = self.X[j0:j1, i0:i1] - x
        Y = self.Y[j0:j1, i0:i1] - y
        cs, sn = math.cos(-yaw), math.sin(-yaw)
        u = X * cs - Y * sn
        v = X * sn + Y * cs
        q = 1 - (u / a) ** 2 - (v / b) ** 2
        m = q > 0
        if not m.any():
            return None
        prof = c * np.sqrt(np.clip(q, 0, 1))
        Hs = self.H[j0:j1, i0:i1]
        z = float(np.max(Hs[m] + prof[m] * 0.92))
        if z > zmax:        # would rest too high (on the rim / top of a full pile) -> reject without touching the field
            return None
        Hs[m] = np.maximum(Hs[m], z + prof[m])
        return z

    def height(self, x, y):
        i = int((x - self.x0) / self.res)
        j = int((y - self.y0) / self.res)
        return float(self.H[min(max(j, 0), self.n - 1), min(max(i, 0), self.n - 1)])


# ---------------------------------------------------------------- bowls
WOOD_INNER = [(0, 0.9), (3, 0.92), (5, 1.0), (6.5, 1.5), (7.8, 2.4), (8.7, 3.4), (9.3, 4.4), (9.6, 5.3)]
WOOD_OUTER = [(9.75, 5.55), (10.0, 5.62), (10.2, 5.48), (10.32, 5.2), (10.15, 4.0), (9.55, 2.7), (8.45, 1.4), (6.8, 0.5), (5.6, 0.2), (5.45, 0.0), (0, 0)]
DISH_INNER = [(0, 0.7), (3.5, 0.72), (4.8, 0.85), (5.8, 1.5), (6.4, 2.3), (6.7, 3.0)]
DISH_OUTER = [(6.82, 3.2), (7.0, 3.22), (7.12, 3.05), (6.9, 2.3), (6.2, 1.25), (4.9, 0.4), (4.3, 0.15), (4.2, 0.0), (0, 0)]


def make_bowl(name, cx, cy, inner, outer, mat, fill_kind, count, dome_top, dome_k, fill_mat, extra=None, yaw=0.0):
    ob = lathe(name, inner + outer, [mat], steps=128, subsurf=2)
    ob.location = (cx, cy, 0)
    ob.rotation_euler = (0, 0, yaw)
    rs = np.array([p[0] for p in inner])
    zs = np.array([p[1] for p in inner])
    ri = inner[-1][0]

    def base(dx, dy):
        r = np.sqrt(dx * dx + dy * dy)
        h = np.interp(r, rs, zs)
        dome = dome_top - dome_k * r * r
        h = np.maximum(h, np.minimum(dome, zs[-1] + 2))
        h[r > ri - 0.05] = 99.0
        return h

    # hidden filler so only the top layers need real items
    bm = bmesh.new()
    nring, nseg = 24, 64
    center = bm.verts.new((0, 0, dome_top - 0.45))
    rings = []
    for i in range(1, nring + 1):
        r = (ri - 0.15) * i / nring
        zr = min(dome_top - dome_k * r * r, 99) - 0.45
        zr = max(zr, float(np.interp(r, rs, zs)) + 0.02)
        rings.append([bm.verts.new((r * math.cos(t), r * math.sin(t), zr)) for t in np.linspace(0, 2 * math.pi, nseg, endpoint=False)])
    for j in range(nseg):
        bm.faces.new((center, rings[0][j], rings[0][(j + 1) % nseg]))
    for i in range(nring - 1):
        for j in range(nseg):
            bm.faces.new((rings[i][j], rings[i + 1][j], rings[i + 1][(j + 1) % nseg], rings[i][(j + 1) % nseg]))
    fo = obj_from_bm(name + '_fill', bm, [fill_mat])
    fo.location = (cx, cy, 0)

    hf = HeightField(cx, cy, ri + 0.5, 0.05 if fill_kind == 'pea' else 0.07, base)
    a, b, c = SPEC[fill_kind]
    placed = 0
    tries = 0
    while placed < count and tries < count * 4:
        tries += 1
        rr = math.sqrt(rng.random()) * (ri - b * 0.9)
        t = rng.random() * 2 * math.pi
        x, y = cx + rr * math.cos(t), cy + rr * math.sin(t)
        # long items near the wall settle along it
        yaw_i = t + math.pi / 2 + R(-0.3, 0.3) if rr > ri - a - 0.4 else rng.random() * 2 * math.pi
        z = hf.drop(x, y, a, b, c, yaw_i, zmax=40.0)
        if z is None:
            continue
        make_item(fill_kind, x, y, z, yaw_i)
        placed += 1
    print(f'{name}: placed {placed}/{count} in {tries} tries')
    if extra:
        extra(hf, cx, cy, ri)
    return hf


def sprinkle(hf, cx, cy, ri, n_pep=160, n_salt=60, rlim=0.9):
    for i in range(n_pep):
        rr = math.sqrt(rng.random()) * ri * rlim
        t = rng.random() * 6.283
        x, y = cx + rr * math.cos(t), cy + rr * math.sin(t)
        z = hf.height(x, y)
        if z > 40:
            continue
        place(rng.choice(PEPPERS), x, y, z + 0.01, Euler((R(0, 6), R(0, 6), R(0, 6))))
    for i in range(n_salt):
        rr = math.sqrt(rng.random()) * ri * rlim
        t = rng.random() * 6.283
        x, y = cx + rr * math.cos(t), cy + rr * math.sin(t)
        z = hf.height(x, y)
        if z > 40:
            continue
        place(rng.choice(SALTS), x, y, z + 0.01, Euler((R(0, 6), R(0, 6), R(0, 6))))


preview = args.preview
k = 0.45 if preview else 1.0

# Layout is given in poster pixels (1200 x 1600) and converted to table cm.
FRAME_W = 42.0
PXS = 1200 / FRAME_W


def P(px, py):
    return (px - 600) / PXS, (800 - py) / PXS


# top-left: big bowl of arbes (the shalom zachar classic), salted & peppered
make_bowl('bowl_arbes', *P(88, 118), WOOD_INNER, WOOD_OUTER, M_WOOD1, 'pea', int(1500 * k), 5.6, 0.013, M_FILL_ARBES,
          extra=lambda hf, cx, cy, ri: sprinkle(hf, cx, cy, ri))
# top-right: peanuts in the shell
make_bowl('bowl_peanuts', *P(1132, 96), WOOD_INNER, WOOD_OUTER, M_WOOD2, 'peanut', int(560 * k), 6.0, 0.015, M_FILL_NUT)
# bottom-left: pistachios
make_bowl('bowl_pist', *P(240, 1648), WOOD_INNER, WOOD_OUTER, M_WOOD3, 'pist', int(520 * k), 5.8, 0.014, M_FILL_PIST)
# right: a second, small ceramic dish of arbes
make_bowl('dish_arbes', *P(1190, 700), DISH_INNER, DISH_OUTER, M_CERAMIC, 'pea', int(650 * k), 3.3, 0.02, M_FILL_ARBES,
          extra=lambda hf, cx, cy, ri: sprinkle(hf, cx, cy, ri, 70, 25))


# ---------------------------------------------------------------- beer stein (bottom-right)
def beer_mug(cx, cy, yaw):
    g_in, g_out, h = 4.55, 4.95, 15.0
    glass = lathe('mug', [(0, 1.2), (g_in - 0.35, 1.2), (g_in - 0.08, 1.35), (g_in, 1.7), (g_in, h - 0.1), (g_in + 0.05, h),
                          (g_in + 0.2, h + 0.08), (g_out - 0.05, h), (g_out, h - 0.15), (g_out, 0.7), (g_out - 0.1, 0.15),
                          (g_out - 0.35, 0.0), (0, 0)], [M_GLASS], steps=128, subsurf=1)
    beer = lathe('beer', [(0, 11.6), (g_in + 0.02, 11.6), (g_in + 0.02, 1.7), (g_in - 0.08, 1.37), (g_in - 0.35, 1.22), (0, 1.22)], [M_BEER], steps=96, subsurf=0)
    foam_prof = [(0, h + 0.55), (1.5, h + 0.52), (2.8, h + 0.42), (3.7, h + 0.25), (4.25, h + 0.05), (g_in + 0.02, h - 0.15),
                 (g_in + 0.02, 11.6), (0, 11.6)]
    foam = lathe('foam', foam_prof, [M_FOAM], steps=96, subsurf=1)
    # little displacement for a lively head
    tex = bpy.data.textures.new('foamdisp', 'CLOUDS')
    tex.noise_scale = 0.9
    dm = foam.modifiers.new('disp', 'DISPLACE')
    dm.texture = tex
    dm.strength = 0.25
    dm.mid_level = 0.5
    sub = foam.modifiers.new('sub2', 'SUBSURF')
    sub.levels = 1
    sub.render_levels = 2
    # handle
    cu = bpy.data.curves.new('handle', 'CURVE')
    cu.dimensions = '3D'
    cu.bevel_depth = 0.62
    cu.bevel_resolution = 6
    sp = cu.splines.new('BEZIER')
    pts = [(g_out - 0.2, 0, 13.2), (8.4, 0, 12.6), (9.0, 0, 7.8), (8.2, 0, 3.6), (g_out - 0.2, 0, 3.2)]
    sp.bezier_points.add(len(pts) - 1)
    for bp_, p in zip(sp.bezier_points, pts):
        bp_.co = p
        bp_.handle_left_type = bp_.handle_right_type = 'AUTO'
    cu.materials.append(M_GLASS)
    handle = bpy.data.objects.new('handle', cu)
    col.objects.link(handle)
    for o in (glass, beer, foam, handle):
        o.location = (cx, cy, 0)
        o.rotation_euler = (0, 0, yaw)
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=1)
    gl = obj_from_bm('beer_glow', bm, [M_GLOW], smooth=False)
    gl.location = (cx + 1.6, cy - 1.8, 0.02)
    gl.scale = (7.5, 6.0, 1)
    gl.rotation_euler = (0, 0, math.radians(-42))


beer_mug(*P(1080, 1404), math.radians(-38))


# ---------------------------------------------------------------- l'chaim: two shot glasses of whisky (left)
def shot_glass(cx, cy, fill=3.9, s=1.18):
    gi = lambda z: 1.95 + (2.12 - 1.95) * (z - 1.4) / (6.0 - 1.4)
    for o in (lathe('shot', [(0, 1.45), (1.8, 1.45), (1.95, 1.6), (2.12, 6.0), (2.17, 6.1), (2.3, 6.12), (2.4, 6.0), (2.12, 0.5),
                             (2.0, 0.08), (1.88, 0.0), (0, 0)], [M_GLASS], steps=96, subsurf=1),
              lathe('whisky', [(0, fill), (gi(fill) + 0.02, fill), (gi(1.62) + 0.02, 1.62), (1.82, 1.47), (0, 1.47)], [M_WHISKY], steps=96, subsurf=0)):
        o.location = (cx, cy, 0)
        o.scale = (s, s, s)
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=1)
    g = obj_from_bm('glow', bm, [M_GLOW], smooth=False)
    g.location = (cx + 1.0 * s, cy - 1.1 * s, 0.02)
    g.scale = (3.0 * s, 2.5 * s, 1)
    g.rotation_euler = (0, 0, math.radians(-42))


shot_glass(*P(76, 842))
shot_glass(*P(150, 994), 3.3)


# ---------------------------------------------------------------- strays on the table
def table_item(kind, x, y, yaw=None):
    a, b, c = SPEC[kind]
    yaw = rng.random() * 6.283 if yaw is None else yaw
    return make_item(kind, x, y, c * 0.93, yaw)


for px, py in [(330, 300), (356, 262), (300, 352), (262, 424), (214, 470), (205, 560), (150, 642), (250, 708),
               (252, 1112), (306, 1080), (68, 1176), (470, 1440), (522, 1474), (616, 1502), (982, 962), (1012, 1004),
               (958, 1012), (902, 1214), (1020, 905), (1060, 1180)]:
    table_item('pea', *P(px + R(-6, 6), py + R(-6, 6)))
for px, py in [(868, 300), (930, 356), (816, 236), (762, 1566), (842, 1530), (1000, 470)]:
    table_item('peanut', *P(px, py))
for px, py in [(480, 1362), (410, 1402), (562, 1424), (40, 1312)]:
    table_item('pist', *P(px, py))
for i in range(80):
    zone = rng.choice([(310, 380, 60), (270, 650, 60), (990, 990, 60), (560, 1470, 90), (180, 1130, 60), (1010, 1190, 50)])
    t, rr = rng.random() * 6.283, math.sqrt(rng.random()) * zone[2]
    place(rng.choice(SALTS if rng.random() < 0.6 else PEPPERS), *P(zone[0] + rr * math.cos(t), zone[1] + rr * math.sin(t)), 0.03,
          Euler((R(0, 6), R(0, 6), R(0, 6))))

# ---------------------------------------------------------------- table
bm = bmesh.new()
bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=90)
obj_from_bm('table', bm, [M_TABLE], smooth=False)

# ---------------------------------------------------------------- light & camera
world = bpy.data.worlds.new('world')
scene.world = world
try:
    world.use_nodes = True
except Exception:
    pass
bgn = world.node_tree.nodes.get('Background')
if bgn is None:
    bgn = world.node_tree.nodes.new('ShaderNodeBackground')
    wo = world.node_tree.nodes.new('ShaderNodeOutputWorld')
    world.node_tree.links.new(bgn.outputs[0], wo.inputs['Surface'])
bgn.inputs['Color'].default_value = srgb('#6b5a4c')
bgn.inputs["Strength"].default_value = 0.035

key = bpy.data.lights.new('key', 'AREA')
key.shape = 'DISK'
key.size = 90
key.energy = 7.0e5
keyo = bpy.data.objects.new('key', key)
keyo.location = (-95, 85, 150)
col.objects.link(keyo)
d = Vector((4, -4, 0)) - keyo.location
keyo.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()

fill = bpy.data.lights.new('fill', 'AREA')
fill.size = 120
fill.energy = 4.0e4
fillo = bpy.data.objects.new('fill', fill)
fillo.location = (110, -60, 160)
col.objects.link(fillo)
d = Vector((0, 0, 0)) - fillo.location
fillo.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()

cam = bpy.data.cameras.new('cam')
cam.sensor_fit = 'HORIZONTAL'
cam.sensor_width = 36
CAM_Z = 115.0
cam.lens = 36 * CAM_Z / FRAME_W
cam.clip_start = 1
cam.clip_end = 1000
camo = bpy.data.objects.new('cam', cam)
camo.location = (0, 0, CAM_Z)
col.objects.link(camo)
scene.camera = camo

# ---------------------------------------------------------------- render settings
r = scene.render
r.engine = 'CYCLES'
r.resolution_x, r.resolution_y = 1200, 1600
r.resolution_percentage = args.scale
r.film_transparent = False
r.image_settings.file_format = 'PNG'
r.image_settings.color_depth = '8'
cy = scene.cycles
cy.device = 'CPU'
cy.samples = args.samples
cy.use_adaptive_sampling = True
cy.adaptive_threshold = 0.015
cy.use_denoising = True
try:
    cy.denoiser = 'OPENIMAGEDENOISE'
except Exception:
    pass
cy.max_bounces = 12
cy.transmission_bounces = 12
cy.glossy_bounces = 6
cy.volume_bounces = 2
cy.blur_glossy = 1.0
cy.caustics_reflective = False
cy.caustics_refractive = True
cy.sample_clamp_indirect = 8
r.threads_mode = 'AUTO'
try:
    scene.view_settings.view_transform = 'AgX'
    scene.view_settings.look = 'AgX - Medium High Contrast'
except Exception as e:
    print('look:', e)
scene.view_settings.exposure = 0.0

if args.blend:
    bpy.ops.wm.save_as_mainfile(filepath=args.blend)
if args.border:
    r.use_border = True
    r.use_crop_to_border = True
    r.border_min_x, r.border_min_y, r.border_max_x, r.border_max_y = args.border
r.filepath = args.out
print('objects:', len(bpy.data.objects))
bpy.ops.render.render(write_still=True)
print('done', args.out)
