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

# --- 3. FONCTION DE CORRECTION DE STRUCTURE (CRUCIAL) ---
def clean_recipe_data(raw_data, fallback_livre):
    """Force la structure pour éviter les 'None' à l'affichage"""
    # Chercher le nom dans différentes clés possibles
    nom = raw_data.get("nom") or raw_data.get("titre") or raw_data.get("name") or "Recette sans nom"
    
    # Chercher la préparation (liste ou texte)
    etapes = raw_data.get("etapes") or raw_data.get("preparation") or raw_data.get("instructions") or []
    if isinstance(etapes, str): etapes = [etapes] # Convertir en liste si c'est du texte brut
    
    return {
        "nom": str(nom).strip(),
        "personnes": raw_data.get("personnes") or raw_data.get("nb_personnes") or "?",
        "temps": raw_data.get("temps") or 0,
        "ingredients": raw_data.get("ingredients") or [],
        "etapes": etapes,
        "type": raw_data.get("type") or "Plat",
        "allergenes": raw_data.get("allergenes") or [],
        "livre": fallback_livre
    }

# --- 4. INTERFACE ---
st.set_page_config(page_title="Ma Cuisine Pro MP2I", layout="wide")
st.title("📚 Assistant Recettes - Version Blindée")

tab1, tab2 = st.tabs(["📥 Importer", "🔍 Bibliothèque"])

with tab1:
    source = st.radio("Source :", ["Lien Web", "Image / Photo"])
    col_b1, col_b2 = st.columns(2)
    with col_b1:
        existing_books = sorted(list(set(json.load(open(os.path.join(DB_PATH, f), 'r', encoding='utf-8')).get('livre') 
                         for f in os.listdir(DB_PATH) if f.endswith('.json')))) if os.path.exists(DB_PATH) else []
        book_opt = st.selectbox("Livre :", ["+ Nouveau"] + existing_books)
    with col_b2:
        nom_livre = st.text_input("Nom du livre", value="Mes Recettes") if book_opt == "+ Nouveau" else book_opt

    file = st.file_uploader("Image", type=['jpg', 'jpeg', 'png']) if source == "Image / Photo" else None
    url = st.text_input("Lien") if source == "Lien Web" else None

    if st.button("Analyser et Sauvegarder"):
        with st.spinner("Analyse visuelle stricte..."):
            # PROMPT AMÉLIORÉ AVEC TES INSTRUCTIONS PRÉCISES
            prompt = f"""Analyse cette image de recette. 
            CONSIGNES VISUELLES :
            - Le NOM de la recette est écrit en gras très foncé en haut.
            - La PRÉPARATION est le bloc de texte où chaque étape commence généralement par un verbe d'action.
            - Les INGRÉDIENTS sont listés avec leurs quantités exactes.
            - Calcule le TEMPS total (préparation + repos + cuisson).
            
            RÉPONDS UNIQUEMENT EN JSON AVEC CES CLÉS :
            "nom", "temps", "personnes", "ingredients", "etapes", "type", "allergenes" (choisis dans {LISTE_ALLERGENES})."""
            
            try:
                res_ai = model.generate_content([prompt, Image.open(file)]) if file else model.generate_content(f"{url}\n{prompt}")
                match = re.search(r'\{.*\}', res_ai.text, re.DOTALL)
                if not match: raise ValueError("Données JSON introuvables.")
                
                # Nettoyage et Normalisation
                raw_json = json.loads(re.sub(r',\s*([\]}])', r'\1', match.group()))
                final_recipe = clean_recipe_data(raw_json, nom_livre)
                
                # Sauvegarde
                safe_name = "".join([c for c in final_recipe["nom"] if c.isalnum()]).lower()
                with open(os.path.join(DB_PATH, f"{safe_name}.json"), "w", encoding='utf-8') as f:
                    json.dump(final_recipe, f, ensure_ascii=False, indent=4)
                
                st.success(f"✅ Recette '{final_recipe['nom']}' sauvegardée !")
                st.download_button("💾 GitHub File", data=json.dumps(final_recipe, indent=4, ensure_ascii=False), file_name=f"{safe_name}.json")
            except Exception as e: st.error(f"Erreur : {e}")

with tab2:
    st.header("Ma Bibliothèque")
    if os.path.exists(DB_PATH):
        files = [f for f in os.listdir(DB_PATH) if f.endswith('.json')]
        for f_name in files:
            with open(os.path.join(DB_PATH, f_name), 'r', encoding='utf-8') as f:
                r = json.load(f)
                tps = format_temps(r.get('temps', 0))
                # Affichage avec clés forcées
                with st.expander(f"📖 {r.get('nom')} — 👥 {r.get('personnes')} pers — ⏱️ {tps}"):
                    if r.get('allergenes'): st.warning(f"⚠️ Contient : {', '.join(r.get('allergenes'))}")
                    c1, c2 = st.columns(2)
                    with c1:
                        st.markdown("### 🍎 Ingrédients")
                        for ing in r.get('ingredients', []): st.write(f"- {ing}")
                    with col2 if 'col2' in locals() else c2: # Correction sécurité
                        st.markdown("### 👨‍🍳 Préparation")
                        for i, e in enumerate(r.get('etapes', []), 1): st.write(f"{i}. {e}")
