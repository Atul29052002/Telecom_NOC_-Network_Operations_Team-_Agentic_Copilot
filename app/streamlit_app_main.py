from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.noc_ui import inject_theme, sidebar_status


APP_DIR = PROJECT_ROOT / "app"
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
inject_theme()

with st.sidebar:
    sidebar_status()
    st.markdown(
        '<div class="noc-eyebrow" style="margin:1.25rem .3rem .25rem;">Network operations</div>',
        unsafe_allow_html=True,
    )

pages = [
    st.Page(PAGE_1_PATH, title="Network Overview", icon=":material/dashboard:"),
    st.Page(PAGE_2_PATH, title="Root Cause Analysis", icon=":material/hub:"),
    st.Page(PAGE_3_PATH, title="Remediation", icon=":material/build:"),
    st.Page(PAGE_4_PATH, title="Auto Resolution", icon=":material/task_alt:"),
    st.Page(PAGE_5_PATH, title="Ticket Management", icon=":material/confirmation_number:"),
]

page = st.navigation(pages, position="sidebar", expanded=True)
page.run()
