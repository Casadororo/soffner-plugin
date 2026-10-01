// Demo takes for the demo skill: Playwright drives a headless Chrome, Chrome's screencast films,
// ffmpeg encodes once.
//
//   node demo-take.js rehearse <shot.js>...           no camera; leaves <shot>.png and <shot>.aria.txt
//   node demo-take.js film <out.mp4> <shot.js>...     every shot in order, one film
//
// A shot exports { setup(page), take(page, cam) }. setup runs with the camera off (preconditions,
// landing on the first screen); take is what ends up on film. cam.chapter(title, description, ms)
// and cam.caption(text, ms) put text on screen while it plays.
//
// env: BASE_URL      page.goto('/path') resolves against it
//      STORAGE       Playwright storageState to load (a signed-in session)
//      SAVE_STORAGE  where rehearse writes the storageState it ends with (the sign-in shot)
//      VIEWPORT=1920x1080  the frame size; Chrome never films above the CSS viewport
//      HOLD_MAX=2.5  seconds a still frame may last; anything longer is dead air and gets cut
//      PW            the playwright package (default: ~/.cache/soffner-demo/node_modules/playwright)
const fs = require('fs');
const os = require('os');
const path = require('path');
const { execFileSync } = require('child_process');
const { chromium } = require(process.env.PW || path.join(os.homedir(), '.cache/soffner-demo/node_modules/playwright'));

const [width, height] = (process.env.VIEWPORT || '1920x1080').split('x').map(Number);
const holdMax = Number(process.env.HOLD_MAX || 2.5);

// Chrome only sends a frame when the page paints, so each JPEG lasts until the next one (or the
// end of its shot): the film keeps real timing, and a still longer than holdMax is thinking, not product.
function encode(frames, ends, workDir, out) {
  const dir = fs.mkdtempSync(path.join(workDir, '.frames-'));
  let list = '';
  const cut = [];
  frames.forEach((f, i) => {
    const file = path.join(dir, `${i}.jpg`);
    fs.writeFileSync(file, f.data);
    const next = frames[i + 1] && frames[i + 1].shot === f.shot ? frames[i + 1].timestamp : ends[f.shot];
    const seconds = (next - f.timestamp) / 1000;
    if (seconds > holdMax) cut.push(seconds.toFixed(1));
    list += `file '${file}'\nduration ${Math.min(seconds, holdMax).toFixed(3)}\n`;
  });
  list += `file '${path.join(dir, `${frames.length - 1}.jpg`)}'\n`;
  fs.writeFileSync(path.join(dir, 'list.txt'), list);
  if (cut.length) console.error(`dead air cut to ${holdMax}s: ${cut.join('s, ')}s`);
  execFileSync('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', path.join(dir, 'list.txt'),
    '-vf', 'fps=30,format=yuv420p', '-c:v', 'libx264', '-crf', '18', '-preset', 'slow', '-tune', 'stillimage',
    '-movflags', '+faststart', out]);
  fs.rmSync(dir, { recursive: true });
}

const captionCss = 'position:fixed;left:50%;bottom:48px;transform:translateX(-50%);max-width:80%;' +
  'padding:14px 28px;border-radius:12px;background:rgba(20,20,20,.82);color:#fff;' +
  'font:600 30px/1.3 system-ui,sans-serif;text-align:center;z-index:2147483647';
const escape = s => s.replace(/[&<>]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c]));

(async () => {
  const [mode, ...rest] = process.argv.slice(2);
  const out = mode === 'film' ? path.resolve(rest.shift()) : null;
  const shotFiles = rest.map(f => path.resolve(f));
  if (!['rehearse', 'film'].includes(mode) || !shotFiles.length) {
    throw new Error('usage: demo-take.js rehearse <shot.js>... | demo-take.js film <out.mp4> <shot.js>...');
  }

  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  const context = await browser.newContext({
    viewport: { width, height }, locale: 'pt-BR', baseURL: process.env.BASE_URL,
    storageState: process.env.STORAGE && fs.existsSync(process.env.STORAGE) ? process.env.STORAGE : undefined,
  });
  const page = await context.newPage();
  const cam = {
    chapter: async (title, description, ms = 2000) => {
      await page.screencast.showChapter(title, { description, duration: ms });
      await page.waitForTimeout(ms);
    },
    caption: (text, ms = 2500) => page.screencast.showOverlay(`<div style="${captionCss}">${escape(text)}</div>`, { duration: ms }),
  };
  const frames = [];
  const ends = [];
  const started = Date.now();
  let current = shotFiles[0];
  try {
    for (const [i, file] of shotFiles.entries()) {
      current = file;
      const shot = require(file);
      if (shot.setup) await shot.setup(page);
      if (mode === 'film') {
        await page.screencast.start({ onFrame: f => frames.push({ ...f, shot: i }), size: { width, height }, quality: 90 });
        // pointer that travels to each action; the default title is Playwright code, useless on film
        await page.screencast.showActions({ cursor: 'pointer', duration: 700, style: { title: 'display:none' } });
      }
      await shot.take(page, cam);
      if (mode === 'film') {
        await page.waitForTimeout(800);
        ends[i] = Date.now();
        await page.screencast.hideActions();
        await page.screencast.stop();
      } else {
        await snapshot(page, file);
      }
    }
    if (mode === 'rehearse' && process.env.SAVE_STORAGE) await context.storageState({ path: process.env.SAVE_STORAGE });
  } catch (e) {
    // where it stopped is what the next edit of the shot needs
    await snapshot(page, current).catch(() => {});
    throw new Error(`${path.basename(current)}: ${e.message.split('\n')[0]} (see ${current.replace(/\.js$/, '.png')})`);
  } finally {
    await browser.close();
  }

  if (mode === 'film') encode(frames, ends, path.dirname(shotFiles[0]), out);
  console.log(JSON.stringify({
    mode, output: out, shots: shotFiles.length, frames: frames.length || undefined,
    viewport: `${width}x${height}`, wall_seconds: (Date.now() - started) / 1000,
  }));
})().catch(e => { console.error(e.message); process.exit(1); });

async function snapshot(page, file) {
  const base = file.replace(/\.js$/, '');
  await page.screenshot({ path: `${base}.png` });
  fs.writeFileSync(`${base}.aria.txt`, `url: ${page.url()}\n${await page.locator('body').ariaSnapshot()}\n`);
}
