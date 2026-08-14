import getpass
import json

from r4_api import fetch_dashboard_completo

if __name__ == "__main__":
    usuario = input("Usuario R4: ")
    password = getpass.getpass("Contraseña R4: ")

    resumen = fetch_dashboard_completo(usuario, password, headless=True)
    print(json.dumps(resumen, indent=2, ensure_ascii=False))
