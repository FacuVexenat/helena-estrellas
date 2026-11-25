#!/usr/bin/env python3
"""Generador de apps de rutina personalizadas.

Uso:  python3 build.py config.json carpeta_salida

Lee un config (perfil, semana tipo, contenidos) y genera una app web instalable
(PWA) lista para publicar: index.html, manifest, service worker, íconos,
reminders.json y, si los avisos están activos, las funciones de Netlify.
"""
import datetime as dt
import json
import math
import os
import re
import shutil
import sys

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
DIAS = ["lun", "mar", "mie", "jue", "vie", "sab", "dom"]
DIAS_LBL = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
HORA_RE = re.compile(r"^([01]?\d|2[0-3]):[0-5]\d$")
HEX_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

DEFAULT_APP = {
    "colores": {"d": "#C2185B", "p": "#F48FB1", "m": "#F8BBD0", "l": "#FCE4EC", "xl": "#FFF5F8", "ink": "#4A0E2B", "g": "#FFC94D"},
    "stickers": ["🦄", "🐱", "🌈", "🦋", "🐰", "🍓", "🐶", "🌻", "🐼", "🍦", "🎀", "🐠", "🌙", "🐞", "🍉", "🦊", "🐣", "🌷", "🧁", "🐨", "🎈", "🐸", "🍒", "🦜", "🌟", "🐬", "🍭", "🏰"],
    "padres_tab": "Ajustes", "padres_emoji": "⚙️", "padres_titulo": "Detalle y ajustes",
    "padres_intro": "Acá está el detalle de cada actividad, el registro de horarios y la voz.",
    "foco_label": "Foco de la semana", "lema": "¡Vamos por todas las estrellas!",
    "cierre_voz": "Cuando termines, tocá la estrella.",
    "avisos": False,
}


class ConfigError(Exception):
    pass


def fail(msg):
    raise ConfigError(msg)


def hora_inicio(h):
    return h.split("–")[0].strip()


def validar(cfg):
    for k in ("perfil", "app", "inicio", "semanas", "semana_tipo"):
        if k not in cfg:
            fail(f"Falta el campo obligatorio «{k}»")
    if not cfg["perfil"].get("nombre"):
        fail("perfil.nombre es obligatorio")
    if not cfg["app"].get("titulo"):
        fail("app.titulo es obligatorio")
    try:
        dt.date.fromisoformat(cfg["inicio"])
    except ValueError:
        fail("inicio debe ser una fecha AAAA-MM-DD")
    if not isinstance(cfg["semanas"], int) or not 1 <= cfg["semanas"] <= 26:
        fail("semanas debe ser un número entre 1 y 26")
    for c, v in cfg["app"].get("colores", {}).items():
        if not HEX_RE.match(str(v)):
            fail(f"Color «{c}» inválido: {v} (usar #RRGGBB)")
    areas, pools = cfg.get("areas", {}), cfg.get("pools", {})
    for dia in DIAS:
        for i, b in enumerate(cfg["semana_tipo"].get(dia, [])):
            donde = f"semana_tipo.{dia}[{i}]"
            if "hora" not in b or "titulo" not in b and "pool" not in b:
                fail(f"{donde}: cada bloque necesita «hora» y «titulo» (o «pool»)")
            h = b["hora"]
            if h not in ("Tarde", "Mañana", "Noche", "Todo el día"):
                for parte in h.split("–"):
                    if not HORA_RE.match(parte.strip()):
                        fail(f"{donde}: hora inválida «{h}» (usar 16:30 o 16:30–16:55)")
            if "pool" in b and b["pool"] not in pools:
                fail(f"{donde}: el pool «{b['pool']}» no existe")
            if "pool" in b and b["pool"] in areas and not pools[b["pool"]]:
                fail(f"pools.{b['pool']} está vacío")
            aviso = b.get("aviso")
            if aviso is not None and not isinstance(aviso, (bool, int)):
                fail(f"{donde}: «aviso» debe ser true o minutos (ej. -15)")
    for p, items in pools.items():
        for j, it in enumerate(items):
            for (t, u) in it.get("videos", []):
                if not str(u).startswith("https://"):
                    fail(f"pools.{p}[{j}]: los links de video deben empezar con https://")


