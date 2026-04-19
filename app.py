from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import database
import random
import IA

app = Flask(__name__)
app.secret_key = 'clau_secreta_cocktail_2026'

USER_ADMIN = "admin"
PASS_ADMIN = "1234"

# ==================== FLUX CLIENT ====================

@app.route('/')
def inici():
    return render_template('index.html')

@app.route('/manual')
def manual():
    try:
        tots = database.get_tots_els_coctels()
        ids_disponibles = database.get_ids_disponibles()
        for c in tots:
            c['disponible'] = c['ID_Coctel'] in ids_disponibles
    except Exception as e:
        print(f"Error a Manual: {e}")
        tots = []
    return render_template('manual.html', coctels=tots)

@app.route('/aleatori')
def aleatori():
    ids_disponibles = database.get_ids_disponibles()
    if not ids_disponibles:
        return "<h1>⚠️ No hi ha prou ingredients!</h1>"
    id_triat = random.choice(ids_disponibles)
    dades = database.get_coctel(id_triat)
    return render_template('aleatori.html', coctel=dades)

@app.route('/confirmacio/<int:id_coctel>')
def confirmacio(id_coctel):
    try:
        dades = database.get_coctel(id_coctel)
        if not dades: return redirect(url_for('manual'))
        ids_disponibles = database.get_ids_disponibles()
        puc_preparar = id_coctel in ids_disponibles
        return render_template('confirmacio.html', coctel=dades, disponible=puc_preparar)
    except Exception as e:
        print(f"Error a Confirmacio: {e}")
        return redirect(url_for('manual'))

# --- RUTA ESPECIAL PER A IA ---
@app.route('/confirmacio_ia')
def confirmacio_ia():
    coctel_ia = session.get('coctel_ia')
    if not coctel_ia: return redirect(url_for('xat'))
    muntatge_actual = database.get_muntatge()
    te_alcohol = 0
    for liquid in coctel_ia['recepta'].keys():
        for m in muntatge_actual:
            if m['Nom_Liquid'] == liquid and m.get('Te_Alcohol', 0) == 1:
                te_alcohol = 1
                break
    dades_virtuals = {
        "ID_Coctel": 999,
        "Nom_Coctel": coctel_ia['nom'],
        "Alcoholic": te_alcohol,
        "Recepta": [{"Nom_Liquid": liq, "Quantitat_ml": ml} for liq, ml in coctel_ia['recepta'].items()]
    }
    return render_template('confirmacio.html', coctel=dades_virtuals, disponible=True)

@app.route('/preparar/<int:id_coctel>', methods=['POST'])
def preparar(id_coctel):
    if id_coctel == 999: # Cas IA
        session.pop('coctel_ia', None)
        return render_template('preparant.html', coctel={"Nom_Coctel": "Creació IA"})
    
    if database.restar_estoc(id_coctel):
        dades = database.get_coctel(id_coctel)
        return render_template('preparant.html', coctel=dades)
    return "Error d'estoc"

# ==================== IA I XAT ====================

@app.route('/emocions')
def emocions():
    return render_template('emocions.html')

@app.route('/recomanacio/<sentit>')
def recomanacio(sentit):
    disponibles = database.get_ids_disponibles()
    if not disponibles: return "No hi ha estoc"
    resultat = IA.recomanar_per_emocio(sentit, database.get_tots_els_coctels())
    coctel = database.get_coctel(resultat['id_coctel'])
    return render_template('confirmacio.html', coctel=coctel, disponible=True)

@app.route('/xat')
def xat():
    if 'historial' not in session: session['historial'] = []
    return render_template('xat.html')

@app.route('/api/generar_xat', methods=['POST'])
def generar_xat():
    dades_web = request.json
    missatge_usuari = dades_web.get('missatge', '')
    session['historial'].append({"role": "user", "content": missatge_usuari})
    
    carrils = ", ".join([m['Nom_Liquid'] for m in database.get_muntatge() if m['Nom_Liquid']])
    resultat = IA.xat_creatiu_amb_memoria(session['historial'], carrils)
    
    if resultat:
        session['historial'].append({"role": "assistant", "content": resultat['resposta_text']})
        if resultat.get('tinc_recepta'):
            session['coctel_ia'] = resultat['dades_coctel']
        return jsonify({"status": "ok", "resposta": resultat['resposta_text'], "tinc_recepta": resultat.get('tinc_recepta')})
    return jsonify({"status": "error"}), 500

# ==================== ADMIN ====================
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form['username'] == USER_ADMIN and request.form['password'] == PASS_ADMIN:
            session['admin_loguejat'] = True
            return redirect(url_for('admin'))
    return render_template('login.html')

@app.route('/admin')
def admin():
    if not session.get('admin_loguejat'): return redirect(url_for('login'))
    return render_template('admin.html', carrils=database.get_muntatge(), liquids=database.get_ingredients())

@app.route('/guardar_carril', methods=['POST'])
def guardar_carril():
    if not session.get('admin_loguejat'): return redirect(url_for('login'))
    database.update_muntatge(int(request.form.get('posicio')), int(request.form.get('id_ingredient')), int(request.form.get('ml')))
    return redirect(url_for('admin'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('inici'))

if __name__ == '__main__':
    app.run(debug=True, port=5050)
