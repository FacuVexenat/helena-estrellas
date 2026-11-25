import { getStore } from "@netlify/blobs";
import { createPrivateKey, sign } from "node:crypto";
import reminders from "../../reminders.json" with { type: "json" };
import { pushHostOk } from "../lib/push.mjs";

// Argentina no tiene horario de verano: UTC-3 todo el año.
const AR_OFFSET_MIN = -180;
const pad = (n) => String(n).padStart(2, "0");
const b64u = (buf) => Buffer.from(buf).toString("base64url");

function arStamp(ms) {
  const d = new Date(ms + AR_OFFSET_MIN * 60000);
  return { f: `${d.getUTCFullYear()}-${pad(d.getUTCMonth() + 1)}-${pad(d.getUTCDate())}`, m: d.getUTCHours() * 60 + d.getUTCMinutes() };
}
function remMs(r) {
  const [y, mo, d] = r.f.split("-").map(Number);
  const [h, mi] = r.t.split(":").map(Number);
  return Date.UTC(y, mo - 1, d, h, mi) - AR_OFFSET_MIN * 60000;
}
function vapidAuth(endpoint) {
  const jwk = JSON.parse(process.env.VAPID_PRIVATE_JWK);
  const pub = b64u(Buffer.concat([Buffer.from([4]), Buffer.from(jwk.x, "base64url"), Buffer.from(jwk.y, "base64url")]));
  const aud = new URL(endpoint).origin;
  const header = b64u(JSON.stringify({ typ: "JWT", alg: "ES256" }));
  const payload = b64u(JSON.stringify({ aud, exp: Math.floor(Date.now() / 1000) + 12 * 3600, sub: process.env.VAPID_SUBJECT || "mailto:avisos@example.com" }));
  const key = createPrivateKey({ key: jwk, format: "jwk" });
  const sig = sign("sha256", Buffer.from(`${header}.${payload}`), { key, dsaEncoding: "ieee-p1363" });
  return `vapid t=${header}.${payload}.${b64u(sig)}, k=${pub}`;
}

export default async () => {
  const store = getStore("helena-push");
  const now = Date.now();
  const last = Number(await store.get("lastRun")) || now - 6 * 60000;
  const from = Math.max(last, now - 30 * 60000); // nunca más de 30 min hacia atrás
  const due = reminders.filter((r) => { const t = remMs(r); return t > from && t <= now; });
  await store.set("lastRun", String(now));
  if (!due.length) return new Response("nada para enviar");

  const subs = (await store.get("subs", { type: "json" })) || [];
  const keep = [];
  for (const s of subs) {
    if (!pushHostOk(s.endpoint)) continue; // nunca llamar a hosts que no sean de push
    let alive = true;
    for (const r of due) {
      // Push sin contenido: el teléfono arma el mensaje con reminders.json
      const res = await fetch(s.endpoint, {
        method: "POST",
        headers: { TTL: "1800", Urgency: "high", Topic: r.k.replace(/[^A-Za-z0-9_-]/g, "").slice(0, 32), Authorization: vapidAuth(s.endpoint), "Content-Length": "0" },
      }).catch(() => null);
      if (res && (res.status === 404 || res.status === 410)) alive = false;
    }
    if (alive) keep.push(s);
  }
  if (keep.length !== subs.length) await store.setJSON("subs", keep);
  return new Response(`enviados ${due.length} avisos a ${keep.length} dispositivos (${arStamp(now).f})`);
};

export const config = { schedule: "*/5 * * * *" };
