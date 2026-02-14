import streamlit as st
import os
import json
import google.generativeai as genai
from PIL import Image

# --- 1. CONFIGURATION ---
# Utilisation de ta clé Zo-4 active
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

# --- 3. MISE EN PAGE ---
st.set_page_config(page_title="Ma Cuisine Pro MP2I", layout="wide")
st.title("📚 Assistant Recettes Complet")
st.info(f"Modèle actif : **{target_model_name}**")

# --- 4. INTERFACE ---
tab1, tab2 = st.tabs(["📥 Importer une Recette", "🔍 Ma Bibliothèque"])

with tab1:
    source = st.radio("Source :", ["Lien Web", "Image / Photo"])
    book_name = st.text_input("Nom du Livre (ex: Marmiton, Mamie...)", value="Mes Recettes")
    
    url_web = st.text_input("Coller le lien de la recette") if source == "Lien Web" else None
    file_img = st.file_uploader("Choisir une image", type=['jpg', 'jpeg', 'png']) if source == "Image / Photo" else None

    if st.button("Analyser et Sauvegarder"):
        if (source == "Lien Web" and not url_web) or (source == "Image / Photo" and not file_img):
            st.warning("Veuillez fournir une source valide.")
        else:
            with st.spinner("L'IA extrait la recette complète..."):
                prompt = """Analyse cette recette. Réponds UNIQUEMENT en JSON strict avec ces clés exactes : 
                'nom', 'ingredients' (liste), 'etapes' (liste détaillée), 'temps' (entier en minutes), 'type' (Entrée, Plat ou Dessert)."""
                
                try:
                    if source == "Lien Web":
                        response = model.generate_content(f"Lien : {url_web}. {prompt}")
                    else:
                        img = Image.open(file_img)
                        response = model.generate_content([prompt, img])
                    
                    # Nettoyage du JSON
                    clean_text = response.text.strip()
                    if "```json" in clean_text:
                        clean_text = clean_text.split("```json")[1].split("```")[0]
                    elif "```" in clean_text:
                        clean_text = clean_text.split("```")[1].split("```")[0]
                    
                    res = json.loads(clean_text)
                    res["livre"] = book_name
                    
                    # Sauvegarde locale sur le serveur Streamlit
                    safe_name = "".join([c for c in res.get('nom', 'recette') if c.isalnum()]).lower()
                    with open(os.path.join(DB_PATH, f"{safe_name}.json"), "w") as f:
                        json.dump(res, f)
                    
                    st.success(f"✅ Recette '{res.get('nom')}' ajoutée avec succès !")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erreur d'analyse : {e}")

with tab2:
    st.header("Mes Recettes Sauvegardées")
    if os.path.exists(DB_PATH):
        files = [f for f in os.listdir(DB_PATH) if f.endswith('.json')]
        if not files:
            st.write("Votre bibliothèque est vide.")
        
        for file in files:
            try:
                with open(os.path.join(DB_PATH, file), 'r') as f:
                    r = json.load(f)
                    
                    # Sécurisation contre les données manquantes (évite le KeyError)
                    nom = r.get('nom', 'Recette sans nom')
                    temps = r.get('temps', 'Inconnu')
                    livre = r.get('livre', 'Non classé')
                    ingredients = r.get('ingredients', [])
                    etapes = r.get('etapes', [])

                    with st.expander(f"📖 {nom} — ⏱️ {temps} min"):
                        st.write(f"**Source / Livre :** {livre}")
                        st.markdown("### 🍎 Ingrédients")
                        st.write(", ".join(ingredients) if ingredients else "Non précisés")
                        
                        st.markdown("### 👨‍🍳 Étapes de préparation")
                        if etapes:
                            for i, etape in enumerate(etapes, 1):
                                st.write(f"**{i}.** {etape}")
                        else:
                            st.write("Aucune étape détaillée.")
            except:
                continue
