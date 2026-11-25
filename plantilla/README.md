# Plantilla de apps de rutina

Genera una app web instalable (PWA) personalizada a partir de un archivo de configuración.

```bash
python3 plantilla/build.py plantilla/ejemplos/ninos.json salida/
python3 plantilla/tests/run_tests.py   # QA + seguridad (necesita Chrome y Node)
```

## Config (resumen)

| Campo | Qué es |
|---|---|
| `perfil` | `nombre`, `apodos` (se usan muy de vez en cuando), `prob_apodo`, `emoji` |
| `app` | `titulo`, `corto`, `letra` (ícono), `colores` (#RRGGBB: d, p, m, l, xl, ink, g), `stickers`, `padres_tab`/`padres_emoji`/`padres_titulo`/`padres_intro`, `foco_label`, `lema`, `elogios`, `dia_completo`, `cierre_voz`, `ejemplo_voz` (5 frases), `avisos` |
| `inicio`, `semanas` | Fecha de arranque (AAAA-MM-DD, idealmente lunes) y cantidad de semanas (1–26) |
| `foco_semanal` | Etiqueta por semana (letra de la semana, objetivo, etc.) |
| `areas` | Áreas de sesión: `{"ENG": {"nombre", "emoji", "mision"}}` |
| `semana_tipo` | Bloques por día (`lun`…`dom`). Bloque: `hora` (16:30 o 16:30–16:55), `titulo`, `emoji`, `voz`, `det`; `mision` lo vuelve tildable; `id` para su clave; `libre: true`; `pool` toma el siguiente contenido; `aviso: true` o minutos (ej. `-15`) |
| `pools` | Contenidos que rotan. Pool de área: `tema`, `objetivo`, `videos` [[texto, url https]], `actividad`, `cierre`, `material`, `voz`. Otro pool: `titulo`, `det`, `voz`, `palabras` [[es, en, emoji]] |

Texto entre `[corchetes]` en `voz` se pronuncia con voz en inglés.

## Publicar
- Sin avisos: cualquier hosting estático (GitHub Pages, Cloudflare Pages, Netlify).
- Con avisos: Netlify (funciones + Blobs). Variables: `VAPID_PRIVATE_JWK` (obligatoria), `SUBSCRIBE_PIN` (recomendada), `VAPID_SUBJECT` (opcional). La clave pública va en el config como `_vapid_pub`.

## Privacidad
No publicar en repos públicos datos que identifiquen a un menor (apellido, colegio, dirección, horarios con lugar). Para clientes, usar repos privados.
