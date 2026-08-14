import getpass
import json

from r4_api import fetch_patrimonio, summarize_patrimonio

if __name__ == "__main__":
    usuario = input("Usuario R4: ")
    password = getpass.getpass("Contraseña R4: ")

    data = fetch_patrimonio(usuario, password, headless=True)
    resumen = summarize_patrimonio(data)
    print(json.dumps(resumen, indent=2, ensure_ascii=False))
