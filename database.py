import sqlite3
import os

RUTA_DB = os.path.join(os.path.dirname(__file__), "database.db")

def connectar():
    connexio = sqlite3.connect(RUTA_DB)
    # Activa WAL per reduir bloquejos en lectures/escriptures simultànies
    connexio.execute('PRAGMA journal_mode=WAL;')
    connexio.row_factory = sqlite3.Row
    return connexio

def get_ingredients():
    connexio = connectar()
    llistat = connexio.execute("SELECT * FROM Ingredients").fetchall()
    connexio.close()
    return [dict(fila) for fila in llistat]

def get_muntatge():
    connexio = connectar()
    llistat = connexio.execute("""
        SELECT m.Posicio, m.ID_Ingredient, i.Nom_Liquid, i.Categoria, i.Te_Alcohol, m.Capacitat_Actual_ml
        FROM Muntatge m
        JOIN Ingredients i ON m.ID_Ingredient = i.ID_Ingredient
        ORDER BY m.Posicio
    """).fetchall()
    connexio.close()
    return [dict(fila) for fila in llistat]

def get_coctel(id):
    connexio = connectar()
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

    ingredients = connexio.execute("""
        SELECT MIN(m.Posicio) as Posicio, i.Nom_Liquid, r.Quantitat_ml, r.Ordre
        FROM Receptes r
        JOIN Ingredients i ON i.Categoria = r.Categoria
        JOIN Muntatge m ON m.ID_Ingredient = i.ID_Ingredient
        WHERE r.ID_Coctel = ?
        GROUP BY r.Categoria
        ORDER BY r.Ordre ASC
    """, (id,)).fetchall()
    connexio.close()

    resultat = dict(coctel)
    resultat["Alcoholic"] = int(resultat["Alcoholic"]) if resultat["Alcoholic"] is not None else 0
    resultat["Recepta"] = [dict(i) for i in ingredients]
    return resultat

def get_coctels_disponibles():
    connexio = connectar()
    llistat = connexio.execute("""
        SELECT c.ID_Coctel, c.Nom_Coctel, c.Descripcio,
               GROUP_CONCAT(DISTINCT r.Categoria) as Ingredients
        FROM Coctels c
        JOIN Receptes r ON r.ID_Coctel = c.ID_Coctel
        WHERE NOT EXISTS (
            SELECT 1 FROM Receptes r2
            WHERE r2.ID_Coctel = c.ID_Coctel
            AND r2.Categoria NOT IN (
                SELECT i.Categoria FROM Muntatge m
                JOIN Ingredients i ON m.ID_Ingredient = i.ID_Ingredient
                WHERE m.Capacitat_Actual_ml >= r2.Quantitat_ml
            )
        )
        GROUP BY c.ID_Coctel
    """).fetchall()
    connexio.close()
    return [dict(fila) for fila in llistat]

def get_tots_els_coctels():
    connexio = connectar()
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

def update_muntatge(posicio, id_ingredient, capacitat):
    connexio = connectar()
    connexio.execute("""UPDATE Muntatge
                        SET Capacitat_Actual_ml = ?, ID_Ingredient = ?
                        WHERE Posicio = ?""", (capacitat, id_ingredient, posicio))
    connexio.commit()
    connexio.close()

def restar_estoc(id_coctel):
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

# --- FUNCIONS NOVES (Comandes i Receptes Manuals) ---

def registrar_comanda(nom_coctel):
    # La taula ja existeix (està a crear_db.py) per tant només cal fer l'INSERT. Molt més ràpid.
    try:
        conn = connectar()
        conn.execute("INSERT INTO Comandes (Nom_Cocktail) VALUES (?)", (nom_coctel,))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"❌ ERROR REGISTRANT COMANDA: {e}")

def get_estadistiques():
    connexio = connectar()
    try:
        llistat = connexio.execute("""
            SELECT Nom_Cocktail, COUNT(*) as quantitat 
            FROM Comandes 
            GROUP BY Nom_Cocktail 
            ORDER BY quantitat DESC
        """).fetchall()
        return [dict(fila) for fila in llistat]
    except Exception as e:
        return []
    finally:
        connexio.close()

def crear_recepta_completa(nom, descripcio, ingredients):
    """
    Guarda un còctel nou buscant la categoria correcta dels líquids passats
    """
    conn = connectar()
    cursor = conn.cursor()
    try:
        # Inserim només Nom i Descripcio (Alcoholic es dedueix sol)
        cursor.execute("INSERT INTO Coctels (Nom_Coctel, Descripcio) VALUES (?, ?)", (nom, descripcio))
        id_coctel = cursor.lastrowid
        
        ordre = 1
        for ing in ingredients:
            # Busquem a quina categoria pertany aquest líquid
            cat_row = cursor.execute("SELECT Categoria FROM Ingredients WHERE ID_Ingredient = ?", (ing['id_liquid'],)).fetchone()
            if cat_row:
                categoria = cat_row['Categoria']
                cursor.execute("INSERT INTO Receptes (ID_Coctel, Categoria, Quantitat_ml, Ordre) VALUES (?, ?, ?, ?)", 
                               (id_coctel, categoria, ing['ml'], ordre))
                ordre += 1
        
        conn.commit()
    except Exception as e:
        print(f"Error creant recepta: {e}")
        conn.rollback()
    finally:
        conn.close()
