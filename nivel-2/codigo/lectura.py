"""Lectura de insumos (pasos 1-4): catálogo, rendimientos, facturas y notas de crédito.
Lo importa costeo.py.

Uso: python costeo.py <carpeta_datos> <salida.csv> [fecha_costeo AAAA-MM-DD]
Requiere `pdftotext` (poppler-utils) para leer facturas y notas en PDF.
"""
import csv, json, re, subprocess, sys
from decimal import Decimal as D, ROUND_HALF_UP
from pathlib import Path

DATA = Path(sys.argv[1]); OUT = Path(sys.argv[2])
FECHA = sys.argv[3] if len(sys.argv) > 3 else "2026-10-31"

def num(s):  # "1.234,56" o "1234,56" -> Decimal
    return D(s.replace(".", "").replace(",", ".")) if "," in s else D(s)

def pdf_text(p):
    return subprocess.run(["pdftotext", "-layout", str(p), "-"], capture_output=True, text=True, check=True).stdout

# 1. Catálogo: cantidad base por (producto, presentación). Cada producto tiene su propia equivalencia.
cat = {(r["producto"], r["presentacion"]): D(r["cantidad_base"])
       for r in csv.DictReader(open(DATA / "catalogo.csv", encoding="utf-8"))}
base_unit = {r["producto"]: r["unidad_base"] for r in csv.DictReader(open(DATA / "catalogo.csv", encoding="utf-8"))}

# 2. Rendimientos: limpio/bruto y cocido/limpio.
rend = {r["producto"]: (D(r["limpio_sobre_bruto"]), D(r["cocido_sobre_limpio"]))
        for r in csv.DictReader(open(DATA / "rendimientos.csv", encoding="utf-8"))}

# 3. Facturas. El orden de columnas varía por proveedor: se lee el encabezado de cada PDF.
COLS = {"Cant.": "cant", "Unidad": "pres", "P. unitario": "precio", "Bonif.%": "bonif", "Neto": "neto"}
lineas = {}   # (factura, renglon) -> dict
facturas = {} # factura -> fecha
for p in sorted((DATA / "facturas").glob("*.pdf")):
    t = pdf_text(p)
    fid = re.search(r"Factura\s+(\S+)", t).group(1)
    fecha = re.search(r"Fecha:\s*(\d{4}-\d{2}-\d{2})", t).group(1)
    facturas[fid] = fecha
    head = next(l for l in t.splitlines() if l.strip().startswith("R ") and "Código" in l)
    orden = [COLS[c] for c in sorted(COLS, key=lambda c: head.index(c))]
    for l in t.splitlines():
        m = re.match(r"\s*(\d+)\s+([A-Z]\d{2})\s+(.+)$", l)
        if not m:
            continue
        toks = m.group(3).split()
        vals = toks[-5:]  # las últimas 5 columnas; la descripción puede tener espacios
        d = dict(zip(orden, vals))
        lineas[(fid, int(m.group(1)))] = {
            "factura": fid, "fecha": fecha, "producto": m.group(2), "pres": d["pres"],
            "cant": num(d["cant"]), "neto": num(d["neto"]),
            "precio": num(d["precio"]), "bonif": num(d["bonif"])}

# 4. Notas de crédito emitidas hasta la fecha de costeo: ajustan su factura y renglón.
for p in sorted((DATA / "notas").glob("*.pdf")) if (DATA / "notas").exists() else []:
    t = pdf_text(p)
    fecha = re.search(r"Fecha:\s*(\d{4}-\d{2}-\d{2})", t).group(1)
    if fecha > FECHA:
        continue
    fac = re.search(r"Factura asociada:\s*(\S+)", t).group(1)
    ren = int(re.search(r"Renglón:\s*(\d+)", t).group(1))
    concepto = re.search(r"Concepto:\s*(\S+)", t).group(1).lower()
    qm = re.search(r"Cantidad devuelta:\s*([\d.,]+)\s*(\S+)", t)
    imp = num(re.search(r"Importe acreditado:\s*\$\s*([\d.,]+)", t).group(1))
    ln = lineas[(fac, ren)]
    ln["neto"] -= imp                        # toda nota resta importe
    if concepto.startswith("devoluci"):      # la devolución además resta unidades
        q, u = num(qm.group(1)), qm.group(2)
        ln["devuelto_base"] = ln.get("devuelto_base", D(0)) + q * cat[(ln["producto"], u)]

