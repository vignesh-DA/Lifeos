# LIFEOS — Your Personal Life Operating System 🧠

## 🏆 VIBE2SHIP Hackathon Submission
**Problem Statement:** The Last-Minute Life Saver

> *"Don't manage your time. Let AI own it."*

## 🎯 What It Does (in 30 seconds)
LIFEOS is an **autonomous AI life operating system** that transforms chaotic brain dumps into perfectly organized life plans. Type or speak everything on your mind — assignments, bills, interviews — and watch 10 AI tools extract tasks, score priorities, build schedules, detect conflicts, and create your optimal day plan in seconds.

**Not a to-do app. An autonomous decision engine.**

## 🚀 Live Demo
> [Live URL will be added after deployment]

## 📸 Screenshots
> Screenshots will be added after UI is finalized.

## 🎥 Demo Video
> [YouTube link will be added]

## ✨ Key Features

| Feature | Description |
|---------|-------------|
| 🧠 **Brain Dump NLP** | Type chaos → Get structured tasks with spaCy NLP extraction |
| 📊 **ML Priority Scoring** | scikit-learn model analyzes 8 factors per task for true urgency |
| 🚨 **Crisis Mode** | Last-minute emergency? Get a step-by-step survival battle plan |
| 🎭 **Mood-Aware Planning** | Schedule dynamically restructures based on energy level |
| 🔍 **Procrastination AI** | ML detects your avoidance patterns and intervenes |
| 📈 **Weekly Life Review** | Auto-generated Sunday performance review with insights |
| 🗓️ **Smart Calendar** | FullCalendar with color-coded tasks and drag-to-reschedule |
| ✉️ **Email Drafter** | AI writes professional deadline extension emails |
| 🎙️ **Voice Input** | Web Speech API for hands-free brain dumps |
| ⏰ **Ambient Pressure** | Dashboard background shifts based on deadline proximity |

## 🧠 How the AI Works
LIFEOS uses a **LangChain autonomous agent** with 10 specialized tools:

```
User Input → Brain Dump NLP → Priority Scorer → Schedule Builder
                                    ↓
                        Conflict Detector → Mood Scheduler
                                    ↓
                         Complete Life Plan (3-5 seconds)
```

The agent uses **multi-step reasoning chains** — it doesn't just respond, it **thinks, decides, and acts** autonomously.

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | HTML5, Tailwind CSS (CDN), Alpine.js, Chart.js, FullCalendar.js |
| **Backend** | Python 3.11+, FastAPI, uvicorn |
| **AI/ML** | LangChain, Groq (Llama 3.1), Gemini Pro, spaCy, scikit-learn |
| **Database** | MongoDB Atlas (motor async driver) |
| **Deployment** | Railway (backend), Vercel (frontend) |

## 🏗️ Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────┐
│   Frontend       │────▶│   FastAPI Backend │────▶│ MongoDB Atlas│
│  (HTML/Tailwind) │     │                  │     └─────────────┘
└─────────────────┘     │  ┌────────────┐  │
                        │  │ LangChain  │  │     ┌─────────────┐
                        │  │   Agent    │──┼────▶│  Groq API   │
                        │  │ (10 tools) │  │     │  (Llama 3.1)│
                        │  └────────────┘  │     └─────────────┘
                        │  ┌────────────┐  │     ┌─────────────┐
                        │  │ spaCy NLP  │  │     │  Gemini Pro │
                        │  │ ML Models  │  │     │  (fallback) │
                        │  └────────────┘  │     └─────────────┘
                        └──────────────────┘
```

## 📦 Installation & Setup

```bash
# Clone the repository
git clone https://github.com/your-username/lifeos.git
cd lifeos

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Download spaCy model
python -m spacy download en_core_web_sm

# Set up environment variables
cp .env.example .env
# Edit .env with your API keys

# Run the backend
cd backend
uvicorn main:app --reload --port 8000

# Open frontend
# Open frontend/index.html in your browser
```

## 🔑 Environment Variables
```env
GEMINI_API_KEY=your_gemini_api_key
GROQ_API_KEY=your_groq_api_key
MONGODB_URI=your_mongodb_atlas_uri
DATABASE_NAME=lifeos
GROQ_MODEL=llama-3.1-70b-versatile
```

## 📡 API Documentation

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/brain-dump` | Extract tasks from messy text |
| POST | `/api/agent/plan` | Generate autonomous life plan |
| GET | `/api/tasks/{user_id}` | Get all user tasks |
| POST | `/api/tasks` | Create a task |
| PUT | `/api/tasks/{id}/complete` | Mark task complete |
| POST | `/api/crisis/activate` | Activate crisis mode |
| POST | `/api/crisis/assist` | Get AI help during crisis |
| GET | `/api/insights/{user_id}` | Get ML insights |
| POST | `/api/review/generate` | Generate weekly review |
| POST | `/api/mood` | Set mood & adjust schedule |
| POST | `/api/email/draft` | Draft extension email |
| GET | `/api/user/{id}/streak` | Get streak info |

## 🗓️ Development Timeline
- **Day 1-2:** Project structure, FastAPI, MongoDB, Landing page, Brain Dump NLP
- **Day 3:** LangChain agent with 5 core tools, Dashboard
- **Day 4:** ML priority scoring, remaining tools, mood scheduler
- **Day 5:** Crisis mode, procrastination tracker, insights page
- **Day 6:** Calendar, polish, end-to-end testing, demo video
- **Day 7:** Deploy, README, submit

## 👤 Developer Info
Built for the VIBE2SHIP Hackathon 2026.

---

*LIFEOS — Because your time is too valuable to manage manually.*
