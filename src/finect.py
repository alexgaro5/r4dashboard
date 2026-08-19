import json
import re
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import requests

_SITEMAP_URL = "https://www.finect.com/v4/bff/sitemap/funds.xml"
_FALLBACK_URL = "https://www.finect.com/fondos-inversion"
_INDEX_PATH = Path(__file__).parent / "finect_isin_index.json"
_MAX_AGE_SECONDS = 7 * 24 * 3600  # refrescar el indice semanalmente

_NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
_ISIN_RE = re.compile(r"/fondos-inversion/([A-Z0-9]{12})-")

_LD_JSON_RE = re.compile(
    r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', re.DOTALL
)
_TIMESERIES_URL = "https://api.finect.com/v4/products/collectives/funds/{fund_id}/timeseries"
# Clave publica del frontend de Finect (visible en el JS de cualquier visitante,
# no es un secreto de backend) para poder llamar directamente a su API.
_TIMESERIES_KEY = "OgcqanUxQ4S6Y5VVvnwlJayUuxeg8Ah5"

_index = None
_fund_id_cache = {}


def _download_index():
    """Descarga el sitemap oficial de fondos de Finect y construye un mapa
    ISIN -> URL exacta. Un unico fetch legitimo (sitemap publico) en vez de
    scrapear un buscador -> no dispara protecciones anti-bot, y cubre
    automaticamente cualquier fondo nuevo que aparezca en Finect."""
    resp = requests.get(_SITEMAP_URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
    resp.raise_for_status()
    root = ET.fromstring(resp.content)

    index = {}
    for url_el in root.findall(f"{_NS}url"):
        loc = url_el.findtext(f"{_NS}loc")
        if not loc:
            continue
        match = _ISIN_RE.search(loc)
        if match:
            index[match.group(1)] = loc
    return index


def _load_index():
    global _index
    if _index is not None:
        return _index

    if _INDEX_PATH.exists():
        age = time.time() - _INDEX_PATH.stat().st_mtime
        if age < _MAX_AGE_SECONDS:
            _index = json.loads(_INDEX_PATH.read_text(encoding="utf-8"))
            return _index

    try:
        _index = _download_index()
        _INDEX_PATH.write_text(json.dumps(_index), encoding="utf-8")
    except Exception:
        if _INDEX_PATH.exists():
            _index = json.loads(_INDEX_PATH.read_text(encoding="utf-8"))
        else:
            _index = {}

    return _index


def finect_url_for_isin(isin):
    return _load_index().get(isin, _FALLBACK_URL)


def _fund_id_for_isin(isin):
    """Extrae el id interno de Finect (el que usa su API de series
    temporales) leyendo el bloque JSON-LD embebido en la ficha publica del
    fondo. Se cachea en memoria porque no cambia durante la vida del proceso."""
    if isin in _fund_id_cache:
        return _fund_id_cache[isin]

    url = finect_url_for_isin(isin)
    if url == _FALLBACK_URL:
        _fund_id_cache[isin] = None
        return None

    fund_id = None
    try:
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
        resp.raise_for_status()
        for match in _LD_JSON_RE.finditer(resp.text):
            try:
                data = json.loads(match.group(1))
            except json.JSONDecodeError:
                continue
            if isinstance(data, dict) and data.get("sku"):
                fund_id = data["sku"]
                break
    except Exception:
        fund_id = None

    _fund_id_cache[isin] = fund_id
    return fund_id


def fetch_fund_history(isin):
    """Historico diario real de valor liquidativo del fondo (fuente: Finect),
    para poder dibujar la evolucion dia a dia de la posicion del usuario.
    Nunca lanza excepcion: si Finect falla o no tiene el fondo, devuelve []."""
    fund_id = _fund_id_for_isin(isin)
    if not fund_id:
        return []

    try:
        resp = requests.get(
            _TIMESERIES_URL.format(fund_id=fund_id),
            params={"start": "2000-01-01"},
            headers={
                "key": _TIMESERIES_KEY,
                "Accept": "application/json",
                "User-Agent": "Mozilla/5.0",
            },
            timeout=30,
        )
        resp.raise_for_status()
        body = resp.json()
    except Exception:
        return []

    return [
        {"fecha": entry["datetime"][:10], "valor": entry["price"]}
        for entry in body.get("data", [])
        if entry.get("datetime") and entry.get("price") is not None
    ]
