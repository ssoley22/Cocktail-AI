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
    
    # Comprovem si algun dels ingredients té alcohol mirant el muntatge real
    muntatge_actual = database.get_muntatge()
    te_alcohol = 0
    for liquid in coctel_ia['recepta'].keys():
        # Busquem aquest líquid al muntatge per veure si és alcohòlic
        for m in muntatge_actual:
            if m['Nom_Liquid'] == liquid and m.get('Te_Alcohol', 0) == 1:
                te_alcohol = 1
                break
    
    # Simulem l'estructura que espera confirmacio.html
    dades_virtuals = {
        "ID_Coctel": 999,
        "Nom_Coctel": coctel_ia['nom'],
        "frase_barman": "Una creació única basada en la nostra conversa.",
        "Alcoholic": te_alcohol, # <-- Ara és dinàmic!
        "Recepta": [{"Nom_Liquid": liq, "Quantitat_ml": ml} for liq, ml in coctel_ia['recepta'].items()]
    }
    return render_template('confirmacio.html', coctel=dades_virtuals, disponible=True, origen='/xat')


@app.route('/preparar/<int:id_coctel>', methods=['POST'])
def preparar(id_coctel):
    # CAS ESPECIAL: Còctel de la IA
    if id_coctel == 999:
        coctel_ia = session.get('coctel_ia')
        if not coctel_ia: return redirect(url_for('xat'))
        
        recepta = coctel_ia['recepta']
        muntatge = {m["Nom_Liquid"]: m for m in database.get_muntatge() if m["Nom_Liquid"]}
        
        # 1. Comprovació d'estoc i protecció contra KeyError
        for liquid, ml in recepta.items():
            carril = muntatge.get(liquid)
            if not carril or carril["Capacitat_Actual_ml"] < ml:
                return render_template('error.html', missatge=f"Ens hem quedat sense prou '{liquid}' per fer aquesta creació.")
        
        # 2. Restar estoc amb protecció BBDD (try/except/finally)
        connexio = database.connectar()
        try:
            for liquid, ml in recepta.items():
                posicio = muntatge[liquid]["Posicio"]
                connexio.execute("UPDATE Muntatge SET Capacitat_Actual_ml = Capacitat_Actual_ml - ? WHERE Posicio = ?", (ml, posicio))
            connexio.commit()
        except Exception as e:
            print(f"[ERROR PREPARAR IA] Fallada a la BBDD: {e}")
            connexio.rollback()
            return render_template('error.html', missatge="Error intern al restar l'estoc.")
        finally:
            connexio.close() # <-- Això garanteix que no es quedi penjada la DB
        
        session.pop('historial', None)
        session.pop('coctel_ia', None)
        return render_template('preparant.html', coctel={"Nom_Coctel": coctel_ia['nom']})

    # CAS NORMAL: Còctel de la BBDD
    if database.restar_estoc(id_coctel):
        dades = database.get_coctel(id_coctel)
        return render_template('preparant.html', coctel=dades)
    
    return render_template('error.html', missatge="No hi ha prou estoc.")


# ==================== EMOCIONS I XAT (provisional) ====================

@app.route('/emocions')
def emocions():
    return render_template('emocions.html')


@app.route('/recomanacio/<sentit>')
def recomanacio(sentit):
    disponibles = database.get_coctels_disponibles()
    if not disponibles:
        return render_template('error.html', missatge="No hi ha estoc per a cap còctel.")

    resultat = IA.recomanar_per_emocio(sentit, disponibles)

    if resultat is None:
        # Fallback: si la IA falla, triem a l'atzar
        coctel = database.get_coctel(random.choice(disponibles)['ID_Coctel'])
    else:
        coctel = database.get_coctel(resultat['id_coctel'])
        coctel['frase_barman'] = resultat['frase_barman']

    return render_template('confirmacio.html', coctel=coctel, disponible=True, origen='/emocions')


@app.route('/xat')
def xat():
    # Inicialitzem historial si no existeix
    if 'historial' not in session:
        session['historial'] = []
    
    # Calculem missatges restants (3 parells de torns = 6 entrades)
    torns_fets = len(session['historial']) // 2
    restants = 3 - torns_fets
    return render_template('xat.html', restants=restants)

@app.route('/api/generar_xat', methods=['POST'])
def generar_xat():
    if 'historial' not in session:
        session['historial'] = []
        
    if len(session['historial']) >= 6:
        return jsonify({"status": "error", "missatge": "Límit de missatges assolit"}), 400

    dades_web = request.json
    missatge_usuari = dades_web.get('missatge', '')

    # 1. Guardem el que diu l'usuari
    session['historial'].append({"role": "user", "content": missatge_usuari})
    session.modified = True 

    # 2. Agafem líquids reals per a l'IA
    muntatge = database.get_muntatge()
    carrils_actius = ", ".join([m['Nom_Liquid'] for m in muntatge if m['Nom_Liquid']])

    # 3. Cridem a l'IA (IA.py)
    resultat = IA.xat_creatiu_amb_memoria(session['historial'], carrils_actius)

    if resultat:
        # 4. Guardem la resposta de l'IA
        session['historial'].append({"role": "assistant", "content": resultat['resposta_text']})
        
        # Si hi ha recepta, la guardem a la sessió per a la confirmació
        if resultat.get('tinc_recepta'):
            session['coctel_ia'] = resultat['dades_coctel']
            
        session.modified = True
        restants = 3 - (len(session['historial']) // 2)
        
        return jsonify({
            "status": "ok", 
            "resposta": resultat['resposta_text'],
            "tinc_recepta": resultat.get('tinc_recepta'),
            "dades_coctel": resultat.get('dades_coctel'), # Per pintar la targeta
            "restants": restants
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
    return render_template('admin.html', carrils=database.get_muntatge(), liquids=database.get_ingredients())


@app.route('/guardar_carril', methods=['POST'])
def guardar_carril():
    if not session.get('admin_loguejat'):
        return redirect(url_for('login'))
    pos = int(request.form.get('posicio'))
    ing_id = int(request.form.get('id_ingredient'))
    quantitat = int(request.form.get('ml'))
    database.update_muntatge(pos, ing_id, quantitat)
    return redirect(url_for('admin'))


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('inici'))



if __name__ == "__main__":
    '''
    Permet que cada cop que modifiques l'arxiu i el guardes reinici el servidor.
    Només funciona si l'executes per terminal:  python app.py
    '''
    app.run(debug=True, port=5000)