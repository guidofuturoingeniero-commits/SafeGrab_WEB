#!/usr/bin/env python3
"""Pone los datos de tu negocio (datos_negocio.json) en todas las páginas .html de esta carpeta.

Uso (en PowerShell, dentro de la carpeta de la web):
    python aplicar_datos.py

Se puede correr las veces que quieras: si cambias un dato, vuelve a correrlo.
No cambia nada si algún dato obligatorio falta o está mal escrito: te dice cuál.
"""
import html
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLACEHOLDER = "[por completar]"


def fail(msgs):
    print("\nNo se cambió ninguna página. Corrige esto en datos_negocio.json:\n")
    for m in msgs:
        print("  -", m)
    sys.exit(1)


def digits(s):
    return re.sub(r"\D", "", s or "")


def pretty_phone(s):
    d = digits(s)
    if len(d) == 11 and d.startswith("51"):          # +51 999 999 999
        return f"+51 {d[2:5]} {d[5:8]} {d[8:]}"
    return ("+" + d) if d else ""


def load():
    try:
        raw = json.loads((HERE / "datos_negocio.json").read_text(encoding="utf-8"))
    except FileNotFoundError:
        fail(["No encuentro datos_negocio.json en esta carpeta."])
    except json.JSONDecodeError as e:
        fail([f"datos_negocio.json tiene un error de escritura (comillas o comas): {e}"])
    return {k: (v.strip() if isinstance(v, str) else v) for k, v in raw.items() if not k.startswith("_")}


def validate(d):
    errs = []
    if len(d.get("razon_social", "")) < 3:
        errs.append("razon_social: escribe el nombre o razón social con el que vendes.")
    if not re.fullmatch(r"\d{11}", d.get("ruc", "")):
        errs.append("ruc: deben ser 11 dígitos, sin espacios.")
    if len(d.get("direccion", "")) < 8:
        errs.append("direccion: escribe calle, distrito y ciudad.")
    if not 9 <= len(digits(d.get("whatsapp", ""))) <= 13:
        errs.append("whatsapp: con código de país y solo números. Ej.: 51999999999")
    if d.get("telefono") and not 7 <= len(digits(d["telefono"])) <= 13:
        errs.append("telefono: si lo pones, que tenga entre 7 y 13 dígitos (o déjalo vacío).")
    if not re.fullmatch(r"[^\s@<>\"]+@[^\s@<>\"]+\.[^\s@<>\"]+", d.get("correo", "")):
        errs.append("correo: no parece un correo válido.")
    return errs


def values(d):
    wa = digits(d["whatsapp"])
    tel = digits(d.get("telefono", ""))
    if tel and len(tel) <= 9:                         # sin código de país: se asume Perú
        tel = "51" + tel
    return {
        "text": {
            "razon_social": d["razon_social"], "ruc": d["ruc"], "direccion": d["direccion"],
            "whatsapp_txt": pretty_phone(wa), "telefono_txt": d.get("telefono", ""),
            "correo": d["correo"], "horario": d.get("horario", ""),
        },
        "href": {
            "whatsapp": f"https://wa.me/{wa}",
            "telefono": f"tel:+{tel}" if tel else "#",
            "correo": f"mailto:{d['correo']}",
        },
        "show": {"telefono": bool(tel), "horario": bool(d.get("horario"))},
    }


def apply(src, v):
    # 1) Textos:  <span data-sg="ruc">…</span>
    def text(m):
        key = m.group("key")
        return m.group("open") + html.escape(v["text"].get(key, ""), quote=False) + m.group("close")
    src = re.sub(
        r'(?P<open><(?P<tag>span|b|strong|a|p|li|dd|dt|h3)\b[^>]*\sdata-sg="(?P<key>[a-z_]+)"[^>]*>)'
        r'(?P<body>.*?)(?P<close></(?P=tag)>)', text, src, flags=re.S)

    # 2) Enlaces:  <a data-sg-href="whatsapp" href="…">
    def href(m):
        return m.group(1) + html.escape(v["href"].get(m.group("key"), "#"), quote=True) + m.group(3)
    src = re.sub(r'(<a\b[^>]*\sdata-sg-href="(?P<key>[a-z_]+)"[^>]*?\shref=")([^"]*)(")',
                 lambda m: m.group(1) + html.escape(v["href"].get(m.group("key"), "#"), quote=True) + m.group(4), src)

    # 3) Mostrar u ocultar bloques opcionales
    def show(m):
        tag = re.sub(r"\shidden(?:=\"\")?(?=[\s>])", "", m.group(0))
        if not v["show"].get(m.group("key"), False):
            tag = tag[:-1] + " hidden>"
        return tag
    src = re.sub(r'<[a-z0-9]+\b[^>]*\sdata-sg-show="(?P<key>[a-z_]+)"[^>]*>', show, src)

    # 4) Correo de las páginas legales
    src = re.sub(r'(var SG_CONTACT = ")[^"]*(";)', lambda m: m.group(1) + v["text"]["correo"] + m.group(2), src)
    return src


def main():
    d = load()
    errs = validate(d)
    if errs:
        fail(errs)
    v = values(d)
    pages = sorted(HERE.glob("*.html"))
    if not pages:
        fail(["No hay páginas .html en esta carpeta."])
    changed = 0
    for p in pages:
        old = p.read_text(encoding="utf-8")
        new = apply(old, v)
        if new != old:
            p.write_text(new, encoding="utf-8")
            changed += 1
        left = new.count(PLACEHOLDER)
        print(f"  {p.name:<20} {'actualizada' if new != old else 'sin cambios'}"
              + (f"   ¡quedan {left} marcas «{PLACEHOLDER}»!" if left else ""))
    print(f"\nListo: {changed} página(s) actualizada(s). Revisa el pie de página y la sección Contacto de index.html,")
    print("y súbelas a GitHub (git add . ; git commit -m \"datos del negocio\" ; git push).")


if __name__ == "__main__":
    main()
