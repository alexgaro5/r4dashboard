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

_index = None


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
