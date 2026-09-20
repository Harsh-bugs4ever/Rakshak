import { readdir, readFile, writeFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { join, relative } from 'node:path';

const root = join(process.cwd(), '.next', 'static');
async function walk(dir) {
  const entries = await readdir(dir, { withFileTypes: true });
  return (await Promise.all(entries.map(entry => entry.isDirectory()
    ? walk(join(dir, entry.name))
    : /\.(js|css|woff2?)$/.test(entry.name) ? [join(dir, entry.name)] : []))).flat();
}
const assets = (await walk(root)).map(file => '/_next/static/' + relative(root, file).replaceAll('\\', '/')).sort();
const buildId = (await readFile('.next/BUILD_ID', 'utf8')).trim();
const version = createHash('sha256').update(buildId + assets.join('\n')).digest('hex').slice(0, 16);
const worker = `
const CACHE = 'rakshak-shell-${version}';
const PAGES = ['/emergency', '/aftermath'];
const ASSETS = ${JSON.stringify(assets)};
self.addEventListener('install', event => {
  event.waitUntil(caches.open(CACHE).then(cache => cache.addAll([...PAGES, ...ASSETS])));
});
self.addEventListener('activate', event => {
  event.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(key => key.startsWith('rakshak-shell-') && key !== CACHE).map(key => caches.delete(key)))).then(() => self.clients.claim()));
});
self.addEventListener('fetch', event => {
  const request = event.request;
  const url = new URL(request.url);
  if (request.method !== 'GET' || url.origin !== self.location.origin) return;
  if (request.mode === 'navigate' && (PAGES.includes(url.pathname) || url.pathname === '/')) {
    event.respondWith((async () => {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 3000);
      try {
        const response = await fetch(request, {signal: controller.signal});
        if (!response.ok) throw new Error('Navigation unavailable');
        return response;
      } catch {
        const cached = await caches.match(url.pathname === '/' ? '/emergency' : url.pathname, {cacheName: CACHE});
        return cached || new Response('Reconnect once to save Rakshak on this device. For an emergency, call 112.', {status: 503, headers: {'Content-Type':'text/plain'}});
      } finally { clearTimeout(timeout); }
    })());
  } else if (ASSETS.includes(url.pathname)) {
    event.respondWith(caches.match(request, {cacheName: CACHE}).then(cached => cached || fetch(request)));
  }
});
`;
await writeFile('public/service-worker.js', worker);
console.log('Offline shell generated: ' + assets.length + ' assets, version ' + version);
