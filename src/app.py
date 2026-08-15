import os
import traceback

from flask import Flask, jsonify, request, send_from_directory
from r4_api import fetch_dashboard_completo
from renta4_scraper import DEBUG_DIR

app = Flask(__name__, static_folder="static", static_url_path="")


@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/api/dashboard", methods=["POST"])
def api_dashboard():
    body = request.get_json(silent=True) or {}
    username = body.get("usuario", "")
    password = body.get("password", "")

    if not username or not password:
        return jsonify({"error": "Usuario y contraseña son obligatorios."}), 400

    try:
        data = fetch_dashboard_completo(username, password, headless=True)
        return jsonify(data)
    except Exception as exc:
        traceback.print_exc()
        return jsonify({"error": str(exc)}), 500
    finally:
        # username/password solo viven en esta request; no se guardan en
        # ninguna variable de modulo, fichero ni log.
        del username, password


@app.route("/api/debug/last-failure")
def debug_last_failure():
    """Diagnostico temporal: expone la ultima captura+texto guardados por un
    login fallido, para ver desde el navegador que responde R4 en Render sin
    necesitar acceso al contenedor. Quitar cuando se resuelva el bloqueo."""
    kind = request.args.get("as", "png")
    filename = "last_failure.png" if kind == "png" else "last_failure.txt"
    path = os.path.join(DEBUG_DIR, filename)
    if not os.path.isfile(path):
        return jsonify({"error": "Todavia no hay ningun fallo registrado."}), 404
    directory, name = os.path.split(path)
    return send_from_directory(directory, name)


if __name__ == "__main__":
    app.run(port=5000, debug=False)
