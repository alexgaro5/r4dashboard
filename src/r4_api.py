from renta4_scraper import login
from finect import fetch_fund_history, finect_url_for_isin

PORTAL_URL = "https://www.r4.com/portal?TX=goto&FWD=MAIN10_REDIRECT"

OPERACIONES_HEADERS = [
    "fecha",
    "concepto",
    "participaciones",
    "valorParticipacion",
    "importeBruto",
    "comision",
    "retencion",
    "efectivo",
]

# Extrae filas de la tabla de operaciones de un fondo. Los <td colspan=N>
# vacios (ej. la fila "VALORACION" solo rellena 3 columnas de golpe) se
# expanden a N celdas para que el numero de columnas siempre cuadre con
# OPERACIONES_HEADERS.
_JS_EXTRAER_FILAS = """rows => rows.map(row => {
    const cells = [];
    for (const td of row.querySelectorAll('td')) {
        const span = parseInt(td.getAttribute('colspan') || '1', 10);
        const text = td.innerText.trim();
        for (let i = 0; i < span; i++) cells.push(i === 0 ? text : '');
    }
    return cells;
})"""


def _fetch_portal_data(page):
    """Navega al portal principal y captura las respuestas JSON de patrimonio,
    evolucion del patrimonio (rentabilidad) y (si aparece en la misma carga)
    planes de ahorro periodico."""
    captured = {}

    def handle_response(response):
        url = response.url
        if "patrimonio" not in captured and "apificacion/patrimonios" in url:
            try:
                body = response.json()
            except Exception:
                return
            if isinstance(body, dict) and isinstance(body.get("summary"), dict):
                captured["patrimonio"] = body
        elif "rentabilidad" not in captured and "apificacion/rentabilidad" in url:
            try:
                body = response.json()
            except Exception:
                return
            if isinstance(body, dict) and "data" in body:
                captured["rentabilidad"] = body
        elif "ahorro" not in captured and "ahorro-periodico/planes-ahorro" in url:
            try:
                body = response.json()
            except Exception:
                return
            if isinstance(body, dict) and "data" in body:
                captured["ahorro"] = body

    page.on("response", handle_response)
    page.goto(PORTAL_URL)

    for _ in range(100):  # hasta ~20s
        if "patrimonio" in captured:
            break
        page.wait_for_timeout(200)
    else:
        raise TimeoutError("No se recibio la respuesta de patrimonios a tiempo")

    # rentabilidad (evolucion del patrimonio) y plan de ahorro son opcionales:
    # les damos un margen corto extra por si llegan despues, sin bloquear si
    # nunca aparecen
    for _ in range(15):
        if "rentabilidad" in captured and "ahorro" in captured:
            break
        page.wait_for_timeout(200)

    page.remove_listener("response", handle_response)
    return captured


def fetch_patrimonio(username, password, headless=True):
    playwright, browser, context, page = login(username, password, headless=headless)
    data = _fetch_portal_data(page)["patrimonio"]
    browser.close()
    playwright.stop()
    return data


def fetch_fondo_operaciones(page, url_detalle):
    page.goto(f"https://www.r4.com/portal?{url_detalle}")
    filas = page.eval_on_selector_all("table.bordered.zebra tr.textos", _JS_EXTRAER_FILAS)

    operaciones = []
    for celdas in filas:
        celdas = celdas[: len(OPERACIONES_HEADERS)]
        celdas += [""] * (len(OPERACIONES_HEADERS) - len(celdas))
        operaciones.append(dict(zip(OPERACIONES_HEADERS, celdas)))
    return operaciones


def fetch_dashboard_completo(username, password, headless=True):
    playwright, browser, context, page = login(username, password, headless=headless)

    raw = _fetch_portal_data(page)
    resumen = summarize_patrimonio(raw["patrimonio"])
    resumen["planesAhorro"] = summarize_planes_ahorro(raw.get("ahorro"))
    resumen["evolucionPatrimonio"] = summarize_rentabilidad(raw.get("rentabilidad"))

    for fondo in resumen["fondos"]:
        fondo["operaciones"] = fetch_fondo_operaciones(page, fondo["url_detalle"])
        fondo["finectUrl"] = finect_url_for_isin(fondo["isin"])
        fondo["historicoFinect"] = fetch_fund_history(fondo["isin"])

    browser.close()
    playwright.stop()
    return resumen


def _strip_colors(obj):
    if isinstance(obj, dict):
        return {k: _strip_colors(v) for k, v in obj.items() if k != "color"}
    if isinstance(obj, list):
        return [_strip_colors(v) for v in obj]
    return obj


def summarize_patrimonio(data):
    fondos = data["summary"].get("Cartera_Fondos_de_Inversion", {})
    posiciones = [
        {
            "nombre": p["nombreFondo"],
            "isin": p["isin"],
            "gestora": p["nombreGestora"],
            "participaciones": p["partis"],
            "valoracion": p["valoracion"],
            "importeAdquisicion": p["importeAdq"],
            "beneficio": p["benef"],
            "rentabilidadPct": p["rentabilidad"],
            "fechaValoracion": p["fechaValoracion"],
            "url_detalle": p["params"]["url"],
        }
        for p in fondos.get("posiciones", [])
    ]

    saldo = data["summary"].get("Saldo en EUR", {}).get("valoracion", 0.0)

    distribuciones = {
        d["descripcion"]: [
            {"categoria": e["descripcion"], "pct": e["porcentaje"], "valor": e["valor"]}
            for e in d["distribuciones"]
        ]
        for d in data.get("distributionsValues", [])
    }

    return {
        "patrimonioTotal": data["patrimonioTotal"],
        "saldoDisponible": saldo,
        "fondos": posiciones,
        "distribuciones": distribuciones,
    }


def summarize_planes_ahorro(ahorro_data):
    if not ahorro_data:
        return []

    planes = []
    for cuenta in ahorro_data.get("data", []):
        for plan in cuenta.get("planesdeAhorro", []):
            planes.append(
                {
                    "alias": plan["alias"],
                    "estado": plan["estadoOrden"],
                    "importeActual": plan["importeActual"],
                    "periodicidad": plan["periodicidadTexto"],
                    "proximaEjecucion": plan["proximaEjecucion"],
                    "fechaInicio": plan["fechaInicio"],
                    "cuentaOrigen": plan["cuentaOrigen"]["iban"],
                    "fondos": [
                        {
                            "isin": f["isin"],
                            "nombre": f["fondo"],
                            "gestora": f["gestora"],
                            "porcentaje": f["porcentaje"],
                            "importe": f["importe"],
                        }
                        for f in plan.get("listaFondos", [])
                    ],
                }
            )
    return planes


def summarize_rentabilidad(rentabilidad_data):
    """Serie temporal real de evolucion del patrimonio (valoracion, entradas
    y salidas por fecha), tal como la usa el propio widget de R4."""
    if not rentabilidad_data:
        return []

    return [
        {
            "fecha": e.get("fecha"),
            "valoracion": e.get("valoracion") or 0,
            "entradas": e.get("entradas") or 0,
            "salidas": e.get("salidas") or 0,
        }
        for e in rentabilidad_data.get("data", [])
    ]
