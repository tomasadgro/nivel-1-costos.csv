# Nivel 2 · Costeo de la carta completa

`costeo.py` (con `lectura.py`, que lee catálogo, rendimientos, facturas y notas) calcula el costo de ingredientes por porción de los 50 platos al 31/10/2026 y genera `nivel-2/costos.csv`.

## Entradas

Carpeta de datos del nivel 2: `catalogo.csv`, `rendimientos.csv`, `recetas.json`, `facturas/*.pdf` (40 facturas) y `notas/*.pdf` (4 notas de crédito). Los PDF se leen con `pdftotext -layout` (poppler-utils). El resto usa solo la biblioteca estándar de Python.

```
python costeo.py <carpeta_datos> nivel-2/costos.csv 2026-10-31
```

## Cómo reproduce el cálculo

1. **Facturas.** Cada proveedor ordena las columnas de forma distinta, así que el script lee el encabezado de cada PDF y asigna cantidad, presentación, precio, bonificación y neto según su posición. Se verificó que en los 320 renglones el neto coincide con cantidad × precio × (1 − bonificación).
2. **Notas de crédito.** Solo se aplican las emitidas hasta la fecha de costeo. Cada nota ajusta su factura y renglón de origen (no es una compra nueva). Toda nota resta su importe del neto; la devolución además resta las unidades devueltas, convertidas con el catálogo. Por eso una nota sobre una factura que ya no es la vigente no cambia el costo.
3. **Precio efectivo.** Para cada producto se toma el renglón de la última factura con fecha ≤ 31/10/2026 (a igual fecha gana el identificador mayor) y se divide el neto ajustado por la cantidad en unidad base (g, ml o unidad) según la equivalencia del catálogo para esa presentación y ese producto.
4. **Cantidad bruta.** El estado del ingrediente define cuánto hay que comprar: `bruto` se usa tal cual, `limpio` se divide por limpio/bruto y `cocido` por (limpio/bruto × cocido/limpio).
5. **Preparaciones.** Las subrecetas (S01–S15) se costean por tanda y se imputan proporcionalmente a la cantidad usada sobre la tanda terminada, en forma recursiva. El agua de red no tiene costo.
6. **Redondeo.** Todo se calcula con `Decimal` sin redondeos intermedios; el resultado se redondea a dos decimales, mitad hacia arriba. Las subrecetas no se incluyen como filas.
