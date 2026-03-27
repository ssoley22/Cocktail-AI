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


def get_coctel(id):
    '''
    Retorna un còctel concret amb els seus ingredients
    {'ID_Coctel': ,'Nom_Coctel': ,'Descripcio': ,'Recepta': [{'ID_Ingredient': ,'Nom_Liquid': ,'Quantitat_ml': },...]}
    '''
    connexio = connectar()
    # Busquem el còctel per ID
    coctel = connexio.execute("SELECT * FROM Coctels WHERE ID_Coctel = ?", (id,)).fetchone()

    # Si no existeix retornem None
    if coctel is None:
        connexio.close()
        return None
    
    ingredients = connexio.execute("""
                                    SELECT i.ID_Ingredient, i.Nom_Liquid, r.Quantitat_ml 
                                    FROM Receptes r 
                                     JOIN Ingredients i ON r.ID_Ingredient = i.ID_Ingredient 
                                     WHERE r.ID_Coctel = ?
    """, (id,)).fetchall()
    connexio.close()

    # Convertim el còctel a diccionari i afegim els ingredients
    resultat = dict(coctel)
    resultat["Recepta"] = [dict(i) for i in ingredients]
    return resultat


def get_muntatge():
    '''
    Retorna l'estat de les 6 posicions del carril
    [{'Posicio': , 'ID_Ingredient': , 'Nom_Liquid': , 'Capacitat_Actual_ml': }, ...]
    '''
    connexio = connectar()
    # Busquem les 6 posicions amb el nom de l'ingredient de cada una
    llistat = connexio.execute("""
                                SELECT m.Posicio, m.ID_Ingredient, i.Nom_Liquid, m.Capacitat_Actual_ml
                                FROM Muntatge m
                                JOIN Ingredients i ON m.ID_Ingredient = i.ID_Ingredient
                                ORDER BY m.Posicio
    """).fetchall()
    connexio.close()

    return [dict(fila) for fila in llistat]


def get_ingredients():
    '''
    Retorna una llista amb tots els ingredients de la base de dades
    [{'ID_Ingredient': , 'Nom_Liquid': , 'Te_Alcohol': }, ...]
    '''
    connexio = connectar()
    llistat = connexio.execute("SELECT * FROM Ingredients").fetchall()
    connexio.close()
    return [dict(fila) for fila in llistat]

def get_coctels_disponibles():
    '''
    Retorna una llista amb tots els còctels de la base de dades que es poden preparar
    [{'ID_Coctel': , 'Nom_Coctel': , 'Descripcio': }, ...]
    '''
    # Obrim la connexió a la base de dades
    connexio = connectar()  
    # Executem la consulta i guardem els resultats
    llistat = connexio.execute("""SELECT c.ID_Coctel, c.Nom_Coctel, c.Descripcio
                               FROM Coctels c
                               WHERE NOT EXISTS (
                                    SELECT 1 FROM Receptes r
                                    LEFT JOIN Muntatge m ON r.ID_Ingredient = m.ID_Ingredient
                                    WHERE r.ID_Coctel = c.ID_Coctel
                                    AND (
                                        m.ID_Ingredient IS NULL
                                        OR  m.Capacitat_Actual_ml < r.Quantitat_ml
                                    )
                               )
                               """).fetchall()
    # Tanquem la connexió
    connexio.close()
    # Retornem els resultats convertits a llista de diccionaris
    return [dict(fila) for fila in llistat]

def update_muntatge(posicio, id_ingredient, capacitat):
    '''
    Acutalitza una posició del muntatge amb un nou ingredient i capacitat
    '''
    connexio = connectar()

    connexio.execute("""UPDATE Muntatge
                     SET Capacitat_Actual_ml = ?, ID_Ingredient = ?
                     Where Posicio = ?""", (capacitat, id_ingredient, posicio))
    
    connexio.commit()
    connexio.close()


def restar_estoc(id_coctel):
    '''
    Resta les quantitats requerides per una recepta de l'estoc actual del muntatge
    '''
    recepta = get_coctel(id_coctel)["Recepta"] # [{'ID_Ingredient': ,'Nom_Liquid': ,'Quantitat_ml': },...]}
    connexio = connectar()
    
    for ingredient in recepta:
        connexio.execute("""UPDATE Muntatge
                         SET Capacitat_Actual_ml = Capacitat_Actual_ml - ?
                         WHERE ID_Ingredient = ?
                         """, (ingredient["Quantitat_ml"], ingredient["ID_Ingredient"]))
    connexio.commit()
    connexio.close()
