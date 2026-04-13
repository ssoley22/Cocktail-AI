
# PROJECTE: SMART COCKTAIL AI 🍹

## Requisits previs
- Python 3.10 o superior
- Git

## Configuració inicial

1. Clonar el repositori:
   `git clone https://github.com/ssoley22/Cocktail-AI.git`

2. Crear l'entorn virtual:
   `python -m venv env`

3. Activar l'entorn:
   - Windows:
     ```
     Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser 
     .\env\Scripts\activate
     ```
   - Linux/Mac:
     `source env/bin/activate`

4. Instal·lar les llibreries:
   `pip install -r requirements.txt`

## Configuració de l'Entorn (Clau API IA)

1. Crear un fitxer anomenat `.env` a l'arrel del projecte (al mateix nivell que `app.py`).
2. Afegir la següent línia substituint el text per la teva clau real:
   ```
   GROQ_API_KEY=la_teva_clau_de_groq
   OPENROUTER_API_KEY=la_teva_clau_de_openrouter
   ```
