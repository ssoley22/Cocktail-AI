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
    tots = database.get_tots_els_coctels()
    disponibles = database.get_coctels_disponibles()
    ids_disponibles = [c['ID_Coctel'] for c in disponibles]
    for c in tots:
        c['disponible'] = c['ID_Coctel'] in ids_disponibles
    return render_template('manual.html', coctels=tots)

@app.route('/aleatori')
def aleatori():
    disponibles = database.get_coctels_disponibles()
    if not disponibles:
        return render_template('error.html', missatge="No hi ha estoc per a cap còctel.")
    coctel = database.get_coctel(random.choice(disponibles)['ID_Coctel'])
    return render_template('aleatori.html', coctel=coctel)

@app.route('/confirmacio/<int:id_coctel>')
def confirmacio(id_coctel):
    dades = database.get_coctel(id_coctel)
    if not dades:
        return redirect(url_for('manual'))
    disponibles = database.get_coctels_disponibles()
    ids_disponibles = [c['ID_Coctel'] for c in disponibles]
    puc_preparar = id_coctel in ids_disponibles
    origen = request.args.get('origen', '/manual')
    return render_template('confirmacio.html', coctel=dades, disponible=puc_preparar, origen=origen)

@app.route('/confirmacio_ia')
def confirmacio_ia():
    coctel_ia = session.get('coctel_ia')
    if not coctel_ia:
        return redirect(url_for('xat'))
    
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
        "frase_barman": "Una creació única basada en la nostra conversa.",
        "Alcoholic": te_alcohol,
        "Recepta": [{"Nom_Liquid": liq, "Quantitat_ml": ml} for liq, ml in coctel_ia['recepta'].items()]
    }
    return render_template('confirmacio.html', coctel=dades_virtuals, disponible=True, origen='/xat')

@app.route('/preparar/<int:id_coctel>', methods=['POST'])
def preparar(id_coctel):
    # ==========================================
    # CAS ESPECIAL: IA (id_coctel == 999)
    # ==========================================
    if id_coctel == 999:
        coctel_ia = session.get('coctel_ia')
        if not coctel_ia: 
            return redirect(url_for('xat'))
        
        recepta = coctel_ia['recepta'] 
        muntatge = {m["Nom_Liquid"]: m for m in database.get_muntatge() if m["Nom_Liquid"]}
        
        # 1. Comprovació d'estoc
        for liquid, ml in recepta.items():
            carril = muntatge.get(liquid)
            if not carril or carril["Capacitat_Actual_ml"] < ml:
                return render_template('error.html', missatge=f"Falta '{liquid}'.")
        
        # 2. Guardar la creació de l'IA a la BD
        try:
            recepta_per_guardar = []
            for nom_liq, ml in recepta.items():
                liq_info = muntatge[nom_liq]
                recepta_per_guardar.append({'id_liquid': liq_info['ID_Ingredient'], 'ml': ml})
            
            database.crear_recepta_completa(
                coctel_ia['nom'], 
                "Creació especial del xat IA", 
                recepta_per_guardar
            )
        except Exception as e:
            print(f"Error creant recepta IA a la BD: {e}")

        # 3. Restar estoc dels carrils i registrar comanda
        connexio = database.connectar()
        try:
            for liquid, ml in recepta.items():
                posicio = muntatge[liquid]["Posicio"]
                connexio.execute(
                    "UPDATE Muntatge SET Capacitat_Actual_ml = Capacitat_Actual_ml - ? WHERE Posicio = ?", 
                    (ml, posicio)
                )
            connexio.commit()
            
            # Registrar comanda per a les estadístiques (Admin)
            database.registrar_comanda(f"IA: {coctel_ia['nom']}")
                
        except Exception as e:
            connexio.rollback()
            return render_template('error.html', missatge="Error al processar els ingredients.")
        finally:
            connexio.close() 
        
        session.pop('historial', None)
        session.pop('coctel_ia', None)
        return render_template('preparant.html', coctel={"Nom_Coctel": coctel_ia['nom']})

    # ==========================================
    # CAS NORMAL: Còctel de la BBDD
    # ==========================================
    if database.restar_estoc(id_coctel):
        dades = database.get_coctel(id_coctel)
        
        # Registrar comanda per a les estadístiques (Admin)
        try:
            database.registrar_comanda(dades['Nom_Coctel'])
        except Exception as e:
            pass

        return render_template('preparant.html', coctel=dades)
    
    return render_template('error.html', missatge="No hi ha prou estoc.")


# ==================== EMOCIONS I XAT ====================

@app.route('/emocions')
def emocions():
    return render_template('emocions.html')

