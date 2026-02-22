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
    """Blindage total contre les crashs PDF (Emojis, Arabe, Symboles spéciaux)"""
    if not isinstance(text, str):
        return str(text)
    clean = text.replace("φ", "phi").replace("€", "Euros").replace("é", "e").replace("è", "e").replace("à", "a").replace("É", "E")
    # Forcer l'encodage pour ignorer les caractères que FPDF ne peut pas imprimer (évite le crash)
    clean = clean.encode('latin-1', 'ignore').decode('latin-1')
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
                
                c5, c6, c7, c8 = st.columns(4)
                nature = c5.selectbox("Métal", ["Cuivre", "Aluminium"])
                
                type_cable = c6.selectbox("Type de Câble", [
                    "U1000 R2V / RO2V", 
                    "H07VU / H07VR (Fils)", 
                    "H07RN-F (Souple)", 
                    "XAV / AR2V (Armé)", 
                    "CR1-C1 (Anti-incendie)", 
                    "Câble Solaire (FG21M21)"
                ])

                type_charge = c7.selectbox("Application", [
                    "Éclairage (Max 3%)", 
                    "Prises de courant (Max 5%)",
                    "Force Motrice / Moteur (Max 5%)",
                    "Chauffage / Cuisson (Max 5%)",
                    "Ligne Principale / Abonné (Max 2%)"
                ])
                cos_phi = c8.slider("Cos φ", 0.7, 1.0, 0.85)

                if st.form_submit_button("Calculer et Ajouter au Carnet"):
                    V = 230 if "230V" in tension else 400
                    rho = 0.0225 if "Cuivre" in nature else 0.036
                    b = 2 if "230V" in tension else 1
                    
                    if "3%" in type_charge: du_max = 3.0
                    elif "2%" in type_charge: du_max = 2.0
                    else: du_max = 5.0

                    Ib = p_w / (V * cos_phi) if b == 2 else p_w / (V * math.sqrt(3) * cos_phi)
                    calibres = [10, 16, 20, 25, 32, 40, 50, 63, 80, 100, 125, 160, 200, 250, 400, 630, 800, 1000]
                    In = next((x for x in calibres if x >= Ib), 1000)
                    
                    S_calc = (b * rho * longueur * Ib) / ((du_max / 100) * V)
                    sections = [1.5, 2.5, 4, 6, 10, 16, 25, 35, 50, 70, 95, 120, 150, 185, 240, 300]
                    S_ret = next((s for s in sections if s >= S_calc), 300)
                    
                    du_reel_pct = (((b * rho * longueur * Ib) / S_ret) / V) * 100

                    st.session_state.projet["cables"].append({
                        "Tableau": nom_tab_cables, "Repère": ref_c, "Type Câble": type_cable, "Métal": nature, 
                        "Tension": tension, "P(W)": p_w, "Long.(m)": longueur,
                        "Ib(A)": round(Ib, 1), "Calibre(A)": In, "Section(mm2)": S_ret, "dU(%)": round(du_reel_pct, 2)
                    })
                    st.success(f"Circuit '{ref_c}' calculé avec succès : {type_cable} {S_ret} mm² protégé par {In}A.")

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
                
                headers = ["Tab.", "Repere", "Type Cable", "U", "L(m)", "Ib(A)", "Disj.", "Section", "dU(%)"]
                widths = [18, 22, 28, 10, 12, 15, 15, 52, 18] # Somme exacte = 190
                
                for i in range(len(headers)): 
                    pdf.cell(widths[i], 8, headers[i], 1, 0, 'C', True)
                pdf.ln()
                
                pdf.set_font("Helvetica", "", 8)
                for row in st.session_state.projet["cables"]:
                    pdf.cell(widths[0], 8, sanitize_text(row.get("Tableau", "TGBT"), 10), 1)
                    pdf.cell(widths[1], 8, sanitize_text(row["Repère"], 12), 1)
                    
                    # CORRECTION: Coupe intelligemment avant la parenthèse pour garder le nom technique
                    raw_type = row.get("Type Câble", "U1000 R2V")
                    clean_type = sanitize_text(raw_type.split(" (")[0], 15) 
                    pdf.cell(widths[2], 8, clean_type, 1, 0, 'C')
                    
                    pdf.cell(widths[3], 8, str(row["Tension"])[0:3], 1, 0, 'C')
                    pdf.cell(widths[4], 8, str(row["Long.(m)"]), 1, 0, 'C')
                    pdf.cell(widths[5], 8, str(row["Ib(A)"]), 1, 0, 'C')
                    pdf.set_font("Helvetica", "B", 8)
                    pdf.cell(widths[6], 8, f"{row['Calibre(A)']}A", 1, 0, 'C')
                    pdf.set_text_color(255, 100, 0)
                    pdf.cell(widths[7], 8, f"{row['Section(mm2)']} mm2", 1, 0, 'C')
                    pdf.set_text_color(0, 0, 0)
                    pdf.set_font("Helvetica", "", 8)
                    pdf.cell(widths[8], 8, str(row["dU(%)"]), 1, 1, 'C')
                return pdf.output()

            col_btn1, col_btn2 = st.columns(2)
            if col_btn1.button("📄 Exporter Carnet (PDF)", type="primary"):
                st.download_button("📥 Télécharger PDF", bytes(generate_pdf_cables()), f"Cables_{sanitize_text(st.session_state.projet['info']['nom'])}.pdf")
            if col_btn2.button("🗑️ Vider le Carnet"):
                st.session_state.projet["cables"] = []; st.rerun()

    # ---------------------------------------------------------
    # MODULE 2 : ARCHITECTURE MULTI-TABLEAUX
    # ---------------------------------------------------------
    elif menu == "🏢 2. Bilan de Puissance (Multi-Tab)":
        st.title("🏢 Bilan de Puissance Global")
        
        with st.container(border=True):
            st.markdown("#### 📋 Identification du Projet")
            nom_p_m2 = st.text_input("Nom du Projet / Client", st.session_state.projet["info"]["nom"], key="proj_m2")
            st.session_state.projet["info"]["nom"] = nom_p_m2
            
            st.markdown("---")
            col_t1, col_t2 = st.columns([3, 1])
            nouveau_tab = col_t1.text_input("Ajouter un Tableau Divisionnaire (ex: TD RDC, TD Sous-sol)")
            if col_t2.button("➕ Créer le tableau", use_container_width=True) and nouveau_tab:
                if nouveau_tab not in st.session_state.projet["tableaux"]:
                    st.session_state.projet["tableaux"][nouveau_tab] = []
                    st.rerun()

        if st.session_state.projet["tableaux"]:
            onglets = st.tabs(list(st.session_state.projet["tableaux"].keys()) + ["🌍 SYNTHÈSE TGBT"])
            
            for i, nom_tab in enumerate(list(st.session_state.projet["tableaux"].keys())):
                with onglets[i]:
                    if st.button(f"❌ Supprimer le tableau '{nom_tab}'", key=f"del_{nom_tab}"):
                        del st.session_state.projet["tableaux"][nom_tab]
                        st.rerun()

                    with st.form(f"form_{i}"):
                        c1, c2, c3, c4 = st.columns([2,1,1,1])
                        c_nom = c1.text_input("Désignation Circuit (ex: Prises Salon)")
                        c_p = c2.number_input("Puissance (W)", min_value=0.0, value=1000.0)
                        
                        c_type = c3.selectbox("Type", [
                            "Éclairage", 
                            "Prises de courant", 
                            "Chauffage électrique", 
                            "Climatisation / PAC", 
                            "Force Motrice", 
                            "Cuisson", 
                            "IRVE (Recharge VE)", 
                            "Divers"
                        ])

                        if c_type in ["Éclairage", "Chauffage électrique", "IRVE (Recharge VE)"]: ku_def = 1.0
                        elif c_type == "Prises de courant": ku_def = 0.5
                        elif c_type == "Cuisson": ku_def = 0.7
                        elif c_type in ["Climatisation / PAC", "Force Motrice"]: ku_def = 0.75
                        else: ku_def = 0.8
                            
                        c_ku = c4.number_input("Ku (Utilisation)", min_value=0.1, max_value=1.0, value=float(ku_def), step=0.05)
                        
                        if st.form_submit_button("Ajouter à ce tableau"):
                            st.session_state.projet["tableaux"][nom_tab].append({
                                "Circuit": c_nom, "Type": c_type, "P(W)": c_p, "Ku": c_ku, "P.Abs(W)": int(c_p * c_ku)
                            })
                            st.rerun()
                    
                    circuits = st.session_state.projet["tableaux"].get(nom_tab, [])
                    if circuits:
                        df_tab = pd.DataFrame(circuits)
                        st.dataframe(df_tab, use_container_width=True)
                        st.metric(f"Total Absorbé ({nom_tab})", f"{df_tab['P.Abs(W)'].sum()} W")

            with onglets[-1]:
                st.markdown("### 🌍 Bilan Bâtiment (TGBT)")
                bilan_global = [{"Tableau": t, "Puissance Absorbée (W)": sum(c["P.Abs(W)"] for c in circs)} for t, circs in st.session_state.projet["tableaux"].items()]
                
                if bilan_global:
                    df_g = pd.DataFrame(bilan_global)
                    st.dataframe(df_g, use_container_width=True)
                    p_totale = df_g["Puissance Absorbée (W)"].sum()
                    
                    ks_global = st.slider("Foisonnement TGBT (Ks Global)", 0.4, 1.0, st.session_state.projet.get("ks_global", 0.8))
                    st.session_state.projet["ks_global"] = ks_global
                    
                    p_appel = int(p_totale * ks_global)
                    kva_estime = round(p_appel / 0.8 / 1000, 1)
                    
                    c1_res, c2_res = st.columns(2)
                    c1_res.success(f"**PUISSANCE ACTIVE D'APPEL : {p_appel} W**")
                    c2_res.info(f"**PUISSANCE APPARENTE (Abonnement) : {kva_estime} kVA**")

                    def generate_pdf_bilan():
                        pdf = FCELEC_Report()
                        pdf.set_auto_page_break(auto=True, margin=15)
                        pdf.add_page()
                        
                        pdf.set_font("Helvetica", "B", 14)
                        titre = sanitize_text(st.session_state.projet['info']['nom']).upper()
                        pdf.cell(190, 10, f"BILAN DE PUISSANCE MULTI-TABLEAUX - {titre}", ln=True, align="C")
                        pdf.ln(5)

                        for tab_name, circs in st.session_state.projet["tableaux"].items():
                            if not circs: continue
                            pdf.set_font("Helvetica", "B", 11)
                            pdf.set_fill_color(220, 220, 220)
                            pdf.cell(190, 8, f" TABLEAU : {sanitize_text(tab_name)}", border=1, ln=True, fill=True)
                            
                            pdf.set_font("Helvetica", "B", 9)
                            pdf.cell(60, 6, "Circuit", 1)
                            pdf.cell(50, 6, "Type", 1, 0, 'C')
                            pdf.cell(30, 6, "P.Inst (W)", 1, 0, 'C')
                            pdf.cell(20, 6, "Ku", 1, 0, 'C')
                            pdf.cell(30, 6, "P.Abs (W)", 1, 1, 'C')
                            
                            pdf.set_font("Helvetica", "", 9)
                            sous_total = 0
                            for c in circs:
                                pdf.cell(60, 6, sanitize_text(c['Circuit'], 30), 1)
                                pdf.cell(50, 6, sanitize_text(c['Type'], 25), 1, 0, 'C')
                                pdf.cell(30, 6, str(c['P(W)']), 1, 0, 'C')
                                pdf.cell(20, 6, str(c['Ku']), 1, 0, 'C')
                                pdf.cell(30, 6, str(c['P.Abs(W)']), 1, 1, 'C')
                                sous_total += c['P.Abs(W)']
                            
                            pdf.set_font("Helvetica", "I", 9)
                            pdf.cell(190, 6, f"Sous-total absorbé pour {sanitize_text(tab_name)} : {sous_total} W", border='B', ln=True, align="R")
                            pdf.ln(4)

                        pdf.ln(5)
                        pdf.set_font("Helvetica", "B", 12)
                        pdf.set_fill_color(255, 245, 230)
                        pdf.cell(190, 10, f"PUISSANCE MAXIMALE D'APPEL (Ks={ks_global}) : {p_appel} W", border=1, ln=True, align="C", fill=True)
                        pdf.cell(190, 10, f"PUISSANCE APPARENTE ESTIMEE (Cos phi 0.8) : {kva_estime} kVA", border=1, ln=True, align="C")
                        return pdf.output()

                    if st.button("📄 Exporter Bilan Complet (PDF)", type="primary"):
                        st.download_button("📥 Télécharger Bilan PDF", bytes(generate_pdf_bilan()), f"Bilan_{sanitize_text(st.session_state.projet['info']['nom'])}.pdf")

    # ---------------------------------------------------------
    # MODULE 3 : NOMENCLATURE & DEVIS
    # ---------------------------------------------------------
    elif menu == "💰 3. Nomenclature & Devis":
        st.title("💰 Devis et Liste d'Achats")
        nomenclatures = []
        
        for cab in st.session_state.projet["cables"]:
            nature = cab.get("Métal", "Cuivre")
            type_c = cab.get("Type Câble", "U1000 R2V").split(" (")[0]
            nomenclatures.append({"Catégorie": "Câble", "Désignation": f"Câble {nature} {type_c} - {cab['Section(mm2)']} mm2", "Quantité": cab["Long.(m)"], "Unité": "m", "Prix Unitaire HT": 15.0})
            nomenclatures.append({"Catégorie": "Protection", "Désignation": f"Disjoncteur {cab['Calibre(A)']}A", "Quantité": 1, "Unité": "U", "Prix Unitaire HT": 80.0})

        for tab, circs in st.session_state.projet["tableaux"].items():
            for c in circs:
                cal_estime = 16 if c["P(W)"] <= 3500 else 20 if c["P(W)"] <= 4500 else 32
                nomenclatures.append({"Catégorie": "Protection", "Désignation": f"Disjoncteur Divisionnaire {cal_estime}A", "Quantité": 1, "Unité": "U", "Prix Unitaire HT": 65.0})

        if not nomenclatures:
            st.info("Saisissez des données dans les modules précédents pour générer le devis.")
        else:
            df_nom = pd.DataFrame(nomenclatures)
            df_nom["Prix Unitaire HT"] = pd.to_numeric(df_nom["Prix Unitaire HT"], errors='coerce').fillna(0)
            df_nom["Quantité"] = pd.to_numeric(df_nom["Quantité"], errors='coerce').fillna(0)
            
            df_grouped = df_nom.groupby(["Catégorie", "Désignation", "Unité"], as_index=False).agg({"Quantité": "sum", "Prix Unitaire HT": "mean"})
            
            st.write("✏️ *Astuce : Modifiez les prix unitaires. Appuyez sur Entrée, puis cliquez sur Exporter.*")
            
            df_edited = st.data_editor(
                df_grouped,
                key="editeur_devis",
                column_config={"Prix Unitaire HT": st.column_config.NumberColumn("Prix U. HT (MAD)", format="%.2f")},
                hide_index=True, use_container_width=True
            )
            
            df_edited["Total HT"] = df_edited["Quantité"] * df_edited["Prix Unitaire HT"]
            total_ht = df_edited["Total HT"].sum()
            
            c1, c2 = st.columns(2)
            c1.metric("Total Matériel (HT)", f"{total_ht:,.2f} MAD")
            c2.metric("Total Matériel (TTC 20%)", f"{total_ht * 1.20:,.2f} MAD")

            st.download_button("📊 Exporter vers Excel (.xlsx)", data=to_excel(df_edited), file_name=f"Devis_{sanitize_text(st.session_state.projet['info']['nom'])}.xlsx", type="primary")

    # ---------------------------------------------------------
    # MODULE 4 : OUTILS
    # ---------------------------------------------------------
    elif menu == "📉 4. Outils (Cos φ & IRVE)":
        onglets = st.tabs(["📉 Cos φ", "🚘 IRVE"])
        with onglets[0]:
            st.title("Compensation d'Energie Réactive")
            with st.container(border=True):
                p_kw = st.number_input("Puissance (kW)", value=100.0)
                c1, c2 = st.columns(2)
                cos_i = c1.slider("Cos φ actuel", 0.5, 0.95, 0.75)
                cos_v = c2.slider("Cos φ cible", 0.9, 1.0, 0.95)
                qc = p_kw * (math.tan(math.acos(cos_i)) - math.tan(math.acos(cos_v)))
                st.success(f"Batterie condensateurs : **{math.ceil(qc)} kVAR**")
            
        with onglets[1]:
            st.title("Mobilité Electrique (IRVE)")
            with st.container(border=True):
                p_b = st.selectbox("Puissance", ["7.4 kW (32A Mono)", "22 kW (32A Tri)"])
                st.info("Différentiel 30mA Type B. Câble : 10 mm² minimum.")

    st.sidebar.markdown("---")
    if st.sidebar.button("🔴 Déconnexion"):
        st.session_state.clear(); st.rerun()