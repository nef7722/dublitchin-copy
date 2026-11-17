# Build a single self-contained HTML file of the tour (no network at all): inline libraries and every asset.
import base64, re, os, sys
S = os.path.dirname(os.path.abspath(__file__))
T = os.path.join(S, 'tour')
html = open(os.path.join(T, 'index.html'), encoding='utf-8').read()

def b64(p):
    return base64.b64encode(open(p, 'rb').read()).decode()

def datauri(rel):
    ext = rel.rsplit('.', 1)[1]
    mime = {'jpg': 'image/jpeg', 'png': 'image/png'}[ext]
    return 'data:%s;base64,%s' % (mime, b64(os.path.join(T, rel)))

# 1) libraries inline, no web fonts
three = open(os.path.join(S, 'npmthree/node_modules/three/build/three.min.js'), encoding='utf-8').read()
gltf = open(os.path.join(S, 'npmthree/node_modules/three/examples/js/loaders/GLTFLoader.js'), encoding='utf-8').read()
html = re.sub(r'<link rel="preconnect"[^>]*>\n?', '', html)
html = re.sub(r'<link rel="stylesheet" href="https://fonts.googleapis.com[^>]*>\n?', '', html)
html = html.replace('<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>',
                    '<script>' + three + '</script>')
html = html.replace('<script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/loaders/GLTFLoader.js"></script>',
                    '<script>' + gltf + '</script>')
assert 'cdnjs' not in html and 'jsdelivr' not in html

# 2) images in the markup
for rel in ('img/map.jpg', 'img/main.jpg', 'img/ne.jpg'):
    html = html.replace('src="%s"' % rel, 'src="%s"' % datauri(rel))

# 3) assets used from script: a lookup table + the model as base64
assets = {}
for d in ('pano', 'walk'):
    for n in sorted(os.listdir(os.path.join(T, d))):
        if n.endswith(('.jpg', '.png')):
            assets[d + '/' + n] = datauri(d + '/' + n)
js = 'window.__ASSETS = {' + ','.join('"%s":"%s"' % kv for kv in assets.items()) + '};\n'
js += 'window.__HOUSE = "' + b64(os.path.join(T, 'walk/house.glb')) + '";\n'
html = html.replace('<script>\n(function () {', '<script>' + js + '</script>\n<script>\n(function () {', 1)

# 4) route the loads through the table
def A(s):
    return "(window.__ASSETS[" + s + "] || " + s + ")"
html = html.replace("loader.load('pano/' + id + '.jpg',", "loader.load(" + A("'pano/' + id + '.jpg'") + ",")
html = html.replace("texLoader.load(small ? 'walk/lightmap_m.jpg' : 'walk/lightmap.jpg',",
                    "texLoader.load(" + A("(small ? 'walk/lightmap_m.jpg' : 'walk/lightmap.jpg')") + ",")
html = html.replace("texLoader.load('pano/foyer.jpg',", "texLoader.load(" + A("'pano/foyer.jpg'") + ",")
html = html.replace("loadImg('walk/walkmap.png')", "loadImg(" + A("'walk/walkmap.png'") + ")")
old = "        var xhr = new XMLHttpRequest();"
assert old in html
html = html.replace(old, """        if (window.__HOUSE) {
          setTimeout(function () {
            try {
              var bin0 = atob(window.__HOUSE), n0 = bin0.length, b0 = new Uint8Array(n0);
              for (var i0 = 0; i0 < n0; i0++) b0[i0] = bin0.charCodeAt(i0);
              new THREE.GLTFLoader().parse(b0.buffer, '', res, rej);
            } catch (err) { rej(err); }
          }, 30);
          return;
        }
        var xhr = new XMLHttpRequest();""", 1)

head = ('<!doctype html>\n<html lang="he">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
        '<style>:root{color-scheme:dark}body{margin:0;font:14px system-ui}img{max-width:100%}[hidden]{display:none!important}</style>\n'
        '</head>\n<body>\n')
out = head + html + '\n</body>\n</html>\n'
dst = sys.argv[1]
open(dst, 'w', encoding='utf-8').write(out)
print('written', dst, round(len(out.encode()) / 1e6, 2), 'MB')
