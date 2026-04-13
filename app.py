"""
app.py — AI Constitutional Intelligence System
Run with: streamlit run app.py
"""

import streamlit as st
from backend import run_search, get_all_articles

# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Constitutional AI | India",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
# CUSTOM CSS
# ─────────────────────────────────────────────
st.markdown("""
<style>
    /* Main background */
    .main { background-color: #f8f6f0; }
    .block-container { padding-top: 2rem; }

    /* Header */
    .header-box {
        background: linear-gradient(135deg, #1a237e 0%, #283593 60%, #1565c0 100%);
        color: white;
        padding: 2rem 2.5rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
    }
    .header-box h1 { color: white; margin: 0; font-size: 1.8rem; }
    .header-box p  { color: #c5cae9; margin: 0.3rem 0 0; font-size: 0.95rem; }

    /* Article result card */
    .result-card {
        background: white;
        border-left: 5px solid #1a237e;
        border-radius: 8px;
        padding: 1.2rem 1.5rem;
        margin-bottom: 1rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.07);
    }
    .result-card.second { border-left-color: #1565c0; }
    .result-card.third  { border-left-color: #42a5f5; }

    .article-badge {
        display: inline-block;
        background: #1a237e;
        color: white;
        padding: 0.2rem 0.7rem;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
        margin-bottom: 0.5rem;
    }
    .article-title {
        font-size: 1.15rem;
        font-weight: 700;
        color: #1a237e;
        margin: 0.3rem 0;
    }
    .relevance-bar {
        font-size: 0.82rem;
        color: #555;
        margin: 0.3rem 0 0.7rem;
    }
    .legal-text {
        background: #f5f5f5;
        border-left: 3px solid #bbb;
        padding: 0.7rem 1rem;
        font-style: italic;
        font-size: 0.88rem;
        color: #444;
        border-radius: 4px;
        margin: 0.5rem 0;
    }
    .explanation-box {
        background: #e8f5e9;
        border-radius: 6px;
        padding: 0.8rem 1rem;
        font-size: 0.92rem;
        color: #1b5e20;
        margin-top: 0.6rem;
    }
    .keyword-tag {
        display: inline-block;
        background: #e3f2fd;
        color: #0d47a1;
        padding: 0.15rem 0.5rem;
        border-radius: 12px;
        font-size: 0.75rem;
        margin: 0.15rem;
    }

    /* Sidebar */
    .sidebar-title { font-weight: 700; font-size: 1rem; color: #1a237e; margin-bottom: 0.5rem; }

    /* Query examples */
    .example-query {
        background: #ede7f6;
        color: #4527a0;
        padding: 0.4rem 0.8rem;
        border-radius: 6px;
        font-size: 0.85rem;
        margin: 0.3rem 0;
        cursor: pointer;
    }

    /* No result */
    .no-result {
        background: #fff3e0;
        border-radius: 8px;
        padding: 1.2rem;
        color: #e65100;
        font-size: 0.95rem;
    }

    /* Stats */
    .stat-box {
        background: white;
        border-radius: 8px;
        padding: 0.8rem 1rem;
        text-align: center;
        box-shadow: 0 1px 4px rgba(0,0,0,0.08);
    }
    .stat-number { font-size: 1.8rem; font-weight: 700; color: #1a237e; }
    .stat-label  { font-size: 0.78rem; color: #888; }

    /* Browse table */
    .browse-row {
        background: white;
        border-radius: 6px;
        padding: 0.7rem 1rem;
        margin: 0.4rem 0;
        border-left: 4px solid #90caf9;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚖️ Constitutional AI")
    st.markdown("---")

    st.markdown("**🔍 Try these queries:**")
    example_queries = [
        "Is Article 21 violated by illegal detention?",
        "Can the government deny me freedom of speech?",
        "What are my rights if I am arrested?",
        "Child labour in factories is happening",
        "Religious discrimination in government job",
        "Right to free education for children",
        "Human trafficking and bonded labour",
        "Writ petition in Supreme Court",
        "Uniform civil code for all religions",
        "Environment protection duty of citizens",
    ]

    for eq in example_queries:
        if st.button(eq, key=f"btn_{eq}", use_container_width=True):
            st.session_state["query_input"] = eq

    st.markdown("---")
    st.markdown("**⚙️ Settings**")
    top_k = st.slider("Results to show", min_value=1, max_value=5, value=3)
    show_legal_text = st.checkbox("Show original legal text", value=True)
    show_keywords = st.checkbox("Show matched keywords", value=True)

    st.markdown("---")
    st.markdown("""
    <div style='font-size:0.78rem; color:#888;'>
    Built with Python + Streamlit<br>
    TF-IDF based constitutional search<br>
    20 articles from Indian Constitution
    </div>
    """, unsafe_allow_html=True)

# ─────────────────────────────────────────────
# MAIN PAGE
# ─────────────────────────────────────────────

# Header
st.markdown("""
<div class="header-box">
    <h1>⚖️ AI Constitutional Intelligence System</h1>
    <p>Governance & Legal Decision Support · Indian Constitution · Powered by NLP Search</p>
</div>
""", unsafe_allow_html=True)

# Stats row
all_articles = get_all_articles()
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.markdown('<div class="stat-box"><div class="stat-number">20</div><div class="stat-label">Constitutional Articles</div></div>', unsafe_allow_html=True)
with col2:
    st.markdown('<div class="stat-box"><div class="stat-number">TF-IDF</div><div class="stat-label">NLP Engine</div></div>', unsafe_allow_html=True)
with col3:
    st.markdown('<div class="stat-box"><div class="stat-number">III</div><div class="stat-label">Fundamental Rights</div></div>', unsafe_allow_html=True)
with col4:
    st.markdown('<div class="stat-box"><div class="stat-number">⚡ Fast</div><div class="stat-label">Instant Results</div></div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# TABS
# ─────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["🔍 Query Search", "📚 Browse Articles", "ℹ️ About System"])

# ════════════════════════════════════════════
# TAB 1: SEARCH
# ════════════════════════════════════════════
with tab1:
    st.markdown("### Enter your legal query")
    st.markdown("Ask anything related to constitutional rights, government duties, arrest, discrimination, etc.")

    # Query input
    default_val = st.session_state.get("query_input", "")
    query = st.text_area(
        label="Legal Query",
        value=default_val,
        placeholder='e.g., "Is it legal for police to arrest someone without telling them the reason?"',
        height=80,
        key="main_query",
        label_visibility="collapsed",
    )

    col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 4])
    with col_btn1:
        search_clicked = st.button("🔍 Search", type="primary", use_container_width=True)
    with col_btn2:
        clear_clicked = st.button("✖ Clear", use_container_width=True)

    if clear_clicked:
        st.session_state["query_input"] = ""
        st.rerun()

    st.markdown("---")

    # Run search
    if search_clicked and query.strip():
        with st.spinner("Searching constitutional database..."):
            results = run_search(query.strip(), top_k=top_k)

        if not results:
            st.markdown("""
            <div class="no-result">
            ⚠️ No relevant articles found. Try different keywords like:
            <br>• <em>arrest, detention, freedom, equality, religion, education, labour, rights</em>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"**Found {len(results)} relevant article(s) for:** *\"{query}\"*")
            st.markdown("<br>", unsafe_allow_html=True)

            card_classes = ["result-card", "result-card second", "result-card third"]

            for i, res in enumerate(results):
                card_class = card_classes[i] if i < 3 else "result-card third"

                # Score bar
                score_pct = min(int(res["score"] * 100 / 0.5 * 100), 100)
                score_bar_color = "#1a237e" if i == 0 else ("#1565c0" if i == 1 else "#42a5f5")

                with st.container():
                    st.markdown(f'<div class="{card_class}">', unsafe_allow_html=True)

                    # Article badge + title
                    st.markdown(f"""
                    <span class="article-badge">{res['article']}</span>
                    <div class="article-title">{res['title']}</div>
                    <div class="relevance-bar">
                        {res['relevance']} &nbsp;|&nbsp; Match Score: {res['score']:.3f} &nbsp;|&nbsp; {res['match_reason']}
                    </div>
                    """, unsafe_allow_html=True)

                    # Score progress bar
                    st.progress(min(res["score"] / 0.6, 1.0))

                    # Legal text
                    if show_legal_text:
                        st.markdown(f'<div class="legal-text">📜 {res["text"]}</div>', unsafe_allow_html=True)

                    # Simple explanation
                    st.markdown(f"""
                    <div class="explanation-box">
                    💡 <strong>Plain Language Explanation:</strong><br>{res['simple_explanation']}
                    </div>
                    """, unsafe_allow_html=True)

                    # Keywords
                    if show_keywords and res["keywords"]:
                        kw_html = " ".join(
                            f'<span class="keyword-tag">{kw}</span>'
                            for kw in res["keywords"][:10]
                        )
                        st.markdown(f"<br><strong>🏷️ Key Terms:</strong><br>{kw_html}", unsafe_allow_html=True)

                    st.markdown("</div>", unsafe_allow_html=True)
                    st.markdown("<br>", unsafe_allow_html=True)

    elif search_clicked and not query.strip():
        st.warning("Please enter a query before searching.")

    else:
        # Show intro when no search yet
        st.markdown("""
        <div style='background:white; border-radius:10px; padding:1.5rem; color:#555; box-shadow: 0 2px 6px rgba(0,0,0,0.05);'>
        <h4 style='color:#1a237e;'>How to use this system</h4>
        <ol>
            <li>Type your legal question or scenario in the box above</li>
            <li>Click <strong>Search</strong> or pick an example from the sidebar</li>
            <li>The AI finds the most relevant constitutional articles</li>
            <li>Each result shows the legal text + plain English explanation</li>
        </ol>
        <p style='color:#888; font-size:0.85rem; margin-top:1rem;'>
        💡 <strong>Tip:</strong> Use natural language — "Can police arrest me without reason?" works better than just "arrest".
        </p>
        </div>
        """, unsafe_allow_html=True)

