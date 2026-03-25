import sqlite3
import os

# Ruta al fitxer de la base de dades
RUTA_DB = os.path.join(os.path.dirname(__file__), "database.db")

# Obre i retorna una connexió a la base de dades
def connectar():
    connexio = sqlite3.connect(RUTA_DB)
    connexio.row_factory = sqlite3.Row
    return connexio


def get_coctels():
    '''
    Retorna una llista amb tots els còctels de la base de dades
    [{'ID_Coctel': , 'Nom_Coctel': , 'Descripcio': }, ...]
    '''
    # Obrim la connexió a la base de dades
    connexio = connectar()  
    # Executem la consulta i guardem els resultats
    llistat = connexio.execute("SELECT * FROM Coctels").fetchall()
    # Tanquem la connexió
    connexio.close()
    # Retornem els resultats convertits a llista de diccionaris
    return [dict(fila) for fila in llistat]


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

for a in get_ingredients():
    print(a)


def coctel_disponible(coctel):
    # coctel = {'ID_Coctel': ,'Nom_Coctel': ,'Descripcio': ,'Recepta': [{'ID_Ingredient': ,'Nom_Liquid': ,'Quantitat_ml': },...]}
    muntatge = get_muntatge()  # [{'Posicio': , 'ID_Ingredient': , 'Nom_Liquid': , 'Capacitat_Actual_ml': }, ...]
    
    for ingredient in coctel["Recepta"]:
        for ampolla in muntatge:
            if ingredient["ID_Ingredient"] == ampolla["ID_Ingredient"]:
                if ampolla["Capacitat_Actual_ml"] >= ingredient["Quantitat_ml"]:
                    return coctel


def get_coctels_disponibles():
    ll_completa = get_coctels()
    ll_disponibles = []

    for coctel in ll_completa:
        ll_disponibles.append(coctel_disponible(coctel))

    return ll_disponibles
