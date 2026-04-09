from flask import Flask, render_template, request, redirect, url_for, session
import database
import random

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


@app.route('/preparar/<int:id_coctel>', methods=['POST'])
def preparar(id_coctel):
    if database.restar_estoc(id_coctel):
        dades = database.get_coctel(id_coctel)
        return render_template('preparant.html', coctel=dades)
    return render_template('error.html', missatge="No hi ha prou estoc per preparar aquest còctel.")


# ==================== EMOCIONS I XAT (provisional) ====================

@app.route('/emocions')
def emocions():
    return render_template('emocions.html')


@app.route('/recomanacio/<sentit>')
def recomanacio(sentit):
    disponibles = database.get_coctels_disponibles()
    if not disponibles:
        return render_template('error.html', missatge="No hi ha estoc per a cap còctel.")
    coctel = database.get_coctel(random.choice(disponibles)['ID_Coctel'])
    return render_template('confirmacio.html', coctel=coctel, disponible=True, origen='/emocions')


@app.route('/xat')
def xat():
    return render_template('xat.html')


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