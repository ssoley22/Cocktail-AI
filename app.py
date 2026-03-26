from flask import Flask, jsonify
import json
import database

# Inicialitzem l'aplicació Flask
app = Flask(__name__)


@app.route("/")
def inici():
    return "a"


@app.route("/api/coctels")
def api_coctels():
    coctels = database.get_coctels_disponibles()
    return jsonify(coctels)


@app.route("/api/muntatge")
def muntatge():
    muntatge = database.get_muntatge()
    return jsonify(muntatge)


if __name__ == "__main__":
    '''
    Permet que cada cop que modifiques l'arxiu i el guardes reinici el servidor.
    Només funciona si l'executes per terminal:  python app.py
    '''
    app.run(debug=True, port=5000)