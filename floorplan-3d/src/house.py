# The house shell: every wall, opening, floor finish, stair and the porch, taken from the plan.
import bpy, math
from mathutils import Vector
from lib import MB, W, MATS
from arch import (B, wall_rect, wall_seg, door_leaf, bifold, flight, balustrade, H, DH, TE, TI, G, ZB, BASE,
                  PORCH)

R_IN = 9.0 / 14          # interior stair riser (7.7")
R_EX = 0.5625            # exterior riser (6.75")


def win(a, b, units=1, **o):
    o['units'] = units
    return (a, b, 'win', o)


def door(a, b, **o):
    return (a, b, 'door', o)


def walls():
    # ---------------- exterior shell
    # North wall (dining + stair + study), two (2)3046 pairs over the dining room
    wall_rect(0, 0, 28.417, 0.5, [win(3.25, 9.25, 2), win(19.95, 25.95, 2)], ext='N')
    wall_rect(28.417, 0, 31.75, 0.5, [], ext='N', bb=False)
    wall_rect(31.75, 0, 43.583, 0.5, [], ext='N')
    # Study east wall, (2)3046
    wall_rect(43.083, 0, 43.583, 16.0, [win(5.4, 11.4, 2)], ext='E')
    # Study south wall: foyer part with the study door 2868, porch part exterior
    wall_rect(32.083, 15.5, 36.167, 16.0, [door(32.667, 35.333)])
    wall_rect(36.167, 15.5, 43.583, 16.0, [], ext='S')
    # Foyer / mud room east wall: window pair, front door 3068, mud room window
    wall_rect(36.167, 16.0, 36.667, 35.583, [win(17.45, 22.95, 2), door(23.06, 26.06), win(30.7, 33.7, 1)], ext='E')
    # Recess at the down stair (east)
    wall_rect(34.0, 35.583, 36.667, 36.083, [], ext='S')
    wall_rect(34.0, 35.583, 34.5, 43.083, [win(37.83, 40.83, 1)], ext='E', bb=False)
    wall_rect(34.0, 42.583, 36.667, 43.083, [], ext='N')
    # Living room east wall, long window behind the sectional
    wall_rect(36.167, 42.583, 36.667, 57.583, [win(46.2, 53.7, 3)], ext='E')
    # South wall (play room + living room / kitchenette)
    wall_rect(10.0, 57.083, 36.667, 57.583, [], ext='S')
    # Play room west wall
    wall_rect(10.0, 37.083, 10.5, 57.583, [win(41.75, 47.75, 2), win(54.0, 56.5, 1)], ext='W')
    # Dinette south wall with (2)3068 sliding door
    wall_rect(0, 37.083, 10.5, 37.583, [(2.9, 8.9, 'slide', {})], ext='S')
    # West wall (dining (2)3046, nook, pantry) and below the bay
    wall_rect(0, 0, 0.5, 26.5, [win(5.0, 11.0, 2)], ext='W')
    wall_rect(0, 36.0, 0.5, 37.583, [], ext='W')
    # Bay window at the dinette: 2046 / 3046 / 2046, projecting 2'-0"
    c = [(0.25, 26.3964), (-1.75, 28.3964), (-1.75, 34.1036), (0.25, 36.1036)]
    s2 = math.sqrt(2) / 2
    wall_seg(c[0], c[1], TE, [(0.414, 2.414, 'win', {'units': 1})], ext=Vector((-s2, s2, 0)), extend=(0.1, 0.1))
    wall_seg(c[1], c[2], TE, [(1.354, 4.354, 'win', {'units': 1})], ext='W', extend=(0.1, 0.1))
    wall_seg(c[2], c[3], TE, [(0.414, 2.414, 'win', {'units': 1})], ext=Vector((-s2, -s2, 0)), extend=(0.1, 0.1))

    # ---------------- interior partitions (4")
    wall_rect(28.083, 0.5, 28.417, 15.5, nobb=['E'])          # basement stair, west wall
    wall_rect(31.75, 0.5, 32.083, 15.5, nobb=['W'])           # basement stair, east wall (study)
    wall_rect(28.417, 15.333, 31.75, 15.667, [door(28.5, 31.167)], nobb=['N'])   # stair door 2868
    wall_rect(4.5, 15.5, 4.833, 25.833)                      # pantry east wall
    wall_rect(0.5, 17.5, 4.5, 17.833)                        # wash-nook / pantry
    wall_rect(0.5, 25.5, 4.833, 25.833, [door(1.667, 4.0)])  # pantry door 2468
    wall_rect(4.833, 15.5, 7.0, 15.833)                      # end wall of the cooktop run
    wall_rect(10.5, 15.5, 22.167, 15.833, h=3.5, capmat='quartz')     # raised bar back (peninsula)
    wall_rect(21.833, 15.833, 22.167, 25.0, h=3.5, capmat='quartz')   # raised bar back (sink leg)
    wall_rect(21.833, 25.0, 22.167, 27.6)                    # end wall at hallway
    wall_rect(21.833, 32.55, 22.167, 47.95)                  # fridge side / play room east wall
    wall_rect(14.333, 37.083, 21.833, 37.417)                # behind REF/FRE
    wall_rect(14.0, 37.083, 14.333, 39.75)                   # play closet west
    wall_rect(14.0, 39.417, 21.833, 39.75, [door(15.417, 20.75)])   # play closet, pair 2868
    wall_rect(21.833, 53.7, 22.167, 57.083)                  # kitchenette end wall
    wall_rect(22.167, 54.583, 36.167, 54.917, [door(23.167, 35.167)])  # kitchenette bifold opening (2)3068
    wall_rect(25.167, 42.75, 34.0, 43.083, nobb=['N'])        # stair / living
    wall_rect(25.167, 35.583, 34.0, 35.917, nobb=['S'])       # stair / powder + mud
    wall_rect(25.167, 26.583, 25.5, 32.583)                  # powder west
    wall_rect(25.167, 26.583, 36.167, 26.917, [door(25.833, 29.833), door(32.75, 35.417)])  # closet 2068 pr, mud 2868
    wall_rect(25.5, 28.917, 30.167, 29.25)                   # closet / toilet
    wall_rect(25.5, 32.25, 30.167, 32.583, [door(25.6, 27.6)])  # toilet door 2068
    wall_rect(30.167, 26.917, 30.5, 35.583)                  # powder / mud


