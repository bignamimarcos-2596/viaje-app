"""App del viaje Disney · Universal · Miami 2027.

Tiene sus propios datos (guardados en un repositorio privado de GitHub). Tu planilla
de Excel/Google Sheets solo se usa una vez para cargarlos y la app nunca la modifica.
Para correrla: `streamlit run app.py` (ver README.md).
"""
from __future__ import annotations

import datetime as dt
import hmac
import json
import os

import pandas as pd
import streamlit as st

import almacen
import datos
import estilo
import importar

st.set_page_config(page_title="Viaje Disney 2027", page_icon="🏰", layout="centered")
estilo.aplicar()

DIAS_SEMANA = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
CUENTAS_APORTE = ["PROV", "BNA", "MANO", "BIP", "PAYPAL", "MASTER CARD", "MERCADO PAGO"]
NUEVA = "➕ Nueva cuenta"


# --------------------------------------------------------------------------
# Utilidades
# --------------------------------------------------------------------------
def secreto(nombre, defecto=None):
    try:
        return st.secrets[nombre]
    except Exception:  # sin archivo de secretos o clave inexistente
        return defecto


def hoy() -> dt.date:
    try:
        from zoneinfo import ZoneInfo

        return dt.datetime.now(ZoneInfo("America/Argentina/Buenos_Aires")).date()
    except Exception:
        return dt.date.today()


def num(x, dec=0) -> str:
    """Número con formato argentino: 12.345,67"""
    return f"{x:,.{dec}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def usd(x, dec=0) -> str:
    return f"USD {num(x, dec)}"


def fecha_corta(f) -> str:
    if isinstance(f, str):
        f = datos.a_fecha(f)
    return f.strftime("%d/%m/%Y") if f else ""


# --------------------------------------------------------------------------
# Acceso, almacenamiento y estado
# --------------------------------------------------------------------------
def en_vivo() -> bool:
    return bool(secreto("github_token") and secreto("github_repo"))


def pedir_clave():
    """Con GitHub conectado la app maneja tus finanzas: exige una clave."""
    clave = secreto("app_password")
    if clave is None:
        if en_vivo():
            st.error("Falta configurar `app_password` en los secretos de la app.")
            st.stop()
        return
    if st.session_state.get("autorizado"):
        return
    estilo.encabezado()
    ingreso = st.text_input("Clave", type="password")
    if ingreso:
        if hmac.compare_digest(str(ingreso).encode(), str(clave).encode()):
            st.session_state["autorizado"] = True
            st.rerun()
        else:
            st.error("Clave incorrecta")
    st.stop()


@st.cache_resource(show_spinner=False)
def obtener_almacen():
    token, repo = secreto("github_token"), secreto("github_repo")
    if token and repo:
        return almacen.GitHubStore(
            str(token), str(repo),
            str(secreto("github_branch", "main")), str(secreto("github_path", "datos.json")),
        )
    ruta = os.environ.get("DATOS_LOCAL") or secreto("datos_local") or "datos_local.json"
    return almacen.LocalStore(ruta)


def cargar_datos():
    """Lee los datos una vez por sesión (o cuando se pide recargar)."""
    if st.session_state.get("cargado"):
        return
    d, token = obtener_almacen().cargar()
    if d is not None:
        datos.validar(d)
    st.session_state["datos"] = d
    st.session_state["token"] = token
    st.session_state["cargado"] = True


def aplicar(nuevo: dict, aviso: str):
    """Guarda `nuevo` y, si salió bien, lo deja como estado actual."""
    try:
        token = obtener_almacen().guardar(nuevo, st.session_state.get("token"))
    except almacen.ErrorAlmacen as e:
        st.error(str(e))
        return
    st.session_state["datos"] = nuevo
    st.session_state["token"] = token
    st.session_state["aviso"] = aviso
    st.rerun()


def intentar(funcion, aviso: str, *args):
    """Aplica un cambio de datos.py y muestra el error si los datos no son válidos."""
    try:
        nuevo = funcion(st.session_state["datos"], *args)
    except ValueError as e:
        st.warning(str(e))
        return
    aplicar(nuevo, aviso)


