# 3D floor plan model (first floor)

A 3D model of the first-floor plan, built with Blender 5.3 (`bpy`) and rendered in Cycles.
1 Blender unit = 1 foot. Plan axes: x = east (right on the drawing), y = south (down on the drawing).

## What is modelled (from the drawing)
- Rooms and dimensions: dining 27'-7"x15'-0", study 11'-0"x15'-0", basement stair 3'-4" between 4" walls,
  kitchen 17'-4"x10'-0", walk-in pantry 4'-0"x7'-8" with a 2'-0" wash nook, dinette 21'-8" (23'-8" at the bay)
  x 11'-7", foyer 11'-1" deep, coat closet 4'-8"x2'-0", toilet and vanity alcove 3'-0" each, mud room
  5'-8"x8'-8", play room 11'-4"x17'-4" with a 7'-6"x2'-0" closet, living room 13'-6"x11'-6" with a
  2'-6" kitchenette behind bifold doors.
- Doors as drawn (size and swing): front 3068, study / stair / mud / play-closet pair 2868, pantry 2468,
  coat-closet pair and toilet 2068, kitchenette bifolds (2)3068, dinette slider (2)3068.
- Windows: (2)3046 pairs, bay 2046 / 3046 / 2046, plus the foyer, mud room, stair landing, living and play room windows.
- Stairs: the enclosed basement stair (door from the foyer, 13 treads down), the U-shaped stair down from the hall
  (6 treads, landing at the window, then back), and the covered-porch stair (7 treads down along the house + 2 steps east).
- Kitchen: two ranges, two sinks, island, raised bar, fridge + freezer columns; the living-room kitchenette (range + sink).

Where the drawing's written dimensions disagreed with each other, the written room sizes were kept and the hallway was
set to 3'-0" (the foyer becomes 14'-0" instead of 13'-6"); this matches the drawn proportions.

## Re-render
```
python -m venv bvenv && ./bvenv/bin/pip install bpy
./bvenv/bin/python src/main.py --view persp --res 3500 --samples 96 --el 57 --az 18 --dist 80 --ty 30 --out main.png
./bvenv/bin/python src/main.py --view top --res 2800 --samples 96 --sun_el 70 --out top.png
```
