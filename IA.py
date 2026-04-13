import os
import json
import random
from openai import OpenAI
from dotenv import load_dotenv

# ==========================================
# 1. CONFIGURACIÓ DE L'ENTORN I CLIENTS
# ==========================================
load_dotenv()

# PLA A: Connexió Directa a Groq (prioritat: velocitat)
client_groq = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=os.getenv("GROQ_API_KEY"),
    timeout=15.0
)

# PLA B: Connexió via OpenRouter
client_or = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
    timeout=15.0
)

# El model que farem servir per a tota l'aplicació
MODEL_IA = "openai/gpt-oss-120b"


# ==========================================
# 2. MOTOR D'INFERÈNCIA REDUNDANT
# ==========================================
def crida_ia_redundant(sys_prompt: str, user_prompt: str) -> dict | None:
    """
    Motor central que gestiona la comunicació amb la IA.
    Si Groq falla, salta automàticament a OpenRouter.
    """
    missatges = [
        {"role": "system", "content": sys_prompt},
        {"role": "user", "content": user_prompt}
    ]
    
    # INTENT 1: Groq
    try:
        resposta = client_groq.chat.completions.create(
            model=MODEL_IA,
            messages=missatges,
            response_format={"type": "json_object"}
        )
        net = resposta.choices[0].message.content.replace('```json', '').replace('```', '').strip()
        return json.loads(net)
    
    except Exception as e_groq:
        print(f"[IA WARNING] Falla Groq: {e_groq}. Saltant a OpenRouter...")
        
        # INTENT 2: OpenRouter
        try:
            resposta_or = client_or.chat.completions.create(
                model=MODEL_IA,
                messages=missatges,
                response_format={"type": "json_object"}
            )
            net_or = resposta_or.choices[0].message.content.replace('```json', '').replace('```', '').strip()
            return json.loads(net_or)
            
        except Exception as e_or:
            print(f"[IA FATAL ERROR] Han fallat els dos proveïdors. Error final: {e_or}")
            return None

def crida_ia_redundant_historial(sys_prompt: str, historial: list) -> dict | None:
    """Variant del motor que accepta l'historial sencer de la conversa."""
    missatges_full = [{"role": "system", "content": sys_prompt}] + historial
    
    try:
        # Intent 1: Groq
        resposta = client_groq.chat.completions.create(
            model=MODEL_IA,
            messages=missatges_full,
            response_format={"type": "json_object"},
        )
        return json.loads(resposta.choices[0].message.content.strip())
    
    except Exception as e:
        print(f"[IA WARNING] Error historial Groq: {e}. Provant OpenRouter...")
        try:
            # Intent 2: OpenRouter
            resposta = client_or.chat.completions.create(
                model=MODEL_IA,
                messages=missatges_full,
                response_format={"type": "json_object"},
                temperature=0.8
            )
            return json.loads(resposta.choices[0].message.content.strip())
        except Exception as e_or:
            print(f"[IA FATAL] Error total xat: {e_or}")
            return None
        

# ==========================================
# 3. MÒDUL D'EMOCIONS
# ==========================================
def recomanar_per_emocio(emocio: str, coctels_disponibles: list) -> dict | None:
    """
    Filtra la llista de còctels disponibles i demana a la IA que en triï un
    basant-se en els sabors que millor acompanyin l'emoció del client.
    """
    if not coctels_disponibles:
        return None
    
    # Desordenem la llista perquè la IA no tingui biaixos de posició
    coctels_shuffled = random.sample(coctels_disponibles, len(coctels_disponibles))
    
    text_carta = "\n".join(
        f"ID: {c['ID_Coctel']} | Nom: {c['Nom_Coctel']} | Ingredients: {c.get('Ingredients', '')}" 
        for c in coctels_shuffled
    )
    
    sys_prompt = f"""Ets un barman expert i molt empàtic. Aquesta és la teva carta actual:
{text_carta}

CRITERIS DE SELECCIÓ:
1. Analitza com se sent el client.
2. Tria el còctel de la carta que tingui els ingredients o sabors que millor s'adaptin al seu estat d'ànim.
3. IGNORA COMPLETAMENT EL NOM del còctel, fixa't només en els ingredients.

Retorna NOMÉS un JSON pur amb aquest format exacte:
{{"id_coctel": 1, "frase_barman": "La teva frase curta en català justificant els sabors escollits per al client."}}"""

    user_prompt = f"El client s'acosta a la barra i et diu: {emocio}"

    dades = crida_ia_redundant(sys_prompt, user_prompt)
    
    if dades:
        ids_valids = {c['ID_Coctel'] for c in coctels_disponibles}
        id_retornat = dades.get('id_coctel')
        
        if id_retornat in ids_valids:
            return dades
            
    return None


# ==========================================
# 4. MÒDUL DE XAT CREATIU (Amb Memòria i Context)
# ==========================================
def xat_creatiu_amb_memoria(historial_missatges: list, carrils_actius: str) -> dict | None:
    """
    Gestiona una conversa de fins a 3 missatges. 
    Decideix si ha de xerrar o si ja té prou info per inventar la recepta.
    """
    if not carrils_actius:
        return None

    # PROMPT DE SISTEMA: Aquí definim la personalitat i el format de sortida
    sys_prompt = f"""Ets un barman creatiu en un xat en directe.
LÍQUIDS DISPONIBLES ALS CARRILS: {carrils_actius}.

LES TEVES REGLES:
1. Si el client encara no ha donat prou detalls, xerra amb ell i pregunta-li coses per definir el seu gust.
2. Si ja saps què li aniria bé, INVENTA un còctel original amb els líquids disponibles.
3. REGLES DE MIXOLOGIA (Molt Important): 
    - No facis barreges boges. Fes servir MÀXIM 4 ingredients en total. 
    - Fes servir MÀXIM 1 o 2 alcohols forts diferents (Vodka, Rom, Ginebra) per beguda. 
    - La quantitat TOTAL d'alcohol fort no hauria de superar els 70ml per motius de proporció i cost. La resta han de ser sucs o refrescos.
4. No tradueixis lliurement els noms dels ingredients, agafa els de la llista dels carrils com a referència.
5. El format de sortida ha de ser SEMPRE un JSON amb aquests camps:
   - "resposta_text": La teva resposta amable o explicació en català.
   - "tinc_recepta": true/false (només true si en aquest missatge ja proposes la beguda final).
   - "dades_coctel": {{"nom": "Nom", "recepta": {{"Líquid": ml}}}} (només si tinc_recepta és true).


IMPORTANT: Si proposes una recepta, la suma total de ml ha de ser EXACTAMENT 200."""

    # En lloc de passar un sol 'user_prompt', passem tot l'historial a la nostra funció redundant
    # Per fer-ho, modificarem lleugerament la crida_ia_redundant més avall.
    return crida_ia_redundant_historial(sys_prompt, historial_missatges)