# --------------------------------------------------------------------------
# Pantallas
# --------------------------------------------------------------------------
def pantalla_importar():
    estilo.encabezado()
    st.write(
        "Para empezar, subí tu planilla en Excel (.xlsx). Se copia **una sola vez** y "
        "después la app trabaja con sus propios datos: no toca tu Google Sheets."
    )
    st.caption("En Google Sheets: Archivo → Descargar → Microsoft Excel (.xlsx).")
    archivo = st.file_uploader("Planilla (.xlsx)", type=["xlsx"])
    if archivo is not None and st.button("Importar"):
        try:
            nuevo = importar.desde_xlsx(archivo)
        except ValueError as e:
            st.error(str(e))
            return
        aplicar(nuevo, "Listo: importé tu planilla. Desde ahora la app usa sus propios datos.")


def pantalla_inicio(d):
    if d["config"].get("fecha_salida"):
        st.caption(f"Salida: {fecha_corta(d['config']['fecha_salida'])}")

    st.subheader("Ahorros")
    ah = datos.resumen_ahorros(d)
    avance = ah["equivalente_usd"] / ah["objetivo"] if ah["objetivo"] else 0.0
    st.progress(max(0.0, min(1.0, avance)), text=f"{avance * 100:.0f}% de la meta")
    c1, c2 = st.columns(2)
    c1.metric("Ahorrado", usd(ah["equivalente_usd"]))
    c2.metric("Falta", usd(max(ah["falta"], 0)))
    st.caption(f"Meta: {usd(ah['objetivo'])}")

    pr = datos.plan_vs_real(d, hoy())
    if pr["plan_a_hoy"]:
        dif = pr["diferencia"]
        signo = "por encima" if dif >= 0 else "por debajo"
        st.write(
            f"Aportes mensuales hasta este mes: plan {usd(pr['plan_a_hoy'])}, "
            f"real {usd(pr['real_a_hoy'])} ({usd(abs(dif))} {signo} del plan)."
        )
    if pr["extras_real"]:
        st.caption(f"Ingresos extra registrados: {usd(pr['extras_real'])}")

    st.subheader("Presupuesto")
    r = datos.resumen_presupuesto(d)
    c1, c2 = st.columns(2)
    c1.metric("Presupuestado", usd(r["total"]))
    c2.metric("Ya pagado", usd(r["pagado_usd"]))
    st.caption(f"Falta pagar (según presupuesto): {usd(r['falta_pagar'])}")

    proximas = [p for p in r["pendientes"] if p["orden"] is not None][:4]
    if proximas:
        st.write("**Próximas reservas (según tu orden):**")
        for p in proximas:
            st.write(f"{p['orden']}. {p['gasto'].title()} · {usd(p['plan'])}")


def pantalla_presupuesto(d):
    gastos = d["gastos"]
    dolar = d["config"]["dolar"]
    r = datos.resumen_presupuesto(d)

    c1, c2, c3 = st.columns(3)
    c1.metric("Presupuestado", usd(r["total"]))
    c2.metric("Pagado", usd(r["pagado_usd"]))
    c3.metric("Falta pagar", usd(r["falta_pagar"]))

    st.dataframe(
        pd.DataFrame([
            {
                "Gasto": f"{'✅' if g['estado'] == 'PAGADO' else '⏳'} {g['gasto'].title()}",
                "Presupuestado": usd(g["plan"]),
                "Real": usd(datos.costo_usd(g, dolar)) if g["estado"] == "PAGADO" else "",
            }
            for g in gastos
        ]),
        hide_index=True,
    )

    st.subheader("Editar un gasto")
    i = st.selectbox("Gasto", list(range(len(gastos))), format_func=lambda k: gastos[k]["gasto"].title())
    g = gastos[i]
    with st.form("form_gasto"):
        plan = st.number_input("Presupuestado (USD)", min_value=0.0, step=10.0, format="%.2f",
                               value=float(g["plan"]), key=f"g_plan_{g['id']}")
        pagado = st.checkbox("Pagado", value=g["estado"] == "PAGADO", key=f"g_pag_{g['id']}")
        real = st.number_input("Valor real en USD (0 = igual al presupuestado)", min_value=0.0,
                               step=10.0, format="%.2f", value=float(g["real"] or 0.0),
                               key=f"g_real_{g['id']}")
        orden = st.number_input("Orden de compra (0 = sin orden)", min_value=0, step=1,
                                value=int(g["orden"] or 0), key=f"g_ord_{g['id']}")
        if st.form_submit_button("Guardar"):
            intentar(datos.editar_gasto, f"Actualicé {g['gasto'].title()}.",
                     g["id"], plan, pagado, real, orden)

    with st.expander("Agregar un gasto"):
        with st.form("form_gasto_nuevo", clear_on_submit=True):
            nombre = st.text_input("Nombre del gasto")
            plan_n = st.number_input("Presupuestado (USD) del gasto nuevo", min_value=0.0, step=10.0, format="%.2f")
            orden_n = st.number_input("Orden de compra del gasto nuevo (0 = sin orden)", min_value=0, step=1)
            if st.form_submit_button("Agregar gasto"):
                intentar(datos.agregar_gasto, f"Agregué el gasto «{nombre.strip()}».", nombre, plan_n, orden_n)


