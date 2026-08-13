# app_pages/technician_support.py
import streamlit as st
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from data_loader import load_repair_events, load_cross_dependency_results


@st.cache_resource(show_spinner="Indexing technician notes...")
def build_tfidf_index():
    events = load_repair_events()
    corpus = events["Technician_Notes"].fillna("").tolist()
    vectorizer = TfidfVectorizer(stop_words="english", max_features=5000)
    matrix = vectorizer.fit_transform(corpus)
    return vectorizer, matrix


def show():
    st.title("Technician Support")
    st.caption("Matched against real historical repair cases.")

    events = load_repair_events()
    vectorizer, matrix = build_tfidf_index()

    appliance_types = ["All"] + sorted(events["Appliance_Type"].unique().tolist())
    cities = ["All"] + sorted(events["City"].unique().tolist())
    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        query = st.text_input("What's the customer describing?",
                               placeholder="e.g. buzzing noise, not cooling properly")
    with col2:
        type_filter = st.selectbox("Appliance type", appliance_types)
    with col3:
        city_filter = st.selectbox("City", cities)

    if not query:
        st.info("Type a description above to search real historical repair cases.")
        return

    query_vec = vectorizer.transform([query])
    sims = cosine_similarity(query_vec, matrix).flatten()

    results = events.copy()
    results["similarity"] = sims
    if type_filter != "All":
        results = results[results["Appliance_Type"] == type_filter]
    if city_filter != "All":
        results = results[results["City"] == city_filter]
    results = results[results["similarity"] > 0.05].sort_values("similarity", ascending=False)

    if len(results) == 0:
        st.warning("No sufficiently similar historical cases found. Try rephrasing, or widening the filters.")
        return

    top_matches = results.head(30)

    st.markdown("---")
    st.subheader(f"Based on {len(top_matches)} similar historical cases")

    root_causes = top_matches["Root_Cause_Tag"].value_counts(normalize=True).head(3)
    parts = top_matches["Part_Category_Needed"].value_counts(normalize=True).head(4)
    resolutions = top_matches["Resolution_Status"].value_counts(normalize=True).head(3)

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.markdown("**Most likely root cause**")
        for cause, pct in root_causes.items():
            st.write(f"{cause}: {pct*100:.0f}%")
    with col_b:
        st.markdown("**Parts frequently involved**")
        for part, pct in parts.items():
            st.write(f"{part}: {pct*100:.0f}%")
    with col_c:
        st.markdown("**How these were typically resolved**", help=(
            "Fixed: resolved without replacing a part (cleaned, adjusted, reset). "
            "Part Replaced: a specific part was physically swapped. "
            "Temporary Fix: a stopgap, a permanent fix is still needed. "
            "Pending Follow-up: the needed part was out of stock at the time."
        ))
        for res, pct in resolutions.items():
            st.write(f"{res}: {pct*100:.0f}%")

    with st.expander("See the actual matched cases this is based on"):
        for _, row in top_matches.head(5).iterrows():
            st.markdown(f"*{row['Technician_Notes']}*")
            st.caption(f"{row['Appliance_Type']}")
            st.markdown("")

    st.markdown("---")
    st.subheader("What else to check")
    st.caption("If the top part above has a known cascade risk, it's worth checking these while you're already there.")

    top_part = parts.index[0] if len(parts) else None
    cross_deps = load_cross_dependency_results()
    relevant_type = type_filter if type_filter != "All" else top_matches.iloc[0]["Appliance_Type"]
    edges = cross_deps.get(relevant_type, [])
    matching = [e for e in edges if e["part_a"] == top_part or e["part_b"] == top_part]

    if not matching:
        st.write(f"No known cascade risk on record for {top_part} on {relevant_type}.")
    else:
        for e in matching:
            if e["part_a"] == top_part:
                headline = f"**{e['part_a']} failing raises the risk of {e['part_b']} issues next**"
            else:
                headline = f"**{e['part_b']} risk rises if {e['part_a']} has already failed on this appliance**"
            st.markdown(
                f"{headline}: {e['lift']}x more likely than baseline "
                f"({e['p_b_given_a_failed']*100:.0f}% vs {e['p_b_given_a_ok']*100:.0f}%)"
            )
            st.caption(e["mechanism"])
