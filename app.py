from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import database
import random
import IA
import threading
import queue
import time
import subprocess
import re
import os
import atexit
import qrcode
from arduino import CocktailMachine

database.recalcular_preus()

app = Flask(__name__)
app.secret_key = 'clau_secreta_cocktail_2026'

tunnel_url = None
tunnel_proc = None

USER_ADMIN = "admin"
PASS_ADMIN = "1234"

# ==================== HARDWARE ARDUINO ====================

ML_PER_DOSE = 30
BOTTLE_PRESS_MS = 3300
REFILL_DELAY_S = 2.5

ADD_ICE_BY_DEFAULT = True
ICE_PRESS_MS = 600

cua_hardware = queue.Queue()
maquina = None
maquina_lock = threading.Lock()


def actualitzar_estat_comanda(id_comanda, estat):
    connexio = database.connectar()
    try:
        connexio.execute(
            "UPDATE Comandes SET Estat = ? WHERE ID_Comanda = ?",
            (estat, id_comanda)
        )
        connexio.commit()
    finally:
        connexio.close()

def netejar_comandes_pendents_inici():
    connexio = database.connectar()
    try:
        connexio.execute(
            """
            UPDATE Comandes
            SET Estat = 'Cancel·lat_Inici'
            WHERE Estat IN ('Pendent', 'Preparant', 'Llest', 'Error_HW')
            """
        )
        connexio.commit()
    finally:
        connexio.close()


def obtenir_maquina():
    global maquina

    with maquina_lock:
        if maquina is None:
            maquina = CocktailMachine(port="/dev/ttyUSB0")

        return maquina


def executar_recepta_hardware(recepta):
    machine = obtenir_maquina()

    if ADD_ICE_BY_DEFAULT:
        machine.dispense_ice(ICE_PRESS_MS)
        
    for ingredient in recepta:
        posicio = int(ingredient["Posicio"])
        quantitat_ml = int(ingredient["Quantitat_ml"])

        if posicio < 1 or posicio > 6:
            raise ValueError(f"Posició d'ampolla invàlida: {posicio}")

        if quantitat_ml <= 0 or quantitat_ml % ML_PER_DOSE != 0:
            raise ValueError(f"Quantitat no compatible amb optics de 30 ml: {quantitat_ml}")

        dosis = quantitat_ml // ML_PER_DOSE

        for dosi_actual in range(dosis):
            machine.dispense_bottle(posicio, BOTTLE_PRESS_MS)

            if dosi_actual < dosis - 1:
                time.sleep(REFILL_DELAY_S)



def worker_hardware():
    while True:
        tasca = cua_hardware.get()

        id_comanda = tasca["id_comanda"]
        recepta = tasca["recepta"]

        try:
            # Pagament RFID: la comanda queda en estat "Pendent" fins que es valida la targeta
            machine = obtenir_maquina()
            machine.wait_payment()

            actualitzar_estat_comanda(id_comanda, "Preparant")

            executar_recepta_hardware(recepta)

            # Quan acaba de servir, torna a HOME
            machine = obtenir_maquina()
            machine.home()

            # Es mostra com a llest durant 5s
            actualitzar_estat_comanda(id_comanda, "Llest")
            time.sleep(5)

            # Estat final perquè surti de la cua/pantalla
            actualitzar_estat_comanda(id_comanda, "Finalitzat")

        except Exception as e:
            print(f"ERROR HARDWARE COMANDA {id_comanda}: {e}")
            actualitzar_estat_comanda(id_comanda, "Error_HW")

        finally:
            cua_hardware.task_done()


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
        "Preu_Final_Cents": coctel_ia.get('preu_final_cents'),
        "Preu_No_Disponible": coctel_ia.get('preu_no_disponible', False),
        "Recepta": [{"Nom_Liquid": liq, "Quantitat_ml": ml} for liq, ml in coctel_ia['recepta'].items()]
    }
    return render_template('confirmacio.html', coctel=dades_virtuals, disponible=True, origen='/xat')

