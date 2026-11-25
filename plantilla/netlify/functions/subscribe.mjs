import { getStore } from "@netlify/blobs";

import { pushHostOk } from "../lib/push.mjs";

export default async (req) => {
  if (req.method !== "POST") return new Response("Método no permitido", { status: 405 });
  const len = Number(req.headers.get("content-length") || 0);
  if (len > 4096) return new Response("Demasiado grande", { status: 413 });
  let body;
  try { const txt = await req.text(); if (txt.length > 4096) throw 0; body = JSON.parse(txt); } catch { return new Response("JSON inválido", { status: 400 }); }
  const pin = process.env.SUBSCRIBE_PIN;
  if (pin && String(body && body.pin || "") !== pin) return new Response("PIN incorrecto", { status: 403 });
  const sub = body && body.subscription;
  if (!sub || typeof sub.endpoint !== "string" || sub.endpoint.length > 1024 || !pushHostOk(sub.endpoint)) {
    return new Response("Suscripción inválida", { status: 400 });
  }
  const store = getStore("rutina-push");
  const subs = (await store.get("subs", { type: "json" })) || [];
  const others = subs.filter((s) => s.endpoint !== sub.endpoint);
  if (body.unsubscribe) {
    await store.setJSON("subs", others);
    return Response.json({ ok: true, total: others.length });
  }
  others.push({ endpoint: sub.endpoint, at: new Date().toISOString() });
  await store.setJSON("subs", others.slice(-5));
  return Response.json({ ok: true, total: Math.min(others.length, 5) });
};

export const config = { path: "/api/subscribe" };
