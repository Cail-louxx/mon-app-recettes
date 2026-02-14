import streamlit as st
import os
import json
import google.generativeai as genai
from PIL import Image

# --- CONFIGURATION STRICTE (CLE EN DUR POUR TEST) ---
# Utilisation de ta clé Zo-4 active
api_key = "AIzaSyBvvqOuMwFdgUH5T4GJlT0fS4i4Qnti8Gk"
genai.configure(api_key=api_key)

# --- DETECTION AUTOMATIQUE DU MODELE ---
# Cette fonction interroge Google pour voir quels modèles tu as le droit d'utiliser
@st.cache_resource
def get_working_model_name():
    try:
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        # Priorité aux modèles Flash (plus rapides et gratuits)
        for target in ['models/gemini-1.5-flash-latest', 'models/gemini-1.5-flash', 'models/gemini-pro']:
            if target in available_models:
                return target
        # Si aucun n'est trouvé, on prend le premier disponible
        return available_models[0]
    except Exception as e:
        return "gemini-1.5-flash" # Repli par défaut

# Initialisation du modèle détecté
target_model_name = get_working_model_name()
model = genai.GenerativeModel(target_model_name)

# --- MISE EN PAGE ---
st.set_page_config(page_title="Ma Cuisine Pro MP2I", layout="wide")
st.title("📚 Assistant Recettes")
st.info(f"Modèle détecté et utilisé : **{target_model_name}**")

# Dossier de stockage
DB_PATH = "ma_base_recettes"
if not os.path.exists(DB_PATH):
    os.makedirs(DB_PATH)

# --- FONCTIONS ---
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

# --- INTERFACE ---
tab1, tab2 = st.tabs(["📥 Importer", "🔍 Bibliothèque"])

with tab1:
    source = st.radio("Source :", ["Lien Web", "Image / Photo"])
    
    col_a, col_b = st.columns(2)
    with col_a:
        existing_books = get_all_books()
        book_option = st.selectbox("Livre :", ["+ Nouveau Livre"] + existing_books)
    with col_b:
        nom_livre_final = st.text_input("Nom du nouveau livre") if book_option == "+ Nouveau Livre" else book_option

    url_web = st.text_input("Coller le lien Marmiton") if source == "Lien Web" else None
    file_img = st.file_uploader("Choisir une image", type=['jpg', 'jpeg', 'png']) if source == "Image / Photo" else None

    if st.button("Analyser et Sauvegarder"):
        with st.spinner("L'IA analyse la recette..."):
            prompt = """Réponds UNIQUEMENT en JSON strict avec ces clés : 
            'nom', 'ingredients' (liste), 'temps' (entier), 'type' (Entrée, Plat, Dessert)."""
            
            try:
                if source == "Lien Web":
                    response = model.generate_content(f"Analyse ce lien : {url_web}. {prompt}")
                else:
                    img = Image.open(file_img)
                    response = model.generate_content([prompt, img])
                
                # Nettoyage JSON
                clean_text = response.text.replace('```json', '').replace('```', '').strip()
                res = json.loads(clean_text)
                res["livre"] = nom_livre_final
                
                # Sauvegarde
                filename = "".join([c for c in res['nom'] if c.isalnum()]).lower() + ".json"
                with open(os.path.join(DB_PATH, filename), "w") as f:
                    json.dump(res, f)
                
                st.success(f"✅ Recette '{res['nom']}' ajoutée !")
                st.rerun()
            except Exception as e:
                st.error(f"Erreur d'analyse : {e}")

with tab2:
    st.header("Mes Recettes Sauvegardées")
    if os.path.exists(DB_PATH):
        files = [f for f in os.listdir(DB_PATH) if f.endswith('.json')]
        for file in files:
            with open(os.path.join(DB_PATH, file), 'r') as f:
                r = json.load(f)
                with st.expander(f"📖 {r['nom']} - {r['temps']} min"):
                    st.write(f"**Livre :** {r.get('livre')}")
                    st.write(f"**Ingrédients :** {', '.join(r['ingredients'])}")