def floors():
    F = B['floors']
    oak = [(0.5, 0.5, 28.083, 15.5), (32.083, 0.5, 43.083, 15.5), (10.5, 37.083, 21.833, 57.083),
           (22.167, 42.75, 36.167, 57.083)]
    tile = [(0.5, 15.5, 22.167, 25.833), (0.5, 25.833, 22.167, 37.083)]
    marble = [(22.167, 15.5, 36.167, 26.583), (22.167, 26.583, 25.167, 42.75), (25.167, 26.583, 30.167, 35.583),
              (25.167, 35.583, 26.5, 39.25), (25.167, 39.25, 30.0, 39.417), (28.417, 15.333, 31.75, 15.5)]
    slate = [(30.5, 26.917, 36.167, 35.583)]
    for m, rs in (('oak', oak), ('tile', tile), ('marble', marble), ('slate', slate)):
        for r in rs:
            F.pbox(r[0], r[1], r[2], r[3], -0.05, 0.0, m)
    bay = [(0.5, 26.5), (-1.5, 28.5), (-1.5, 34.0), (0.5, 36.0)]
    F.prism([(x, -y) for x, y in bay], -0.05, 0.0, 'tile')
    # basement floors at the bottom of the stair wells
    F.pbox(28.417, 0.5, 31.75, 5.6, BASE - 0.05, BASE, 'oak')
    F.pbox(23.0, 35.917, 26.6, 39.25, BASE - 0.05, BASE, 'oak')


