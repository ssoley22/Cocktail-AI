import sqlite3
import os

DB_PATH = "database.db"

# Esborra la DB si ja existeix per començar net
if os.path.exists(DB_PATH):
    os.remove(DB_PATH)
    print("DB anterior esborrada. Creant la nova versió per CATEGORIES...")

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# =====================
# CREAR TAULES
# =====================
cursor.executescript("""
    CREATE TABLE Coctels (
        ID_Coctel  INTEGER PRIMARY KEY AUTOINCREMENT,
        Nom_Coctel TEXT NOT NULL,
        Descripcio TEXT
    );

    CREATE TABLE Ingredients (
        ID_Ingredient INTEGER PRIMARY KEY AUTOINCREMENT,
        Nom_Liquid    TEXT NOT NULL,
        Te_Alcohol    INTEGER NOT NULL DEFAULT 0,
        Categoria     TEXT NOT NULL
    );

    CREATE TABLE Receptes (
        ID_Coctel     INTEGER NOT NULL,
        Categoria     TEXT NOT NULL, 
        Quantitat_ml  INTEGER NOT NULL,
        Ordre         INTEGER NOT NULL,
        FOREIGN KEY (ID_Coctel) REFERENCES Coctels(ID_Coctel)
    );

    CREATE TABLE Muntatge (
        Posicio             INTEGER PRIMARY KEY CHECK (Posicio BETWEEN 1 AND 6),
        ID_Ingredient       INTEGER NOT NULL,
        Capacitat_Actual_ml INTEGER NOT NULL DEFAULT 0,
        FOREIGN KEY (ID_Ingredient) REFERENCES Ingredients(ID_Ingredient)
    );
""")

# =====================
# INGREDIENTS
# =====================
ingredients = [
    # ID, Nom, Alcohol, Categoria
    (1,  "Johnnie Walker",    1, "Whisky"),
    (2,  "JB",                1, "Whisky"),
    (3,  "Ballantine's",      1, "Whisky"),
    (4,  "Jack Daniel's",     1, "Whisky"),
    (5,  "Chivas Regal",      1, "Whisky"),
    (6,  "White Label",       1, "Whisky"),
    (7,  "Absolut Vodka",     1, "Vodka"),
    (8,  "Smirnoff",          1, "Vodka"),
    (9,  "Grey Goose",        1, "Vodka"),
    (10, "Belvedere",         1, "Vodka"),
    (11, "Eristoff",          1, "Vodka"),
    (12, "Seagram's",         1, "Ginebra"),
    (13, "Beefeater",         1, "Ginebra"),
    (14, "Tanqueray",         1, "Ginebra"),
    (15, "Bombay Sapphire",   1, "Ginebra"),
    (16, "Larios",            1, "Ginebra"),
    (17, "Puerto de Indias",  1, "Ginebra"),
    (18, "Brugal",            1, "Rom"),
    (19, "Barceló",           1, "Rom"),
    (20, "Havana Club",       1, "Rom"),
    (21, "Bacardí",           1, "Rom"),
    (22, "Captain Morgan",    1, "Rom"),
    (23, "Jägermeister",      1, "Licor Herbes"),
    (24, "Baileys",           1, "Crema"),
    (25, "Licor 43",          1, "Licor Dolç"),
    (26, "Malibu",            1, "Licor Coco"),
    (27, "Amaretto",          1, "Licor Ametlla"),
    (28, "Cointreau",         1, "Licor Taronja"),
    (29, "Tequila",           1, "Tequila"),
    (30, "Vermut",            1, "Vermut"),
    (31, "Campari",           1, "Aperitiu"),
    (32, "Aperol",            1, "Aperitiu"),
    (33, "Coca-Cola",         0, "Refresc Cola"),
    (34, "Fanta de taronja",  0, "Refresc Taronja"),
    (35, "Fanta de llimona",  0, "Refresc Llimona"),
    (36, "Sprite",            0, "Refresc Llima-Llimona"),
    (37, "7Up",               0, "Refresc Llima-Llimona"),
    (38, "Tònica",            0, "Tònica"),
    (39, "Bitter Kas",        0, "Bitter"),
    (40, "Nestea",            0, "Té"),
    (41, "Aquarius llimona",  0, "Isotònic"),
    (42, "Aquarius taronja",  0, "Isotònic"),
    (43, "Suc de taronja",    0, "Suc Taronja"),
    (44, "Suc de pinya",      0, "Suc Pinya"),
    (45, "Suc de préssec",    0, "Suc Préssec"),
    (46, "Suc de llimona",    0, "Suc Llimona"),
    (47, "Suc de llima",      0, "Suc Llima"),
    (48, "Aigua amb gas",     0, "Gasosa"),
    (49, "Granadina",         0, "Colorant Vermell"),
    (50, "Suc de Nabius",     0, "Colorant Vermell"), 
]

cursor.executemany(
    "INSERT INTO Ingredients (ID_Ingredient, Nom_Liquid, Te_Alcohol, Categoria) VALUES (?, ?, ?, ?)",
    ingredients
)

id_a_cat = {item[0]: item[3] for item in ingredients}

