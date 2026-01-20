import streamlit as st
from supabase import create_client
import pandas as pd
import os
from dotenv import load_dotenv

# Chargement des variables (pour le local)
load_dotenv()

# Configuration de la page
st.set_page_config(page_title="EcoArch FinOps Dashboard", page_icon="🌿", layout="wide")

# Connexion Supabase
@st.cache_resource
def init_supabase():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY")
    if not url or not key:
        st.error("❌ Les identifiants Supabase manquent (.env)")
        return None
    return create_client(url, key)

supabase = init_supabase()

# Titre
st.title("🌿 EcoArch FinOps Platform")
st.markdown("Suivi des coûts et de l'empreinte financière de l'infrastructure Cloud.")

if supabase:
    # 1. Récupération des données
    response = supabase.table("cost_history").select("*").order("created_at", desc=True).execute()
    df = pd.DataFrame(response.data)

    if not df.empty:
        # Conversion date
        df['created_at'] = pd.to_datetime(df['created_at'])

        # --- KPI CARDS ---
        col1, col2, col3 = st.columns(3)
        
        last_run = df.iloc[0]
        prev_run = df.iloc[1] if len(df) > 1 else last_run

        with col1:
            st.metric(label="💰 Coût Mensuel Actuel", 
                      value=f"{last_run['total_monthly_cost']} $",
                      delta=f"{last_run['total_monthly_cost'] - prev_run['total_monthly_cost']:.2f} $",
                      delta_color="inverse") # Inverse car + de coût c'est mauvais

        with col2:
            budget_limit = last_run['budget_limit']
            usage_percent = (last_run['total_monthly_cost'] / budget_limit) * 100
            st.metric(label="📉 Utilisation Budget", 
                      value=f"{usage_percent:.1f} %",
                      help=f"Budget Max: {budget_limit} $")

        with col3:
            status = "✅ OK" if last_run['status'] == 'PASSED' else "❌ DANGER"
            st.metric(label="Statut Dernier Pipeline", value=status)

        # --- GRAPHIQUES ---
        st.divider()
        
        c1, c2 = st.columns([2, 1])

        with c1:
            st.subheader("Evolution du Coût Mensuel")
            st.line_chart(df.set_index("created_at")["total_monthly_cost"], color="#15803d")

        with c2:
            st.subheader("Derniers Runs")
            st.dataframe(df[['created_at', 'branch_name', 'total_monthly_cost', 'status']].head(10), hide_index=True)

    else:
        st.info("Aucune donnée dans Supabase pour le moment.")