def pantalla_ahorros(d):
    ah = datos.resumen_ahorros(d)

    st.subheader("Cuentas")
    st.dataframe(
        pd.DataFrame([
            {"Cuenta": c["cuenta"], "USD": usd(c["usd"]), "Pesos": f"$ {num(c['pesos'])}" if c["pesos"] else ""}
            for c in d["cuentas"]
        ]),
        hide_index=True,
    )
    st.caption(f"Total: {usd(ah['usd'])} · dólar de referencia: $ {num(ah['dolar'])}")

    st.write("**Actualizar el saldo de una cuenta**")
    opciones = [c["cuenta"] for c in d["cuentas"]] + [NUEVA]
    sel = st.selectbox("Cuenta de ahorro", opciones)
    actual = next((c for c in d["cuentas"] if c["cuenta"] == sel), None)
    with st.form("form_saldo"):
        nombre = st.text_input("Nombre de la cuenta nueva") if actual is None else sel
        saldo_usd = st.number_input("Saldo en USD", min_value=0.0, step=10.0, format="%.2f",
                                    value=float(actual["usd"]) if actual else 0.0, key=f"s_usd_{sel}")
        saldo_pesos = st.number_input("Saldo en pesos ($)", min_value=0.0, step=1000.0, format="%.2f",
                                      value=float(actual["pesos"]) if actual else 0.0, key=f"s_pes_{sel}")
        if st.form_submit_button("Guardar saldo"):
            intentar(datos.guardar_saldo, "Actualicé el saldo.", nombre, saldo_usd, saldo_pesos)

    st.subheader("Plan de aportes")
    st.dataframe(
        pd.DataFrame([
            {
                "Mes": a["origen"].title(),
                "Plan": usd(a["plan"]),
                "Real": usd(a["real"]) if a["real"] is not None else "",
                "Fecha": fecha_corta(a["fecha"]) or a["fecha_txt"],
                "Cuenta": a["cuenta"],
                "Estado": a["estado"].title(),
            }
            for a in d["aportes"]
        ]),
        hide_index=True,
    )

    st.write("**Registrar un aporte**")
    ids = [a["id"] for a in d["aportes"]] + [0]
    por_id = {a["id"]: a for a in d["aportes"]}

    def etiqueta(k):
        if k == 0:
            return "➕ Otro ingreso (nuevo)"
        a = por_id[k]
        return f"{'✅ ' if a['real'] is not None else ''}{a['origen'].title()}"

    with st.form("form_aporte", clear_on_submit=True):
        k = st.selectbox("Aporte", ids, format_func=etiqueta)
        nombre_n = st.text_input("Nombre (solo si es un ingreso nuevo)")
        monto = st.number_input("USD comprados", min_value=0.0, step=10.0, format="%.2f")
        fecha = st.date_input("Fecha", value=hoy(), format="DD/MM/YYYY")
        cuenta = st.selectbox("Cuenta", CUENTAS_APORTE)
        if st.form_submit_button("Guardar aporte"):
            if monto <= 0:
                st.warning("Ingresá un monto mayor a cero.")
            else:
                intentar(datos.registrar_aporte, f"Registré {usd(monto)}.", k, nombre_n, monto, fecha, cuenta)


