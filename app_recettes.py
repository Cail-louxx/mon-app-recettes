import streamlit as st
import os
import json
import google.generativeai as genai
from PIL import Image

# --- CONFIGURATION STRICTE ---
# On utilise ta clé valide Zo-4
api_key = "AIzaSyBvvqOuMwFdgUH5T4GJlT0fS4i4Qnti8Gk"
genai.configure(api_key=api_key)

# Utilisation du nom simple. Si Flash échoue, on bascule sur Pro automatiquement.
try:
    model = genai.GenerativeModel('gemini-1.5-flash')
except:
    model = genai.GenerativeModel('gemini-pro')

st.set_page_config(page_title="Ma Cuisine Pro MP2I", layout="wide")
st.title("📚 Assistant Recettes")

DB_PATH = "ma_base_recettes"
if not os.path.exists(DB_PATH):
    os.makedirs(DB_PATH)

# --- INTERFACE ---
source = st.radio("Source :", ["Lien Web", "Image"])
url_web = st.text_input("Lien Marmiton") if source == "Lien Web" else None
file_img = st.file_uploader("Image", type=['jpg', 'jpeg', 'png']) if source == "Image" else None

if st.button("Analyser"):
    with st.spinner("Analyse en cours..."):
        prompt = "Analyse cette recette. Réponds UNIQUEMENT en JSON : {'nom': '', 'ingredients': [], 'temps': 0, 'type': ''}"
        try:
            if source == "Lien Web":
                # On force une requête simple
                response = model.generate_content(f"{prompt} URL: {url_web}")
            else:
                img = Image.open(file_img)
                response = model.generate_content([prompt, img])
            
            # Affichage direct du résultat pour vérifier
            st.json(response.text)
            
            # Sauvegarde rapide
            res = json.loads(response.text.replace('```json', '').replace('```', ''))
            with open(f"{DB_PATH}/recette_{res['nom']}.json", "w") as f:
                json.dump(res, f)
            st.success("Sauvegardé !")
            
        except Exception as e:
            st.error(f"L'API refuse encore le modèle. Détails : {e}")

# --- AFFICHAGE ---
st.divider()
if os.path.exists(DB_PATH):
    for f in os.listdir(DB_PATH):
        st.write(f"📖 {f}")
