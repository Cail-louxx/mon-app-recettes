import streamlit as st
import os
import json
import google.generativeai as genai
from PIL import Image
import re

# --- 1. CONFIGURATION ---
api_key = st.secrets["GEMINI_API_KEY"]
genai.configure(api_key=api_key)

@st.cache_resource
def get_model():
    return genai.GenerativeModel('gemini-1.5-flash')

model = get_model()

# --- 2. SETUP ---
DB_PATH = "ma_base_recettes"
if not os.path.exists(DB_PATH): os.makedirs(DB_PATH)

LISTE_ALLERGENES = ["Gluten", "Lactose", "Fruits à coque", "Oeufs", "Poisson", "Crustacés", "Soja", "Arachides", "Moutarde", "Sésame"]

def format_temps(minutes):
    try:
        m = int(minutes)
        return f"{m} min" if m < 60 else f"{m // 60}h{m % 60:02d}"
    except: return "Inconnu"

def clean_recipe_data(raw_data, fallback_livre):
    nom = raw_data.get("nom") or raw_data.get("titre") or "Recette sans nom"
    etapes = raw_data.get("etapes") or raw_data.get("preparation") or []
    if isinstance(etapes, str): etapes = [etapes]
    
    return {
        "nom": str(nom).strip(),
        "personnes": raw_data.get("personnes") or "?",
        "temps": raw_data.get("temps") or 0,
        "ingredients": raw_data.get("ingredients") or [],
        "etapes": etapes,
        "type": raw_data.get("type") or "Plat",
        "allergenes": raw_data.get("allergenes") or [],
        "livre": fallback_livre
    }

# --- 3. INTERFACE ---
st.set_page_config(page_title="Ma Cuisine Pro MP2I", layout="wide")
st.title("📚 Gestionnaire de Recettes Expert")

tab1, tab2 = st.tabs(["📥 Importer", "🔍 Bibliothèque & Gestion"])

with tab1:
    source = st.radio("Source :", ["Lien Web", "Image / Photo"])
    
    # Récupération dynamique des livres
    existing_books = []
    if os.path.exists(DB_PATH):
        for f in os.listdir(DB_PATH):
            if f.endswith('.json'):
                try:
                    with open(os.path.join(DB_PATH, f), 'r', encoding='utf-8') as file:
                        d = json.load(file)
                        if d.get("livre"): existing_books.append(d["livre"])
                except: continue
    existing_books = sorted(list(set(existing_books)))
    
    col_b1, col_b2 = st.columns(2)
    with col_b1:
        book_opt = st.selectbox("Livre :", ["+ Nouveau"] + existing_books)
    with col_b2:
        nom_livre = st.text_input("Nom du livre", value="Mes Recettes") if book_opt == "+ Nouveau" else book_opt

    uploaded_file = st.file_uploader("Image", type=['jpg', 'jpeg', 'png']) if source == "Image / Photo" else None
    url_input = st.text_input("Lien") if source == "Lien Web" else None

    if st.button("Analyser et Sauvegarder"):
        with st.spinner("Analyse visuelle..."):
            prompt = f"""Analyse cette recette. 
            NOM : En gras foncé. 
            PRÉPARATION : Bloc commençant par des verbes.
            RÉPONDS EN JSON : "nom", "temps" (total min), "personnes", "ingredients", "etapes", "type", "allergenes" (choisis dans {LISTE_ALLERGENES})."""
            
            try:
                res_ai = model.generate_content([prompt, Image.open(uploaded_file)]) if uploaded_file else model.generate_content(f"{url_input}\n{prompt}")
                match = re.search(r'\{.*\}', res_ai.text, re.DOTALL)
                if match:
                    data = clean_recipe_data(json.loads(re.sub(r',\s*([\]}])', r'\1', match.group())), nom_livre)
                    safe_name = "".join([c for c in data["nom"] if c.isalnum()]).lower()
                    with open(os.path.join(DB_PATH, f"{safe_name}.json"), "w", encoding='utf-8') as f:
                        json.dump(data, f, ensure_ascii=False, indent=4)
                    st.success(f"✅ Recette '{data['nom']}' ajoutée !")
                else: st.error("Erreur de format JSON.")
            except Exception as e: st.error(f"Erreur : {e}")

with tab2:
    st.header("Ma Bibliothèque")
    
    # Filtres
    f1, f2, f3 = st.columns(3)
    with f1: s_nom = st.text_input("🔍 Rechercher un nom")
    with f2: s_no_all = st.selectbox("🚫 Exclure l'allergène", ["Aucun"] + LISTE_ALLERGENES)
    with f3: s_type = st.multiselect("🍴 Type", ["Entrée", "Plat", "Dessert", "Gâteau", "Boisson"])

    st.divider()

    if os.path.exists(DB_PATH):
        files = [f for f in os.listdir(DB_PATH) if f.endswith('.json')]
        for f_name in files:
            file_path = os.path.join(DB_PATH, f_name)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    r = json.load(f)
                    
                    # Logique de filtrage
                    match_nom = s_nom.lower() in r.get('nom','').lower()
                    match_all = (s_no_all == "Aucun") or (s_no_all not in r.get('allergenes', []))
                    match_type = not s_type or r.get('type') in s_type

                    if match_nom and match_all and match_type:
                        col_exp, col_del = st.columns([0.85, 0.15])
                        
                        with col_exp:
                            tps = format_temps(r.get('temps', 0))
                            with st.expander(f"📖 {r.get('nom')} — ⏱️ {tps}"):
                                if r.get('allergenes'): st.warning(f"⚠️ Contient : {', '.join(r.get('allergenes'))}")
                                c1, c2 = st.columns(2)
                                with c1:
                                    st.markdown("**🍎 Ingrédients**")
                                    for ing in r.get('ingredients', []): st.write(f"- {ing}")
                                with c2:
                                    st.markdown("**👨‍🍳 Préparation**")
                                    for i, e in enumerate(r.get('etapes', []), 1): st.write(f"{i}. {e}")
                        
                        with col_del:
                            # BOUTON DE SUPPRESSION
                            if st.button("🗑️", key=f"del_{f_name}", help="Supprimer cette recette"):
                                os.remove(file_path)
                                st.rerun() # Rafraîchit la page après suppression
            except: continue
