import streamlit as st
import os
import json
import google.generativeai as genai
from PIL import Image

# --- CONFIGURATION ---
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

st.set_page_config(page_title="Ma Cuisine Pro MP2I", layout="wide")
st.title("📚 Assistant Recettes Complet")
st.info(f"Modèle actif : **{target_model_name}**")

DB_PATH = "ma_base_recettes"
if not os.path.exists(DB_PATH): os.makedirs(DB_PATH)

# --- INTERFACE ---
tab1, tab2 = st.tabs(["📥 Importer", "🔍 Bibliothèque"])

with tab1:
    source = st.radio("Source :", ["Lien Web", "Image / Photo"])
    book_name = st.text_input("Nom du Livre", value="Marmiton")
    
    url_web = st.text_input("Lien de la recette") if source == "Lien Web" else None
    file_img = st.file_uploader("Image", type=['jpg', 'png']) if source == "Image / Photo" else None

    if st.button("Analyser et Sauvegarder"):
        with st.spinner("Extraction de la recette complète..."):
            # PROMPT AMÉLIORÉ POUR TOUT RÉCUPÉRER
            prompt = """Analyse cette recette et extrais TOUTES les informations. 
            Réponds UNIQUEMENT en JSON strict avec ces clés : 
            'nom', 'ingredients' (liste), 'etapes' (liste détaillée des instructions), 'temps' (entier), 'type' (Plat, Dessert, etc)."""
            
            try:
                if source == "Lien Web":
                    response = model.generate_content(f"Lien : {url_web}. {prompt}")
                else:
                    img = Image.open(file_img)
                    response = model.generate_content([prompt, img])
                
                clean_text = response.text.replace('```json', '').replace('```', '').strip()
                res = json.loads(clean_text)
                res["livre"] = book_name
                
                filename = "".join([c for c in res['nom'] if c.isalnum()]).lower() + ".json"
                with open(os.path.join(DB_PATH, filename), "w") as f:
                    json.dump(res, f)
                
                st.success(f"✅ '{res['nom']}' sauvegardé avec étapes !")
                st.rerun()
            except Exception as e:
                st.error(f"Erreur : {e}")

with tab2:
    st.header("Ma Bibliothèque")
    if os.path.exists(DB_PATH):
        for file in os.listdir(DB_PATH):
            if file.endswith('.json'):
                with open(os.path.join(DB_PATH, file), 'r') as f:
                    r = json.load(f)
                    with st.expander(f"📖 {r['nom']} - {r['temps']} min"):
                        st.write(f"**Livre :** {r.get('livre')}")
                        st.subheader("Ingrédients")
                        st.write(", ".join(r['ingredients']))
                        
                        st.subheader("Préparation")
                        # Affichage des étapes point par point
                        for i, etape in enumerate(r.get('etapes', []), 1):
                            st.write(f"{i}. {etape}")