def expandir(cfg):
    inicio = dt.date.fromisoformat(cfg["inicio"])
    areas, pools = cfg.get("areas", {}), cfg.get("pools", {})
    cursor = {p: 0 for p in pools}
    cierre = cfg["app"].get("cierre_voz", DEFAULT_APP["cierre_voz"])
    days = []
    for i in range(cfg["semanas"] * 7):
        d = inicio + dt.timedelta(days=i)
        f, wd = d.isoformat(), d.weekday()
        bloques, ses, usados = [], None, set()
        for b in cfg["semana_tipo"].get(DIAS[wd], []):
            blk = dict(hora=b["hora"], titulo=b.get("titulo", ""), det=b.get("det", ""), voz=b.get("voz") or b.get("titulo", ""),
                       k=None, libre=bool(b.get("libre")), emoji=b.get("emoji"), mision=b.get("mision"))
            item = None
            if "pool" in b:
                lst = pools[b["pool"]]
                item = lst[cursor[b["pool"]] % len(lst)]
                cursor[b["pool"]] += 1
            if item is not None and b["pool"] in areas:
                a = areas[b["pool"]]
                s = dict(area=b["pool"], tema=item["tema"], objetivo=item.get("objetivo", ""), videos=item.get("videos", []),
                         actividad=item.get("actividad", ""), cierre=item.get("cierre", ""), material=item.get("material", ""))
                blk.update(titulo=f"{a['emoji']} {a['nombre']}: {item['tema']}", emoji=a["emoji"], mision=a.get("mision", a["nombre"]),
                           voz=(item.get("voz") or f"Hoy toca {a['nombre']}: {item['tema']}.") + " " + cierre, sesion=s)
                ses = ses or s
            elif item is not None:
                for campo in ("titulo", "det", "voz", "emoji", "palabras"):
                    if campo in item:
                        blk[campo] = item[campo]
            if blk.get("mision") or (item is not None and b["pool"] in areas):
                base = b.get("id") or b.get("pool") or re.sub(r"[^a-z0-9]+", "-", blk["titulo"].lower()).strip("-")[:20] or "m"
                key, n = base, 2
                while key in usados:
                    key, n = f"{base}{n}", n + 1
                usados.add(key)
                blk["k"] = f"{f}:{key}"
                if blk.get("mision") and b.get("pool") not in areas and blk["voz"] == blk["titulo"]:
                    blk["voz"] = blk["titulo"] + ". " + cierre
            blk["aviso"] = b.get("aviso")
            bloques.append(blk)
        days.append(dict(fecha=f, dia=DIAS_LBL[wd], semana=i // 7, bloques=bloques, ses=ses,
                         plaza=None, clase=False))
    etiquetas = cfg.get("foco_semanal", [])
    weeks = []
    for w in range(cfg["semanas"]):
        a, b = inicio + dt.timedelta(days=7 * w), inicio + dt.timedelta(days=7 * w + 6)
        weeks.append([f"Semana {w + 1}", f"{a.day}/{a.month} – {b.day}/{b.month}", etiquetas[w] if w < len(etiquetas) else ""])
    return days, weeks


def recordatorios(days, cfg):
    rem = []
    titulo = cfg["app"]["titulo"]
    for d in days:
        for b in d["bloques"]:
            av = b.get("aviso")
            if av in (None, False) or not b.get("k") or not HORA_RE.match(hora_inicio(b["hora"])):
                continue
            h, m = map(int, hora_inicio(b["hora"]).split(":"))
            t = h * 60 + m + (av if isinstance(av, int) and not isinstance(av, bool) else 0)
            if t < 0:
                continue
            body = b["sesion"]["tema"] if b.get("sesion") else (b.get("det") or "Tocá para ver qué hacer.")
            rem.append(dict(f=d["fecha"], t=f"{t // 60:02d}:{t % 60:02d}", k=b["k"],
                            title=f"{b.get('emoji') or '⭐'} {b.get('mision') or b['titulo']}"[:60], body=body[:140]))
    return rem


def icono(size, path, color, letra, nombre, pad=0.0):
    im = Image.new("RGBA", (size, size), color)
    d = ImageDraw.Draw(im)
    cx, cy, R = size / 2, size * 0.47, size * (0.34 - pad)
    pts = [(cx + (R if i % 2 == 0 else R * 0.45) * math.cos(-math.pi / 2 + i * math.pi / 5),
            cy + (R if i % 2 == 0 else R * 0.45) * math.sin(-math.pi / 2 + i * math.pi / 5)) for i in range(10)]
    d.polygon(pts, fill="#FFFFFF")
    d.text((cx, cy + size * 0.03), letra[:2], fill=color, font=ImageFont.truetype(FONT, int(size * 0.2)), anchor="mm")
    d.text((cx, size * 0.88), nombre[:12], fill="#FFFFFF", font=ImageFont.truetype(FONT, int(size * 0.085)), anchor="mm")
    im.convert("RGB").save(path)


