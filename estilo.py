"""Estilo visual de la app: paleta "noche de castillo" y tipografías de cuento.

Colores originales (azul real, violeta, dorado y crema) y fuentes gratuitas de Google Fonts:
  - Títulos: Cinzel Decorative (aire de cuento clásico) y Fredoka (redondeada y amable)
  - Texto: Nunito
El tema claro se fija en .streamlit/config.toml; acá va el resto (tarjetas, botones, encabezado).
"""
from __future__ import annotations

import datetime as dt

PALETA = {
    "noche": "#14286E",      # azul de noche
    "real": "#2548B5",       # azul real
    "magia": "#6B3FA0",      # violeta
    "oro": "#F5B82E",        # dorado
    "oro_claro": "#FFE08A",  # dorado suave
    "crema": "#FFF8E7",      # fondo
    "tinta": "#14213D",      # texto
}

MESES_ES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
            "agosto", "septiembre", "octubre", "noviembre", "diciembre"]

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Cinzel+Decorative:wght@700&family=Fredoka:wght@400;500;600&family=Nunito:wght@400;600;700&display=swap');

:root{
  --noche:#14286E; --real:#2548B5; --magia:#6B3FA0; --oro:#F5B82E;
  --oro-claro:#FFE08A; --crema:#FFF8E7; --tinta:#14213D; color-scheme: light;
}

/* Base */
.stApp{background:linear-gradient(180deg,#FFF8E7 0%,#F4EEFF 100%);color:var(--tinta);font-family:'Nunito',sans-serif;}
[data-testid="stHeader"]{background:transparent;}
.block-container{max-width:720px;padding:1rem 1rem 3rem;}
footer{visibility:hidden;}
.stApp h1,.stApp h2,.stApp h3{font-family:'Fredoka',sans-serif;color:var(--noche);}
.stApp h2,.stApp h3{border-bottom:3px solid var(--oro-claro);padding-bottom:.25rem;}
.stApp [data-testid="stCaptionContainer"]{color:#4A5578;}

/* Encabezado */
.hero{position:relative;overflow:hidden;border-radius:22px;padding:1.4rem 1rem 1.2rem;margin:.2rem 0 1.1rem;
  text-align:center;color:#fff;border:2px solid var(--oro);box-shadow:0 8px 20px rgba(20,40,110,.28);
  background:radial-gradient(circle at 18% 15%,rgba(255,224,138,.35) 0,transparent 38%),
             linear-gradient(160deg,var(--noche) 0%,var(--magia) 100%);}
.hero:before{content:"";position:absolute;inset:0;pointer-events:none;
  background-image:
    radial-gradient(3px 3px at 8% 30%,#fff 50%,transparent 51%),
    radial-gradient(2.5px 2.5px at 22% 72%,#FFE08A 50%,transparent 51%),
    radial-gradient(3px 3px at 41% 18%,#FFE08A 50%,transparent 51%),
    radial-gradient(2.5px 2.5px at 63% 80%,#fff 50%,transparent 51%),
    radial-gradient(3px 3px at 78% 24%,#fff 50%,transparent 51%),
    radial-gradient(2.5px 2.5px at 91% 66%,#FFE08A 50%,transparent 51%);}
.hero > *{position:relative;}
.hero-titulo{font-family:'Cinzel Decorative','Fredoka',serif;font-weight:700;font-size:clamp(1.3rem,6vw,2rem);
  line-height:1.25;color:var(--oro-claro);text-shadow:0 2px 0 rgba(0,0,0,.25);}
.hero-sub{font-family:'Fredoka',sans-serif;letter-spacing:.14em;text-transform:uppercase;font-size:.8rem;margin-top:.4rem;}
.hero-dias{display:inline-block;margin-top:.85rem;padding:.35rem 1.1rem;border-radius:999px;background:var(--oro);
  color:var(--noche);font-family:'Fredoka',sans-serif;font-weight:600;font-size:1.05rem;}

/* Tarjetas de números */
[data-testid="stMetric"]{background:#fff;border:2px solid var(--oro-claro);border-radius:16px;padding:.7rem .9rem;
  box-shadow:0 3px 10px rgba(107,63,160,.12);}
[data-testid="stMetricLabel"],[data-testid="stMetricLabel"] p{color:var(--magia);font-family:'Fredoka',sans-serif;font-weight:500;}
[data-testid="stMetricValue"]{color:var(--noche);font-family:'Fredoka',sans-serif;font-weight:600;}

/* Pestañas */
.stTabs [data-baseweb="tab-list"]{gap:.2rem;overflow-x:auto;border-bottom:2px solid var(--oro-claro);}
.stTabs [data-baseweb="tab"]{font-family:'Fredoka',sans-serif;font-weight:500;color:var(--magia);padding:.4rem .7rem;white-space:nowrap;}
.stTabs [aria-selected="true"]{color:var(--real);}
.stTabs [data-baseweb="tab-highlight"]{background-color:var(--oro);height:3px;}

/* Botones */
.stButton>button,[data-testid="stFormSubmitButton"]>button,[data-testid="stDownloadButton"]>button{
  font-family:'Fredoka',sans-serif;font-weight:500;border:none;border-radius:999px;color:#fff;
  background:linear-gradient(135deg,var(--real),var(--magia));padding:.45rem 1.3rem;box-shadow:0 3px 8px rgba(37,72,181,.3);}
.stButton>button p,[data-testid="stFormSubmitButton"]>button p,[data-testid="stDownloadButton"]>button p{color:#fff;}
.stButton>button:hover,[data-testid="stFormSubmitButton"]>button:hover,[data-testid="stDownloadButton"]>button:hover{filter:brightness(1.12);color:#fff;}

/* Formularios, desplegables y barra de progreso */
[data-testid="stForm"]{background:rgba(255,255,255,.78);border:1.5px solid var(--oro-claro);border-radius:16px;}
[data-testid="stExpander"]{background:rgba(255,255,255,.65);border:1.5px solid var(--oro-claro);border-radius:14px;}
[data-testid="stProgress"] [role="progressbar"]>div,.stProgress>div>div>div>div{background:linear-gradient(90deg,var(--oro),#FF9F43);}
"""


def hero_html(salida: dt.date | None = None, dias: int | None = None) -> str:
    """Encabezado de la app. Solo lleva textos fijos y números calculados (nada escrito por el usuario)."""
    sub = f"{MESES_ES[salida.month - 1].capitalize()} {salida.year}" if salida else "Prepará la magia"
    badge = ""
    if dias is not None:
        if dias < 0:
            texto = "¡Ya salimos!"
        elif dias == 0:
            texto = "¡Es hoy!"
        elif dias == 1:
            texto = "Falta 1 día"
        else:
            texto = f"Faltan {int(dias)} días"
        badge = f'<div class="hero-dias">✨ {texto} ✨</div>'
    return (
        '<div class="hero">'
        '<div class="hero-titulo">Disney · Universal · Miami</div>'
        f'<div class="hero-sub">✨ {sub} ✨</div>'
        f"{badge}</div>"
    )


def aplicar() -> None:
    import streamlit as st

    st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)


def encabezado(salida: dt.date | None = None, dias: int | None = None) -> None:
    import streamlit as st

    st.markdown(hero_html(salida, dias), unsafe_allow_html=True)
