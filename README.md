# Las estrellas de Helena

App web instalable (PWA) con la rutina diaria de Helena: misiones con estrellas, voz, registro de horarios y avisos.

- Sitio estático en la raíz (sin build).
- `netlify/functions/subscribe.mjs`: guarda la suscripción de avisos del teléfono (Netlify Blobs).
- `netlify/functions/notify.mjs`: función programada cada 5 minutos que envía los avisos de `reminders.json` (hora Argentina).
- Variable de entorno necesaria en Netlify: `VAPID_PRIVATE_JWK` (clave privada de los avisos).
