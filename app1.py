import streamlit as st
import math
import datetime
import json
import pandas as pd
from io import BytesIO
from fpdf import FPDF

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="FC ELEC - Ingénierie & Chiffrage", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    .reportview-container { background: #f4f6f9; }
    .stButton>button { border-radius: 5px; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# --- INITIALISATION DE LA BASE DE DONNÉES ---
if 'projet' not in st.session_state:
    st.session_state.projet = {
        "info": {"nom": "Chantier Résidentiel"},
        "cables": [],          
        "tableaux": {},        
        "ks_global": 0.8
    }

# --- FONCTIONS UTILITAIRES ---
def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Chiffrage_FCELEC')
    return output.getvalue()

def sanitize_text(text, max_len=30):
    if not isinstance(text, str):
        return str(text)
    clean = text.replace("φ", "phi").replace("€", "Euros").replace("é", "e").replace("è", "e").replace("à", "a")
    return clean[:max_len] + "..." if len(clean) > max_len else clean

# --- CLASSE PDF PROFESSIONNELLE ---
class FCELEC_Report(FPDF):
    def header(self):
        try: self.image("logoFCELEC.png", 10, 8, 25)
        except: pass
        self.set_font("Helvetica", "B", 14)
        self.cell(30)
        self.cell(130, 8, "DOSSIER TECHNIQUE ELECTRIQUE", border=0, ln=0, align="C")
        self.set_font("Helvetica", "I", 9)
        self.cell(30, 8, f"{datetime.date.today().strftime('%d/%m/%Y')}", border=0, ln=1, align="R")
        self.set_font("Helvetica", "I", 9)
        self.cell(30)
        self.cell(130, 5, "Note de calcul conforme a la norme NF C 15-100", border=0, ln=1, align="C")
        self.line(10, 25, 200, 25)
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(128, 128, 128)
        self.line(10, 282, 200, 282)
        self.cell(0, 5, f"FC ELEC - Bureau d'Etudes | WhatsApp : +212 6 74 53 42 64 | Page {self.page_no()}", 0, 0, "C")

# --- SÉCURITÉ ---
def check_password():
    if "password_correct" not in st.session_state:
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            st.image("logoFCELEC.png", width=250)
            st.markdown("### 🔐 Portail Ingénierie FC ELEC")
            user = st.text_input("Identifiant")
            pw = st.text_input("Mot de passe", type="password")
            if st.button("Authentification"):
                if "passwords" in st.secrets and user in st.secrets["passwords"] and pw == st.secrets["passwords"][user]:
                    st.session_state["password_correct"] = True
                    st.rerun()
                else:
                    st.error("Accès refusé.")
        return False
    return True

if check_password():
    # --- BARRE LATÉRALE ---
    st.sidebar.image("logoFCELEC.png", use_container_width=True)
    st.sidebar.markdown("### 💾 GESTION DE PROJET")
    
    st.sidebar.info(f"📁 Projet actif : **{st.session_state.projet['info']['nom']}**")

    projet_json = json.dumps(st.session_state.projet, indent=4)
    st.sidebar.download_button("📥 Sauvegarder Projet (.json)", data=projet_json, file_name=f"{sanitize_text(st.session_state.projet['info']['nom'])}.json", mime="application/json")
    
    fichier_charge = st.sidebar.file_uploader("📂 Charger un Projet", type=['json'])
    if fichier_charge is not None:
        try:
            donnees = json.load(fichier_charge)
            if donnees != st.session_state.projet:
                st.session_state.projet = donnees
                st.sidebar.success("Projet chargé !")
                st.rerun()
        except:
            st.sidebar.error("Fichier invalide.")

    st.sidebar.markdown("---")
    menu = st.sidebar.radio("Navigation :", [
        "🔌 1. Carnet de Câbles",
        "🏢 2. Bilan de Puissance (Multi-Tab)",
        "💰 3. Nomenclature & Devis",
        "📉 4. Outils (Cos φ & IRVE)"
    ])

    # ---------------------------------------------------------
    # MODULE 1 : CARNET DE CÂBLES
    # ---------------------------------------------------------
    if menu == "🔌 1. Carnet de Câbles":
        st.title("🔌 Dimensionnement des Lignes")
        
        with st.container(border=True):
            st.markdown("#### 📋 Identification de la ligne")
            col_p1, col_p2, col_p3 = st.columns(3)
            nom_p = col_p1.text_input("Nom du Projet / Client", st.session_state.projet["info"]["nom"], key="proj_m1")
            st.session_state.projet["info"]["nom"] = nom_p
            nom_tab_cables = col_p2.text_input("Tableau (ex: TGBT, TD1)", "TGBT")
            ref_c = col_p3.text_input("Désignation du Circuit", "Départ Sous-sol")

            st.markdown("---")
            with st.form("ajout_cable"):
                st.markdown("#### ⚙️ Paramètres Techniques de la Ligne")
                c1, c2, c3 = st.columns(3)
                tension = c1.selectbox("Tension", ["230V", "400V"])
                p_w = c2.number_input("Puissance (W)", min_value=0.0, value=3500.0)
                longueur = c3.number_input("Longueur (m)", min_value=1.0, value=50.0)
                
                c5, c6, c7 = st.columns(3)
                nature = c5.selectbox("Métal", ["Cuivre", "Aluminium"])
                type_charge = c6.selectbox("Application", ["Eclairage (Max 3%)", "Autres (Max 5%)"])
                cos_phi = c7.slider("Cos φ", 0.7, 1.0, 0.85)

                if st.form_submit_button("Calculer et Ajouter au Carnet"):
                    V = 230 if "230V" in tension else 400
                    rho = 0.0225 if "Cuivre" in nature else 0.036
                    b = 2 if "230V" in tension else 1
                    du_max = 3.0 if "Eclairage" in type_charge else 5.0

                    Ib = p_w / (V * cos_phi) if b == 2 else p_w / (V * math.sqrt(3) * cos_phi)
                    calibres = [10, 16, 20, 25, 32, 40, 50, 63, 80, 100, 125, 160, 200, 250, 400, 630, 800, 1000]
                    In = next((x for x in calibres if x >= Ib), 1000)
                    
                    S_calc = (b * rho * longueur * Ib) / ((du_max / 100) * V)
                    sections = [1.5, 2.5, 4, 6, 10, 16, 25, 35, 50, 70, 95, 120, 150, 185, 240, 300]
                    S_ret = next((s for s in sections if s >= S_calc), 300)
                    
                    du_reel_pct = (((b * rho * longueur * Ib) / S_ret) / V) * 100

                    st.session_state.projet["cables"].append({
                        "Tableau": nom_tab_cables, "Repère": ref_c, "Tension": tension, "P(W)": p_w, "Long.(m)": longueur,
                        "Ib(A)": round(Ib, 1), "Calibre(A)": In, "Section(mm2)": S_ret, "dU(%)": round(du_reel_pct, 2)
                    })
                    st.success(f"Circuit '{ref_c}' calculé avec succès : Câble {S_ret} mm² protégé par {In}A.")

        if st.session_state.projet["cables"]:
            st.markdown("### 📑 Carnet de Câbles")
            st.dataframe(pd.DataFrame(st.session_state.projet["cables"]), use_container_width=True)
            
            def generate_pdf_cables():
                pdf = FCELEC_Report()
                pdf.set_auto_page_break(auto=True, margin=15)
                pdf.add_page()
                pdf.set_font("Helvetica", "B", 12)
                pdf.set_fill_color(230, 230, 230)
                titre = sanitize_text(st.session_state.projet['info']['nom']).upper()
                pdf.cell(190, 10, f" CARNET DE CABLES - PROJET : {titre}", border=1, ln=True, align="C", fill=True)
                pdf.ln(5)
                pdf.set_font("Helvetica", "B", 8)
                pdf.set_fill_color(200, 200, 200)
                
                headers = ["Tableau", "Repere", "U", "L(m)", "P(W)", "Ib(A)", "Disj.", "Section", "dU(%)"]
                widths = [25, 25, 12, 12, 16, 16, 16, 48,