@app.route('/pantalla')
def pantalla_estat():
    return render_template('pantalla.html')

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

        recepta_hardware = []

        # 1. Comprovació d'estoc i quantitats compatibles amb optics de 30 ml
        for liquid, ml in recepta.items():
            ml = int(ml)
            carril = muntatge.get(liquid)

            if ml <= 0 or ml % ML_PER_DOSE != 0:
                return render_template(
                    'error.html',
                    missatge=f"La quantitat de '{liquid}' no és múltiple de 30 ml."
                )

            if not carril or carril["Capacitat_Actual_ml"] < ml:
                return render_template('error.html', missatge=f"Falta '{liquid}'.")

            recepta_hardware.append({
                "Posicio": carril["Posicio"],
                "Nom_Liquid": liquid,
                "Quantitat_ml": ml
            })

        # 2. Guardar la creació de l'IA a la BD
        try:
            recepta_per_guardar = []

            for nom_liq, ml in recepta.items():
                liq_info = muntatge[nom_liq]
                recepta_per_guardar.append({
                    'id_liquid': liq_info['ID_Ingredient'],
                    'ml': int(ml)
                })

            database.crear_recepta_completa(
                coctel_ia['nom'],
                "Creació especial del xat IA",
                recepta_per_guardar
            )

        except Exception as e:
            print(f"Error creant recepta IA a la BD: {e}")

        # 3. Reservar estoc, registrar comanda i posar-la a la cua de hardware
        connexio = database.connectar()

        try:
            for ingredient in recepta_hardware:
                connexio.execute(
                    "UPDATE Muntatge SET Capacitat_Actual_ml = Capacitat_Actual_ml - ? WHERE Posicio = ?",
                    (ingredient["Quantitat_ml"], ingredient["Posicio"])
                )

            connexio.commit()

            id_comanda, num_comanda = database.registrar_comanda(
                f"IA: {coctel_ia['nom']}",
                coctel_ia.get('cost_cents', 0),
                coctel_ia.get('preu_final_cents', 0)
            )

            cua_hardware.put({
                "id_comanda": id_comanda,
                "recepta": recepta_hardware
            })

        except Exception as e:
            connexio.rollback()
            return render_template('error.html', missatge="Error al processar els ingredients.")

        finally:
            connexio.close()

        session.pop('historial', None)
        session.pop('coctel_ia', None)

        return render_template(
            'tiquet.html',
            coctel={"Nom_Coctel": coctel_ia['nom']},
            num=num_comanda
        )

    # ==========================================
    # CAS NORMAL: Còctel de la BBDD
    # ==========================================
    dades = database.get_coctel(id_coctel)

    if not dades:
        return render_template('error.html', missatge="Còctel no trobat.")

    for ingredient in dades["Recepta"]:
        quantitat_ml = int(ingredient["Quantitat_ml"])

        if quantitat_ml <= 0 or quantitat_ml % ML_PER_DOSE != 0:
            return render_template(
                'error.html',
                missatge="Aquest còctel té una quantitat que no és múltiple de 30 ml."
            )

    if database.restar_estoc(id_coctel):
        try:
            id_comanda, num_comanda = database.registrar_comanda(
                dades['Nom_Coctel'],
                dades.get('Preu_Produccio_Cents', 0),
                dades.get('Preu_Final_Cents', 0)
            )

            cua_hardware.put({
                "id_comanda": id_comanda,
                "recepta": dades["Recepta"]
            })

        except Exception as e:
            print(f"Error registrant comanda o afegint-la a la cua: {e}")
            return render_template('error.html', missatge="Error registrant la comanda.")

        return render_template('tiquet.html', coctel=dades, num=num_comanda)
    
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
    if request.args.get('nou') == '1':
        session.pop('historial', None)
        session.pop('coctel_ia', None)

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
            dades_coctel = resultat['dades_coctel']

            # Calculem el preu en temps real segons els carrils actius
            if dades_coctel and isinstance(dades_coctel.get('recepta'), dict):
                preu_ia = database.calcular_preu_recepta_ia(dades_coctel['recepta'])
                if preu_ia.get('ok'):
                    dades_coctel['preu_final_cents'] = preu_ia['preu_final_cents']
                    dades_coctel['cost_cents'] = preu_ia['cost_cents']
                    dades_coctel['preu_no_disponible'] = False
                else:
                    dades_coctel['preu_no_disponible'] = True

            session['coctel_ia'] = dades_coctel
            resultat['dades_coctel'] = dades_coctel
        
        session.modified = True
        return jsonify({
            "status": "ok", 
            "resposta": resultat['resposta_text'],
            "tinc_recepta": resultat.get('tinc_recepta'),
            "dades_coctel": resultat.get('dades_coctel'),
            "restants": 3 - (len(session['historial']) // 2)
        })
        
    return jsonify({"status": "error"}), 500

@app.route('/api/cua', methods=['GET'])
def api_cua():
    dades = database.get_estat_pantalla()
    return jsonify(dades)

@app.route('/api/tunnel_info', methods=['GET'])
def api_tunnel_info():
    return jsonify({"url": tunnel_url, "qr": "/static/img/qr_acces.png"})

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
    dashboard = database.get_dades_dashboard()
    marge_actual = database.get_configuracio().get('marge', 3.0)
    
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
                           coctels=tots,
                           dashboard=dashboard,
                           marge_actual=marge_actual)

