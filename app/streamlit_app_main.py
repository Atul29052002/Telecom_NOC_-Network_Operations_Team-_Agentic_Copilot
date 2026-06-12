from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

APP_DIR = PROJECT_ROOT / "app"
DATA_DIR = PROJECT_ROOT / "data"
LOGO_DIR = APP_DIR / "logo"
PAGE_1_PATH = APP_DIR / "01_Telecom_dashboard.py"
PAGE_2_PATH = APP_DIR / "02_Root_cause_dashboard.py"
PAGE_3_PATH = APP_DIR / "03_Remediation_Dashboard.py"
PAGE_4_PATH = APP_DIR / "04_Auto_Resolution_Dashboard.py"
PAGE_5_PATH = APP_DIR / "05_Ticket_Management_Dashboard.py"

st.set_page_config(
    page_title="Telecom NOC Command Center",
    page_icon=":material/network_check:",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
      
      :root {
        --noc-navy: #0f172a;
        --noc-blue: #3b82f6;
        --noc-muted: #94a3b8;
        --noc-border: #334155;
        --noc-card: #1e293b;
      }
      html, body, [data-testid="stAppViewContainer"] {
        font-family: 'Inter', sans-serif;
      }
      .stApp {
        background-color: var(--noc-navy);
        background-image: radial-gradient(circle at 92% 8%, rgba(59, 130, 246, 0.12), transparent 30rem);
        color: #f8fafc;
      }
      .block-container {
        max-width: 1500px;
        padding-top: 1.6rem;
        padding-bottom: 2.5rem;
      }
      div[data-testid="stSidebar"] {
        background: #0b1324;
        border-right: 1px solid #1e293b;
      }
      div[data-testid="stSidebar"] * {
        color: #e2e8f0;
      }
      div[data-testid="stSidebarNav"] {
        background-color: transparent;
        padding-top: 1rem;
      }
      div[data-testid="stSidebarNav"] a {
        border-radius: 10px;
        margin: 0.18rem 0.55rem;
      }
      div[data-testid="stSidebarNav"] a:hover {
        background: rgba(96, 165, 250, 0.12);
      }
      div[data-testid="stSidebarNav"] a[aria-current="page"] {
        background: var(--noc-blue);
      }
      .sidebar-card {
        background: linear-gradient(145deg, rgba(37, 99, 235, 0.22), rgba(15, 23, 42, 0.3));
        border: 1px solid rgba(148, 163, 184, 0.2);
        border-radius: 14px;
        padding: 1rem;
        margin: 0.25rem 0.5rem 1rem;
      }
      header[data-testid="stHeader"] {
        background: rgba(15, 23, 42, 0.8);
        backdrop-filter: blur(10px);
      }
      .logo-img {
        filter: drop-shadow(0 0 5px rgba(59, 130, 246, 0.4));
        margin-bottom: 1rem;
      }
      .sidebar-footer {
        position: absolute;
        bottom: 20px;
        left: 20px;
        right: 20px;
      }
    </style>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    # Top Branding Logo
    logo1 = LOGO_DIR / "logo1.png"
    if logo1.exists():
        st.image(str(logo1), use_container_width=True)
    elif (LOGO_DIR / "logo1.jpg").exists():
        st.image(str(LOGO_DIR / "logo1.jpg"), use_container_width=True)

    st.markdown(
        """
        <div class="sidebar-card">
          <h3 style="margin:0; color:#f8fafc;">Telecom NOC Copilot</h3>
          <p style="margin:0.35rem 0 0; color:#cbd5e1; line-height:1.45;">
            Monitor alarms, investigate root causes, and coordinate incident response.
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # This pushes subsequent content (if any) or helps define bottom space
    # Bottom Partner/Secondary Logo
    logo2 = LOGO_DIR / "logo2.png"
    if logo2.exists():
        st.sidebar.image(str(logo2), width=100)
    elif (LOGO_DIR / "logo2.jpg").exists():
        st.sidebar.image(str(LOGO_DIR / "logo2.jpg"), width=100)

pages = [
    st.Page(page=PAGE_1_PATH, title="Network Overview", icon=":material/dashboard:"),
    st.Page(page=PAGE_2_PATH, title="Root Cause Analysis", icon=":material/hub:"),
    st.Page(page=PAGE_3_PATH, title="Remediation", icon=":material/build:"),
    st.Page(page=PAGE_4_PATH, title="Auto Resolution", icon=":material/task_alt:"),
    st.Page(page=PAGE_5_PATH, title="Ticket Management", icon=":material/confirmation_number:"),
]

page = st.navigation(pages, position="sidebar", expanded=True)
page.run()
