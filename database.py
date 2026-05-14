import sqlite3
import os
from decimal import Decimal, ROUND_HALF_UP

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
        SELECT m.Posicio, m.ID_Ingredient, i.Nom_Liquid, i.Categoria, i.Te_Alcohol,
               m.Capacitat_Actual_ml, m.Preu_Ampolla_Cents, m.Mida_Ampolla_ml
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
        CASE
            WHEN c.Te_Preu_Fix = 1 AND c.Preu_Fix_Cents IS NOT NULL AND c.Preu_Fix_Cents > 0
                THEN c.Preu_Fix_Cents
            ELSE c.Preu_Calculat_Cents
        END as Preu_Final_Cents,
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
        CASE
            WHEN c.Te_Preu_Fix = 1 AND c.Preu_Fix_Cents IS NOT NULL AND c.Preu_Fix_Cents > 0
                THEN c.Preu_Fix_Cents
            ELSE c.Preu_Calculat_Cents
        END as Preu_Final_Cents,
        (SELECT MAX(i.Te_Alcohol)
         FROM Receptes r
         JOIN Ingredients i ON i.Categoria = r.Categoria
         WHERE r.ID_Coctel = c.ID_Coctel) as Alcoholic
        FROM Coctels c
    """).fetchall()
    connexio.close()
    return [dict(fila) for fila in llistat]

def update_muntatge(posicio, id_ingredient, capacitat, preu_ampolla_cents, mida_ampolla_ml):
    connexio = connectar()
    connexio.execute("""UPDATE Muntatge
                        SET Capacitat_Actual_ml = ?,
                            ID_Ingredient = ?,
                            Preu_Ampolla_Cents = ?,
                            Mida_Ampolla_ml = ?
                        WHERE Posicio = ?""", (capacitat, id_ingredient, preu_ampolla_cents, mida_ampolla_ml, posicio))
    connexio.commit()
    connexio.close()

def get_configuracio():
    connexio = connectar()
    try:
        fila = connexio.execute(
            "SELECT Valor FROM Configuracio WHERE Clau = 'MARGE_BENEFICI'"
        ).fetchone()
        try:
            marge = float(fila['Valor']) if fila else 3.0
        except Exception:
            marge = 3.0
        return {"marge": marge}
    finally:
        connexio.close()

def update_marge_configuracio(nou_marge_str):
    nou_marge = float(nou_marge_str)
    connexio = connectar()
    try:
        connexio.execute(
            "UPDATE Configuracio SET Valor = ? WHERE Clau = 'MARGE_BENEFICI'",
            (str(nou_marge),)
        )
        connexio.commit()
    finally:
        connexio.close()

def get_dades_dashboard():
    connexio = connectar()
    try:
        estoc_ampolles = [dict(fila) for fila in connexio.execute("""
            SELECT i.Nom_Liquid, m.Capacitat_Actual_ml, m.Mida_Ampolla_ml
            FROM Muntatge m
            JOIN Ingredients i ON i.ID_Ingredient = m.ID_Ingredient
            ORDER BY m.Posicio
        """).fetchall()]

        finances_row = connexio.execute("""
            SELECT
                COALESCE(SUM(Preu_Venut_Cents), 0) AS Ingressos_Cents,
                COALESCE(SUM(Cost_Cents), 0) AS Costos_Cents
            FROM Comandes
        """).fetchone()

        top_coctels = [dict(fila) for fila in connexio.execute("""
            WITH comandes_norm AS (
                SELECT
                    CASE
                        WHEN Nom_Cocktail LIKE 'IA: %' THEN SUBSTR(Nom_Cocktail, 5)
                        ELSE Nom_Cocktail
                    END AS Nom_Normalitzat
                FROM Comandes
            )
            SELECT Nom_Normalitzat AS Nom, COUNT(*) AS Vendes
            FROM comandes_norm
            GROUP BY Nom_Normalitzat
            ORDER BY Vendes DESC
            LIMIT 10
        """).fetchall()]

        mix_ia = connexio.execute("""
            SELECT
                COALESCE(SUM(CASE WHEN Nom_Cocktail LIKE 'IA: %' THEN 1 ELSE 0 END), 0) AS IA,
                COALESCE(SUM(CASE WHEN Nom_Cocktail LIKE 'IA: %' THEN 0 ELSE 1 END), 0) AS Carta
            FROM Comandes
        """).fetchone()

        mix_alcohol = connexio.execute("""
            WITH comandes_norm AS (
                SELECT
                    CASE
                        WHEN Nom_Cocktail LIKE 'IA: %' THEN SUBSTR(Nom_Cocktail, 5)
                        ELSE Nom_Cocktail
                    END AS Nom_Normalitzat
                FROM Comandes
            ),
            coctels_alc AS (
                SELECT
                    c.Nom_Coctel,
                    COALESCE((
                        SELECT MAX(i.Te_Alcohol)
                        FROM Receptes r
                        JOIN Ingredients i ON i.Categoria = r.Categoria
                        WHERE r.ID_Coctel = c.ID_Coctel
                    ), 0) AS Alcoholic
                FROM Coctels c
            )
            SELECT
                COALESCE(SUM(CASE WHEN ca.Alcoholic = 1 THEN 1 ELSE 0 END), 0) AS Amb_Alcohol,
                COALESCE(SUM(CASE WHEN ca.Alcoholic = 1 THEN 0 ELSE 1 END), 0) AS Sense_Alcohol
            FROM comandes_norm cn
            LEFT JOIN coctels_alc ca ON ca.Nom_Coctel = cn.Nom_Normalitzat
        """).fetchone()

        ingressos = finances_row['Ingressos_Cents'] if finances_row else 0
        costos = finances_row['Costos_Cents'] if finances_row else 0

        return {
            "Estoc_Ampolles": estoc_ampolles,
            "Finances": {
                "Ingressos_Cents": ingressos,
                "Costos_Cents": costos,
                "Benefici_Cents": ingressos - costos
            },
            "Top_Coctels": top_coctels,
            "Mix_IA_vs_Carta": {
                "IA": mix_ia['IA'] if mix_ia else 0,
                "Carta": mix_ia['Carta'] if mix_ia else 0
            },
            "Mix_Alcohol_vs_00": {
                "Amb_Alcohol": mix_alcohol['Amb_Alcohol'] if mix_alcohol else 0,
                "Sense_Alcohol": mix_alcohol['Sense_Alcohol'] if mix_alcohol else 0
            }
        }
    finally:
        connexio.close()

def update_preu_fix_coctel(id_coctel, te_preu_fix, preu_fix_cents):
    connexio = connectar()
    connexio.execute("""
        UPDATE Coctels
        SET Te_Preu_Fix = ?,
            Preu_Fix_Cents = ?
        WHERE ID_Coctel = ?
    """, (te_preu_fix, preu_fix_cents, id_coctel))
    connexio.commit()
    connexio.close()

def round_half_up(valor: Decimal) -> int:
    return int(valor.quantize(Decimal('1'), rounding=ROUND_HALF_UP))

def arrodoniment_psicologic_cents(preu_cents):
    if preu_cents <= 0:
        return 0

    # Arrodoniment comercial a passos de 5 cèntims, sempre cap amunt
    return ((preu_cents + 4) // 5) * 5

def calcular_cost_ingredient_cents(preu_ampolla_cents, mida_ampolla_ml, quantitat_ml):
    if mida_ampolla_ml <= 0 or preu_ampolla_cents < 0 or quantitat_ml <= 0:
        return 0

    cost_per_ml = Decimal(preu_ampolla_cents) / Decimal(mida_ampolla_ml)
    cost_ingredient = Decimal(quantitat_ml) * cost_per_ml
    return round_half_up(cost_ingredient)

def recalcular_preus():
    connexio = connectar()
    try:
        # Transacció única per evitar valors inconsistents si hi ha un error
        marge_row = connexio.execute(
            "SELECT Valor FROM Configuracio WHERE Clau = 'MARGE_BENEFICI'"
        ).fetchone()

        try:
            marge_benefici = Decimal(marge_row['Valor']) if marge_row else Decimal('3.0')
        except Exception:
            marge_benefici = Decimal('3.0')

        costos_categoria = {}
        files_muntatge = connexio.execute("""
            SELECT i.Categoria, m.Preu_Ampolla_Cents, m.Mida_Ampolla_ml
            FROM Muntatge m
            JOIN Ingredients i ON i.ID_Ingredient = m.ID_Ingredient
        """).fetchall()

        for fila in files_muntatge:
            costos_categoria[fila['Categoria']] = {
                'preu_ampolla_cents': fila['Preu_Ampolla_Cents'],
                'mida_ampolla_ml': fila['Mida_Ampolla_ml']
            }

        coctels = connexio.execute("SELECT ID_Coctel FROM Coctels").fetchall()

        for coctel in coctels:
            id_coctel = coctel['ID_Coctel']
            recepta = connexio.execute(
                "SELECT Categoria, Quantitat_ml FROM Receptes WHERE ID_Coctel = ?",
                (id_coctel,)
            ).fetchall()

            cost_total = 0
            for ingredient in recepta:
                dades_categoria = costos_categoria.get(ingredient['Categoria'])
                if not dades_categoria:
                    continue

                cost_total += calcular_cost_ingredient_cents(
                    dades_categoria['preu_ampolla_cents'],
                    dades_categoria['mida_ampolla_ml'],
                    ingredient['Quantitat_ml']
                )

            preu_cru = round_half_up(Decimal(cost_total) * marge_benefici)
            preu_calculat = arrodoniment_psicologic_cents(preu_cru)

            connexio.execute("""
                UPDATE Coctels
                SET Preu_Produccio_Cents = ?,
                    Preu_Calculat_Cents = ?
                WHERE ID_Coctel = ?
            """, (cost_total, preu_calculat, id_coctel))

        connexio.commit()
    except Exception:
        connexio.rollback()
        raise
    finally:
        connexio.close()

def calcular_preu_recepta_ia(recepta_ia):
    connexio = connectar()
    try:
        if not isinstance(recepta_ia, dict) or not recepta_ia:
            return {"ok": False, "motiu": "recepta_buida"}

        marge_row = connexio.execute(
            "SELECT Valor FROM Configuracio WHERE Clau = 'MARGE_BENEFICI'"
        ).fetchone()

        try:
            marge_benefici = Decimal(marge_row['Valor']) if marge_row else Decimal('3.0')
        except Exception:
            marge_benefici = Decimal('3.0')

        muntatge = connexio.execute("""
            SELECT i.Nom_Liquid, m.Preu_Ampolla_Cents, m.Mida_Ampolla_ml
            FROM Muntatge m
            JOIN Ingredients i ON i.ID_Ingredient = m.ID_Ingredient
        """).fetchall()

        costos_per_liquid = {
            fila['Nom_Liquid']: {
                'preu_ampolla_cents': fila['Preu_Ampolla_Cents'],
                'mida_ampolla_ml': fila['Mida_Ampolla_ml']
            }
            for fila in muntatge
        }

        cost_total = 0
        for liquid, ml in recepta_ia.items():
            if liquid not in costos_per_liquid:
                return {"ok": False, "motiu": "ingredient_no_trobat", "ingredient": liquid}

            dades = costos_per_liquid[liquid]
            cost_total += calcular_cost_ingredient_cents(
                dades['preu_ampolla_cents'],
                dades['mida_ampolla_ml'],
                int(ml)
            )

        preu_cru = round_half_up(Decimal(cost_total) * marge_benefici)
        preu_final = arrodoniment_psicologic_cents(preu_cru)

        return {
            "ok": True,
            "cost_cents": cost_total,
            "preu_final_cents": preu_final
        }
    except Exception:
        return {"ok": False, "motiu": "error_calcul"}
    finally:
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

def registrar_comanda(nom_coctel, cost_cents, preu_venut_cents):
    conn = connectar()
    try:
        # Bloqueig d'escriptura per evitar col·lisions de torn simultànies
        conn.execute("BEGIN IMMEDIATE")

        fila = conn.execute("""
            SELECT Num_Comanda
            FROM Comandes
            WHERE DATE(Data_Hora, 'localtime') = DATE('now', 'localtime')
            ORDER BY ID_Comanda DESC
            LIMIT 1
        """).fetchone()

        ultim_num = int(fila['Num_Comanda']) if fila and fila['Num_Comanda'] is not None else 0

        # Torns cíclics diaris: 1..99 i torna a 1
        if ultim_num <= 0:
            nou_num = 1
        elif ultim_num >= 99:
            nou_num = 1
        else:
            nou_num = ultim_num + 1

        cost = int(cost_cents or 0)
        preu = int(preu_venut_cents or 0)

        cursor = conn.execute(
            """
            INSERT INTO Comandes (Nom_Cocktail, Cost_Cents, Preu_Venut_Cents, Estat, Num_Comanda)
            VALUES (?, ?, ?, 'Pendent', ?)
            """,
            (nom_coctel, cost, preu, nou_num)
        )

        conn.commit()
        return cursor.lastrowid, nou_num
    except Exception as e:
        conn.rollback()
        print(f"❌ ERROR REGISTRANT COMANDA: {e}")
        raise
    finally:
        conn.close()

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
