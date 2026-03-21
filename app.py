from flask import Flask, jsonify
import json

app = Flask(__name__)

with open("coctels.json", "r") as coctels:
    ll_coctels = json.load(coctels)
with open("ingredients.json", "r") as ingredients:
    ll_ingredients = json.load(ingredients)

@app.route("/api/hola")
def hola():
    return jsonify({
        "missatge": "Hola món",
        "estat": "OK"
    })


@app.route("/api/adeu")
def adeu():
    return "Fins aviat!"


@app.route("/api/coctels/<int:id>")
def trobar_coctel(id):
    for coctel in ll_coctels:
        if coctel["id"] == id:
            return jsonify(coctel)
    return jsonify({"error": "Còctel no trobat"})


@app.route("/api/coctels/")
def coctels():
    return jsonify(ll_coctels)

@app.route("/api/ingredients/")
def ingredients():
    return jsonify(ll_ingredients)


if __name__ == "__main__":
    app.run(debug=True, port=5000)