import traceback

from flask import Flask, jsonify, request, send_from_directory
from r4_api import fetch_dashboard_completo

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


if __name__ == "__main__":
    app.run(port=5000, debug=False)
