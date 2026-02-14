import streamlit as st
import google.generativeai as genai

# Configuration avec ta clé Zo-4
api_key = "AIzaSyBvvqOuMwFdgUH5T4GJlT0fS4i4Qnti8Gk"
genai.configure(api_key=api_key)

# --- DÉTECTION AUTOMATIQUE DU MODÈLE ---
@st.cache_resource
def get_working_model():
    available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
    # On cherche flash d'abord, sinon pro, sinon le premier de la liste
    if 'models/gemini-1.5-flash-latest' in available_models:
        return 'gemini-1.5-flash-latest'
    if 'models/gemini-1.5-flash' in available_models:
        return 'gemini-1.5-flash'
    if 'models/gemini-pro' in available_models:
        return 'gemini-pro'
    return available_models[0].replace('models/', '')

try:
    target_model = get_working_model()
    model = genai.GenerativeModel(target_model)
    st.info(f"Modèle activé : {target_model}")
except Exception as e:
    st.error(f"Impossible de lister les modèles : {e}")
