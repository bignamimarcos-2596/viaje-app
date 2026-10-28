"""Datos propios de la app: cálculos y cambios.

Los datos son un diccionario simple (se guardan como JSON). Ninguna función de acá
toca Excel, Google ni la red; los cambios devuelven una copia nueva y no modifican
el original.
"""
from __future__ import annotations

import copy
import datetime as dt
import re

MESES = {
    "ENERO": 1, "FEBRERO": 2, "MARZO": 3, "ABRIL": 4, "MAYO": 5, "JUNIO": 6,
    "JULIO": 7, "AGOSTO": 8, "SEPTIEMBRE": 9, "OCTUBRE": 10,
    "NOVIEMBRE": 11, "DICIEMBRE": 12,
}
CLAVES = ("config", "cuentas", "aportes", "gastos", "movimientos", "itinerario", "notas")


def validar(d) -> None:
    if (
        not isinstance(d, dict)
        or any(k not in d for k in CLAVES)
        or not isinstance(d["itinerario"], dict)
        or not all(v in d["itinerario"] for v in ("1", "2"))
    ):
        raise ValueError("El archivo de datos no tiene el formato esperado.")


def a_fecha(s):
    """Fecha desde un texto ISO (aaaa-mm-dd); None si no hay."""
    if not s:
        return None
    try:
        return dt.date.fromisoformat(str(s))
    except ValueError:
        return None


# --------------------------------------------------------------------------
# Cálculos
# --------------------------------------------------------------------------
def dias_para(d: dict, hoy: dt.date):
    salida = a_fecha(d["config"].get("fecha_salida"))
    return (salida - hoy).days if salida else None


def resumen_ahorros(d: dict) -> dict:
    cfg = d["config"]
    usd = sum(c["usd"] for c in d["cuentas"])
    pesos = sum(c["pesos"] for c in d["cuentas"])
    dolar = cfg["dolar"]
    equivalente = usd + (pesos / dolar if dolar else 0.0)
    return {
        "usd": usd, "pesos": pesos, "dolar": dolar, "objetivo": cfg["objetivo"],
        "equivalente_usd": equivalente, "falta": cfg["objetivo"] - equivalente,
    }


def mes_de(nombre: str):
    """(año, mes) si el nombre del aporte termina en 'MES AA' (ej. 'JULIO 26')."""
    m = re.search(r"(" + "|".join(MESES) + r")\s+(\d{2})\b", str(nombre).strip().upper())
    return (2000 + int(m.group(2)), MESES[m.group(1)]) if m else None


def plan_vs_real(d: dict, hoy: dt.date) -> dict:
    """Plan vs real de los aportes mensuales hasta el mes actual (los demás son 'extras')."""
    limite = (hoy.year, hoy.month)
    con_mes = [(a, mes_de(a["origen"])) for a in d["aportes"]]
    hasta_hoy = [a for a, m in con_mes if m and m <= limite]
    extras = [a for a, m in con_mes if not m]
    plan = sum(a["plan"] for a in hasta_hoy)
    real = sum(a["real"] or 0.0 for a in hasta_hoy)
    return {
        "plan_a_hoy": plan, "real_a_hoy": real, "diferencia": real - plan,
        "extras_plan": sum(a["plan"] for a in extras),
        "extras_real": sum(a["real"] or 0.0 for a in extras),
    }


def costo_usd(g: dict, dolar: float) -> float:
    """Costo real en USD (dólares + pesos convertidos); si no hay real, el presupuestado."""
    if g["real"] is not None or g["pesos"]:
        return (g["real"] or 0.0) + (g["pesos"] / dolar if dolar else 0.0)
    return g["plan"]


def resumen_presupuesto(d: dict) -> dict:
    dolar = d["config"]["dolar"]
    gastos = d["gastos"]
    pagados = [g for g in gastos if g["estado"] == "PAGADO"]
    pendientes = [g for g in gastos if g["estado"] != "PAGADO"]
    pendientes.sort(key=lambda g: (g["orden"] is None, g["orden"] or 0, g["id"]))
    return {
        "total": sum(g["plan"] for g in gastos),
        "pagado_usd": sum(costo_usd(g, dolar) for g in pagados),
        "falta_pagar": sum(g["plan"] for g in pendientes),
        "pendientes": pendientes,
    }


def totales_movimientos(d: dict) -> dict:
    def suma(tipo, campo):
        return sum(m[campo] for m in d["movimientos"] if m["tipo"] == tipo)

    return {
        "ingresos_usd": suma("INGRESO", "usd"), "egresos_usd": suma("EGRESO", "usd"),
        "ingresos_pesos": suma("INGRESO", "pesos"), "egresos_pesos": suma("EGRESO", "pesos"),
    }