FOOT = [(0, 0), (43.583, 0), (43.583, 16.0), (36.667, 16.0), (36.667, 36.083), (34.5, 36.083), (34.5, 42.583),
        (36.667, 42.583), (36.667, 57.583), (10.0, 57.583), (10.0, 37.583), (0, 37.583), (0, 36.207),
        (-2.0, 34.207), (-2.0, 28.293), (0, 26.293)]

CUTTERS = [  # (x0, y0, x1, y1, z0, z1)
    (28.417, 0.5, 31.75, 15.333, BASE, 1.0),          # basement stair between dining room and study
    (25.167, 39.417, 34.0, 42.75, BASE, 1.0),         # U stair, first flight
    (26.5, 35.917, 34.0, 39.25, BASE, 1.0),           # U stair, second flight
    (30.0, 39.25, 34.0, 39.417, BASE, 1.0),           # landing joint
    (23.0, 35.917, 26.5, 39.25, BASE, -1.3),          # second flight continuing under the hall
]


def foundation(coll):
    fd = MB('foundation_block')
    fd.prism([(x, -y) for x, y in FOOT], ZB, -0.05, 'found')
    ob = fd.finish(coll)
    MB.all.remove(fd)
    for i, c in enumerate(CUTTERS):
        cm = MB('cut%d' % i)
        cm.pbox(c[0], c[1], c[2], c[3], c[4], c[5], 'wall')
        co = cm.finish(coll)
        MB.all.remove(cm)
        co.hide_render = True
        co.display_type = 'WIRE'
        mod = ob.modifiers.new('cut%d' % i, 'BOOLEAN')
        mod.operation = 'DIFFERENCE'
        mod.solver = 'EXACT'
        mod.material_mode = 'TRANSFER'
        mod.object = co
    # ground (the stair wells are cut out of it as well)
    gm = MB('ground')
    gm.box(-400, -460, G - 0.5, 440, 400, G, 'ground')
    go = gm.finish(coll)
    MB.all.remove(gm)
    for i, m in enumerate([m for m in ob.modifiers if m.type == 'BOOLEAN']):
        gmod = go.modifiers.new('cut%d' % i, 'BOOLEAN')
        gmod.operation = 'DIFFERENCE'
        gmod.solver = 'EXACT'
        gmod.material_mode = 'TRANSFER'
        gmod.object = m.object


def stairs():
    st = B['stairs']
    # Basement stair (enclosed, door 2868 from the foyer): 13 treads descending north, 14 risers
    flight(28.417, 5.5, 31.75, 15.333, 'N', 13, 0.0, R_IN)
    st.pbox(28.417, 15.24, 31.75, 15.333, -0.09, 0.0, 'oak_tread')
    # wall handrail on the west wall
    zt, zb = 2.83, -12 * R_IN + 2.83
    st.rod(W(28.62, 15.0, zt), W(28.62, 6.0, zb), 0.07, 'rail_wood')
    for y in (14.0, 10.5, 7.0):
        z = zt + (zb - zt) * (15.0 - y) / 9.0
        st.rod(W(28.417, y, z - 0.05), W(28.62, y, z - 0.05), 0.025, 'nickel')

    # U-shaped stair down from the hall: 6 treads east, landing at the window, 7 treads back west
    flight(25.167, 39.417, 30.0, 42.75, 'E', 6, 0.0, R_IN)
    st.pbox(30.0, 35.917, 34.0, 42.75, ZB, -7 * R_IN - 0.09, 'trim')
    st.pbox(29.9, 35.917, 34.0, 42.75, -7 * R_IN - 0.09, -7 * R_IN, 'oak_tread')
    flight(23.875, 35.917, 30.0, 39.25, 'W', 7, -7 * R_IN, R_IN)
    st.pbox(25.07, 39.417, 25.167, 42.75, -0.09, 0.0, 'oak_tread')
    # guards at hall level
    balustrade((26.5, 35.95), (26.5, 39.33), 0.0)
    balustrade((25.25, 39.333), (30.0, 39.333), 0.0)
    # wall handrails
    st.rod(W(25.5, 42.5, 2.83), W(29.8, 42.5, -6 * R_IN + 2.83), 0.07, 'rail_wood')
    st.rod(W(33.8, 36.15, -7 * R_IN + 2.83), W(29.9, 36.15, -7 * R_IN + 2.83), 0.07, 'rail_wood')
    st.rod(W(29.9, 36.15, -7 * R_IN + 2.83), W(26.6, 36.15, -11 * R_IN + 2.83), 0.07, 'rail_wood')


