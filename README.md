# ⚖️ AI Constitutional Intelligence System

AI-powered search engine for Indian Constitutional Articles.
Built with Python + Streamlit + TF-IDF NLP.

---

## 🚀 Setup (From Zero)

### Step 1 — Install Python
Make sure Python 3.9+ is installed:
```
python --version
```

### Step 2 — Install dependencies
```
pip install streamlit
```

### Step 3 — Run the app
```
cd constitutional_ai
streamlit run app.py
```

The app opens at: http://localhost:8501

---

## 📁 Folder Structure

```
constitutional_ai/
│
├── app.py           ← Main Streamlit UI
├── backend.py       ← TF-IDF search engine
├── requirements.txt ← Python dependencies
├── README.md        ← This file
└── data/
    └── articles.json ← 20 constitutional articles
```

---

## 🔍 5 Test Queries

| Query | Expected Articles |
|-------|-----------------|
| "Can police arrest me without telling me why?" | Art. 22, 21 |
| "My child is not getting free education" | Art. 21A |
| "Discrimination in government job based on caste" | Art. 16, 15 |
| "Religious conversion by force" | Art. 25 |
| "File a writ petition in Supreme Court" | Art. 32, 226 |

---

## 🎤 Demo Explanation (5 lines)

"This system uses TF-IDF NLP to match legal queries against Indian constitutional articles.
When a user enters a scenario, it tokenizes the query, computes cosine similarity against all article vectors,
and applies keyword bonus scoring for precision. Top matching articles are shown with legal text and plain explanations.
The system can support governance, legal aid, and public awareness by making the Constitution accessible to citizens."

---

## ⚙️ How the NLP Works

1. All 20 articles are pre-processed into TF-IDF vectors at startup
2. User query is tokenized (lowercase, stopwords removed)
3. Query vector is built using the same TF-IDF weights
4. Cosine similarity is computed between query and each article
5. Keyword bonus boosts articles with direct keyword matches
6. Top-k results ranked by final score are displayed

---

Built for: AI/ML Project Presentation
Tech: Python, Streamlit, Custom TF-IDF (no heavy ML dependencies)
