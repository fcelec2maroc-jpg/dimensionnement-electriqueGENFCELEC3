import streamlit as st
import math
import datetime
import json
import pandas as pd
from io import BytesIO
from fpdf import FPDF

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="FC ELEC - Ingénierie & Chiffrage", layout="wide")

st.markdown("""
    <style>
    .stButton>button { border-radius: 5px; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# --- INITIALISATION DE LA BASE DE DONNÉES (SESSION STATE) ---
if 'projet' not in st.session_state:
    st.session_state.projet = {
        "info": {"nom": "Nouveau Projet", "client": ""},
        "cables": [],          # Carnet de câbles
        "tableaux": {},        # Multi-tableaux (Nom du tableau -> Liste des circuits)
        "ks_global": 0.8
    }

# --- FONCTION EXPORT EXCEL ---
def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Nomenclature_Chiffrage')
    return output.getvalue()

# --- SÉCURITÉ ---
def check_password():
    if "password_correct" not in st.session_state:
        st.image("logoFCELEC.png", width=200)
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
    # --- BARRE LATÉRALE : SAUVEGARDE & NAVIGATION ---
    st.sidebar.image("logoFCELEC.png", use_container_width=True)
    
    st.sidebar.markdown("### 💾 GESTION DE PROJET")
    # Nom du projet en direct
    st.session_state.projet["info"]["nom"] = st.sidebar.text_input("Nom du Projet", st.session_state.projet["info"]["nom"])
    
    # Sauvegarder
    projet_json = json.dumps(st.session_state.projet, indent=4)
    st.sidebar.download_button(label="📥 Sauvegarder le Projet (.json)", data=projet_json, file_name=f"{st.session_state.projet['info']['nom']}.json", mime="application/json")
    
    # Charger
    fichier_charge = st.sidebar.file_uploader("📂 Charger un Projet", type=['json'])
    if fichier_charge is not None:
        try:
            st.session_state.projet = json.load(fichier_charge)
            st.sidebar.success("Projet chargé avec succès ! Cliquez à nouveau pour rafraîchir.")
        except:
            st.sidebar.error("Fichier corrompu.")

    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📐 MODULES")
    menu = st.sidebar.radio("Navigation :", [
        "🔌 1. Carnet de Câbles",
        "🏢 2. Architecture Multi-Tableaux",
        "💰 3. Nomenclature & Chiffrage (Excel)",
        "📉 4. Outils (Cos φ & IRVE)"
    ])

    # ---------------------------------------------------------
    # MODULE 1 : CARNET DE CÂBLES
    # ---------------------------------------------------------
    if menu == "🔌 1. Carnet de Câbles":
        st.title("🔌 Dimensionnement des Lignes")
        
        with st.form("ajout_cable"):
            c1, c2, c3, c4 = st.columns(4)
            ref_c = c1.text_input("Repère", "L1")
            tension = c2.selectbox("Tension", ["230V", "400V"])
            p_w = c3.number_input("Puissance (W)", min_value=0, value=3500)
            longueur = c4.number_input("Longueur (m)", min_value=1, value=50)
            
            c5, c6, c7 = st.columns(3)
            nature = c5.selectbox("Métal", ["Cuivre", "Aluminium"])
            type_charge = c6.selectbox("Application", ["Éclairage (3%)", "Prises/Moteur (5%)"])
            cos_phi = c7.slider("Cos φ", 0.7, 1.0, 0.85)

            if st.form_submit_button("Calculer et Ajouter"):
                V = 230 if "230V" in tension else 400
                rho = 0.0225 if "Cuivre" in nature else 0.036
                b = 2 if "230V" in tension else 1
                du_max = 3.0 if "Éclairage" in type_charge else 5.0

                Ib = p_w / (V * cos_phi) if b == 2 else p_w / (V * math.sqrt(3) * cos_phi)
                calibres = [10, 16, 20, 25, 32, 40, 50, 63, 80, 100, 125, 160, 200, 250, 400, 630]
                In = next((x for x in calibres if x >= Ib), 630)
                
                S_calc = (b * rho * longueur * Ib) / ((du_max / 100) * V)
                sections = [1.5, 2.5, 4, 6, 10, 16, 25, 35, 50, 70, 95, 120, 150, 185, 240, 300]
                S_ret = next((s for s in sections if s >= S_calc), 300)

                st.session_state.projet["cables"].append({
                    "Repère": ref_c, "Tension": tension, "P(W)": p_w, "Long.(m)": longueur,
                    "Ib(A)": round(Ib, 1), "Calibre(A)": In, "Section(mm2)": S_ret
                })

        if st.session_state.projet["cables"]:
            st.dataframe(pd.DataFrame(st.session_state.projet["cables"]), use_container_width=True)
            if st.button("🗑️ Vider les câbles"):
                st.session_state.projet["cables"] = []
                st.rerun()

    # ---------------------------------------------------------
    # MODULE 2 : MULTI-TABLEAUX
    # ---------------------------------------------------------
    elif menu == "🏢 2. Architecture Multi-Tableaux":
        st.title("🏢 Architecture Bilan de Puissance")
        
        # Gestion des tableaux
        col_t1, col_t2 = st.columns([3, 1])
        nouveau_tab = col_t1.text_input("Créer un nouveau Tableau (ex: TD Éclairage, TD Cuisine)")
        if col_t2.button("➕ Créer le tableau", use_container_width=True) and nouveau_tab:
            if nouveau_tab not in st.session_state.projet["tableaux"]:
                st.session_state.projet["tableaux"][nouveau_tab] = []
                st.success(f"Tableau '{nouveau_tab}' créé.")
                st.rerun()

        if not st.session_state.projet["tableaux"]:
            st.info("Commencez par créer un tableau ci-dessus.")
        else:
            onglets = st.tabs(list(st.session_state.projet["tableaux"].keys()) + ["🌍 SYNTHÈSE TGBT"])
            
            # Pour chaque tableau
            for i, nom_tab in enumerate(st.session_state.projet["tableaux"].keys()):
                with onglets[i]:
                    st.markdown(f"### Circuits du tableau : {nom_tab}")
                    with st.form(f"form_{nom_tab}"):
                        c1, c2, c3, c4 = st.columns([2,1,1,1])
                        c_nom = c1.text_input("Désignation du circuit")
                        c_p = c2.number_input("Puissance (W)", value=1000, key=f"pw_{nom_tab}")
                        c_type = c3.selectbox("Type", ["Éclairage", "Prises", "CVC/Moteur"], key=f"typ_{nom_tab}")
                        c_ku = c4.number_input("Ku", value=1.0 if c_type=="Éclairage" else 0.8, max_value=1.0, key=f"ku_{nom_tab}")
                        
                        if st.form_submit_button("Ajouter à ce tableau"):
                            st.session_state.projet["tableaux"][nom_tab].append({
                                "Circuit": c_nom, "Type": c_type, "P(W)": c_p, "Ku": c_ku, "P.Abs(W)": int(c_p * c_ku)
                            })
                            st.rerun()
                    
                    circuits = st.session_state.projet["tableaux"][nom_tab]
                    if circuits:
                        df_tab = pd.DataFrame(circuits)
                        st.dataframe(df_tab, use_container_width=True)
                        p_abs_tab = df_tab["P.Abs(W)"].sum()
                        st.metric(f"Total Absorbé ({nom_tab})", f"{p_abs_tab} W")

            # Onglet Synthèse Globale TGBT
            with onglets[-1]:
                st.markdown("### 🌍 Bilan Global du TGBT")
                bilan_global = []
                for tab, circs in st.session_state.projet["tableaux"].items():
                    p_abs = sum(c["P.Abs(W)"] for c in circs)
                    bilan_global.append({"Tableau Divisionnaire": tab, "Puissance Absorbée (W)": p_abs})
                
                if bilan_global:
                    df_global = pd.DataFrame(bilan_global)
                    st.dataframe(df_global, use_container_width=True)
                    
                    p_total_usine = df_global["Puissance Absorbée (W)"].sum()
                    ks_global = st.slider("Foisonnement TGBT (Ks Global)", 0.4, 1.0, st.session_state.projet.get("ks_global", 0.8))
                    st.session_state.projet["ks_global"] = ks_global
                    
                    p_souscrite = int(p_total_usine * ks_global)
                    
                    st.success(f"**PUISSANCE TOTALE D'APPEL DU BÂTIMENT : {p_souscrite} Watts**")

    # ---------------------------------------------------------
    # MODULE 3 : NOMENCLATURE ET CHIFFRAGE (L'INNOVATION PRO)
    # ---------------------------------------------------------
    elif menu == "💰 3. Nomenclature & Chiffrage (Excel)":
        st.title("💰 Devis, Chiffrage et Liste d'Achats")
        st.write("Ce module compile automatiquement tous les éléments saisis pour générer votre devis.")

        # Compilation des données
        nomenclatures = []
        
        # 1. Analyser les câbles
        for cab in st.session_state.projet["cables"]:
            # On regroupe par section pour avoir la longueur totale
            nomenclatures.append({
                "Catégorie": "Câble",
                "Désignation": f"Câble Cuivre {cab['Section(mm2)']} mm²",
                "Quantité": cab["Long.(m)"],
                "Unité": "mètre",
                "Prix Unitaire HT": 15.0 if cab['Section(mm2)'] <= 6 else 45.0 # Prix par défaut modifiables
            })
            # Et le disjoncteur associé
            nomenclatures.append({
                "Catégorie": "Protection",
                "Désignation": f"Disjoncteur Magnéto-Thermique {cab['Calibre(A)']}A",
                "Quantité": 1,
                "Unité": "pièce",
                "Prix Unitaire HT": 80.0 if cab['Calibre(A)'] <= 32 else 250.0
            })

        # 2. Analyser les circuits des tableaux (estimations)
        for tab, circs in st.session_state.projet["tableaux"].items():
            for c in circs:
                calibre_estime = 16 if c["P(W)"] <= 3500 else 20 if c["P(W)"] <= 4500 else 32
                nomenclatures.append({
                    "Catégorie": "Protection (Multi-Tab)",
                    "Désignation": f"Disjoncteur Divisionnaire {calibre_estime}A ({tab})",
                    "Quantité": 1,
                    "Unité": "pièce",
                    "Prix Unitaire HT": 65.0
                })

        if not nomenclatures:
            st.info("Saisissez des câbles ou des circuits dans les modules précédents pour générer le chiffrage.")
        else:
            # Agrégation des quantités identiques
            df_nom = pd.DataFrame(nomenclatures)
            df_grouped = df_nom.groupby(["Catégorie", "Désignation", "Unité", "Prix Unitaire HT"], as_index=False).sum()
            
            st.markdown("### 📝 Ajustement des Prix Unitaires")
            st.write("Modifiez les prix unitaires directement dans le tableau ci-dessous :")
            
            # Tableau éditable par l'utilisateur !
            df_edited = st.data_editor(
                df_grouped,
                column_config={
                    "Prix Unitaire HT": st.column_config.NumberColumn("Prix U. HT (MAD)", min_value=0, format="%.2f"),
                    "Quantité": st.column_config.NumberColumn("Quantité", disabled=True),
                    "Catégorie": st.column_config.TextColumn("Catégorie", disabled=True),
                    "Désignation": st.column_config.TextColumn("Désignation", disabled=True)
                },
                hide_index=True,
                use_container_width=True
            )
            
            # Calcul du total
            df_edited["Total HT"] = df_edited["Quantité"] * df_edited["Prix Unitaire HT"]
            total_ht = df_edited["Total HT"].sum()
            total_ttc = total_ht * 1.20 # TVA 20%
            
            col_tot1, col_tot2 = st.columns(2)
            col_tot1.metric("Montant Total Matériel (HT)", f"{total_ht:,.2f} MAD")
            col_tot2.metric("Montant Total Matériel (TTC 20%)", f"{total_ttc:,.2f} MAD")

            st.markdown("---")
            # Export Excel
            excel_data = to_excel(df_edited)
            st.download_button(
                label="📊 Exporter le Chiffrage vers Excel (.xlsx)",
                data=excel_data,
                file_name=f"Devis_{st.session_state.projet['info']['nom']}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary"
            )

    # ---------------------------------------------------------
    # MODULE 4 : OUTILS
    # ---------------------------------------------------------
    elif menu == "📉 4. Outils (Cos φ & IRVE)":
        onglets = st.tabs(["📉 Compensation Cos φ", "🚘 Bornes IRVE"])
        with onglets[0]:
            st.title("Compensation d'Énergie Réactive")
            p_kw = st.number_input("Puissance Active (kW)", value=100.0)
            c1, c2 = st.columns(2)
            cos_i = c1.slider("Cos φ actuel", 0.5, 0.95, 0.75)
            cos_v = c2.slider("Cos φ cible", 0.9, 1.0, 0.95)
            qc = p_kw * (math.tan(math.acos(cos_i)) - math.tan(math.acos(cos_v)))
            st.success(f"Batterie de condensateurs requise : **{math.ceil(qc)} kVAR**")
            
        with onglets[1]:
            st.title("Mobilité Électrique (IRVE)")
            p_borne = st.selectbox("Puissance Borne", ["7.4 kW (32A Mono)", "22 kW (32A Tri)"])
            st.info("Protection : Différentiel 30mA Type B. Câble : 10 mm² minimum.")

    st.sidebar.markdown("---")
    if st.sidebar.button("🔴 Se déconnecter"):
        st.session_state.clear()
        st.rerun()