def porch():
    pc = B['porch']
    # raised covered porch (L-shaped) at porch level
    for r in ((36.667, 16.0, 40.1, 28.2), (40.1, 24.7, 43.5, 28.2)):
        pc.pbox(r[0], r[1], r[2], r[3], G, PORCH - 0.12, 'found')
        pc.pbox(r[0] - (0.08 if r[0] < 37 else 0), r[1], r[2] + (0.08 if r[2] > 43 else 0), r[3] + 0.08, PORCH - 0.12,
                PORCH, 'paver')
    # stair: 7 treads descending north along the house, lower landing, then 2 treads east
    flight(40.4, 19.4, 43.5, 24.7, 'N', 7, PORCH, R_EX, zbot=G, tread_mat='paver', nos=0.06, body_mat='found',
           tread_t=0.12)
    pc.pbox(40.4, 16.0, 43.5, 19.4, G, PORCH - 8 * R_EX - 0.12, 'found')
    pc.pbox(40.4, 16.0, 43.58, 19.46, PORCH - 8 * R_EX - 0.12, PORCH - 8 * R_EX, 'paver')
    flight(43.5, 16.0, 44.82, 19.4, 'E', 2, PORCH - 8 * R_EX, R_EX, zbot=G, tread_mat='paver', nos=0.06,
           body_mat='found', tread_t=0.12)
    # railings
    balustrade((40.25, 16.1), (40.25, 24.7), PORCH)
    balustrade((43.4, 19.45), (43.4, 24.7), PORCH - 8 * R_EX, z1=PORCH, newel=(True, False))
    balustrade((43.4, 24.7), (43.4, 28.1), PORCH)
    balustrade((36.8, 28.1), (43.4, 28.1), PORCH, newel=(False, True))


def doors():
    # front door 3068 (opens in, drawn fully open along the south jamb)
    door_leaf((36.12, 25.98), (-1, 0), 2.95, mat='front_door', panels=3)
    door_leaf((32.72, 15.44), (0, -1), 2.62)                 # study 2868
    door_leaf((28.55, 15.72), (0, 1), 2.6)                    # basement stair 2868 (opens to foyer)
    door_leaf((3.95, 25.44), (0, -1), 2.28)                   # pantry 2468
    door_leaf((15.47, 39.81), (0, 1), 2.62)                   # play closet pair 2868
    door_leaf((20.70, 39.81), (0, 1), 2.62)
    s = math.sqrt(2) / 2
    door_leaf((25.88, 26.52), (s, -s), 1.97, knob=True)       # coat closet pair 2068
    door_leaf((29.78, 26.52), (-s, -s), 1.97, knob=True)
    door_leaf((35.37, 26.98), (0, 1), 2.62)                   # mud room 2868
    door_leaf((25.65, 32.19), (s, -s), 1.95)                  # toilet 2068
    bifold((23.2, 54.75), +1)                                 # kitchenette bifolds (2)3068
    bifold((35.13, 54.75), -1)
    # front door exterior trim + threshold
    tr = B['trim']
    tr.pbox(36.667, 22.77, 36.75, 23.06, 0, DH + 0.3, 'trim')
    tr.pbox(36.667, 26.06, 36.75, 26.35, 0, DH + 0.3, 'trim')
    tr.pbox(36.667, 22.77, 36.75, 26.35, DH, DH + 0.3, 'trim')
    tr.pbox(36.1, 23.06, 36.8, 26.06, -0.05, 0.03, 'marble')


def build_shell(coll):
    walls()
    floors()
    foundation(coll)
    stairs()
    porch()
    doors()
