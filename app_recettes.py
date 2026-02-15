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
def get_working_model_name():
    try:
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        for target in ['models/gemini-1.5-flash-latest', 'models/gemini-pro']:
            if target in available_models: return target
        return available_models[0]
    except: return "gemini-1.5-flash"

model = genai.GenerativeModel(get_working_model_name())

# --- 2. SETUP ---
DB_PATH = "ma_base_recettes"
if not os.path.exists(DB_PATH): os.makedirs(DB_PATH)

LISTE_ALLERGENES = ["Gluten", "Lactose", "Fruits à coque", "Oeufs", "Poisson", "Crustacés", "Soja", "Arachides", "Moutarde", "Sésame"]

def format_temps(minutes):
    try:
        m = int(minutes)
        if m < 60: return f"{m} min"
        return f"{m // 60}h{m % 60:02d}"
    except: return "Inconnu"

def get_all_books():
    books = set()
    if os.path.exists(DB_PATH):
        files = [f for f in os.listdir(DB_PATH) if f.endswith('.json')]
        for file in files:
            try:
                with open(os.path.join(DB_PATH, file), 'r', encoding='utf-8') as f:
                    d = json.load(f)
                    if d.get("livre"): books.add(d["livre"])
            except: continue
    return sorted(list(books))

# --- 3. INTERFACE ---
st.set_page_config(page_title="Ma Cuisine Pro MP2I", layout="wide")
st.title("📚 Assistant Recettes - Correction Structure")

tab1, tab2 = st.tabs(["📥 Importer", "🔍 Bibliothèque"])

with tab1:
    source = st.radio("Source :", ["Lien Web", "Image / Photo"])
    existing_books = get_all_books()
    c_b1, c_b2 = st.columns(2)
    with c_b1: book_opt = st.selectbox("Livre :", ["+ Nouveau Livre"] + existing_books)
    with c_b2: nom_livre = st.text_input("Nom du livre", value="Mes Recettes") if book_opt == "+ Nouveau Livre" else book_opt

    url = st.text_input("Lien") if source == "Lien Web" else None
    img_file = st.file_uploader("Image", type=['jpg', 'jpeg', 'png']) if source == "Image / Photo" else None

    if st.button("Analyser et Sauvegarder"):
        with st.spinner("Analyse en cours..."):
            prompt = f"""Extraire les données de cette recette. 
            SOIS TRÈS PRÉCIS SUR LES NOMS DES CLÉS JSON.
            - nom : titre de la recette
            - temps : somme préparation + cuisson + repos en minutes
            - personnes : nombre de personnes (ex: 20)
            - ingredients : liste des ingrédients avec quantités
            - etapes : liste des instructions de préparation
            - type : Entrée, Plat, Dessert, Gâteau ou Boisson
            - allergenes : liste parmi {", ".join(LISTE_ALLERGENES)}
            
            RÉPONDS UNIQUEMENT EN JSON AVEC CES 7 CLÉS."""
            
            try:
                res_ai = model.generate_content([prompt, Image.open(img_file)]) if source == "Image / Photo" else model.generate_content(f"{url}\n{prompt}")
                match = re.search(r'\{.*\}', res_ai.text, re.DOTALL)
                if not match: raise ValueError("JSON non trouvé")
                
                data = json.loads(re.sub(r',\s*([\]}])', r'\1', match.group()))
                data["livre"] = nom_livre
                
                # SÉCURITÉ : On s'assure que les clés existent pour l'affichage
                final_data = {
                    "nom": data.get("nom") or data.get("titre") or "Sans nom",
                    "personnes": data.get("personnes") or data.get("nb_personnes") or "?",
                    "temps": data.get("temps") or 0,
                    "ingredients": data.get("ingredients") or [],
                    "etapes": data.get("etapes") or data.get("preparation") or data.get("instructions") or [],
                    "type": data.get("type") or "Plat",
                    "allergenes": data.get("allergenes") or [],
                    "livre": nom_livre
                }

                safe_name = "".join([c for c in str(final_data["nom"]) if c.isalnum()]).lower()
                with open(os.path.join(DB_PATH, f"{safe_name}.json"), "w", encoding='utf-8') as f:
                    json.dump(final_data, f, ensure_ascii=False)
                
                st.success(f"✅ '{final_data['nom']}' analysé !")
                st.download_button("💾 Télécharger pour GitHub", data=json.dumps(final_data, indent=4, ensure_ascii=False), file_name=f"{safe_name}.json")
            except Exception as e: st.error(f"Erreur : {e}")

with tab2:
    st.header("Ma Bibliothèque")
    all_books = get_all_books()
    f1, f2, f3, f4, f5 = st.columns(5)
    with f1: s_nom = st.text_input("🔍 Nom")
    with f2: s_ing = st.text_input("🍎 Ingrédient")
    with f3: s_type = st.multiselect("🍴 Type", ["Entrée", "Plat", "Dessert", "Gâteau", "Boisson"])
    with f4: s_no_all = st.selectbox("🚫 Sans l'allergène", ["Aucun"] + LISTE_ALLERGENES)
    with f5: s_livre = st.multiselect("📖 Livres", all_books)

    if os.path.exists(DB_PATH):
        for file in [f for f in os.listdir(DB_PATH) if f.endswith('.json')]:
            try:
                with open(os.path.join(DB_PATH, file), 'r', encoding='utf-8') as f:
                    r = json.load(f)
                    if s_nom.lower() in r.get('nom','').lower():
                        m_ing = not s_ing or any(s_ing.lower() in i.lower() for i in r.get('ingredients',[]))
                        m_type = not s_type or r.get('type') in s_type
                        m_all = (s_no_all == "Aucun") or (s_no_all not in r.get('allergenes', []))
                        if m_ing and m_type and m_all:
                            t = format_temps(r.get('temps', 0))
                            # AFFICHAGE RENFORCÉ
                            with st.expander(f"📖 {r.get('nom')} — 👥 {r.get('personnes')} pers — ⏱️ {t}"):
                                if r.get('allergenes'): st.warning(f"⚠️ Contient : {', '.join(r.get('allergenes'))}")
                                c1, c2 = st.columns(2)
                                with c1:
                                    st.subheader("🍎 Ingrédients")
                                    for ing in r.get('ingredients', []): st.write(f"- {ing}")
                                with c2:
                                    st.subheader("👨‍🍳 Préparation")
                                    # On vérifie si c'est une liste ou du texte brut
                                    etp = r.get('etapes', [])
                                    if isinstance(etp, list):
                                        for i, e in enumerate(etp, 1): st.write(f"{i}. {e}")
                                    else: st.write(etp)
            except: continue
