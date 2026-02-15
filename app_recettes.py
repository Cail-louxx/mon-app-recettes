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
st.set_page_config(page_title="Ma Cuisine Pro MP2I", layout="wide")
st.title("📚 Mon Assistant Recettes Persistant")

tab1, tab2 = st.tabs(["📥 Importer une Recette", "🔍 Ma Bibliothèque"])

with tab1:
    source = st.radio("Source de la recette :", ["Lien Web", "Image / Photo"])
    
    existing_books = get_all_books()
    col_book1, col_book2 = st.columns(2)
    with col_book1:
        book_option = st.selectbox("Choisir un livre :", ["+ Nouveau Livre"] + existing_books)
    with col_book2:
        nom_livre_final = st.text_input("Nom du livre", value="Mes Recettes") if book_option == "+ Nouveau Livre" else book_option

    url_web = st.text_input("Lien de la recette") if source == "Lien Web" else None
    file_img = st.file_uploader("Choisir une image", type=['jpg', 'jpeg', 'png']) if source == "Image / Photo" else None

    if st.button("Analyser et Sauvegarder"):
        with st.spinner("L'IA analyse la recette complète..."):
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
                
                # Sauvegarde temporaire (pour la session actuelle)
                safe_name = "".join([c for c in res.get('nom', 'recette') if c.isalnum()]).lower()
                with open(os.path.join(DB_PATH, f"{safe_name}.json"), "w") as f:
                    json.dump(res, f)
                
                st.success(f"✅ Recette '{res.get('nom')}' analysée !")
                
                # --- NOUVEAU : BOUTON DE SAUVEGARDE POUR GITHUB ---
                st.warning("⚠️ Pour ne pas perdre cette recette au prochain réveil de l'app, téléchargez-la et déposez-la dans votre dossier GitHub.")
                json_string = json.dumps(res, indent=4)
                st.download_button(
                    label="💾 Télécharger pour GitHub",
                    data=json_string,
                    file_name=f"{safe_name}.json",
                    mime="application/json"
                )
                
            except Exception as e:
                st.error(f"Erreur : {e}")

with tab2:
    st.header("Filtrer mes recettes")
    all_books = get_all_books()
    
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
                    if s_nom.lower() in r.get('nom','').lower() and (not s_ing or any(s_ing.lower() in i.lower() for i in r.get('ingredients',[]))):
                        nom, tps, pers = r.get('nom','?'), r.get('temps','?'), r.get('personnes','?')
                        with st.expander(f"📖 {nom} — ⏱️ {tps} min — 👥 {pers} pers"):
                            st.write(f"**Livre :** {r.get('livre')}")
                            col1, col2 = st.columns(2)
                            with col1:
                                st.markdown("### 🍎 Ingrédients")
                                for ing in r.get('ingredients', []): st.write(f"- {ing}")
                            with col2:
                                st.markdown("### 👨‍🍳 Étapes")
                                for i, etape in enumerate(r.get('etapes', []), 1): st.write(f"{i}. {etape}")
            except: continue
