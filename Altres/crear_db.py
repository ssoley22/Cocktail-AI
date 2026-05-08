import sqlite3
import os

RUTA_DB = os.path.join(os.path.dirname(__file__), "database.db")

def crear_database():
    if os.path.exists(RUTA_DB):
        os.remove(RUTA_DB)
        print("Base de dades existent eliminada.")

    conn = sqlite3.connect(RUTA_DB)

    # ==========================================
    # 1. CREAR TAULES (Ara amb Comandes inclosa)
    # ==========================================
    conn.executescript("""
        CREATE TABLE Ingredients (
            ID_Ingredient INTEGER PRIMARY KEY AUTOINCREMENT,
            Nom_Liquid    TEXT NOT NULL,
            Te_Alcohol    INTEGER NOT NULL DEFAULT 0,
            Categoria     TEXT NOT NULL
        );

        CREATE TABLE Coctels (
            ID_Coctel  INTEGER PRIMARY KEY AUTOINCREMENT,
            Nom_Coctel TEXT NOT NULL,
            Descripcio TEXT,
            Preu_Produccio_Cents INTEGER NOT NULL DEFAULT 0,
            Preu_Calculat_Cents INTEGER NOT NULL DEFAULT 0,
            Preu_Fix_Cents INTEGER,
            Te_Preu_Fix INTEGER NOT NULL DEFAULT 0
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
            Preu_Ampolla_Cents  INTEGER NOT NULL DEFAULT 0,
            Mida_Ampolla_ml     INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (ID_Ingredient) REFERENCES Ingredients(ID_Ingredient)
        );

        CREATE TABLE Configuracio (
            Clau TEXT PRIMARY KEY,
            Valor TEXT NOT NULL
        );

        CREATE TABLE Comandes (
            ID_Comanda    INTEGER PRIMARY KEY AUTOINCREMENT,
            Nom_Cocktail  TEXT NOT NULL,
            Data_Hora     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # ==========================================
    # 2. INSERIR INGREDIENTS (50)
    # ==========================================
    ingredients = [
        (1,  'Johnnie Walker',     1, 'Whisky'),
        (2,  'JB',                 1, 'Whisky'),
        (3,  "Ballantine's",       1, 'Whisky'),
        (4,  "Jack Daniel's",      1, 'Whisky'),
        (5,  'Chivas Regal',       1, 'Whisky'),
        (6,  'White Label',        1, 'Whisky'),
        (7,  'Absolut Vodka',      1, 'Vodka'),
        (8,  'Smirnoff',           1, 'Vodka'),
        (9,  'Grey Goose',         1, 'Vodka'),
        (10, 'Belvedere',          1, 'Vodka'),
        (11, 'Eristoff',           1, 'Vodka'),
        (12, "Seagram's",          1, 'Ginebra'),
        (13, 'Beefeater',          1, 'Ginebra'),
        (14, 'Tanqueray',          1, 'Ginebra'),
        (15, 'Bombay Sapphire',    1, 'Ginebra'),
        (16, 'Larios',             1, 'Ginebra'),
        (17, 'Puerto de Indias',   1, 'Ginebra'),
        (18, 'Brugal',             1, 'Rom'),
        (19, 'Barceló',            1, 'Rom'),
        (20, 'Havana Club',        1, 'Rom'),
        (21, 'Bacardí',            1, 'Rom'),
        (22, 'Captain Morgan',     1, 'Rom'),
        (23, 'Jägermeister',       1, 'Licor Herbes'),
        (24, 'Baileys',            1, 'Crema'),
        (25, 'Licor 43',           1, 'Licor Dolç'),
        (26, 'Malibu',             1, 'Licor Coco'),
        (27, 'Amaretto',           1, 'Licor Ametlla'),
        (28, 'Cointreau',          1, 'Licor Taronja'),
        (29, 'Tequila',            1, 'Tequila'),
        (30, 'Vermut',             1, 'Vermut'),
        (31, 'Campari',            1, 'Aperitiu'),
        (32, 'Aperol',             1, 'Aperitiu'),
        (33, 'Coca-Cola',          0, 'Refresc Cola'),
        (34, 'Fanta de taronja',   0, 'Refresc Taronja'),
        (35, 'Fanta de llimona',   0, 'Refresc Llimona'),
        (36, 'Sprite',             0, 'Refresc Llima-Llimona'),
        (37, '7Up',                0, 'Refresc Llima-Llimona'),
        (38, 'Tònica',             0, 'Tònica'),
        (39, 'Bitter Kas',         0, 'Bitter'),
        (40, 'Nestea',             0, 'Té'),
        (41, 'Aquarius llimona',   0, 'Isotònic'),
        (42, 'Aquarius taronja',   0, 'Isotònic'),
        (43, 'Suc de taronja',     0, 'Suc Taronja'),
        (44, 'Suc de pinya',       0, 'Suc Pinya'),
        (45, 'Suc de préssec',     0, 'Suc Préssec'),
        (46, 'Suc de llimona',     0, 'Suc Llimona'),
        (47, 'Suc de llima',       0, 'Suc Llima'),
        (48, 'Aigua amb gas',      0, 'Gasosa'),
        (49, 'Granadina',          0, 'Colorant Vermell'),
        (50, 'Suc de Nabius',      0, 'Colorant Vermell'),
    ]
    conn.executemany(
        "INSERT INTO Ingredients (ID_Ingredient, Nom_Liquid, Te_Alcohol, Categoria) VALUES (?, ?, ?, ?)",
        ingredients
    )

    # ==========================================
    # 3. INSERIR COCTELS AMB DESCRIPCIONS (57)
    # ==========================================
    coctels = [
        (1,  'Whisky Cola',              "El clàssic atemporal. La intensitat de la fusta del whisky amb l'espurna dolça de la cola."),
        (2,  'Whisky Llimona',           "Un contrast perfecte entre el caràcter fort del whisky i la frescor del cítric."),
        (3,  'Whisky Ginger',            "Notes suaus i refrescants que eleven el whisky a un combinat molt fàcil de beure."),
        (4,  'Whisky Sprite',            "Bombolles cristal·lines que suavitzen la intensitat i donen un toc dolç."),
        (5,  'Whisky Taronja',           "Una combinació atrevida i afruitada, ideal per sortir de la rutina."),
        (6,  'Vodka Llimona',            "L'ànima de la festa. Cítric, potent i extremadament refrescant."),
        (7,  'Vodka Taronja',            "El clàssic 'Tornavís'. Un toc de dolçor i vitamina per gaudir de la nit."),
        (8,  'Vodka Tònica',             "Sec, transparent i directe. Per als paladars més elegants i sofisticats."),
        (9,  'Vodka Sprite',             "Dolçor suau i neta amb una espurna elèctrica al final."),
        (10, 'Vodka Cola',               "Intens i fosc, l'alternativa moderna al clàssic cubalibre."),
        (11, 'Vodka Pinya',              "Viatge directe al Carib. Un combinat dolç, tropical i molt suau."),
        (12, 'Vodka Préssec',            "Aterciopelat i molt afruitat, una delícia per als més llaminers."),
        (13, 'Cuba Libre',               "L'autèntic sabor de l'Havana. Rom, cola i un toc inconfusiblement llatí."),
        (14, 'Rom Llimona',              "L'esperit pirata barrejat amb una alenada de frescor estiuenca."),
        (15, 'Rom Taronja',              "Dolçor afruitada que combina a la perfecció amb els matisos del rom daurat."),
        (16, 'Rom Sprite',               "Llima, llimona i rom: una trinitat refrescant per a les nits llargues."),
        (17, 'Rom Pinya',                "La pinya colada minimalista. Pura fruita tropical amb caràcter."),
        (18, 'Ginebra Llimona',          "El toc botànic inconfusible de la ginebra tancat en una explosió cítrica."),
        (19, 'Gin Tònic',                "El rei indiscutible de la cocteleria moderna. Sec, amargant i aromàtic."),
        (20, 'Ginebra Sprite',           "Una versió molt més dolça i suau per als que fugen de l'amargor de la tònica."),
        (21, 'Ginebra Taronja',          "Un gir divertit i afruitat per redescobrir el gust de l'enginy."),
        (22, 'Jäger Cola',               "Energia pura i notes herbals fosques. Prepara't perquè la nit és jove."),
        (23, 'Jäger Llimona',            "Un contrast sorprenent que equilibra l'herbal amargant amb el cítric."),
        (24, 'Jäger Tònica',             "Complex, profund i molt amargant. Un repte només per als més atrevits."),
        (25, 'Licor 43 Pinya',           "Un somni dolç i avainillat envoltat de pur paisatge tropical."),
        (26, 'Licor 43 Cola',            "L'essència daurada de Cartagena de Indias barrejada amb la foscor de la cola."),
        (27, 'Malibu Pinya',             "Tanca els ulls: coco, pinya i brisa marina. Ets a una platja de sorra blanca."),
        (28, 'Malibu Cola',              "El toc inconfusible del coco del Carib banyat en refresc de cola."),
        (29, 'Amaretto Cola',            "Ametlla amarga que transforma el refresc en pura elegància a la italiana."),
        (30, 'Aperol Spritz (Mecatrònic)',"La versió robòtica de l'aperitiu milanès per excel·lència. Fresc i amargant."),
        (31, 'Aperol Tònica',            "Més sec que el seu germà 'Spritz', és la sofisticació feta aperitiu."),
        (32, 'Campari Soda',             "Roig passió, amargant i ple d'estil. Un clàssic intocable."),
        (33, 'Vermut Taronja',           "L'hora del vermut no falla mai. Tocs cítrics perfectes per obrir la gana."),
        (34, 'Tequila Llimona',          "La Margarita dels rebels. Cítric, potent i directe a l'ànima."),
        (35, 'Tequila Sprite',           "L'espurna de la llima-llimona suavitza el caràcter volcànic de l'agave."),
        (36, 'Tequila Cola',             "Coneguda com 'La Batanga'. Fosc, salvatge i ple d'actitud mexicana."),
        (37, 'Vodka Sunrise',            "Com un trenc d'alba a la copa. Afruitat, dolç i visualment espectacular."),
        (38, 'Tequila Sunrise',          "Tota la nostàlgia dels anys 70. Taronja, foc vermell i l'escalfor del tequila."),
        (39, 'Rom Sunrise',              "Una versió molt més dolça i tropical de la cèlebre sortida del sol."),
        (40, 'Gin Sunrise',              "Els botànics es desperten banyats en colors càlids i aromes de fruita."),
        (41, 'Cosmopolitan',             "L'estil de Nova York a la teva mà. Sofisticat, lleugerament àcid i molt vermell."),
        (42, 'Pink Lemonade',            "Fresc i molt perillós. Una llimonada que amaga l'esperit del vodka a dins."),
        (43, 'Brisa Tropical',           "Com el vent del mar al Carib. Afruitat, rogenc i extremadament fàcil de beure."),
        (44, 'Tornavís',                 "Recepta històrica d'enginyers i miners. Senzillesa cítrica amb un secret potent."),
        (45, 'Black Russian',            "L'elegància en la foscor. El poder del vodka endolcit i emmascarat amb notes profundes."),
        (46, 'Mexican Mule',             "Refrescant, esfervescent i ple de vida gràcies a la màgia mexicana."),
        (47, 'Italian Job',              "Un combinat d'alta costura, complet, botànic i amb l'amargor justa per triomfar."),
        (48, 'Sweet Sunrise',            "El capvespre més sa. Un degradat de sabors cítrics i dolços lliure d'alcohol."),
        (49, 'San Francisco',            "El rei indiscutible dels còctels afruitats. Una barreja clàssica i plena de color sense gota d'alcohol."),
        (50, 'Llimonada Rosa',           "Refrescant, dolça i amb un toc divertit i vistós. Ideal per compartir en família."),
        (51, 'Shirley Temple',           "El primer 'mocktail' de la història. Creat a Hollywood, és dolç, bonic i deliciós."),
        (52, 'Roy Rogers',               "El 'germà gran' del Shirley Temple. Combina l'alegria del colorant vermell amb el cos de la Cola."),
        (53, 'Arnold Palmer',            "Refrescant i perfectament equilibrat. El favorits dels golfistes americans per passar la set."),
        (54, 'Puntx Tropical',           "Una festa a la boca. Explosió de sabors de fruites variades amb l'alegria de les bombolles."),
        (55, 'Bitter Taronja',           "L'aperitiu definitiu sense alcohol. Notes cítriques, profunditat amargant i molt d'estil."),
        (56, 'Brindis Vermell',          "Sec, amb molta presència i sofisticació. Ideal per a la prèvia d'un gran sopar de celebració."),
        (57, 'Isotònic Festiu',          "Aigua, energia i sabor per a recuperar l'esperit de la festa, sent el més responsable de tots."),
    ]
    conn.executemany(
        "INSERT INTO Coctels (ID_Coctel, Nom_Coctel, Descripcio) VALUES (?, ?, ?)",
        coctels
    )

    # ==========================================
    # 4. INSERIR RECEPTES (129 Combinacions)
    # ==========================================
    receptes = [
        (1, 'Refresc Cola', 200, 1), (1, 'Whisky', 50, 2),
        (2, 'Refresc Llimona', 200, 1), (2, 'Whisky', 50, 2),
        (3, 'Refresc Llima-Llimona', 200, 1), (3, 'Whisky', 50, 2),
        (4, 'Refresc Llima-Llimona', 200, 1), (4, 'Whisky', 50, 2),
        (5, 'Suc Taronja', 200, 1), (5, 'Whisky', 50, 2),
        (6, 'Refresc Llimona', 200, 1), (6, 'Vodka', 50, 2),
        (7, 'Refresc Taronja', 200, 1), (7, 'Vodka', 50, 2),
        (8, 'Tònica', 200, 1), (8, 'Vodka', 50, 2),
        (9, 'Refresc Llima-Llimona', 200, 1), (9, 'Vodka', 50, 2),
        (10, 'Refresc Cola', 200, 1), (10, 'Vodka', 50, 2),
        (11, 'Suc Pinya', 200, 1), (11, 'Vodka', 50, 2),
        (12, 'Suc Préssec', 200, 1), (12, 'Vodka', 50, 2),
        (13, 'Refresc Cola', 200, 1), (13, 'Rom', 50, 2),
        (14, 'Refresc Llimona', 200, 1), (14, 'Rom', 50, 2),
        (15, 'Suc Taronja', 200, 1), (15, 'Rom', 50, 2),
        (16, 'Refresc Llima-Llimona', 200, 1), (16, 'Rom', 50, 2),
        (17, 'Suc Pinya', 200, 1), (17, 'Rom', 50, 2),
        (18, 'Refresc Llimona', 200, 1), (18, 'Ginebra', 50, 2),
        (19, 'Tònica', 200, 1), (19, 'Ginebra', 50, 2),
        (20, 'Refresc Llima-Llimona', 200, 1), (20, 'Ginebra', 50, 2),
        (21, 'Refresc Taronja', 200, 1), (21, 'Ginebra', 50, 2),
        (22, 'Refresc Cola', 200, 1), (22, 'Licor Herbes', 50, 2),
        (23, 'Refresc Llimona', 200, 1), (23, 'Licor Herbes', 50, 2),
        (24, 'Tònica', 200, 1), (24, 'Licor Herbes', 50, 2),
        (25, 'Suc Pinya', 200, 1), (25, 'Licor Dolç', 50, 2),
        (26, 'Refresc Cola', 200, 1), (26, 'Licor Dolç', 50, 2),
        (27, 'Suc Pinya', 200, 1), (27, 'Licor Coco', 50, 2),
        (28, 'Refresc Cola', 200, 1), (28, 'Licor Coco', 50, 2),
        (29, 'Refresc Cola', 200, 1), (29, 'Licor Ametlla', 50, 2),
        (30, 'Gasosa', 100, 1), (30, 'Refresc Taronja', 100, 2), (30, 'Aperitiu', 50, 3),
        (31, 'Tònica', 200, 1), (31, 'Aperitiu', 50, 2),
        (32, 'Gasosa', 200, 1), (32, 'Aperitiu', 50, 2),
        (33, 'Refresc Taronja', 150, 1), (33, 'Vermut', 100, 2),
        (34, 'Refresc Llimona', 200, 1), (34, 'Tequila', 50, 2),
        (35, 'Refresc Llima-Llimona', 200, 1), (35, 'Tequila', 50, 2),
        (36, 'Refresc Cola', 200, 1), (36, 'Tequila', 50, 2),
        (37, 'Suc Taronja', 150, 1), (37, 'Vodka', 50, 2), (37, 'Colorant Vermell', 30, 3),
        (38, 'Suc Taronja', 150, 1), (38, 'Tequila', 50, 2), (38, 'Colorant Vermell', 30, 3),
        (39, 'Suc Taronja', 150, 1), (39, 'Rom', 50, 2), (39, 'Colorant Vermell', 30, 3),
        (40, 'Suc Taronja', 150, 1), (40, 'Ginebra', 50, 2), (40, 'Colorant Vermell', 30, 3),
        (41, 'Colorant Vermell', 120, 1), (41, 'Refresc Llimona', 80, 2), (41, 'Vodka', 50, 3),
        (42, 'Refresc Llimona', 170, 1), (42, 'Vodka', 50, 2), (42, 'Colorant Vermell', 30, 3),
        (43, 'Suc Taronja', 100, 1), (43, 'Colorant Vermell', 100, 2), (43, 'Rom', 50, 3),
        (44, 'Suc Taronja', 200, 1), (44, 'Vodka', 50, 2),
        (45, 'Vodka', 30, 1), (45, 'Licor Ametlla', 20, 2),
        (46, 'Refresc Llima-Llimona', 150, 1), (46, 'Tequila', 40, 2), (46, 'Licor Taronja', 10, 3),
        (47, 'Tònica', 150, 1), (47, 'Aperitiu', 30, 2), (47, 'Ginebra', 20, 3),
        (48, 'Suc Taronja', 150, 1), (48, 'Refresc Llimona', 50, 2), (48, 'Colorant Vermell', 50, 3),
        (49, 'Suc Taronja', 100, 1), (49, 'Suc Pinya', 50, 2), (49, 'Suc Préssec', 50, 3), (49, 'Colorant Vermell', 30, 4),
        (50, 'Refresc Llimona', 200, 1), (50, 'Colorant Vermell', 40, 2),
        (51, 'Refresc Llima-Llimona', 150, 1), (51, 'Colorant Vermell', 20, 2),
        (52, 'Refresc Cola', 150, 1), (52, 'Colorant Vermell', 20, 2),
        (53, 'Té', 100, 1), (53, 'Refresc Llimona', 100, 2),
        (54, 'Suc Pinya', 100, 1), (54, 'Suc Préssec', 50, 2), (54, 'Refresc Llima-Llimona', 50, 3),
        (55, 'Bitter', 100, 1), (55, 'Suc Taronja', 100, 2),
        (56, 'Tònica', 150, 1), (56, 'Colorant Vermell', 50, 2),
        (57, 'Isotònic', 150, 1), (57, 'Suc Llima', 20, 2), (57, 'Colorant Vermell', 10, 3),
    ]
    conn.executemany(
        "INSERT INTO Receptes (ID_Coctel, Categoria, Quantitat_ml, Ordre) VALUES (?, ?, ?, ?)",
        receptes
    )

    # ==========================================
    # 5. INSERIR MUNTATGE INICIAL (6 carrils)
    # ==========================================
    muntatge = [
        (1, 18, 1000, 1500, 700),  # Brugal (Rom)
        (2, 7,  1000, 1500, 700),  # Absolut Vodka
        (3, 12, 1000, 1500, 700),  # Seagram's (Ginebra)
        (4, 43, 1000, 1500, 700),  # Suc de taronja
        (5, 49, 1000, 1500, 700),  # Granadina
        (6, 35, 1000, 1500, 700),  # Fanta de llimona
    ]
    conn.executemany(
        "INSERT INTO Muntatge (Posicio, ID_Ingredient, Capacitat_Actual_ml, Preu_Ampolla_Cents, Mida_Ampolla_ml) VALUES (?, ?, ?, ?, ?)",
        muntatge
    )

    conn.execute(
        "INSERT INTO Configuracio (Clau, Valor) VALUES (?, ?)",
        ('MARGE_BENEFICI', '3.0')
    )

    conn.commit()
    conn.close()
    print("✅ Base de dades creada correctament amb la taula Comandes inclosa!")

if __name__ == "__main__":
    crear_database()
