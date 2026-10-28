"""Importa tu planilla (.xlsx) a los datos propios de la app.

Se usa una sola vez al empezar (o si querés volver a cargar todo desde el Excel).
Solo LEE el archivo: no se conecta con Google ni modifica tu planilla.

Celdas que lee (según cómo tenés armada la planilla):
  AHORROS      cuentas A13:D17 · aportes A22:I44 · meta N12 · dólar I18
  PRESUPUESTO  gastos A13:G30 · dólar M12
  MOVIMIENTOS  desde la fila 13, columnas A:H
  ITINERARIO   versión 1: filas 13-35 · versión 2: filas 75-99 · notas sueltas
"""
from __future__ import annotations

import datetime as dt
import re

EPOCH = dt.date(1899, 12, 30)  # origen de las fechas numéricas de Excel/Sheets

TABS = ("AHORROS", "PRESUPUESTO", "MOVIMIENTOS", "ITINERARIO")
BLOQUES_ITINERARIO = {"1": (13, 35), "2": (75, 99)}


def _norm(texto) -> str:
    return str(texto).strip().upper()


def a1_a_rc(a1: str) -> tuple[int, int]:
    m = re.fullmatch(r"([A-Za-z]+)(\d+)", a1.strip())
    if not m:
        raise ValueError(f"Celda inválida: {a1!r}")
    col = 0
    for ch in m.group(1).upper():
        col = col * 26 + (ord(ch) - 64)
    return int(m.group(2)), col


def a_num(valor, defecto=0.0):
    """Número de una celda; `defecto` si está vacía o no es un número."""
    if valor is None or isinstance(valor, bool):
        return defecto
    if isinstance(valor, (int, float)):
        return float(valor)
    try:
        return float(str(valor).strip().replace(",", "."))
    except ValueError:
        return defecto


def a_fecha(valor):
    """Fecha de una celda: datetime, número de serie o texto ISO / dd/mm/aaaa."""
    if valor is None:
        return None
    if isinstance(valor, dt.datetime):
        return valor.date()
    if isinstance(valor, dt.date):
        return valor
    if isinstance(valor, (int, float)) and not isinstance(valor, bool):
        if 30000 < valor < 80000:
            return EPOCH + dt.timedelta(days=int(valor))
        return None
    texto = str(valor).strip()
    for formato in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return dt.datetime.strptime(texto, formato).date()
        except ValueError:
            pass
    return None


def _iso(valor):
    f = a_fecha(valor)
    return f.isoformat() if f else None


class Grid:
    """Hoja como matriz, con acceso estilo A1 (filas y columnas desde 1)."""

    def __init__(self, filas: list[list]):
        self.filas = filas

    @property
    def n_filas(self) -> int:
        return len(self.filas)

    def rc(self, r: int, c: int):
        try:
            v = self.filas[r - 1][c - 1]
        except IndexError:
            return None
        return None if v == "" else v

    def valor(self, a1: str):
        return self.rc(*a1_a_rc(a1))

    def num(self, a1: str, defecto=0.0) -> float:
        return a_num(self.valor(a1), defecto)

    def texto(self, a1: str) -> str:
        v = self.valor(a1)
        return "" if v is None else str(v).strip()

    def fila_vacia(self, r: int, c1: int, c2: int) -> bool:
        return all(self.rc(r, c) is None for c in range(c1, c2 + 1))


# --------------------------------------------------------------------------
def _cuentas(g: Grid) -> list[dict]:
    salida = []
    for r in range(13, 18):
        nombre = g.texto(f"A{r}")
        if nombre:
            salida.append({"cuenta": nombre, "usd": g.num(f"C{r}"), "pesos": g.num(f"D{r}")})
    return salida


def _aportes(g: Grid) -> list[dict]:
    salida = []
    for r in range(22, 45):
        nombre = g.texto(f"A{r}")
        if not nombre:
            continue
        crudo = g.valor(f"G{r}")
        iso = _iso(crudo)
        salida.append({
            "id": len(salida) + 1,
            "origen": nombre,
            "plan": g.num(f"C{r}"),
            "real": a_num(g.valor(f"E{r}"), None),
            "fecha": iso,
            "fecha_txt": "" if crudo is None or iso else str(crudo).strip(),
            "cuenta": g.texto(f"H{r}"),
            "estado": g.texto(f"I{r}").upper(),
        })
    return salida


