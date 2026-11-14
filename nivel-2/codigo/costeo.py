"""Costeo de ingredientes por porción - El Término Medio (nivel 2).

Uso: python costeo.py <carpeta_datos> <salida.csv> [fecha_costeo AAAA-MM-DD]
Los pasos 1-4 (lectura de insumos y notas) están en lectura.py.
"""
import json
from decimal import Decimal as D, ROUND_HALF_UP
from lectura import DATA, OUT, FECHA, cat, base_unit, rend, lineas

# 5. Precio efectivo por unidad base: última factura <= fecha (empate: id mayor).
ultima = {}
for (fid, r), ln in lineas.items():
    if ln["fecha"] > FECHA:
        continue
    k = (ln["fecha"], fid)
    if ln["producto"] not in ultima or k > ultima[ln["producto"]][0]:
        ultima[ln["producto"]] = (k, ln)
precio = {}
for prod, (_, ln) in ultima.items():
    q_base = ln["cant"] * cat[(prod, ln["pres"])] - ln.get("devuelto_base", D(0))
    precio[prod] = ln["neto"] / q_base

# 6. Recetas: costo total de la receta (rendimiento declarado). Las subrecetas se prorratean por su tanda.
rec = {r["codigo"]: r for r in json.load(open(DATA / "recetas.json", encoding="utf-8"))}
memo = {}
def costo(c):
    if c in memo:
        return memo[c]
    tot = D(0)
    for i in rec[c]["ingredientes"]:
        q, p = D(str(i["cantidad"])), i["producto"]
        if p in rec:   # preparación: se mide sobre la tanda terminada
            tot += q * costo(p) / D(str(rec[p]["rendimiento"]))
            continue
        assert i["unidad"] == base_unit[p], (c, p, i["unidad"])
        lb, cl = rend[p]
        if i["estado"] == "limpio":
            q /= lb
        elif i["estado"] == "cocido":
            q /= lb * cl
        tot += q * precio[p]
    memo[c] = tot
    return tot

with open(OUT, "w", encoding="utf-8", newline="") as f:
    f.write("plato,costo_por_porcion\n")
    for c, r in rec.items():
        if r["unidad_rendimiento"] == "porción":
            v = (costo(c) / D(str(r["rendimiento"]))).quantize(D("0.01"), ROUND_HALF_UP)
            f.write(f"{c},{v}\n")
