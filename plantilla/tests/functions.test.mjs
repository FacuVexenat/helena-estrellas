// Pruebas de las funciones de avisos con stubs (sin red).
import { createPublicKey, generateKeyPairSync, verify } from "node:crypto";
import assert from "node:assert/strict";
const { privateKey } = generateKeyPairSync("ec", { namedCurve: "prime256v1" });
const jwk = privateKey.export({ format: "jwk" });
process.env.VAPID_PRIVATE_JWK = JSON.stringify(jwk);
const sent = [];
globalThis.fetch = async (u, o) => { sent.push({ u, o }); return { status: 201 }; };
const base = process.argv[2];
const sub = (await import(`${base}/netlify/functions/subscribe.mjs`)).default;
const post = (body, headers = {}) => sub(new Request("https://x/api/subscribe", { method: "POST", headers, body: typeof body === "string" ? body : JSON.stringify(body) }));
let ok = 0; const t = async (name, fn) => { await fn(); ok++; console.log("  ✔", name); };

await t("rechaza GET", async () => assert.equal((await sub(new Request("https://x/api/subscribe"))).status, 405));
await t("rechaza JSON inválido", async () => assert.equal((await post("{no json")).status, 400));
await t("rechaza host que no es de push (SSRF)", async () => {
  for (const e of ["http://169.254.169.254/latest", "https://localhost/x", "https://evil.com/fcm.googleapis.com", "https://fcm.googleapis.com.evil.com/x", "https://fcm.googleapis.com:8443/x"])
    assert.equal((await post({ subscription: { endpoint: e } })).status, 400, e);
});
await t("rechaza cuerpos enormes", async () => assert.equal((await post({ subscription: { endpoint: "https://fcm.googleapis.com/x" }, pad: "x".repeat(5000) })).status, 400));
process.env.SUBSCRIBE_PIN = "4321";
await t("exige PIN si está configurado", async () => assert.equal((await post({ subscription: { endpoint: "https://fcm.googleapis.com/fcm/send/a" }, pin: "0000" })).status, 403));
await t("acepta suscripción válida con PIN", async () => assert.equal((await post({ subscription: { endpoint: "https://fcm.googleapis.com/fcm/send/a" }, pin: "4321" })).status, 200));
await t("guarda como máximo 5 dispositivos", async () => {
  for (let i = 0; i < 8; i++) await post({ subscription: { endpoint: `https://fcm.googleapis.com/fcm/send/${i}` }, pin: "4321" });
  assert.equal(JSON.parse(globalThis.__mem.get("subs")).length, 5);
});
await t("la función programada ignora endpoints no permitidos guardados a mano", async () => {
  globalThis.__mem.set("subs", JSON.stringify([{ endpoint: "http://10.0.0.1/admin" }, { endpoint: "https://web.push.apple.com/abc" }]));
  const rem = (await import(`${base}/reminders.json`, { with: { type: "json" } })).default;
  const r0 = rem[0]; const [y, mo, d] = r0.f.split("-").map(Number); const [h, mi] = r0.t.split(":").map(Number);
  const at = Date.UTC(y, mo - 1, d, h, mi) + 180 * 60000 + 60000;
  Date.now = () => at; globalThis.__mem.set("lastRun", String(at - 5 * 60000)); sent.length = 0;
  const notify = (await import(`${base}/netlify/functions/notify.mjs`)).default;
  await notify();
  assert.ok(sent.length >= 1 && sent.every((s) => s.u.startsWith("https://web.push.apple.com/")), JSON.stringify(sent.map((s) => s.u)));
  const tok = /t=([^,]+), k=/.exec(sent[0].o.headers.Authorization)[1].split(".");
  const pub = createPublicKey({ key: { kty: "EC", crv: "P-256", x: jwk.x, y: jwk.y }, format: "jwk" });
  assert.ok(verify("sha256", Buffer.from(tok[0] + "." + tok[1]), { key: pub, dsaEncoding: "ieee-p1363" }, Buffer.from(tok[2], "base64url")), "firma VAPID");
});
console.log(`funciones: ${ok} pruebas OK`);
