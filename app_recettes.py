import streamlit as st
import os
import json
import google.generativeai as genai
from PIL import Image

# --- CONFIGURATION GEMINI (GRATUIT) ---
# Récupération de la clé depuis les secrets Streamlit Cloud
try:
    api_key = st.secrets["GEMINI_API_KEY"]
except:
    # Pour tes tests dans Spyder uniquement
    api_key = "AIzaSyDt209x24lHpOmY-GzBDJ5bNDoXH-hZo-4"

genai.configure(api_key=api_key)
# Utilisation du nom complet du modèle pour éviter l'erreur NotFound
model = genai.GenerativeModel('gemini-pro')

st.set_page_config(page_title="Ma Cuisine Pro MP2I", layout="wide")
st.title("📚 Assistant Recettes Gratuit")

# Dossier de stockage des recettes sur le serveur
DB_PATH = "ma_base_recettes"
if not os.path.exists(DB_PATH):
    os.makedirs(DB_PATH)

# --- FONCTIONS UTILES ---
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
tab1, tab2 = st.tabs(["📥 Importer une Recette", "🔍 Ma Bibliothèque"])

with tab1:
    source = st.radio("Source de la recette :", ["Appareil Photo", "Galerie", "Lien Web"])
    
    existing_books = get_all_books()
    book_option = st.selectbox("Livre :", ["+ Nouveau Livre"] + existing_books)
    nom_livre_final = st.text_input("Nom du nouveau livre") if book_option == "+ Nouveau Livre" else book_option
    
    file_to_analyze = None
    url_web = None

    if source == "Appareil Photo":
        file_to_analyze = st.camera_input("Prendre la photo")
    elif source == "Galerie":
        file_to_analyze = st.file_uploader("Choisir une image", type=['png', 'jpg', 'jpeg'])
    else:
        url_web = st.text_input("Coller le lien de la recette (ex: Marmiton)")

    if st.button("Analyser et Sauvegarder"):
        if (source == "Lien Web" and not url_web) or (source != "Lien Web" and not file_to_analyze):
            st.error("Donnée manquante !")
        else:
            with st.spinner("L'IA Gemini analyse la recette..."):
                prompt = """Analyse cette recette. Réponds UNIQUEMENT avec un objet JSON strict contenant ces clés : 
                'nom', 'ingredients' (liste), 'temps' (entier en minutes), 'type' (Entrée, Plat, Dessert ou Gâteau) et 'allergenes' (liste)."""
                
                try:
                    if source == "Lien Web":
                        response = model.generate_content(f"Lien : {url_web}. {prompt}")
                    else:
                        img = Image.open(file_to_analyze)
                        response = model.generate_content([prompt, img])
                    
                    # Nettoyage de la réponse pour extraire le JSON proprement
                    raw_text = response.text.strip()
                    if "```json" in raw_text:
                        raw_text = raw_text.split("```json")[1].split("```")[0]
                    elif "```" in raw_text:
                        raw_text = raw_text.split("```")[1].split("```")[0]
                    
                    res = json.loads(raw_text)
                    res["livre"] = nom_livre_final
                    
                    # Sauvegarde
                    safe_name = "".join([c for c in res['nom'] if c.isalnum() or c==' ']).rstrip()
                    with open(f"{DB_PATH}/{safe_name.replace(' ', '_')}.json", "w") as f:
                        json.dump(res, f)
                    
                    st.success(f"✅ '{res['nom']}' ajouté !")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erreur d'analyse : {e}")

with tab2:
    st.header("Filtrer mes recettes")
    all_books = get_all_books()
    
    col1, col2 = st.columns(2)
    with col1:
        s_nom = st.text_input("🔍 Rechercher par nom")
        s_ing = st.text_input("🍎 Rechercher un ingrédient")
    with col2:
        s_livre = st.multiselect("📖 Filtrer par Livre(s)", all_books)
        s_type = st.multiselect("🍴 Type de plat", ["Entrée", "Plat", "Dessert", "Gâteau"])

    st.divider()

    files = [f for f in os.listdir(DB_PATH) if f.endswith('.json')]
    for file in files:
        with open(os.path.join(DB_PATH, file), 'r') as f:
            r = json.load(f)
            
            # Logique de filtrage
            match_nom = s_nom.lower() in r['nom'].lower()
            match_ing = not s_ing or any(s_ing.lower() in i.lower() for i in r['ingredients'])
            match_livre = not s_livre or r.get('livre') in s_livre
            match_type = not s_type or r.get('type') in s_type
            
            if match_nom and match_ing and match_livre and match_type:
                with st.expander(f"{r['nom']} ({r.get('type', 'Plat')}) — {r['temps']} min"):
                    st.write(f"**Livre :** {r.get('livre', 'Non précisé')}")
                    st.write(f"**Ingrédients :** {', '.join(r['ingredients'])}")
                    if r.get('allergenes'):

                        st.warning(f"⚠️ Allergènes : {', '.join(r['allergenes'])}")



