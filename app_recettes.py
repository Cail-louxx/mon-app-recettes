import streamlit as st
import os
import json
import google.generativeai as genai
from PIL import Image

# --- CONFIGURATION GEMINI (GRATUIT) ---
try:
    api_key = st.secrets["GEMINI_API_KEY"]
except:
    api_key = "AIzaSyAhZDb3xl0WROARUTB_4vHM2sisArZPcV0"

genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-1.5-flash')

st.set_page_config(page_title="Ma Cuisine Gratuite MP2I", layout="wide")
st.title("📚 Mon Assistant Recettes (Mode Gratuit)")

DB_PATH = "ma_base_recettes"
if not os.path.exists(DB_PATH): os.makedirs(DB_PATH)

def get_all_books():
    books = set()
    if os.path.exists(DB_PATH):
        files = [f for f in os.listdir(DB_PATH) if f.endswith('.json')]
        for file in files:
            with open(os.path.join(DB_PATH, file), 'r') as f:
                data = json.load(f)
                if data.get("livre"): books.add(data["livre"])
    return sorted(list(books))

tab1, tab2 = st.tabs(["📥 Importer", "🔍 Bibliothèque"])

with tab1:
    source = st.radio("Source :", ["Appareil Photo", "Galerie", "Lien Web"])
    existing_books = get_all_books()
    book_option = st.selectbox("Livre :", ["+ Nouveau Livre"] + existing_books)
    nom_livre_final = st.text_input("Nom du nouveau livre") if book_option == "+ Nouveau Livre" else book_option
    
    file_to_analyze = None
    if source == "Appareil Photo": file_to_analyze = st.camera_input("Photo")
    elif source == "Galerie": file_to_analyze = st.file_uploader("Image", type=['png', 'jpg', 'jpeg'])
    else: url_web = st.text_input("Lien de la recette")

    if st.button("Analyser gratuitement"):
        with st.spinner("Analyse Gemini en cours..."):
            prompt = "Analyse cette recette. Donne-moi UNIQUEMENT un objet JSON avec : nom, ingredients (liste), temps (entier en min), type (Entrée, Plat, Dessert ou Gâteau) et allergenes (liste)."
            
            if source == "Lien Web":
                response = model.generate_content(f"Analyse ce lien : {url_web}. {prompt}")
            else:
                img = Image.open(file_to_analyze)
                response = model.generate_content([prompt, img])
            
            # Nettoyage de la réponse pour extraire le JSON
            text_response = response.text.replace('```json', '').replace('```', '').strip()
            res = json.loads(text_response)
            res["livre"] = nom_livre_final
            
            with open(f"{DB_PATH}/{res['nom'].replace(' ', '_')}.json", "w") as f:
                json.dump(res, f)
            st.success("✅ Recette ajoutée !")
            st.rerun()

with tab2:
    all_books = get_all_books()
    col1, col2 = st.columns(2)
    with col1:
        s_nom = st.text_input("🔍 Nom")
        s_ing = st.text_input("🍎 Ingrédient")
    with col2:
        s_livre = st.multiselect("📖 Livre(s)", all_books)
        s_type = st.multiselect("🍴 Type", ["Entrée", "Plat", "Dessert", "Gâteau"])

    files = [f for f in os.listdir(DB_PATH) if f.endswith('.json')]
    for file in files:
        with open(os.path.join(DB_PATH, file), 'r') as f:
            r = json.load(f)
            if (s_nom.lower() in r['nom'].lower() and 
                (not s_ing or any(s_ing.lower() in i.lower() for i in r['ingredients'])) and
                (not s_livre or r.get('livre') in s_livre) and
                (not s_type or r.get('type') in s_type)):
                with st.expander(f"{r['nom']} - {r['temps']} min"):
                    st.write(f"**Ingrédients :** {', '.join(r['ingredients'])}")
                    st.write(f"**Allergènes :** {', '.join(r.get('allergenes', []))}")