def pantalla_movimientos(d):
    movs = d["movimientos"]
    tot = datos.totales_movimientos(d)

    c1, c2 = st.columns(2)
    c1.metric("Ingresos USD", usd(tot["ingresos_usd"]))
    c2.metric("Egresos USD", usd(tot["egresos_usd"]))
    if tot["ingresos_pesos"] or tot["egresos_pesos"]:
        st.caption(f"En pesos: ingresos $ {num(tot['ingresos_pesos'])} · egresos $ {num(tot['egresos_pesos'])}")

    st.subheader("Últimos movimientos")
    recientes = sorted(movs, key=lambda m: (m["fecha"] or "", m["id"]), reverse=True)[:15]
    st.dataframe(
        pd.DataFrame([
            {
                "Fecha": fecha_corta(m["fecha"]),
                "Descripción": m["desc"].title(),
                "Tipo": m["tipo"].title(),
                "Cuenta": m["cuenta"],
                "USD": usd(m["usd"]) if m["usd"] else "",
                "Pesos": f"$ {num(m['pesos'])}" if m["pesos"] else "",
            }
            for m in recientes
        ]),
        hide_index=True,
    )

    st.subheader("Agregar movimiento")
    with st.form("form_mov", clear_on_submit=True):
        desc = st.text_input("Descripción")
        detalle = st.text_input("Detalle (opcional)")
        tipo = st.radio("Tipo", ["INGRESO", "EGRESO"], horizontal=True)
        fecha = st.date_input("Fecha del movimiento", value=hoy(), format="DD/MM/YYYY")
        cuenta = st.text_input("Cuenta del movimiento", value="Banco Provincia")
        origen = st.text_input("Origen (opcional)")
        monto_usd = st.number_input("Valor USD", min_value=0.0, step=10.0, format="%.2f")
        monto_pesos = st.number_input("Valor pesos ($)", min_value=0.0, step=1000.0, format="%.2f")
        if st.form_submit_button("Guardar movimiento"):
            if monto_usd <= 0 and monto_pesos <= 0:
                st.warning("Ingresá un monto en USD o en pesos.")
            else:
                intentar(datos.agregar_movimiento, f"Agregué el movimiento «{desc.strip()}».",
                         desc, detalle, fecha, tipo, cuenta, origen, monto_usd, monto_pesos)

    if recientes:
        with st.expander("Borrar un movimiento"):
            por_id = {m["id"]: m for m in recientes}
            with st.form("form_borrar", clear_on_submit=True):
                mid = st.selectbox(
                    "Movimiento a borrar", list(por_id),
                    format_func=lambda k: f"{fecha_corta(por_id[k]['fecha'])} · {por_id[k]['desc'].title()}",
                )
                ok = st.checkbox("Confirmo que quiero borrarlo")
                if st.form_submit_button("Borrar"):
                    if not ok:
                        st.warning("Tildá la confirmación para borrar.")
                    else:
                        intentar(datos.borrar_movimiento, "Borré el movimiento.", mid)


def pantalla_itinerario(d):
    version = st.radio(
        "Versión", ["1", "2"],
        format_func=lambda v: "1 · Orlando → Miami" if v == "1" else "2 · Con crucero",
        horizontal=True,
    )
    dias = d["itinerario"][version]

    for dia in dias:
        f = datos.a_fecha(dia["fecha"])
        if f and dia["dia"] is not None:
            etiqueta = f"Día {dia['dia']} · {DIAS_SEMANA[f.weekday()]} {f.strftime('%d/%m')}"
        elif dia["dia"] is not None:
            etiqueta = f"Día {dia['dia']}"
        else:
            etiqueta = "—"
        titulo = dia["desc"] or dia["parque"].title() or dia["lugar"].title()
        extra = f" ({dia['parque'].title()})" if dia["parque"] and dia["parque"].title() not in titulo.title() else ""
        st.markdown(f"{'✅ ' if dia['listo'] else ''}**{etiqueta}** · {dia['lugar'].title()}  \n{titulo}{extra}")
        if dia["obs"]:
            st.caption(dia["obs"])
        if dia["analizar"]:
            st.caption("🔎 " + dia["analizar"])

    st.subheader("Editar un día")
    i = st.selectbox(
        "Día", list(range(len(dias))),
        format_func=lambda k: f"Día {dias[k]['dia'] if dias[k]['dia'] is not None else '?'} · "
                              f"{dias[k]['desc'] or dias[k]['lugar'].title()}",
    )
    dia = dias[i]
    clave = f"{version}_{dia['id']}"
    with st.form("form_dia"):
        desc = st.text_input("Descripción", value=dia["desc"], key=f"d_desc_{clave}")
        parque = st.text_input("Parque", value=dia["parque"], key=f"d_par_{clave}")
        obs = st.text_input("Observaciones", value=dia["obs"], key=f"d_obs_{clave}")
        analizar = st.text_input("Cosas para analizar", value=dia["analizar"], key=f"d_ana_{clave}")
        listo = st.checkbox("Listo / reservado", value=dia["listo"], key=f"d_ok_{clave}")
        if st.form_submit_button("Guardar día"):
            intentar(datos.editar_dia, "Actualicé el día.", version, dia["id"], desc, parque, obs, analizar, listo)

    st.subheader("Notas y cosas para analizar")
    for n in d["notas"]:
        st.write("• " + n)
    with st.form("form_nota", clear_on_submit=True):
        nota = st.text_input("Nota nueva")
        if st.form_submit_button("Agregar nota"):
            intentar(datos.agregar_nota, "Agregué la nota.", nota)
    if d["notas"]:
        with st.expander("Borrar una nota"):
            with st.form("form_nota_borrar", clear_on_submit=True):
                idx = st.selectbox("Nota a borrar", list(range(len(d["notas"]))),
                                   format_func=lambda k: d["notas"][k][:60])
                ok = st.checkbox("Confirmo que quiero borrar la nota")
                if st.form_submit_button("Borrar nota"):
                    if not ok:
                        st.warning("Tildá la confirmación para borrar.")
                    else:
                        intentar(datos.borrar_nota, "Borré la nota.", idx)


