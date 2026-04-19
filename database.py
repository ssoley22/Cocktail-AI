import sqlite3
import os

# Ruta al fitxer de la base de dades
RUTA_DB = os.path.join(os.path.dirname(__file__), "database.db")

"""
ESQUEMA BASE DE DADES (database.db)
===================================
1. Ingredients: [ID_Ingredient, Nom_Liquid, Te_Alcohol, Categoria]
   Ex: (7, 'Absolut Vodka', 1, 'Vodka'), (35, 'Fanta Llimona', 0, 'Llimona')

2. Coctels:     [ID_Coctel, Nom_Coctel, Descripcio]
   Ex: (1, 'Vodka Llimona', ''), (2, 'Rom Sunrise', '')

3. Receptes:    [ID_Coctel, Categoria, Quantitat_ml, Ordre]
   Ex: (1, 'Vodka', 50, 1), (1, 'Llimona', 200, 2)

4. Muntatge:    [Posicio, ID_Ingredient, Capacitat_Actual_ml]
   Ex: (1, 7, 750), (2, 18, 1000)
"""


# Obre i retorna una connexió a la base de dades
def connectar():
    connexio = sqlite3.connect(RUTA_DB)
    connexio.row_factory = sqlite3.Row
    return connexio


def get_ingredients():
    '''
    Retorna una llista amb tots els ingredients de la base de dades
    [{'ID_Ingredient': , 'Nom_Liquid': , 'Te_Alcohol': , 'Categoria': }, ...]
    '''
    connexio = connectar()
    llistat = connexio.execute("SELECT * FROM Ingredients").fetchall()
    connexio.close()
    return [dict(fila) for fila in llistat]


def get_muntatge():
    '''
    Retorna l'estat de les 6 posicions del carril
    [{'Posicio': ,'ID_Ingredient': ,'Nom_Liquid': ,'Categoria': ,'Capacitat_Actual_ml': }, ...]
    '''
    connexio = connectar()
    llistat = connexio.execute("""
                                SELECT m.Posicio, m.ID_Ingredient, i.Nom_Liquid, i.Categoria, m.Capacitat_Actual_ml
                                FROM Muntatge m
                                JOIN Ingredients i ON m.ID_Ingredient = i.ID_Ingredient
                                ORDER BY m.Posicio
    """).fetchall()
    connexio.close()
    return [dict(fila) for fila in llistat]


def get_coctel(id):
    '''
    Retorna un còctel concret amb els seus ingredients i si té alcohol
    '''
    connexio = connectar()
    
    # MODIFICACIÓ: Afegim una subquery per calcular si el còctel és alcoholic (0 o 1)
    coctel = connexio.execute("""
        SELECT c.*, 
        (SELECT MAX(i.Te_Alcohol) 
         FROM Receptes r 
         JOIN Ingredients i ON i.Categoria = r.Categoria 
         WHERE r.ID_Coctel = c.ID_Coctel) as Alcoholic
        FROM Coctels c 
        WHERE c.ID_Coctel = ?
    """, (id,)).fetchone()

    if coctel is None:
        connexio.close()
        return None

    # Obtenim els ingredients de la recepta que estan actualment al muntatge
    ingredients = connexio.execute("""
        SELECT m.Posicio, i.Nom_Liquid, r.Quantitat_ml, r.Ordre
        FROM Receptes r
        JOIN Ingredients i ON i.Categoria = r.Categoria
        JOIN Muntatge m ON m.ID_Ingredient = i.ID_Ingredient
        WHERE r.ID_Coctel = ?
        GROUP BY r.Categoria
        ORDER BY r.Ordre ASC
    """, (id,)).fetchall()
    
    connexio.close()

    resultat = dict(coctel)
    # Ens assegurem que Alcoholic sigui un enter (0 o 1) per no tenir problemes al HTML
    resultat["Alcoholic"] = int(resultat["Alcoholic"]) if resultat["Alcoholic"] is not None else 0
    resultat["Recepta"] = [dict(i) for i in ingredients]
    
    return resultat

def get_coctels_disponibles():
    '''
    Retorna una llista amb tots els còctels de la base de dades que es poden preparar
    [{'ID_Coctel': , 'Nom_Coctel': , 'Descripcio': }, ...]
    '''
    connexio = connectar()
    llistat = connexio.execute("""SELECT c.ID_Coctel, c.Nom_Coctel, c.Descripcio
                               FROM Coctels c
                               WHERE NOT EXISTS (
                                    SELECT 1 FROM Receptes r
                                    WHERE r.ID_Coctel = c.ID_Coctel
                                    AND r.Categoria
                                    NOT IN (
                                    SELECT i.Categoria
                                    FROM Muntatge m
                                    JOIN Ingredients i ON m.ID_Ingredient = i.ID_Ingredient
                                    WHERE m.Capacitat_Actual_ml >= r.Quantitat_ml
                                    )
                               )
                               """).fetchall()
    connexio.close()
    return [dict(fila) for fila in llistat]


def update_muntatge(posicio, id_ingredient, capacitat):
    '''
    Actualitza una posició del muntatge amb un nou ingredient i capacitat
    '''
    connexio = connectar()
    connexio.execute("""UPDATE Muntatge
                     SET Capacitat_Actual_ml = ?, ID_Ingredient = ?
                     WHERE Posicio = ?""", (capacitat, id_ingredient, posicio))
    connexio.commit()
    connexio.close()


def restar_estoc(id_coctel):
    '''
    Resta les quantitats requerides per una recepta de l'estoc actual del muntatge.
    Retorna True si ha anat bé, False si no hi ha prou estoc.
    '''
    coctel = get_coctel(id_coctel)
    if coctel is None:
        return False

    recepta = coctel["Recepta"]
    muntatge = {m["Posicio"]: m["Capacitat_Actual_ml"] for m in get_muntatge()}

    for ingredient in recepta:
        if muntatge.get(ingredient["Posicio"], 0) < ingredient["Quantitat_ml"]:
            return False

    connexio = connectar()
    for ingredient in recepta:
        connexio.execute("""UPDATE Muntatge
                         SET Capacitat_Actual_ml = Capacitat_Actual_ml - ?
                         WHERE Posicio = ?
                         """, (ingredient["Quantitat_ml"], ingredient["Posicio"]))
    connexio.commit()
    connexio.close()
    return True

def get_tots_els_coctels():
    '''
    Retorna absolutament tots els còctels per al catàleg manual.
    També mirem si tenen alcohol sumant si algun ingredient de la recepta en té.
    '''
    connexio = connectar()
    # Agafem els còctels i mirem si algun dels seus ingredients té alcohol (Te_Alcohol = 1)
    llistat = connexio.execute("""
        SELECT c.*, 
        (SELECT MAX(i.Te_Alcohol) 
         FROM Receptes r 
         JOIN Ingredients i ON i.Categoria = r.Categoria 
         WHERE r.ID_Coctel = c.ID_Coctel) as Alcoholic
        FROM Coctels c
    """).fetchall()
    connexio.close()
    return [dict(fila) for fila in llistat]

def get_ids_disponibles():
    '''
    Retorna només una llista amb els IDs dels còctels que es poden fer ARA.
    Aquesta funció ens servirà per posar el "check" de disponibilitat.
    '''
    coctels_ok = get_coctels_disponibles()
    return [c['ID_Coctel'] for c in coctels_ok]


