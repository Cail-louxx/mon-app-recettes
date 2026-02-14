import streamlit as st
import os
import json
import google.generativeai as genai
from PIL import Image

# --- 1. CONFIGURATION ---
api_key = "AIzaSyBvvqOuMwFdgUH5T4GJlT0fS4i4Qnti8Gk"
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

# --- 2. SETUP DOSSIER ---
DB_PATH = "ma_base_recettes"
if not os.path.exists(DB_PATH):
    os.makedirs(DB_PATH)

# --- 3. FONCTIONS UTILES ---
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

# --- 4. INTERFACE ---
st.set_page_config(page_title="Ma Cuisine Pro", layout="wide")
st.title("👩🏻‍🍳 Assistant Recettes Intelligent")

tab1, tab2 = st.tabs(["📥 Importer une Recette", "🔍 Ma Bibliothèque"])

with tab1:
    source = st.radio("Source de la recette :", ["Lien Web", "Image / Photo"])
    
    # Gestion du choix du livre (remis comme demandé)
    existing_books = get_all_books()
    col_book1, col_book2 = st.columns(2)
    with col_book1:
        book_option = st.selectbox("Choisir un livre :", ["+ Nouveau Livre"] + existing_books)
    with col_book2:
        if book_option == "+ Nouveau Livre":
            nom_livre_final = st.text_input("Nom du nouveau livre", value="Mes Recettes")
        else:
            nom_livre_final = book_option

    url_web = st.text_input("Coller le lien de la recette") if source == "Lien Web" else None
    file_img = st.file_uploader("Choisir une image", type=['jpg', 'jpeg', 'png']) if source == "Image / Photo" else None

    if st.button("Analyser et Sauvegarder"):
        if (source == "Lien Web" and not url_web) or (source == "Image / Photo" and not file_img):
            st.warning("Veuillez fournir une source valide.")
        else:
            with st.spinner("L'IA analyse la recette complète..."):
                # PROMPT mis à jour avec 'personnes'
                prompt = """Analyse cette recette. Réponds UNIQUEMENT en JSON strict avec ces clés exactes : 
                'nom', 'ingredients' (liste), 'etapes' (liste détaillée), 'temps' (entier en minutes), 
                'personnes' (entier), 'type' (Entrée, Plat ou Dessert)."""
                
                try:
                    if source == "Lien Web":
                        response = model.generate_content(f"Lien : {url_web}. {prompt}")
                    else:
                        img = Image.open(file_img)
                        response = model.generate_content([prompt, img])
                    
                    clean_text = response.text.replace('```json', '').replace('```', '').strip()
                    res = json.loads(clean_text)
                    res["livre"] = nom_livre_final
                    
                    safe_name = "".join([c for c in res.get('nom', 'recette') if c.isalnum()]).lower()
                    with open(os.path.join(DB_PATH, f"{safe_name}.json"), "w") as f:
                        json.dump(res, f)
                    
                    st.success(f"✅ Recette '{res.get('nom')}' ajoutée au livre '{nom_livre_final}' !")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erreur d'analyse : {e}")

with tab2:
    st.header("Filtrer mes recettes")
    all_books = get_all_books()
    
    # Critères de sélection (remis comme demandé)
    c1, c2, c3, c4 = st.columns(4)
    with c1: s_nom = st.text_input("🔍 Nom")
    with c2: s_ing = st.text_input("🍎 Ingrédient")
    with c3: s_livre = st.multiselect("📖 Livres", all_books)
    with c4: s_type = st.multiselect("🍴 Type", ["Entrée", "Plat", "Dessert"])

    st.divider()

    if os.path.exists(DB_PATH):
        files = [f for f in os.listdir(DB_PATH) if f.endswith('.json')]
        for file in files:
            try:
                with open(os.path.join(DB_PATH, file), 'r') as f:
                    r = json.load(f)
                    
                    # Logique de filtrage
                    m_nom = s_nom.lower() in r.get('nom', '').lower()
                    m_ing = not s_ing or any(s_ing.lower() in i.lower() for i in r.get('ingredients', []))
                    m_livre = not s_livre or r.get('livre') in s_livre
                    m_type = not s_type or r.get('type') in s_type
                    
                    if m_nom and m_ing and m_livre and m_type:
                        nom = r.get('nom', 'Sans nom')
                        tps = r.get('temps', '?')
                        pers = r.get('personnes', '?')
                        
                        with st.expander(f"📖 {nom} — ⏱️ {tps} min — 👥 {pers} pers"):
                            st.write(f"**Livre :** {r.get('livre', 'Non classé')}")
                            st.write(f"**Type :** {r.get('type', 'Plat')}")
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                st.markdown("### 🍎 Ingrédients")
                                for ing in r.get('ingredients', []):
                                    st.write(f"- {ing}")
                            with col2:
                                st.markdown("### 👨‍🍳 Étapes")
                                for i, etape in enumerate(r.get('etapes', []), 1):
                                    st.write(f"{i}. {etape}")
            except: continue