def pantalla_ajustes(d):
    st.subheader("Valores generales")
    cfg = d["config"]
    with st.form("form_config"):
        dolar = st.number_input("Dólar de referencia ($)", min_value=1.0, step=5.0, format="%.2f",
                                value=float(cfg["dolar"]))
        objetivo = st.number_input("Meta de ahorro (USD)", min_value=0.0, step=100.0, format="%.2f",
                                   value=float(cfg["objetivo"]))
        salida = st.date_input("Fecha de salida", value=datos.a_fecha(cfg["fecha_salida"]) or hoy(),
                               format="DD/MM/YYYY")
        if st.form_submit_button("Guardar valores"):
            intentar(datos.cambiar_config, "Actualicé los valores generales.", dolar, objetivo, salida)

    st.subheader("Copia de seguridad")
    st.download_button(
        "Descargar copia de los datos (JSON)",
        data=json.dumps(d, ensure_ascii=False, indent=1).encode("utf-8"),
        file_name="viaje-datos.json",
        mime="application/json",
    )
    if st.button("Recargar datos"):
        st.session_state.pop("cargado", None)
        st.rerun()

    with st.expander("Volver a importar desde Excel"):
        st.warning("Esto reemplaza TODOS los datos actuales de la app por los del Excel.")
        archivo = st.file_uploader("Planilla nueva (.xlsx)", type=["xlsx"])
        ok = st.checkbox("Entiendo que se reemplazan los datos actuales")
        if st.button("Reemplazar con el Excel"):
            if archivo is None or not ok:
                st.warning("Elegí el archivo y tildá la confirmación.")
            else:
                try:
                    nuevo = importar.desde_xlsx(archivo)
                except ValueError as e:
                    st.error(str(e))
                else:
                    aplicar(nuevo, "Reemplacé los datos con el Excel.")


# --------------------------------------------------------------------------
# Programa principal
# --------------------------------------------------------------------------
def main():
    pedir_clave()

    try:
        tienda = obtener_almacen()
        cargar_datos()
    except (almacen.ErrorAlmacen, ValueError) as e:
        estilo.encabezado()
        st.error(str(e))
        if st.button("Reintentar"):
            st.session_state.pop("cargado", None)
            st.rerun()
        st.stop()

    if tienda.es_demo:
        st.warning(
            "Modo de prueba: no hay GitHub conectado, así que los datos se guardan en un archivo "
            "local que se borra si la app se reinicia. Mirá el README para conectarlo."
        )

    d = st.session_state.get("datos")
    if d is None:
        pantalla_importar()
        st.stop()

    estilo.encabezado(datos.a_fecha(d["config"]["fecha_salida"]), datos.dias_para(d, hoy()))
    aviso = st.session_state.pop("aviso", None)
    if aviso:
        st.success(aviso)

    t_inicio, t_presu, t_ahorros, t_mov, t_itin, t_ajustes = st.tabs(
        ["🏰 Inicio", "🎟️ Presupuesto", "🐷 Ahorros", "💸 Movimientos", "🗓️ Itinerario", "⚙️ Ajustes"]
    )
    with t_inicio:
        pantalla_inicio(d)
    with t_presu:
        pantalla_presupuesto(d)
    with t_ahorros:
        pantalla_ahorros(d)
    with t_mov:
        pantalla_movimientos(d)
    with t_itin:
        pantalla_itinerario(d)
    with t_ajustes:
        pantalla_ajustes(d)


main()