# --------------------------------------------------------------------------
# Cambios (devuelven una copia nueva)
# --------------------------------------------------------------------------
def _t(x, largo=300) -> str:
    return str(x or "").strip()[:largo]


def _sig(lista: list) -> int:
    return max((x["id"] for x in lista), default=0) + 1


def _buscar(lista: list, ident: int) -> dict:
    for x in lista:
        if x["id"] == ident:
            return x
    raise ValueError("No encontré ese elemento (puede que los datos hayan cambiado).")


def guardar_saldo(d, nombre, usd, pesos):
    d = copy.deepcopy(d)
    nombre = _t(nombre, 60)
    if not nombre:
        raise ValueError("Escribí el nombre de la cuenta.")
    for c in d["cuentas"]:
        if c["cuenta"] == nombre:
            c["usd"], c["pesos"] = float(usd), float(pesos)
            break
    else:
        d["cuentas"].append({"cuenta": nombre, "usd": float(usd), "pesos": float(pesos)})
    return d


def registrar_aporte(d, aporte_id, nombre, usd, fecha: dt.date, cuenta):
    """Registra lo comprado en un aporte planificado (aporte_id) o crea uno nuevo (aporte_id=0)."""
    d = copy.deepcopy(d)
    if aporte_id:
        a = _buscar(d["aportes"], aporte_id)
    else:
        nombre = _t(nombre, 80)
        if not nombre:
            raise ValueError("Escribí un nombre para el ingreso nuevo.")
        a = {"id": _sig(d["aportes"]), "origen": nombre.upper(), "plan": 0.0}
        d["aportes"].append(a)
    a.update(real=float(usd), fecha=fecha.isoformat(), fecha_txt="",
             cuenta=_t(cuenta, 40), estado="COMPRADO")
    return d


def editar_gasto(d, gid, plan, pagado, real, orden):
    d = copy.deepcopy(d)
    g = _buscar(d["gastos"], gid)
    g["plan"] = float(plan)
    g["estado"] = "PAGADO" if pagado else ""
    g["real"] = float(real) if real and real > 0 else None
    g["orden"] = int(orden) if orden else None
    return d


def agregar_gasto(d, nombre, plan, orden):
    d = copy.deepcopy(d)
    nombre = _t(nombre, 80)
    if not nombre:
        raise ValueError("Escribí el nombre del gasto.")
    d["gastos"].append({
        "id": _sig(d["gastos"]), "gasto": nombre.upper(), "plan": float(plan),
        "orden": int(orden) if orden else None, "estado": "", "real": None, "pesos": 0.0,
    })
    return d


def agregar_movimiento(d, desc, detalle, fecha: dt.date, tipo, cuenta, origen, usd, pesos):
    d = copy.deepcopy(d)
    if not _t(desc):
        raise ValueError("Escribí una descripción.")
    if tipo not in ("INGRESO", "EGRESO"):
        raise ValueError("El tipo tiene que ser ingreso o egreso.")
    d["movimientos"].append({
        "id": _sig(d["movimientos"]), "desc": _t(desc, 120), "detalle": _t(detalle, 120),
        "fecha": fecha.isoformat(), "tipo": tipo, "cuenta": _t(cuenta, 60),
        "origen": _t(origen, 80), "usd": float(usd or 0.0), "pesos": float(pesos or 0.0),
    })
    return d


def borrar_movimiento(d, mid):
    d = copy.deepcopy(d)
    _buscar(d["movimientos"], mid)
    d["movimientos"] = [m for m in d["movimientos"] if m["id"] != mid]
    return d


def editar_dia(d, version, did, desc, parque, obs, analizar, listo):
    d = copy.deepcopy(d)
    dia = _buscar(d["itinerario"][str(version)], did)
    dia.update(desc=_t(desc, 200), parque=_t(parque, 60).upper(), obs=_t(obs, 500),
               analizar=_t(analizar, 500), listo=bool(listo))
    return d


def agregar_nota(d, texto):
    d = copy.deepcopy(d)
    if not _t(texto, 500):
        raise ValueError("Escribí la nota.")
    d["notas"].append(_t(texto, 500))
    return d


def borrar_nota(d, indice):
    d = copy.deepcopy(d)
    if not 0 <= indice < len(d["notas"]):
        raise ValueError("No encontré esa nota.")
    del d["notas"][indice]
    return d


def cambiar_config(d, dolar, objetivo, fecha_salida: dt.date):
    d = copy.deepcopy(d)
    if dolar <= 0:
        raise ValueError("El dólar tiene que ser mayor a cero.")
    d["config"].update(dolar=float(dolar), objetivo=float(objetivo),
                       fecha_salida=fecha_salida.isoformat())
    return d
