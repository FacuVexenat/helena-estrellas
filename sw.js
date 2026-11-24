const C='helena-v7';
const FILES=['./','./index.html','./manifest.webmanifest','./icon-192.png','./icon-512.png','./apple-touch-icon.png','./reminders.json'];
self.addEventListener('install',e=>{e.waitUntil(caches.open(C).then(c=>c.addAll(FILES)));self.skipWaiting();});
self.addEventListener('activate',e=>{e.waitUntil(caches.keys().then(k=>Promise.all(k.filter(x=>x!==C).map(x=>caches.delete(x)))));self.clients.claim();});
self.addEventListener('fetch',e=>{if(e.request.method!=='GET'||new URL(e.request.url).origin!==location.origin)return;
e.respondWith(fetch(e.request).then(r=>{const cp=r.clone();caches.open(C).then(c=>c.put(e.request,cp));return r;}).catch(()=>caches.match(e.request).then(r=>r||caches.match('./index.html'))));});
const pad=n=>String(n).padStart(2,'0');
function arNow(){const d=new Date(Date.now()-3*3600*1000);return {f:`${d.getUTCFullYear()}-${pad(d.getUTCMonth()+1)}-${pad(d.getUTCDate())}`,m:d.getUTCHours()*60+d.getUTCMinutes()};}
async function getJSON(u,cache){try{const r=await fetch(u,{cache:'no-store'});if(r.ok)return await r.json();}catch(e){}try{const c=await caches.open(cache||C);const r=await c.match(u);if(r)return await r.json();}catch(e){}return null;}
self.addEventListener('push',e=>{e.waitUntil((async()=>{
  let rem=null;try{rem=e.data&&e.data.json();}catch(x){}
  if(!rem||!rem.title){const all=(await getJSON('./reminders.json'))||[];const n=arNow();
    const cand=all.filter(r=>r.f===n.f).map(r=>{const[h,m]=r.t.split(':').map(Number);return {...r,diff:n.m-(h*60+m)};}).filter(r=>r.diff>=-2&&r.diff<=20).sort((a,b)=>a.diff-b.diff);
    rem=cand[0]||{title:'⭐ Las estrellas de Helena',body:'¡Tenés una misión esperándote!'};}
  let st={};try{const c=await caches.open('helena-state');const r=await c.match('./state.json');if(r)st=await r.json();}catch(x){}
  const done=rem.k&&st[rem.k];
  await self.registration.showNotification(done?'✔ ¡Muy bien, Helena!':rem.title,{body:done?'Esta misión ya tiene su estrella. ¡Seguí así!':rem.body,icon:'icon-192.png',badge:'icon-192.png',tag:rem.k||'helena',renotify:true,data:{url:'./'}});
})());});
self.addEventListener('notificationclick',e=>{e.notification.close();e.waitUntil((async()=>{const cs=await clients.matchAll({type:'window',includeUncontrolled:true});for(const c of cs){if('focus' in c)return c.focus();}return clients.openWindow('./');})());});