# ════════════════════════════════════════════
# TAB 2: BROWSE
# ════════════════════════════════════════════
with tab2:
    st.markdown("### 📚 All Constitutional Articles in Database")
    st.markdown(f"Showing **{len(all_articles)}** articles from the Indian Constitution")
    st.markdown("---")

    search_filter = st.text_input("🔎 Filter articles", placeholder="Type to filter...")

    for art in all_articles:
        # Filter
        if search_filter:
            combined = (art["article"] + art["title"] + art["text"]).lower()
            if search_filter.lower() not in combined:
                continue

        with st.expander(f"**{art['article']}** — {art['title']}"):
            st.markdown(f"**Original Text:**")
            st.markdown(f"> {art['text']}")
            st.markdown(f"**Plain Explanation:** {art['simple_explanation']}")
            kw_html = " ".join(
                f'<span class="keyword-tag">{kw}</span>'
                for kw in art["keywords"][:12]
            )
            st.markdown(f"**Keywords:** {kw_html}", unsafe_allow_html=True)

# ════════════════════════════════════════════
# TAB 3: ABOUT
# ════════════════════════════════════════════
with tab3:
    st.markdown("### ℹ️ About This System")

    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown("""
        **What is this?**

        An AI-powered system that helps citizens and legal professionals quickly find relevant Indian constitutional articles for any legal query or scenario.

        **How it works (Technical):**
        1. User enters a natural language query
        2. The backend tokenizes and cleans the text
        3. TF-IDF vectors are computed for query and all articles
        4. Cosine similarity scores each article against the query
        5. Keyword bonus scoring improves precision
        6. Top results are returned with relevance scores

        **Tech Stack:**
        - Python 3.10+
        - Streamlit (UI)
        - scikit-learn style TF-IDF (custom implementation)
        - No external API or internet needed
        """)

    with col_b:
        st.markdown("""
        **Articles Covered:**

        | Part | Articles |
        |------|---------|
        | Part III (Fundamental Rights) | 12, 13, 14, 15, 16, 17, 19, 20, 21, 21A, 22, 23, 24, 25, 26, 32 |
        | Part IV (Directive Principles) | 39A, 44 |
        | Part IVA (Fundamental Duties) | 51A |
        | Part VI (High Courts) | 226 |

        **5 Test Queries (for demo):**
        1. "Can police detain me without reason?" → Art. 22, 21
        2. "My child is not getting free education" → Art. 21A
        3. "Discrimination based on caste in job" → Art. 16, 15
        4. "Religious conversion by force" → Art. 25
        5. "File a writ petition for rights" → Art. 32, 226
        """)

    st.markdown("---")
    st.markdown("""
    **📋 5-Line Viva/Demo Explanation:**

    > *"This system uses TF-IDF based NLP to match legal queries against a curated database of Indian constitutional articles.
    > When a user enters a scenario, the system tokenizes the query, computes cosine similarity against all article vectors,
    > and applies a keyword bonus for precision. The top matching articles are returned with their original legal text,
    > a plain-language explanation, and a relevance score. This can support governance, legal aid, and public awareness
    > by making the Constitution accessible to every citizen."*
    """)

    st.markdown("---")
    st.info("Built by: Your Name | Project: AI Constitutional Intelligence System | Technology: Python + Streamlit + TF-IDF NLP")
