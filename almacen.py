"""Dónde guarda sus datos la app.

- GitHubStore: un archivo JSON en un repositorio PRIVADO de tu cuenta de GitHub
  (gratis, no se pierde cuando la app se reinicia y queda con historial de cambios).
- LocalStore: un archivo local, solo para probar. Se borra si la app se reinicia.

Los errores se devuelven como ErrorAlmacen con un mensaje claro y nunca incluyen el token.
"""
from __future__ import annotations

import base64
import json
import os
import re
import tempfile

import requests

API = "https://api.github.com"


class ErrorAlmacen(Exception):
    """Error al leer o guardar los datos (el mensaje es apto para mostrar al usuario)."""


def _serializar(datos: dict) -> bytes:
    return json.dumps(datos, ensure_ascii=False, indent=1).encode("utf-8")


class LocalStore:
    es_demo = True

    def __init__(self, ruta: str):
        self.ruta = ruta

    def cargar(self):
        if not os.path.exists(self.ruta):
            return None, None
        try:
            with open(self.ruta, encoding="utf-8") as f:
                return json.load(f), "local"
        except (OSError, ValueError):
            raise ErrorAlmacen("El archivo local de datos está dañado.") from None

    def guardar(self, datos: dict, token):
        carpeta = os.path.dirname(os.path.abspath(self.ruta))
        fd, tmp = tempfile.mkstemp(dir=carpeta, suffix=".tmp")
        try:
            with os.fdopen(fd, "wb") as f:
                f.write(_serializar(datos))
            os.replace(tmp, self.ruta)  # escritura atómica
        except OSError:
            raise ErrorAlmacen("No pude guardar el archivo local.") from None
        return "local"


def _pedir(metodo: str, url: str, token: str, **kw):
    """Único punto de contacto con la red (se reemplaza en las pruebas)."""
    return requests.request(
        metodo,
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        timeout=20,
        **kw,
    )


class GitHubStore:
    es_demo = False

    def __init__(self, token: str, repo: str, rama: str = "main", ruta: str = "datos.json"):
        repo = repo.strip().strip("/")
        if not re.fullmatch(r"[\w.-]+/[\w.-]+", repo):
            raise ErrorAlmacen(
                "El nombre del repositorio tiene que tener la forma usuario/repositorio "
                "(por ejemplo, marcos/viaje-datos)."
            )
        self.token = token.strip()
        self.repo = repo
        self.rama = rama.strip() or "main"
        self.ruta = ruta.strip().lstrip("/") or "datos.json"

    # -- internos ---------------------------------------------------------
    def _req(self, metodo: str, camino: str, **kw):
        try:
            return _pedir(metodo, API + camino, self.token, **kw)
        except requests.RequestException:
            raise ErrorAlmacen("No pude comunicarme con GitHub. Probá de nuevo en un momento.") from None

    def _explicar(self, r) -> str:
        try:
            detalle = r.json().get("message", "")
        except Exception:
            detalle = ""
        if r.status_code == 401:
            return "GitHub rechazó el token (vencido o mal copiado). Creá uno nuevo y actualizá los secretos."
        if r.status_code == 403:
            return (
                "El token no tiene permiso para este repositorio. Tiene que incluir el repositorio "
                "de datos con el permiso «Contents: Read and write»."
                + (f" (GitHub dice: {detalle})" if detalle else "")
            )
        if r.status_code == 404:
            return (
                f"No encuentro el repositorio «{self.repo}» o el token no tiene acceso a él. "
                "Revisá el nombre (usuario/repositorio) y que el token incluya ese repositorio."
            )
        return f"GitHub respondió con un error ({r.status_code}). {detalle}".strip()

    # -- API pública ------------------------------------------------------
    def cargar(self):
        """Devuelve (datos, sha). Si todavía no hay archivo: (None, None)."""
        r = self._req("GET", f"/repos/{self.repo}/contents/{self.ruta}", params={"ref": self.rama})
        if r.status_code == 200:
            j = r.json()
            try:
                crudo = base64.b64decode(j["content"])
                return json.loads(crudo.decode("utf-8")), j["sha"]
            except (KeyError, ValueError):
                raise ErrorAlmacen("El archivo de datos en GitHub está dañado o es ilegible.") from None
        if r.status_code == 404:
            repo = self._req("GET", f"/repos/{self.repo}")
            if repo.status_code == 200:
                return None, None  # el repositorio existe, falta crear el archivo
            raise ErrorAlmacen(self._explicar(repo))
        raise ErrorAlmacen(self._explicar(r))

    def guardar(self, datos: dict, sha):
        """Guarda y devuelve el nuevo sha. `sha` es el de la última lectura (None si es el primero)."""
        cuerpo = {
            "message": "Actualización desde la app del viaje",
            "content": base64.b64encode(_serializar(datos)).decode("ascii"),
            "branch": self.rama,
        }
        if sha:
            cuerpo["sha"] = sha
        r = self._req("PUT", f"/repos/{self.repo}/contents/{self.ruta}", json=cuerpo)
        if r.status_code in (200, 201):
            return r.json()["content"]["sha"]
        if r.status_code in (409, 422):
            raise ErrorAlmacen(
                "Los datos cambiaron desde otro dispositivo o pestaña. Andá a Ajustes, tocá "
                "«Recargar datos» y repetí el cambio."
            )
        raise ErrorAlmacen(self._explicar(r))
