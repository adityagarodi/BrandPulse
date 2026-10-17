# BrandPulse: Sentiment Analysis of Social Media Data for Brand Monitoring

![Architecture](https://img.shields.io/badge/Architecture-Split%20Deployment-indigo.svg)
![Backend](https://img.shields.io/badge/Backend-Flask%20JSON%20API%20%28Render%29-blue.svg)
![Frontend](https://img.shields.io/badge/Frontend-Static%20HTML%2FCSS%2FJS%20%28Vercel%29-black.svg)
![NLP](https://img.shields.io/badge/NLP-VADER%20%26%20NLTK-purple.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

**BrandPulse** is a modern brand monitoring and social sentiment intelligence platform built with a **Split Deployment Architecture**:
- **Backend**: Pure Flask JSON REST API (no HTML rendering) ready for one-click deployment on **Render**.
- **Frontend**: Zero-build static Single Page Application (HTML, CSS, Vanilla JS, Bootstrap 5, Chart.js) ready for deployment on **Vercel** or any static host.
- **Communication**: The frontend connects to the backend using `fetch()` with CORS configured via `frontend/js/config.js`.

---

## 🏗️ Project Structure

```text
brandpulse/
├── backend/
│   ├── app.py                      # Flask JSON API routes & CORS configuration
│   ├── requirements.txt            # Python dependencies (gunicorn, flask-cors, nltk, etc.)
│   ├── Procfile                    # Render process entrypoint (web: gunicorn app:app)
│   ├── runtime.txt                 # Python runtime version (python-3.11.9)
│   ├── .env.example                # Template for environment variables & API tokens
│   ├── .env                        # Local environment settings
│   ├── services/
│   │   ├── __init__.py             # Clean module exports
│   │   ├── twitter_service.py      # Twitter API v2, rate limit handling, CSV/sample loaders
│   │   ├── preprocessing.py        # NLTK data auto-download, tokenization & lemmatization
│   │   ├── sentiment.py            # VADER polarity scoring & brand health metrics
│   │   └── charts.py               # Base64 WordCloud generation & visualization formatting
│   ├── data/
│   │   └── sample_tweets.csv       # Curated realistic multi-brand tweets
│   └── tests/
│       └── test_basic.py           # Pytest test suite for all backend REST endpoints
├── frontend/
│   ├── index.html                  # Single-page interface (search inputs + live dashboard)
│   ├── css/
│   │   └── style.css               # Modern dark theme design system
│   └── js/
│       ├── config.js               # API_BASE_URL configuration (single place to change)
│       └── app.js                  # Frontend logic: fetch API, charts, table, CSV export
├── .gitignore                      # Git ignore rules for Python, caches, and env files
└── README.md                       # Comprehensive project & deployment documentation
```

---

## ⚡ Backend REST API Endpoints

| Method | Endpoint | Description | Payload / Parameters |
|---|---|---|---|
| `GET` | `/health` | Health check endpoint | Returns `{"status":"ok", "service":"BrandPulse API"}` |
| `POST` | `/api/analyze/sample` | Runs analysis on sample data | JSON `{ "brand": "Apple", "count": 50, "threshold": 40 }` |
| `POST` | `/api/analyze/csv` | Multipart CSV file upload | FormData with `file` (CSV), optional `brand`, `count`, `threshold` |
| `POST` | `/api/analyze/live` | Live Twitter API v2 search | JSON `{ "keyword": "Tesla", "count": 50, "threshold": 40 }` |

### Unified Analysis Response Format
All `/api/analyze/*` endpoints return a single unified JSON response:
```json
{
  "summary": {
    "total_posts": 50,
    "positive_pct": 64.0,
    "neutral_pct": 18.0,
    "negative_pct": 18.0,
    "positive_count": 32,
    "neutral_count": 9,
    "negative_count": 9,
    "avg_compound": 0.4851,
    "brand_health": "Healthy",
    "health_badge_class": "success",
    "health_description": "Brand sentiment is overwhelmingly favorable and positive."
  },
  "alert": {
    "alert_triggered": false,
    "alert_threshold": 40.0,
    "alert_message": "Sentiment is within normal boundaries."
  },
  "distribution": {
    "labels": ["Positive", "Neutral", "Negative"],
    "counts": [32, 9, 9],
    "percentages": [64.0, 18.0, 18.0]
  },
  "daily_trend": {
    "dates": ["Oct 15", "Oct 16", "Oct 17"],
    "positive": [11, 13, 8],
    "neutral": [3, 4, 2],
    "negative": [2, 3, 4],
    "avg_compound": [0.52, 0.49, 0.44]
  },
  "top_keywords": [
    {"word": "camera", "count": 18},
    {"word": "battery", "count": 14}
  ],
  "wordclouds": {
    "positive": "data:image/png;base64,...",
    "negative": "data:image/png;base64,..."
  },
  "posts": [
    {
      "id": "sample-1",
      "text": "The battery life on the new iPhone 15 is phenomenal!",
      "cleaned_text": "battery life new iphone phenomenal",
      "sentiment": "Positive",
      "compound_score": 0.852,
      "pos_score": 0.65,
      "neu_score": 0.35,
      "neg_score": 0.0,
      "date": "2026-10-17"
    }
  ],
  "meta": {
    "brand": "Apple",
    "source": "Sample Dataset (Apple)",
    "count": 50,
    "timestamp": "2026-10-17 16:30:00 UTC"
  }
}
```

---

## 🚀 Local Development Setup

### 1. Run the Backend API
```bash
# Navigate to backend directory
cd backend

# Create & activate virtual environment
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start backend server
python app.py
```
The backend starts at: **`http://127.0.0.1:5000`**

### 2. Run the Frontend (Static)
You can open `frontend/index.html` directly in your browser, or serve it using any local HTTP server:
```bash
# Python 3 built-in HTTP server:
cd frontend
python -m http.server 5500
```
Open **`http://127.0.0.1:5500`** in your browser.
*(CORS is automatically pre-configured to allow requests from port 5500, 5000, 3000, and your custom FRONTEND_URL).*

---

## ☁️ Deployment Instructions

### Deploy Backend to Render (Free Web Service)
1. Push your repository to GitHub.
2. Log into [Render Dashboard](https://dashboard.render.com/) and click **New + &rarr; Web Service**.
3. Select your repository.
4. Set the following settings:
   - **Root Directory**: `backend`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
5. Add Environment Variables in the Render dashboard:
   - `TWITTER_BEARER_TOKEN`: *(Your Twitter v2 bearer token, if available)*
   - `FRONTEND_URL`: `https://your-brandpulse-frontend.vercel.app`
   - `PYTHON_VERSION`: `3.11.9`
6. Click **Create Web Service**. Your API will be live at `https://brandpulse-api.onrender.com`.

### Deploy Frontend to Vercel (Free Static Hosting)
1. In `frontend/js/config.js`, update `API_BASE_URL` with your live Render backend URL:
   ```javascript
   const API_BASE_URL = "https://brandpulse-api.onrender.com";
   ```
2. Log into [Vercel](https://vercel.com/) and click **Add New &rarr; Project**.
3. Select your GitHub repository.
4. In **Root Directory**, click edit and select **`frontend`**.
5. Leave Build Command and Output Directory as default (no build step needed).
6. Click **Deploy**. Your static single-page app is instantly live!

> [!TIP]
> **Render Free Tier Cold Starts**: Render free instances sleep after 15 minutes of inactivity. When a user triggers an analysis, BrandPulse automatically detects server wake-up times and displays a friendly notice: *"Waking up the server, this can take up to 60 seconds on first use."*

---

## 🧪 Testing

Run the automated backend test suite:
```bash
python -m pytest backend/tests/test_basic.py -v
```
All 4 endpoints (`/health`, `/api/analyze/sample`, `/api/analyze/csv`, `/api/analyze/live`) are validated automatically.
