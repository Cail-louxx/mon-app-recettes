import streamlit as st
import os
import json
import base64
from openai import OpenAI

# --- CONFIGURATION DE L'IA ---
# Sur ton PC : remplace st.secrets par "ta-clé-ici" entre guillemets
# Sur Streamlit Cloud : laisse tel quel
try:
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
except:
    client = OpenAI(api_key="METS_TA_CLE_ICI_POUR_TESTER_SUR_SPYDER")

st.set_page_config(page_title="Ma Cuisine Pro MP2I", layout="wide")
st.title("📚 Gestionnaire de Recettes Intelligent")

DB_PATH = "ma_base_recettes"
if not os.path.exists(DB_PATH):
    os.makedirs(DB_PATH)

# Fonction pour lister les livres existants
def get_all_books():
    books = set()
    if os.path.exists(DB_PATH):
        files = [f for f in os.listdir(DB_PATH) if f.endswith('.json')]
        for file in files:
            with open(os.path.join(DB_PATH, file), 'r') as f:
                data = json.load(f)
                if data.get("livre"): books.add(data["livre"])
    return sorted(list(books))

def encoder_image(image_file):
    return base64.b64encode(image_file.read()).decode('utf-8')

tab1, tab2 = st.tabs(["📥 Importer une Recette", "🔍 Ma Bibliothèque"])

with tab1:
    source = st.radio("Source :", ["Appareil Photo", "Galerie", "Lien Web"])
    
    existing_books = get_all_books()
    book_option = st.selectbox("Livre :", ["+ Nouveau Livre"] + existing_books)
    nom_livre_final = st.text_input("Nom du nouveau livre") if book_option == "+ Nouveau Livre" else book_option
    
    image_to_analyze = None
    url_to_analyze = None

    if source == "Appareil Photo": image_to_analyze = st.camera_input("Prendre la photo")
    elif source == "Galerie": image_to_analyze = st.file_uploader("Choisir une image", type=['png', 'jpg', 'jpeg'])
    else: url_to_analyze = st.text_input("Lien URL de la recette")

    if st.button("Analyser et Sauvegarder"):
        with st.spinner("Analyse par l'IA en cours..."):
            prompt = "Analyse cette recette. Donne le NOM, les INGREDIENTS (liste), le TEMPS (en min, entier), le TYPE (Entrée, Plat, Dessert, Gâteau) et les ALLERGENES en JSON."
            
            if image_to_analyze:
                b64 = encoder_image(image_to_analyze)
                content = [{"type": "text", "text": prompt}, {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}]
            else:
                content = f"Analyse ce lien : {url_to_analyze}. {prompt}"

            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": content}],
                response_format={ "type": "json_object" }
            )
            
            res = json.loads(response.choices[0].message.content)
            res["livre"] = nom_livre_final
            
            with open(f"{DB_PATH}/{res['nom'].replace(' ', '_')}.json", "w") as f:
                json.dump(res, f)
            st.success(f"✅ Recette ajoutée !")
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
                    st.write(f"**Livre :** {r.get('livre')}")
                    st.write(f"**Ingrédients :** {', '.join(r['ingredients'])}")
                    st.write(f"**Allergènes :** {', '.join(r.get('allergenes', []))}")