// Solo servicios de push reales: evita que alguien registre una URL cualquiera
// y que la función programada termine llamando a servidores internos (SSRF).
const PUSH_HOSTS = [/^fcm\.googleapis\.com$/, /^updates\.push\.services\.mozilla\.com$/, /^push\.services\.mozilla\.com$/, /^web\.push\.apple\.com$/, /\.notify\.windows\.com$/];
export const pushHostOk = (u) => {
  try { const x = new URL(u); return x.protocol === "https:" && !x.port && PUSH_HOSTS.some((r) => r.test(x.hostname)); }
  catch { return false; }
};
