from playwright.sync_api import sync_playwright

LOGIN_URL = "https://www.r4.com/login"

# NIF fijo: no es un dato sensible (es publico/conocido), a diferencia de
# usuario/contraseña que SIEMPRE llegan desde fuera (formulario del
# dashboard) y nunca se guardan en disco.
DNI = "77241496K"

# Renta 4 usa web components (r4wc-fake-input / r4wc-boton) que envuelven un
# <input> real, probablemente en shadow DOM. Playwright atraviesa shadow DOM
# abierto automaticamente con selectores CSS normales, por eso el combinador
# descendente "componente input" funciona igual que si fuera DOM normal.
SELECTORS = {
    "dni_input": 'r4wc-fake-input[inputid="EF_DNI"] input',
    "username_input": 'r4wc-fake-input[inputid="USUARIO"] input',
    "password_input": 'r4wc-fake-input[inputid="PASSWORD"] input',
    "submit_button": 'r4wc-boton#B_ENVIAR',
}


# Recursos que no hacen falta para leer datos/rellenar formularios: se
# bloquean para bajar el consumo de memoria de Chromium (el plan free de
# Render solo da 512MB, y cargar imagenes/fuentes/trackers de la pagina
# completa lo agota facilmente).
_BLOCKED_RESOURCE_TYPES = {"image", "media", "font"}


def _block_unnecesary_resources(context):
    def handle_route(route):
        if route.request.resource_type in _BLOCKED_RESOURCE_TYPES:
            route.abort()
        else:
            route.continue_()

    context.route("**/*", handle_route)


def _accept_cookies(page):
    candidates = [
        "a.button-accept-cookies",  # Cookiebot, el que usa r4.com
        "#onetrust-accept-btn-handler",
        "button:has-text('Aceptar todas')",
        "button:has-text('Aceptar todo')",
        "button:has-text('Aceptar')",
    ]
    for selector in candidates:
        try:
            page.click(selector, timeout=3000)
            return
        except Exception:
            continue


def login(username, password, headless=True):
    """Devuelve (playwright, browser, context, page). El llamador es responsable
    de cerrar con browser.close() y playwright.stop() cuando termine.

    No se persiste ninguna credencial ni sesion a disco: cada llamada hace un
    login limpio (contexto nuevo, sin storage_state guardado) con el usuario
    y contraseña que pasa el llamador.

    OJO: no usar 'with sync_playwright() as p:' aqui - al hacer return dentro
    de ese bloque, Python ejecuta el __exit__ (que cierra la conexion) antes
    de devolver el control, dejando browser/page ya inservibles para quien
    llama.
    """
    p = sync_playwright().start()
    browser = p.chromium.launch(
        headless=headless,
        args=[
            # Reducen memoria/procesos de Chromium; necesarios para caber en
            # los 512MB del plan free de Render.
            "--disable-dev-shm-usage",
            "--disable-gpu",
            "--no-sandbox",
            "--disable-extensions",
            "--disable-background-networking",
            "--disable-default-apps",
            "--disable-sync",
            "--mute-audio",
            "--no-first-run",
            "--single-process",
        ],
    )
    context = browser.new_context()
    _block_unnecesary_resources(context)
    page = context.new_page()
    page.goto(LOGIN_URL)
    _accept_cookies(page)

    page.fill(SELECTORS["dni_input"], DNI)
    page.fill(SELECTORS["username_input"], username)
    page.fill(SELECTORS["password_input"], password)
    page.click(SELECTORS["submit_button"])

    try:
        # 45s: en Render el redirect tras enviar el formulario puede tardar
        # bastante mas que en local (arranque en frio, latencia UE).
        page.wait_for_url(lambda url: "login" not in url, timeout=45000)
    except Exception:
        browser.close()
        p.stop()
        raise RuntimeError(
            "Login fallido: revisa usuario y contraseña "
            "(o puede que la web pida una verificación adicional)."
        )

    return p, browser, context, page
