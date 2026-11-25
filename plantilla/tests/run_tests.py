#!/usr/bin/env python3
"""QA y seguridad de la plantilla. Uso: python3 tests/run_tests.py"""
import json, os, re, shutil, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
import build
CHROME = shutil.which("google-chrome") or shutil.which("chromium")
ok = fail = 0
def check(name, cond, extra=""):
    global ok, fail
    print(("  ✔ " if cond else "  ✘ ") + name + (f" — {extra}" if extra and not cond else ""))
    ok += bool(cond); fail += (not cond)

def run_page(html_path, js):
    src = open(html_path, encoding="utf-8").read()
    assert "render(); mirror();\n" in src
    src = src.replace("render(); mirror();\n", "render(); mirror(); try{ " + js + " }catch(e){ document.title='ERR '+e.message }\n", 1)
    p = html_path.replace("index.html", "_t.html"); open(p, "w", encoding="utf-8").write(src)
    out = subprocess.run([CHROME, "--headless=new", "--no-sandbox", "--disable-gpu", "--virtual-time-budget=4000", "--dump-dom", "file://" + p],
                         capture_output=True, text=True, timeout=90).stdout
    m = re.search(r"<title>([^<]*)</title>", out); return (m.group(1) if m else ""), out

print("1) Validación del config")
base = json.load(open(os.path.join(ROOT, "ejemplos/ninos.json")))
casos = [("hora inválida", lambda c: c["semana_tipo"]["lun"].__setitem__(0, {"hora": "25:99", "titulo": "x"})),
         ("pool inexistente", lambda c: c["semana_tipo"]["lun"].append({"hora": "10:00", "pool": "NOEXISTE"})),
         ("color inválido", lambda c: c["app"].__setitem__("colores", {"d": "red;}</style>"})),
         ("video sin https", lambda c: c["pools"]["ABC"][0].__setitem__("videos", [["x", "javascript:alert(1)"]])),
         ("semanas fuera de rango", lambda c: c.__setitem__("semanas", 500)),
         ("falta el nombre", lambda c: c["perfil"].__setitem__("nombre", ""))]
for nombre, mut in casos:
    c = json.loads(json.dumps(base)); mut(c)
    try: build.validar(c); check(f"rechaza {nombre}", False, "no dio error")
    except build.ConfigError: check(f"rechaza {nombre}", True)

print("2) Generación y funcionamiento de cada ejemplo")
tmp = tempfile.mkdtemp()
for ej in ("ninos", "gym", "adulto"):
    out = os.path.join(tmp, ej); r = build.build(json.load(open(os.path.join(ROOT, f"ejemplos/{ej}.json"))), out)
    check(f"{ej}: genera {r['dias']} días y {r['misiones']} misiones", r["dias"] > 0 and r["misiones"] > 0)
    title, _ = run_page(os.path.join(out, "index.html"), """
      idx=1; render(); const s=document.querySelector('.mission .star'); s.click();
      const k=s.dataset.k; if(!st[k]||!/^\\d\\d:\\d\\d$/.test(st[k].t)) throw new Error('no guardó la hora');
      for (const t of ['premios','semana','papis','hoy']) { tab=t; render(); }
      tab='papis'; render(); const inp=document.querySelector('[data-edit]'); inp.value='06:05'; inp.onchange();
      if (st[k].t!=='06:05') throw new Error('no editó la hora');
      tab='hoy'; idx=1; render(); const first=document.querySelector('.tl div span').textContent;
      if (!first.startsWith('06:05')) throw new Error('no reordenó: '+first);
      document.querySelector('.mission .star').click(); if (st[k]) throw new Error('no desmarcó');
      document.title='OK';""")
    check(f"{ej}: marcar, registrar hora, editar, reordenar y desmarcar", title == "OK", title)
    check(f"{ej}: sin datos personales sensibles en reminders.json", "@" not in open(os.path.join(out, "reminders.json")).read())

print("3) Seguridad: inyección de HTML/JS desde el config")
c = json.loads(json.dumps(base))
evil = "</script><script>document.title='PWNED'</script><img src=x onerror=\"document.title='PWNED'\">"
c["perfil"]["nombre"] = "Mía" + evil; c["app"]["titulo"] = "T" + evil
c["semana_tipo"]["lun"][1]["titulo"] = evil; c["semana_tipo"]["lun"][1]["mision"] = evil; c["semana_tipo"]["lun"][1]["det"] = evil
c["pools"]["ABC"][0]["tema"] = evil
out = os.path.join(tmp, "evil"); build.build(c, out)
html = open(os.path.join(out, "index.html"), encoding="utf-8").read()
check("los datos no pueden abrir ni cerrar etiquetas <script>", html.count("<script") == 1 and html.count("</script>") == 1)
title, dom = run_page(os.path.join(out, "index.html"), """
  for (const t of ['hoy','premios','semana','papis']) { tab=t; for (let i=0;i<7;i++){ idx=i; render(); } }
  document.querySelectorAll('[data-open]').forEach(b=>b.click());
  if (document.querySelector('img[onerror]')) throw new Error('img inyectada en el DOM');
  if (document.title!=='PWNED') document.title='OK';""")
check("ningún texto del config se ejecuta como código (XSS)", title == "OK", title)

print("4) Seguridad: archivos publicados")
pub = os.path.join(tmp, "ninos")
todo = "".join(open(os.path.join(dp, f), errors="ignore").read() for dp, _, fs in os.walk(pub) for f in fs if not f.endswith(".png"))
check("no se publica ninguna clave privada", '"d":' not in todo and "PRIVATE" not in todo.replace("VAPID_PRIVATE_JWK", ""))
check("CSP presente en la app", "Content-Security-Policy" in todo)
check("sin tokens ni contraseñas en los archivos", not re.search(r"(ghp_|sk-[A-Za-z0-9]{10}|password\s*=)", todo))

print("5) Funciones de avisos (Node)")
fdir = os.path.join(tmp, "ninos"); nm = os.path.join(fdir, "node_modules"); os.makedirs(nm, exist_ok=True)
shutil.copytree(os.path.join(HERE, "stubs/@netlify"), os.path.join(nm, "@netlify"), dirs_exist_ok=True)
r = subprocess.run(["node", os.path.join(HERE, "functions.test.mjs"), fdir], capture_output=True, text=True, timeout=60)
print(r.stdout.rstrip()); check("funciones de avisos", r.returncode == 0, r.stderr[-400:])

print(f"\nResultado: {ok} OK, {fail} con error")
sys.exit(1 if fail else 0)
