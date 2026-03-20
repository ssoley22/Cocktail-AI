
# PROJECTE: SMART COCKTAIL AI 🍹

## Requisits previs
- Python 3.10 o superior
- Git

## Configuració inicial

1. Clonar el repositori:
   git clone https://github.com/ssoley22/Cocktail-AI.git

2. Crear l'entorn virtual:
   python -m venv env

3. Activar l'entorn:
   - Windows:
     Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
     .\env\Scripts\activate
   - Linux/Mac:
     source env/bin/activate

4. Instal·lar les llibreries:
   pip install -r requirements.txt

## Estructura del projecte
```
COCKTAIL-AI/
├── backend/
│   ├── app.py          ← Servidor Flask i endpoints
│   ├── database.py     ← Funcions de consulta a la base de dades
│   └── cocktail.db     ← Base de dades SQLite
├── frontend/
│   └── index.html      ← Interfície web
├── .gitignore
├── README.md
└── requirements.txt
```