@app.route('/recomanacio/<sentit>')
def recomanacio(sentit):
    disponibles = database.get_coctels_disponibles()
    if not disponibles:
        return render_template('error.html', missatge="Sense estoc.")

    resultat = IA.recomanar_per_emocio(sentit, disponibles)
    
    if resultat is None:
        coctel = database.get_coctel(random.choice(disponibles)['ID_Coctel'])
    else:
        coctel = database.get_coctel(resultat['id_coctel'])
        if 'frase_barman' in resultat:
            coctel['frase_barman'] = resultat['frase_barman']

    return render_template('confirmacio.html', coctel=coctel, disponible=True, origen='/emocions')

@app.route('/xat')
def xat():
    if 'historial' not in session:
        session['historial'] = []
    torns_fets = len(session['historial']) // 2
    restants = 3 - torns_fets
    return render_template('xat.html', restants=restants)

@app.route('/api/generar_xat', methods=['POST'])
def generar_xat():
    # Protecció: si la petició no porta JSON, evitem errors de processament
    if not request.json:
        return jsonify({"status": "error", "missatge": "Petició buida"}), 400

    if 'historial' not in session:
        session['historial'] = []
    
    if len(session['historial']) >= 6:
        return jsonify({"status": "error", "missatge": "Límit assolit"}), 400

    dades_web = request.json
    missatge_usuari = dades_web.get('missatge', '')
    
    session['historial'].append({"role": "user", "content": missatge_usuari})
    session.modified = True 

    muntatge = database.get_muntatge()
    carrils_actius = ", ".join([m['Nom_Liquid'] for m in muntatge if m['Nom_Liquid']])

    resultat = IA.xat_creatiu_amb_memoria(session['historial'], carrils_actius)
    
    if resultat:
        session['historial'].append({"role": "assistant", "content": resultat['resposta_text']})
        if resultat.get('tinc_recepta'):
            session['coctel_ia'] = resultat['dades_coctel']
        
        session.modified = True
        return jsonify({
            "status": "ok", 
            "resposta": resultat['resposta_text'],
            "tinc_recepta": resultat.get('tinc_recepta'),
            "dades_coctel": resultat.get('dades_coctel'),
            "restants": 3 - (len(session['historial']) // 2)
        })
        
    return jsonify({"status": "error"}), 500

@app.route('/reiniciar_xat')
def reiniciar_xat():
    session.pop('historial', None)
    session.pop('coctel_ia', None)
    return redirect(url_for('xat'))


# ==================== ADMIN ====================

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        if request.form['username'] == USER_ADMIN and request.form['password'] == PASS_ADMIN:
            session['admin_loguejat'] = True
            return redirect(url_for('admin'))
        error = "Usuari o contrasenya incorrectes."
    return render_template('login.html', error=error)

@app.route('/admin')
def admin():
    if not session.get('admin_loguejat'):
        return redirect(url_for('login'))
    
    carrils = database.get_muntatge()
    liquids = database.get_ingredients()
    estadistiques = database.get_estadistiques()
    
    tots = database.get_tots_els_coctels()
    disponibles_ara = database.get_coctels_disponibles()
    ids_disponibles = [c['ID_Coctel'] for c in disponibles_ara]
    
    for c in tots:
        c['puc_fer_lo'] = c['ID_Coctel'] in ids_disponibles

    tots.sort(key=lambda x: x['puc_fer_lo'], reverse=True)
    
    return render_template('admin.html', 
                           carrils=carrils, 
                           liquids=liquids,
                           estadistiques=estadistiques,
                           coctels=tots)

@app.route('/guardar_carril', methods=['POST'])
def guardar_carril():
    if not session.get('admin_loguejat'):
        return redirect(url_for('login'))

    # Protecció: evitem un error 500 si arriben valors malformats al formulari
    try:
        pos = int(request.form.get('posicio'))
        ing_id = int(request.form.get('id_ingredient'))
        quantitat = int(request.form.get('ml'))
    except (TypeError, ValueError):
        return redirect(url_for('admin'))

    database.update_muntatge(pos, ing_id, quantitat)

    # Recalculem preus després de tocar un carril per mantenir el motor financer al dia
    try:
        database.recalcular_preus()
    except Exception as e:
        print(f"Error recalculant preus: {e}")

    return redirect(url_for('admin'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('inici'))

@app.route('/guardar_recepta_manual', methods=['POST'])
def guardar_recepta_manual():
    if not session.get('admin_loguejat'):
        return redirect(url_for('login'))
    
    nom = request.form.get('nom_coctel')
    descripcio = request.form.get('frase_barman') or "Una creació manual de la casa."
    
    ids_ingredients = request.form.getlist('ingredients[]')
    quantitats = request.form.getlist('quantitats[]')
    
    recepta_final = []
    for i in range(len(ids_ingredients)):
        if ids_ingredients[i] and quantitats[i]:
            recepta_final.append({
                'id_liquid': int(ids_ingredients[i]),
                'ml': int(quantitats[i])
            })
    
    if nom and recepta_final:
        database.crear_recepta_completa(nom, descripcio, recepta_final)
    
    return redirect(url_for('admin'))

if __name__ == "__main__":
    app.run(debug=True, port=5000, host="0.0.0.0")
