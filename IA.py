import os
import json
import random
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

MODEL_RAPID   = "gemini-3.1-flash-lite-preview"  # Emocions: tria lògica tancada
MODEL_CREATIU = "gemini-3-flash-preview"          # Xat: raonament obert (més endavant)


def recomanar_per_emocio(emocio: str, coctels_disponibles: list) -> dict | None:
    """
    Donada una emoció i la llista de còctels amb estoc,
    retorna {'id_coctel': int, 'frase_barman': str} o None si falla.
    """
    
    if not coctels_disponibles:
        return None
    
    coctels_disponibles = random.sample(coctels_disponibles, len(coctels_disponibles)) # Desordena la llista de coctels per evitar patrons de comportament/tria amb la IA

    llistat = "\n".join(
        f"{c['ID_Coctel']}: {c['Nom_Coctel']} (ingredients: {c.get('Ingredients', '')})"
        for c in coctels_disponibles
    )
    
    prompt = f"""Ets un barman expert i empàtic. Un client s'acosta a la barra i et diu que avui se sent: "{emocio}".
Aquesta és la teva carta de còctels disponibles ara mateix (amb els seus ingredients):
{llistat}

CRITERI DE SELECCIÓ MESTRE:
1. Ignora completament el nom del còctel (ex: no triïs un "Sunrise" només perquè el nom sona alegre).
2. Analitza exclusivament els INGREDIENTS de cada opció.
3. Tria pensant en com el seu perfil de gust (refrescant, dolç, àcid, intens, suau, amb/sense alcohol) ajudarà a l'estat d'ànim del client.

Respon ÚNICAMENT amb un JSON pur amb aquest format exacte. NO incloguis etiquetes markdown (com ```json) ni cap text de salutació:
{{"id_coctel": <ID enter>, "frase_barman": "<frase curta i simpàtica en català, màxim 15 paraules, on justifiquis la tria pel sabor o efecte dels ingredients>"}}"""


    try:
        resposta = client.models.generate_content(
            model=MODEL_RAPID,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )
        dades = json.loads(resposta.text)

        # Validem que l'ID retornat és un dels que existeixen realment
        ids_valids = {c['ID_Coctel'] for c in coctels_disponibles}
        if dades.get('id_coctel') not in ids_valids:
            print(f"[IA] ID invàlid rebut: {dades.get('id_coctel')}")
            return None

        return dades

    except Exception as e:
        print(f"[IA ERROR - emocions] {e}")
        return None