const { chromium } = require('playwright');
(async () => {
  const url = process.argv[2], out = process.argv[3], w = +process.argv[4] || 1440, h = +process.argv[5] || 900;
  const b = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
  const mob = w < 600;
  const p = await b.newPage({ viewport: { width: w, height: h }, deviceScaleFactor: 1, hasTouch: mob, isMobile: mob });
  const logs = [];
  const fs = require('fs');
  await p.route('https://cdnjs.cloudflare.com/**', r => r.fulfill({ contentType: 'application/javascript', body: fs.readFileSync(__dirname + '/npmthree/node_modules/three/build/three.min.js', 'utf8') }));
  await p.route('https://cdn.jsdelivr.net/**', r => r.fulfill({ contentType: 'application/javascript', body: fs.readFileSync(__dirname + '/npmthree/node_modules/three/examples/js/loaders/GLTFLoader.js', 'utf8') }));
  await p.route('https://fonts.googleapis.com/**', r => r.fulfill({ contentType: 'text/css', body: '' }));
  p.on('console', m => logs.push(m.type() + ': ' + m.text()));
  p.on('pageerror', e => logs.push('pageerror: ' + e.message));
  await p.goto(url);
  await p.waitForTimeout(+process.argv[6] || 6000);
  if (process.argv[7]) { await p.evaluate(s => eval(s), process.argv[7]); await p.waitForTimeout(+process.argv[8] || 4000); console.log('STATE', JSON.stringify(await p.evaluate(() => window.__tour && window.__tour.walk.state()))); }
  await p.screenshot({ path: out, timeout: 180000 });
  console.log(logs.join('\n'));
  await b.close();
})();