@app.route('/guardar_marge', methods=['POST'])
def guardar_marge():
    if not session.get('admin_loguejat'):
        return jsonify({"status": "error", "message": "No autoritzat"}), 401

    dades_json = request.get_json(silent=True) or {}
    marge = dades_json.get('marge') if 'marge' in dades_json else request.form.get('marge')

    try:
        database.update_marge_configuracio(marge)
        database.recalcular_preus()
        return jsonify({"status": "ok"})
    except (TypeError, ValueError):
        return jsonify({"status": "error", "message": "Marge invàlid"}), 400
    except Exception:
        return jsonify({"status": "error", "message": "Error intern"}), 500

@app.route('/guardar_carril', methods=['POST'])
def guardar_carril():
    if not session.get('admin_loguejat'):
        return redirect(url_for('login'))

    es_ajax = (
        request.headers.get("X-Requested-With") == "XMLHttpRequest"
        or "application/json" in request.headers.get("Accept", "")
    )

    # Protecció: evitem un error 500 si arriben valors malformats al formulari
    try:
        pos = int(request.form.get('posicio'))
        ing_id = int(request.form.get('id_ingredient'))
        preu_ampolla_cents = int(round(float(request.form.get('preu_ampolla_eur')) * 100))
        mida_ampolla_ml = int(request.form.get('mida_ampolla_ml'))
        quantitat = mida_ampolla_ml
    except (TypeError, ValueError):
        if es_ajax:
            return jsonify({"status": "error", "message": "Dades invàlides"}), 400
        return redirect(url_for('admin'))

    try:
        database.update_muntatge(pos, ing_id, quantitat, preu_ampolla_cents, mida_ampolla_ml)

        # Recalculem preus després de tocar un carril per mantenir el motor financer al dia
        database.recalcular_preus()
    except Exception as e:
        print(f"Error recalculant preus: {e}")
        if es_ajax:
            return jsonify({"status": "error", "message": "Error intern"}), 500
        return redirect(url_for('admin'))

    if es_ajax:
        return jsonify({"status": "ok", "message": "Desat"})

    return redirect(url_for('admin'))

@app.route('/guardar_preu_fix', methods=['POST'])
def guardar_preu_fix():
    if not session.get('admin_loguejat'):
        return redirect(url_for('login'))

    es_ajax = (
        request.headers.get("X-Requested-With") == "XMLHttpRequest"
        or "application/json" in request.headers.get("Accept", "")
    )

    try:
        id_coctel = int(request.form.get('id_coctel'))
        te_preu_fix = 1 if request.form.get('te_preu_fix') == 'on' else 0
        valor_preu_fix = (request.form.get('preu_fix_eur') or '').strip()
    except (TypeError, ValueError):
        if es_ajax:
            return jsonify({"status": "error", "message": "Dades invàlides"}), 400
        return redirect(url_for('admin'))

    preu_fix_cents = None
    if valor_preu_fix:
        try:
            preu_fix_cents = int(round(float(valor_preu_fix) * 100))
        except (TypeError, ValueError):
            te_preu_fix = 0
            preu_fix_cents = None

    if te_preu_fix == 1 and (preu_fix_cents is None or preu_fix_cents <= 0):
        te_preu_fix = 0

    try:
        database.update_preu_fix_coctel(id_coctel, te_preu_fix, preu_fix_cents)
    except Exception:
        if es_ajax:
            return jsonify({"status": "error", "message": "Error intern"}), 500
        return redirect(url_for('admin'))

    if es_ajax:
        return jsonify({"status": "ok", "message": "Desat"})

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


def iniciar_tunnel():
    global tunnel_url, tunnel_proc
    try:
        # Obrim stdout+stderr per detectar la URL en qualsevol stream de logs
        tunnel_proc = subprocess.Popen(
            ["cloudflared", "tunnel", "--url", "http://localhost:5000"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
    except Exception as e:
        print(f"Error iniciant cloudflared: {e}")
        return
    
    patro_url = re.compile(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com")

    # Llegim línia a línia fins trobar la URL pública del Quick Tunnel
    for linia in tunnel_proc.stdout:
        coincidencia = patro_url.search(linia)
        if coincidencia:
            tunnel_url = coincidencia.group(0)
            os.makedirs('static/img', exist_ok=True)
            img_qr = qrcode.make(tunnel_url)
            img_qr.save('static/img/qr_acces.png')
            break


def tancar_tunnel():
    global tunnel_proc
    if tunnel_proc:
        tunnel_proc.terminate()


atexit.register(tancar_tunnel)

if __name__ == "__main__":
    netejar_comandes_pendents_inici()
    threading.Thread(target=iniciar_tunnel, daemon=True).start()
    threading.Thread(target=worker_hardware, daemon=True).start()

    app.run(debug=False, port=5000, host="0.0.0.0", use_reloader=False)
