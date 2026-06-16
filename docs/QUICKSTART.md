# Quickstart Guide — GEE-LLM

Get GEE-LLM running locally in under 5 minutes.

---

## Step 1: Clone & Install

```bash
git clone https://github.com/AmanSharma000/gee-llm.git
cd gee-llm
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux / macOS
source .venv/bin/activate

pip install -r requirements.txt
```

---

## Step 2: Authenticate Google Earth Engine

```bash
earthengine authenticate
```

A browser window will open. Sign in with your Google account linked to your GEE project. Copy the authorization code back to the terminal.

> 💡 Don't have a GEE account? [Sign up here](https://earthengine.google.com) — it's free for research use.

---

## Step 3: Set Your API Key

Create the file `.streamlit/secrets.toml` in the project root:

```toml
COHERE_API_KEY = "your-cohere-api-key-here"
```

> Get a free Cohere key at [cohere.com](https://cohere.com). The free tier is sufficient for hundreds of queries.  
> Alternatively, use Groq (`GROQ_API_KEY`) or run fully offline with [Ollama](https://ollama.com).

---

## Step 4: Launch the App

```bash
streamlit run app.py
```

Open your browser at **[http://localhost:8501](http://localhost:8501)**.

---

## Step 5: Try Your First Query

Type a natural-language query into the search box and press **Run**:

| Example Query | What it does |
|---|---|
| `ndvi of delhi for 2023` | NDVI histogram for Delhi, Sentinel-2, 2023 |
| `compare ndvi of delhi vs mumbai for 2023` | Side-by-side NDVI comparison |
| `mndwi of west bengal for 2023` | Water extent mapping, Landsat-8 |
| `forest change in western ghats from 2015 to 2023` | NBR time-series, Landsat-8 |

---

## What Happens Under the Hood

1. Your query is matched against 51 GEE template scripts (TF-IDF).
2. The best-matching template is injected into the LLM prompt.
3. The LLM generates a GEE Python script.
4. The script runs in a local subprocess sandbox.
5. If it fails, the error is translated into a correction prompt and retried (up to 3×).
6. Results are validated for physical plausibility, then displayed.

---

## Next Steps

- 📖 **Full installation options**: [README.md](../README.md)
- 🗂️ **All inputs/outputs/options**: [docs/USER_GUIDE.md](USER_GUIDE.md)
- 🏗️ **Architecture deep-dive**: [docs/ARCHITECTURE.md](ARCHITECTURE.md)
- 🔁 **Reproduce paper results**: [reproduce/README_reproduce.md](../reproduce/README_reproduce.md)
