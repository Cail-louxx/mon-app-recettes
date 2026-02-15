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
                    data = json.load(f)
                    if data.get("livre"): books.add(data["livre"])
            except: continue
    return sorted(list(books))

# --- 3. INTERFACE ---
st.set_page_config(page_title="Ma Cuisine Pro MP2I", layout="wide")
st.title("📚 Assistant Recettes - Précision Totale")

tab1, tab2 = st.tabs(["📥 Importer une Recette", "🔍 Ma Bibliothèque"])

with tab1:
    source = st.radio("Source de la recette :", ["Lien Web", "Image / Photo"])
    
    existing_books = get_all_books()
    col_b1, col_b2 = st.columns(2)
    with col_b1:
        book_option = st.selectbox("Choisir un livre :", ["+ Nouveau Livre"] + existing_books)
    with col_b2:
        nom_livre_final = st.text_input("Nom du livre", value="Mes Recettes") if book_option == "+ Nouveau Livre" else book_option

    url_web = st.text_input("Lien de la recette") if source == "Lien Web" else None
    file_img = st.file_uploader("Image / Photo", type=['jpg', 'jpeg', 'png']) if source == "Image / Photo" else None

    if st.button("Analyser et Sauvegarder"):
        with st.spinner("Extraction des données en cours..."):
            prompt = f"""Tu es un scanner culinaire ultra-précis. 
            NE RIEN INVENTER. Recopie exactement les informations visibles.

            CONSIGNES :
            1. 'nom' : Le nom exact de la recette.
            2. 'temps' : Somme totale (Préparation + Cuisson + Repos) en minutes.
            3. 'personnes' : Nombre de personnes.
            4. 'ingredients' : Liste des quantités + noms (ex: '140g de sucre').
            5. 'etapes' : Liste complète et détaillée de la préparation.
            6. 'type' : Choisir entre Entrée, Plat, Dessert, Gâteau ou Boisson.
            7. 'allergenes' : Liste parmi {", ".join(LISTE_ALLERGENES)}.
            
            Réponds EXCLUSIVEMENT en JSON strict avec ces clés exactes : 
            'nom', 'ingredients', 'etapes', 'temps', 'personnes', 'type', 'allergenes'."""
            
            try:
                if source == "Lien Web":
                    response = model.generate_content(f"Source: {url_web}\n\n{prompt}")
                else:
                    img = Image.open(file_img)
                    response = model.generate_content([prompt, img])
                
                # Nettoyage JSON
                match = re.search(r'\{.*\}', response.text, re.DOTALL)
                if match:
                    json_str = re.sub(r',\s*([\]}])', r'\1', match.group())
                    res = json.loads(json_str)
                else: raise ValueError("Format JSON non détecté.")

                res["livre"] = nom_livre_final
                
                safe_name = "".join([c for c in res.get('nom', 'recette') if c.isalnum()]).lower()
                with open(os.path.join(DB_PATH, f"{safe_name}.json"), "w", encoding='utf-8') as f:
                    json.dump(res, f, ensure_ascii=False)
                
                st.success(f"✅ '{res.get('nom')}' enregistré avec succès !")
                st.download_button("💾 Télécharger pour GitHub", data=json.dumps(res, indent=4, ensure_ascii=False), file_name=f"{safe_name}.json", mime="application/json")
                
            except Exception as e:
                st.error(f"Erreur : {e}")

with tab2:
    st.header("Mes Recettes Sauvegardées")
    all_books = get_all_books()
    
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1: s_nom = st.text_input("🔍 Nom")
    with c2: s_ing = st.text_input("🍎 Ingrédient")
    with c3: s_type = st.multiselect("🍴 Type", ["Entrée", "Plat", "Dessert", "Gâteau", "Boisson"])
    with c4: s_no_all = st.selectbox("🚫 Exclure l'allergène", ["Aucun"] + LISTE_ALLERGENES)
    with c5: s_livre = st.multiselect("📖 Livres", all_books)

    if os.path.exists(DB_PATH):
        files = [f for f in os.listdir(DB_PATH) if f.endswith('.json')]
        for file in files:
            try:
                with open(os.path.join(DB_PATH, file), 'r', encoding='utf-8') as f:
                    r = json.load(f)
                    
                    # Filtres
                    if s_nom.lower() in r.get('nom', '').lower():
                        m_ing = not s_ing or any(s_ing.lower() in i.lower() for i in r.get('ingredients', []))
                        m_type = not s_type or r.get('type') in s_type
                        m_livre = not s_livre or r.get('livre') in s_livre
                        m_all = (s_no_all == "Aucun") or (s_no_all not in r.get('allergenes', []))
                        
                        if m_ing and m_type and m_livre and m_all:
                            tps = format_temps(r.get('temps', 0))
                            with st.expander(f"📖 {r.get('nom', 'Sans nom')} — 👥 {r.get('personnes', '?')} pers — ⏱️ {tps}"):
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