def build(cfg, out):
    validar(cfg)
    app = {**DEFAULT_APP, **cfg["app"]}
    app["colores"] = {**DEFAULT_APP["colores"], **cfg["app"].get("colores", {})}
    perfil = cfg["perfil"]
    nombre = perfil["nombre"]
    slug = re.sub(r"[^a-z0-9]+", "-", (cfg.get("slug") or app["titulo"]).lower()).strip("-")
    days, weeks = expandir(cfg)
    os.makedirs(out, exist_ok=True)
    meta = dict(
        nombre=nombre, apodos=perfil.get("apodos", []), moteProb=perfil.get("prob_apodo", 0.15), emoji=perfil.get("emoji", "🌟"),
        storageKey=f"rutina-{slug}-v1", padresTab=app["padres_tab"], padresEmoji=app["padres_emoji"],
        padresTitulo=app["padres_titulo"], padresIntro=app["padres_intro"], focoLabel=app["foco_label"], lema=app["lema"],
        stickers=app["stickers"], avisos=bool(app["avisos"]),
        elogios=app.get("elogios") or [f"¡Muy bien, {nombre}! Ganaste una estrella.", "¡Genial! Una estrella más.", "¡Bravo! Seguí así."],
        diaCompleto=app.get("dia_completo") or f"¡Increíble, {nombre}! Completaste todas tus misiones.",
        ejemploVoz=(app.get("ejemplo_voz") or [
            "Hoy tenés una misión nueva. Tocala para escuchar qué hacer.",
            "¿Lista para ganar una estrella? ¡Vamos!",
            "Ya casi termina el día. Revisá si te queda alguna misión.",
            "¡Ganaste una estrella! Seguimos.",
            "Paso a paso… se llega lejos. ¿Arrancamos?"]) + [""] * 5,
    )
    areas = {k: [v["nombre"], v["emoji"]] for k, v in cfg.get("areas", {}).items()}
    data = json.dumps(dict(S=days, AREAS=areas, WEEKS=weeks, META=meta), ensure_ascii=False)
    data = data.replace("<", "\\u003c")  # ningún texto del config puede abrir ni cerrar etiquetas dentro del <script>
    html = open(os.path.join(HERE, "app.html"), encoding="utf-8").read()
    c = app["colores"]
    repl = {"__DATA__": data, "__TITULO__": app["titulo"], "__CORTO__": app.get("corto", nombre)}
    repl.update({f"__COLOR_{k.upper()}__": v for k, v in c.items()})
    for k, v in repl.items():
        if k != "__DATA__":
            v = v.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
        html = html.replace(k, v)
    vapid = cfg.get("_vapid_pub", "")
    html = html.replace("__VAPID__", vapid)
    open(f"{out}/index.html", "w", encoding="utf-8").write(html)

    letra = app.get("letra", nombre[:1].upper())
    icono(192, f"{out}/icon-192.png", c["d"], letra, nombre)
    icono(512, f"{out}/icon-512.png", c["d"], letra, nombre)
    icono(180, f"{out}/apple-touch-icon.png", c["d"], letra, nombre)
    icono(512, f"{out}/icon-maskable.png", c["d"], letra, nombre, pad=0.06)
    json.dump({"name": app["titulo"], "short_name": app.get("corto", nombre), "start_url": "./", "scope": "./",
               "display": "standalone", "orientation": "portrait", "background_color": c["xl"], "theme_color": c["d"],
               "lang": "es-AR", "icons": [{"src": "icon-192.png", "sizes": "192x192", "type": "image/png"},
                                          {"src": "icon-512.png", "sizes": "512x512", "type": "image/png"},
                                          {"src": "icon-maskable.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"}]},
              open(f"{out}/manifest.webmanifest", "w"), ensure_ascii=False, indent=1)
    rem = recordatorios(days, cfg)
    json.dump(rem, open(f"{out}/reminders.json", "w"), ensure_ascii=False, indent=0)
    sw = open(os.path.join(HERE, "sw.js"), encoding="utf-8").read().replace("__CACHE__", f"{slug}-{dt.datetime.now():%Y%m%d%H%M}")
    sw = sw.replace("__TITULO__", json.dumps(app["titulo"], ensure_ascii=False))
    open(f"{out}/sw.js", "w", encoding="utf-8").write(sw)
    open(f"{out}/.nojekyll", "w").close()
    if app["avisos"]:
        shutil.copytree(os.path.join(HERE, "netlify"), f"{out}/netlify", dirs_exist_ok=True)
        shutil.copy(os.path.join(HERE, "netlify.toml"), f"{out}/netlify.toml")
        shutil.copy(os.path.join(HERE, "package.json"), f"{out}/package.json")
    return dict(dias=len(days), misiones=sum(1 for d in days for b in d["bloques"] if b.get("k")), avisos=len(rem))


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(2)
    try:
        cfg = json.load(open(sys.argv[1], encoding="utf-8"))
        print(json.dumps(build(cfg, sys.argv[2]), ensure_ascii=False))
    except ConfigError as e:
        print(f"Error en el config: {e}", file=sys.stderr)
        sys.exit(1)
