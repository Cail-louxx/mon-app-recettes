import streamlit as st
import os
import json
import google.generativeai as genai
from PIL import Image

# --- 1. CONFIGURATION ---
api_key = st.secrets["GEMINI_API_KEY"]
genai.configure(api_key=api_key)

@st.cache_resource
def get_working_model_name():
    try:
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        for target in ['models/gemini-1.5-flash-latest', 'models/gemini-1.5-flash', 'models/gemini-pro']:
            if target in available_models: return target
        return available_models[0]
    except: return "gemini-1.5-flash"

target_model_name = get_working_model_name()
model = genai.GenerativeModel(target_model_name)

# --- 2. SETUP ---
DB_PATH = "ma_base_recettes"
if not os.path.exists(DB_PATH):
    os.makedirs(DB_PATH)

LISTE_ALLERGENES = ["Gluten", "Lactose", "Fruits à coque", "Oeufs", "Poisson", "Crustacés", "Soja", "Arachides", "Moutarde", "Sésame"]

def format_temps(minutes):
    """Convertit les minutes en format H:MM"""
    try:
        m = int(minutes)
        if m < 60: return f"{m} min"
        heures = m // 60
        mins = m % 60
        return f"{heures}h{mins:02d}"
    except: return "?"

def get_all_books():
    books = set()
    if os.path.exists(DB_PATH):
        files = [f for f in os.listdir(DB_PATH) if f.endswith('.json')]
        for file in files:
            try:
                with open(os.path.join(DB_PATH, file), 'r') as f:
                    data = json.load(f)
                    if data.get("livre"): books.add(data["livre"])
            except: continue
    return sorted(list(books))

# --- 3. INTERFACE ---
st.set_page_config(page_title="Ma Cuisine Pro MP2I", layout="wide")
st.title("📚 Assistant Recettes - Précision Culinaire")

tab1, tab2 = st.tabs(["📥 Importer", "🔍 Bibliothèque"])

with tab1:
    source = st.radio("Source :", ["Lien Web", "Image / Photo"])
    
    existing_books = get_all_books()
    col_b1, col_b2 = st.columns(2)
    with col_b1:
        book_option = st.selectbox("Livre :", ["+ Nouveau Livre"] + existing_books)
    with col_b2:
        nom_livre_final = st.text_input("Nom du livre", value="Mes Recettes") if book_option == "+ Nouveau Livre" else book_option

    url_web = st.text_input("Lien de la recette") if source == "Lien Web" else None
    file_img = st.file_uploader("Image", type=['jpg', 'jpeg', 'png']) if source == "Image / Photo" else None

    if st.button("Analyser et Sauvegarder"):
        with st.spinner("Analyse approfondie en cours..."):
            # PROMPT AVEC CALCUL DU TEMPS ET RESPECT DES QUANTITÉS
            prompt = f"""Tu es un expert culinaire. Analyse cette recette.
            
            CONSIGNES CRUCIALES :
            1. 'temps' : Calcule la somme (Préparation + Cuisson + Repos/Attente). Donne uniquement le total en minutes.
            2. 'ingredients' : Recopie EXACTEMENT les quantités et unités comme trouvées (ex: '3 oeufs', '1 pincée', '150g'). Ne change rien.
            3. 'personnes' : Nombre de personnes.
            4. 'allergenes' : Liste choisie PARMI : {", ".join(LISTE_ALLERGENES)}.
            
            Réponds UNIQUEMENT en JSON strict :
            {{
                "nom": "nom",
                "ingredients": ["quantité + nom"],
                "etapes": ["liste"],
                "temps": 0,
                "personnes": 0,
                "type": "Entrée, Plat, Dessert, Gâteau ou Boisson",
                "allergenes": ["liste"]
            }}"""
            
            try:
                if source == "Lien Web":
                    response = model.generate_content(f"Source: {url_web}\n\n{prompt}")
                else:
                    img = Image.open(file_img)
                    response = model.generate_content([prompt, img])
                
                clean_text = response.text.replace('```json', '').replace('```', '').strip()
                res = json.loads(clean_text)
                res["livre"] = nom_livre_final
                
                safe_name = "".join([c for c in res.get('nom', 'recette') if c.isalnum()]).lower()
                with open(os.path.join(DB_PATH, f"{safe_name}.json"), "w") as f:
                    json.dump(res, f)
                
                st.success(f"✅ '{res.get('nom')}' prêt !")
                st.download_button("💾 Télécharger pour GitHub", data=json.dumps(res, indent=4), file_name=f"{safe_name}.json", mime="application/json")
                
            except Exception as e:
                st.error(f"Erreur d'analyse : {e}")

with tab2:
    st.header("Ma Bibliothèque")
    all_books = get_all_books()
    
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1: s_nom = st.text_input("🔍 Nom")
    with c2: s_ing = st.text_input("🍎 Ingrédient")
    with c3: s_type = st.multiselect("🍴 Type", ["Entrée", "Plat", "Dessert", "Gâteau", "Boisson"])
    with c4: s_no_all = st.selectbox("🚫 Exclure l'allergène", ["Aucun"] + LISTE_ALLERGENES)
    with c5: s_livre = st.multiselect("📖 Livres", all_books)

    st.divider()

    if os.path.exists(DB_PATH):
        files = [f for f in os.listdir(DB_PATH) if f.endswith('.json')]
        for file in files:
            try:
                with open(os.path.join(DB_PATH, file), 'r') as f:
                    r = json.load(f)
                    
                    # Filtrage
                    m_nom = s_nom.lower() in r.get('nom', '').lower()
                    m_ing = not s_ing or any(s_ing.lower() in i.lower() for i in r.get('ingredients', []))
                    m_type = not s_type or r.get('type') in s_type
                    m_livre = not s_livre or r.get('livre') in s_livre
                    m_all = (s_no_all == "Aucun") or (s_no_all not in r.get('allergenes', []))
                    
                    if m_nom and m_ing and m_type and m_all and m_livre:
                        # Affichage du temps converti en H:MM
                        tps_brut = r.get('temps', 0)
                        tps_formate = format_temps(tps_brut)
                        
                        with st.expander(f"📖 {r.get('nom')} — 👥 {r.get('personnes')} pers — ⏱️ {tps_formate}"):
                            if r.get('allergenes'):
                                st.warning(f"⚠️ Contient : {', '.join(r.get('allergenes'))}")
                                
                            col1, col2 = st.columns(2)
                            with col1:
                                st.subheader("🍎 Ingrédients")
                                for ing in r.get('ingredients', []): st.write(f"- {ing}")
                            with col2:
                                st.subheader("👨‍🍳 Préparation")
                                for i, etape in enumerate(r.get('etapes', []), 1): st.write(f"{i}. {etape}")
            except: continue