# =====================
# CÒCTELS MESTRES
# =====================
coctels_mestres = [
    ("Whisky Cola",     [(33,200,1),(1,50,2)]),
    ("Whisky Llimona",  [(35,200,1),(1,50,2)]),
    ("Whisky Ginger",   [(37,200,1),(1,50,2)]),
    ("Whisky Sprite",   [(36,200,1),(1,50,2)]),
    ("Whisky Taronja",  [(43,200,1),(1,50,2)]),
    ("Vodka Llimona",   [(35,200,1),(7,50,2)]),
    ("Vodka Taronja",   [(34,200,1),(7,50,2)]),
    ("Vodka Tònica",    [(38,200,1),(7,50,2)]),
    ("Vodka Sprite",    [(36,200,1),(7,50,2)]),
    ("Vodka Cola",      [(33,200,1),(7,50,2)]),
    ("Vodka Pinya",     [(44,200,1),(7,50,2)]),
    ("Vodka Préssec",   [(45,200,1),(7,50,2)]),
    ("Cuba Libre",      [(33,200,1),(18,50,2)]),
    ("Rom Llimona",     [(35,200,1),(18,50,2)]),
    ("Rom Taronja",     [(43,200,1),(18,50,2)]),
    ("Rom Sprite",      [(36,200,1),(18,50,2)]),
    ("Rom Pinya",       [(44,200,1),(18,50,2)]),
    ("Ginebra Llimona", [(35,200,1),(12,50,2)]),
    ("Gin Tònic",       [(38,200,1),(12,50,2)]),
    ("Ginebra Sprite",  [(36,200,1),(12,50,2)]),
    ("Ginebra Taronja", [(34,200,1),(12,50,2)]),
    ("Jäger Cola",      [(33,200,1),(23,50,2)]),
    ("Jäger Llimona",   [(35,200,1),(23,50,2)]),
    ("Jäger Tònica",    [(38,200,1),(23,50,2)]),
    ("Licor 43 Pinya",  [(44,200,1),(25,50,2)]),
    ("Licor 43 Cola",   [(33,200,1),(25,50,2)]),
    ("Malibu Pinya",    [(44,200,1),(26,50,2)]),
    ("Malibu Cola",     [(33,200,1),(26,50,2)]),
    ("Amaretto Cola",   [(33,200,1),(27,50,2)]),
    ("Aperol Spritz (Mecatrònic)", [(48,100,1),(34,100,2),(32,50,3)]),
    ("Aperol Tònica",   [(38,200,1),(32,50,2)]),
    ("Campari Soda",    [(48,200,1),(31,50,2)]),
    ("Vermut Taronja",  [(34,150,1),(30,100,2)]),
    ("Tequila Llimona", [(35,200,1),(29,50,2)]),
    ("Tequila Sprite",  [(36,200,1),(29,50,2)]),
    ("Tequila Cola",    [(33,200,1),(29,50,2)]),
    ("Vodka Sunrise",   [(43,150,1),(7,50,2),(50,30,3)]),
    ("Tequila Sunrise", [(43,150,1),(29,50,2),(50,30,3)]),
    ("Rom Sunrise",     [(43,150,1),(18,50,2),(50,30,3)]),
    ("Gin Sunrise",     [(43,150,1),(12,50,2),(50,30,3)]),
    ("Cosmopolitan",    [(50,120,1),(35,80,2),(7,50,3)]),
    ("Pink Lemonade",   [(35,170,1),(7,50,2),(50,30,3)]),
    ("Brisa Tropical",  [(43,100,1),(50,100,2),(18,50,3)]),
    ("Tornavís",        [(43,200,1),(7,50,2)]),
    ("Black Russian",   [(10,30,1),(27,20,2)]),
    ("Mexican Mule",    [(36,150,1),(29,40,2),(28,10,3)]),
    ("Italian Job",     [(38,150,1),(31,30,2),(16,20,3)]),
    ("Sweet Sunrise",   [(43,150,1),(35,50,2),(50,50,3)]),
    ("San Francisco",   [(43,100,1),(44,50,2),(45,50,3),(50,30,4)]),
    ("Llimonada Rosa",  [(35,200,1),(50,40,2)]),
]

# Inserir còctels i receptes
for nom, recepta in coctels_mestres:
    cursor.execute("INSERT INTO Coctels (Nom_Coctel, Descripcio) VALUES (?, NULL)", (nom,))
    id_coctel = cursor.lastrowid
    for id_ing, ml, ordre in recepta:
        categoria_text = id_a_cat[id_ing]
        cursor.execute(
            "INSERT INTO Receptes (ID_Coctel, Categoria, Quantitat_ml, Ordre) VALUES (?, ?, ?, ?)",
            (id_coctel, categoria_text, ml, ordre)
        )

# =====================
# MUNTATGE INICIAL (ACTUALITZAT)
# =====================
muntatge_inicial = [
    (1, 1),   # Posició 1 - Johnnie Walker (Whisky)
    (2, 7),   # Posició 2 - Absolut Vodka (Vodka)
    (3, 12),  # Posició 3 - Seagram's (Ginebra)
    (4, 18),  # Posició 4 - Brugal (Rom)
    (5, 33),  # Posició 5 - Coca-Cola (Refresc Cola)
    (6, 35),  # Posició 6 - Fanta de llimona (Refresc Llimona)
]

for posicio, id_ingredient in muntatge_inicial:
    cursor.execute(
        "INSERT INTO Muntatge (Posicio, ID_Ingredient, Capacitat_Actual_ml) VALUES (?, ?, 0)",
        (posicio, id_ingredient)
    )

conn.commit()

# Resum final
print(f"✅ DB creada amb èxit!")
print(f"  - Receptes usant CATEGORIES genèriques.")
print(f"  - Muntatge configurat per: Whisky, Vodka, Gin, Rom, Cola i Llimona.")
conn.close()