def _gastos(g: Grid) -> list[dict]:
    salida = []
    for r in range(13, 31):
        nombre = g.texto(f"A{r}")
        if not nombre:
            continue
        orden = a_num(g.valor(f"D{r}"), None)
        salida.append({
            "id": len(salida) + 1,
            "gasto": nombre,
            "plan": g.num(f"C{r}"),
            "orden": int(orden) if orden else None,
            "estado": "PAGADO" if g.texto(f"E{r}").upper() == "PAGADO" else "",
            "real": a_num(g.valor(f"F{r}"), None),
            "pesos": g.num(f"G{r}"),
        })
    return salida


def _movimientos(g: Grid) -> list[dict]:
    ultima = 0
    for r in range(13, g.n_filas + 1):
        if not g.fila_vacia(r, 1, 8):
            ultima = r
    salida = []
    for r in range(13, ultima + 1):
        if g.fila_vacia(r, 1, 8):
            continue
        salida.append({
            "id": len(salida) + 1,
            "desc": g.texto(f"A{r}"),
            "detalle": g.texto(f"B{r}"),
            "fecha": _iso(g.valor(f"C{r}")),
            "tipo": g.texto(f"D{r}").upper(),
            "cuenta": g.texto(f"E{r}"),
            "origen": g.texto(f"F{r}"),
            "usd": g.num(f"G{r}"),
            "pesos": g.num(f"H{r}"),
        })
    return salida


def _itinerario(g: Grid, version: str) -> list[dict]:
    ini, fin = BLOQUES_ITINERARIO[version]
    dias = []
    for r in range(ini, fin + 1):
        if g.fila_vacia(r, 1, 7):
            continue
        dia = a_num(g.valor(f"B{r}"), None)
        dias.append({
            "id": len(dias) + 1,
            "fecha": _iso(g.valor(f"A{r}")),
            "dia": int(dia) if dia is not None else None,
            "lugar": g.texto(f"C{r}"),
            "desc": g.texto(f"D{r}"),
            "parque": g.texto(f"E{r}"),
            "obs": g.texto(f"F{r}"),
            "analizar": g.texto(f"G{r}"),
            "listo": False,
        })
    return dias


def _notas(g: Grid) -> list[str]:
    notas = [g.texto(f"C{r}") for r in range(38, 68)]
    notas += [g.texto("B113"), g.texto("B115")]
    return [n for n in notas if n]


# --------------------------------------------------------------------------
def desde_xlsx(origen) -> dict:
    """Arma los datos de la app a partir de un .xlsx (ruta o archivo subido)."""
    import openpyxl

    try:
        libro = openpyxl.load_workbook(origen, data_only=True)
    except Exception:
        raise ValueError(
            "No pude leer el archivo. Descargá tu planilla desde Google Sheets como "
            "Excel (.xlsx) y subila de nuevo."
        ) from None

    tablas = {}
    for ws in libro.worksheets:
        tablas[_norm(ws.title)] = Grid(
            [["" if c is None else c for c in fila] for fila in ws.iter_rows(values_only=True)]
        )
    faltan = [t for t in TABS if t not in tablas]
    if faltan:
        raise ValueError(
            "Este archivo no parece ser tu planilla del viaje: falta la pestaña "
            + ", ".join(faltan) + "."
        )

    ah, pr = tablas["AHORROS"], tablas["PRESUPUESTO"]
    mov, it = tablas["MOVIMIENTOS"], tablas["ITINERARIO"]

    cuentas = _cuentas(ah)
    objetivo = ah.num("N12")
    # J12 es el total de ahorros (una fórmula): si viene vacío, el archivo no trae valores calculados
    if cuentas and ah.valor("J12") is None:
        raise ValueError(
            "El archivo no trae los valores calculados de las fórmulas. Descargalo de nuevo "
            "desde Google Sheets (Archivo → Descargar → Microsoft Excel) y subilo otra vez."
        )

    itinerario = {v: _itinerario(it, v) for v in BLOQUES_ITINERARIO}
    primera = next((d["fecha"] for d in itinerario["1"] if d["fecha"]), None)

    return {
        "version": 1,
        "config": {
            "dolar": ah.num("I18") or pr.num("M12") or 1000.0,
            "objetivo": objetivo,
            "fecha_salida": primera,
        },
        "cuentas": cuentas,
        "aportes": _aportes(ah),
        "gastos": _gastos(pr),
        "movimientos": _movimientos(mov),
        "itinerario": itinerario,
        "notas": _notas(it),
    }
