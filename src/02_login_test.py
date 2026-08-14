import getpass

from renta4_scraper import login

if __name__ == "__main__":
    usuario = input("Usuario R4: ")
    password = getpass.getpass("Contraseña R4: ")

    playwright, browser, context, page = login(usuario, password, headless=False)
    print("URL tras login:", page.url)
    page.screenshot(path="login_result.png", full_page=True)
    print("Screenshot guardado en login_result.png")
    input("Pulsa Enter para cerrar el navegador...")
    browser.close()
    playwright.stop()
