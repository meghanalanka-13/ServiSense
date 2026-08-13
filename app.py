# app.py
import streamlit as st
from config import APP_TITLE, APP_TAGLINE, COLOR_BG, COLOR_TEXT, COLOR_BORDER

st.set_page_config(
    page_title=f"{APP_TITLE} \u2014 Co-Repairs Analytics",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(f"""
<style>
    .stApp {{ background-color: {COLOR_BG}; }}
    h1, h2, h3 {{ color: {COLOR_TEXT}; font-weight: 600; }}

    [data-testid="stSidebar"] {{
        background-color: #0D0D0D;
        border-right: 1px solid #000000;
    }}
    [data-testid="stSidebar"] * {{ color: #F2F2F0 !important; }}
    [data-testid="stSidebar"] hr {{ border-color: #3A3A3A; }}
    [data-testid="stSidebar"] p, [data-testid="stSidebar"] label {{ color: #C9C9C6 !important; }}
    [data-testid="stSidebar"] h1 {{ color: #FFFFFF !important; }}
    [data-testid="stSidebar"] button {{
        background-color: #1A1A1A !important;
        border: 1px solid #3A3A3A !important;
        color: #F2F2F0 !important;
    }}
    [data-testid="stSidebar"] button:hover {{ border-color: #6B6B68 !important; }}

    /* Title-as-home-link and About-link: target by position within the
       sidebar's button elements (1st = title, 2nd = About), using plain
       CSS structural selectors -- no dependency on container(key=...) or
       any other newer-Streamlit-only feature, so this works identically
       across old and new Streamlit versions alike. */
    .st-key-home_link_btn button,
    .st-key-home_link_btn button p {{
        background: transparent !important;
        border: none !important;
        padding: 0 !important;
        font-size: 2.0rem !important;
        font-weight: 700 !important;
        color: #FFFFFF !important;
        text-align: left !important;
        box-shadow: none !important;
        justify-content: flex-start !important;
        white-space: nowrap !important;
    }}
    .st-key-home_link_btn button:hover {{
        color: #C9C9C6 !important;
    }}

    /* Nav item labels (Overview, Failure Risk, etc.) */
    [data-testid="stSidebar"] [data-testid="stRadioOption"] p {{
        font-size: 1.0rem !important;
    }}

    .st-key-about_link_btn button,
    .st-key-about_link_btn button p {{
        background: transparent !important;
        border: none !important;
        padding: 0 !important;
        font-size: 0.78rem !important;
        font-weight: 400 !important;
        color: #6B6B68 !important;
        text-decoration: underline !important;
        box-shadow: none !important;
        justify-content: flex-start !important;
    }}
    .st-key-about_link_btn button:hover {{
        color: #9C9A94 !important;
    }}
    [data-testid="stSidebar"] [data-testid="stCaptionContainer"]:nth-of-type(2),
    [data-testid="stSidebar"] [data-testid="stCaptionContainer"]:nth-of-type(2) p {{
        font-size: 0.78rem !important;
        font-weight: 400 !important;
    }}

    div[data-testid="stMetric"] {{ background: transparent; padding: 0; border: none; }}
    div[data-testid="stMetricLabel"] {{ color: #6B6B68; font-size: 0.85rem; }}
    hr {{ border-color: {COLOR_BORDER}; margin: 1.2rem 0; }}
    h1 {{ margin-top: 0 !important; padding-top: 0 !important; }}
    div[data-testid="stMainBlockContainer"] {{ padding-top: 4rem !important; }}
</style>
""", unsafe_allow_html=True)

# The "Trained on..." caption's font-size wasn't reliably overridden by
# CSS !important -- Streamlit's own emotion-cache styles appear to load
# after and win the cascade regardless. Setting the style directly via
# JS sidesteps that fight entirely (same reliable pattern already used
# for the footer spacer earlier in this file).
st.components.v1.html("""
<script>
(function fixCaptionSize() {
    const doc = window.parent.document;
    const captions = doc.querySelectorAll('[data-testid="stSidebar"] [data-testid="stCaptionContainer"] p');
    for (const p of captions) {
        if (p.textContent.includes('Trained on')) {
            p.style.fontSize = '0.78rem';
            p.style.fontWeight = '400';
            p.parentElement.style.fontSize = '0.78rem';
            return;
        }
    }
    setTimeout(fixCaptionSize, 150);
})();
</script>
""", height=0)

NAV_OPTIONS = [
    "Overview",
    "Failure Risk",
    "Inventory & Parts",
    "Preventive Maintenance",
    "Technician Support",
    "Customer Outreach",
    "Strategic Intelligence",
]

if "current_page" not in st.session_state:
    st.session_state.current_page = "Overview"
if "previous_page" not in st.session_state:
    st.session_state.previous_page = None
if "_last_nav_choice" not in st.session_state:
    st.session_state._last_nav_choice = "Overview"

# Title as a clickable "go home" link -- especially useful as an escape
# hatch from the About page, which has no nav radio option of its own.
# Note: this and normal sidebar navigation deliberately do NOT touch
# previous_page -- only Overview's specific "See these appliances" /
# "See inventory details" shortcut links set it, so the "Back" link on
# those destination pages only appears when it's actually meaningful
# (led there from a specific place), not on every ordinary navigation.
if st.sidebar.button(APP_TITLE, key="home_link_btn"):
    st.session_state.current_page = "Overview"
    st.session_state.previous_page = None
    st.session_state.nav_radio = "Overview"
    st.session_state._last_nav_choice = "Overview"
st.sidebar.caption(APP_TAGLINE)
st.sidebar.markdown("---")

nav_choice = st.sidebar.radio(
    "Navigate", NAV_OPTIONS, label_visibility="collapsed", key="nav_radio",
)

if nav_choice != st.session_state._last_nav_choice:
    st.session_state.current_page = nav_choice
    st.session_state.previous_page = None
    st.session_state._last_nav_choice = nav_choice

# Push the About/footer group down toward the bottom of the sidebar. A
# fixed-height spacer, not flexbox: an earlier flex-based attempt at
# true dynamic bottom-pinning produced unpredictable results (centered
# content instead of pinning it) that couldn't be fully explained even
# after investigation. This is less "perfect" (a fixed gap, not one
# that adapts to every possible viewport height) but far more
# predictable and low-risk.
st.sidebar.markdown('<div style="height: 6vh;"></div>', unsafe_allow_html=True)

# Footer area: About link styled as plain understated text, not a
# prominent button -- sits with the "trained on" caption, not shouting
# for attention.
st.sidebar.markdown("---")
if st.sidebar.button("About this tool", key="about_link_btn"):
    st.session_state.current_page = "About"
st.sidebar.caption("Trained on 200,000 synthetic appliances \u00b7 5.7 years of simulated history")

page = st.session_state.current_page

if page == "Overview":
    from app_pages import overview
    overview.show()
elif page == "Failure Risk":
    from app_pages import failure_risk
    failure_risk.show()
elif page == "Inventory & Parts":
    from app_pages import inventory
    inventory.show()
elif page == "Preventive Maintenance":
    from app_pages import preventive_maintenance
    preventive_maintenance.show()
elif page == "Technician Support":
    from app_pages import technician_support
    technician_support.show()
elif page == "Customer Outreach":
    from app_pages import outreach
    outreach.show()
elif page == "Strategic Intelligence":
    from app_pages import strategic_intelligence
    strategic_intelligence.show()
elif page == "About":
    from app_pages import about
    about.show()
