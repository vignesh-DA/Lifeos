
╔══════════════════════════════════════════════════════════════╗
║           LIFEOS — LEGENDARY BUILD PROMPT v1.0              ║
║        The Last-Minute Life Saver — Hackathon Edition       ║
╚══════════════════════════════════════════════════════════════╝

You are an expert full-stack AI engineer building LIFEOS —
a production-grade, award-winning hackathon project called
"The Last-Minute Life Saver" for the VIBE2SHIP hackathon.

This is NOT a simple to-do app or reminder chatbot.
This is an AUTONOMOUS AI LIFE OPERATING SYSTEM that thinks,
plans, adapts, and acts on behalf of the user.

════════════════════════════════════════════════
PRODUCT IDENTITY
════════════════════════════════════════════════

Name: LIFEOS — Your Personal Life Operating System
Tagline: "Don't manage your time. Let AI own it."
Target Users: Students, professionals, freelancers
Core Promise: Zero friction input → Fully autonomous life planning

════════════════════════════════════════════════
TECH STACK — NON NEGOTIABLE
════════════════════════════════════════════════

FRONTEND:
- HTML5 + CSS3 + Vanilla JavaScript
- Tailwind CSS (via CDN) for all styling
- Alpine.js (via CDN) for reactivity
- Chart.js (via CDN) for analytics charts
- FullCalendar.js (via CDN) for calendar view
- Web Speech API for voice input
- Dark mode first design
- Fully mobile responsive

BACKEND:
- Python 3.11+
- FastAPI (REST API framework)
- LangChain (AI agent orchestration)
- spaCy (NLP task extraction)
- scikit-learn (ML priority scoring)
- HuggingFace transformers (sentiment/mood)
- Gemini Pro API (LLM brain via Google AI Studio)
- python-dotenv (env management)
- motor (async MongoDB driver)
- uvicorn (ASGI server)

DATABASE:
- MongoDB Atlas (free tier)
- Collections: users, tasks, patterns, sessions, reviews

DEPLOYMENT:
- Backend: Railway.app
- Frontend: Vercel
- Domain: Namecheap (custom domain)
- Repo: GitHub

════════════════════════════════════════════════
FOLDER STRUCTURE — BUILD EXACTLY THIS
════════════════════════════════════════════════

LIFEOS/
│
├── frontend/
│   ├── index.html          ← Landing page (SaaS-grade hero)
│   ├── dashboard.html      ← Main user dashboard
│   ├── onboard.html        ← Brain dump onboarding
│   ├── calendar.html       ← FullCalendar week view
│   ├── insights.html       ← ML analytics & patterns
│   ├── crisis.html         ← Crisis mode (red UI)
│   ├── css/
│   │   └── styles.css      ← Custom Tailwind overrides
│   └── js/
│       ├── app.js          ← Core app logic + API calls
│       ├── voice.js        ← Web Speech API handler
│       ├── charts.js       ← Chart.js configurations
│       └── calendar.js     ← FullCalendar setup
│
├── backend/
│   ├── main.py             ← FastAPI app entry point
│   ├── config.py           ← Settings & env variables
│   ├── agent/
│   │   ├── life_agent.py   ← LangChain autonomous agent
│   │   └── tools.py        ← All agent tools
│   ├── nlp/
│   │   ├── brain_dump.py   ← spaCy NLP extractor
│   │   └── sentiment.py    ← Mood/sentiment analysis
│   ├── ml/
│   │   ├── priority.py     ← ML priority scoring model
│   │   └── patterns.py     ← Behavioral pattern ML
│   ├── routes/
│   │   ├── tasks.py        ← Task CRUD endpoints
│   │   ├── agent.py        ← Agent planning endpoints
│   │   ├── crisis.py       ← Crisis mode endpoints
│   │   └── insights.py     ← Analytics endpoints
│   └── db/
│       └── mongodb.py      ← Async MongoDB connection
│
├── requirements.txt
├── Procfile                ← Railway deployment
├── README.md               ← Professional documentation
├── .env.example            ← Environment template
└── .gitignore

════════════════════════════════════════════════
FEATURE 1 — BRAIN DUMP NLP ENGINE
════════════════════════════════════════════════

File: backend/nlp/brain_dump.py

The user types or speaks freely in any messy format.
Your NLP pipeline must extract structured tasks from chaos.

INPUT EXAMPLE:
"I'm so stressed, ML professor said submission is this week,
gotta call mom its her birthday, electricity bill overdue,
TCS interview coming up haven't prepared, rent by Sunday"

REQUIRED OUTPUT:
{
  "tasks": [
    {
      "title": "ML Assignment Submission",
      "deadline": "2026-06-27",
      "deadline_confidence": "high",
      "category": "academic",
      "urgency_score": 9.2,
      "estimated_hours": 3,
      "extracted_keywords": ["ML", "professor", "submission"]
    },
    {
      "title": "Call Mom — Birthday",
      "deadline": "2026-06-23",
      "deadline_confidence": "high",
      "category": "personal",
      "urgency_score": 10.0,
      "estimated_hours": 0.5,
      "extracted_keywords": ["mom", "birthday", "call"]
    },
    {
      "title": "Pay Electricity Bill",
      "deadline": "overdue",
      "deadline_confidence": "medium",
      "category": "finance",
      "urgency_score": 10.0,
      "estimated_hours": 0.25,
      "extracted_keywords": ["electricity", "bill", "overdue"]
    },
    {
      "title": "TCS Interview Preparation",
      "deadline": "unknown",
      "deadline_confidence": "low",
      "category": "career",
      "urgency_score": 8.0,
      "estimated_hours": 8,
      "extracted_keywords": ["TCS", "interview", "prepared"]
    },
    {
      "title": "Pay Rent",
      "deadline": "2026-06-29",
      "deadline_confidence": "high",
      "category": "finance",
      "urgency_score": 7.5,
      "estimated_hours": 0.25,
      "extracted_keywords": ["rent", "Sunday"]
    }
  ],
  "summary": "5 tasks extracted. 2 finance items, 1 academic, 1 career, 1 personal.",
  "stress_level": "high",
  "immediate_action_required": ["Call Mom — Birthday", "Pay Electricity Bill"]
}

IMPLEMENTATION REQUIREMENTS:
- Use spaCy en_core_web_sm model
- Custom NER for deadline detection (today/tomorrow/Sunday/Friday etc)
- Keyword-based category classification
- Urgency scoring algorithm:
  urgency = (deadline_proximity * 0.4) + (consequence_weight * 0.3)
            + (frequency_of_mention * 0.2) + (overdue_flag * 0.1)
- Handle ambiguous deadlines with confidence scoring
- Detect "overdue" language patterns

════════════════════════════════════════════════
FEATURE 2 — LANGCHAIN LIFE AGENT
════════════════════════════════════════════════

File: backend/agent/life_agent.py + tools.py

This is the autonomous brain of LIFEOS.
The agent must make decisions WITHOUT asking the user.
It uses Gemini Pro as the LLM with LangChain orchestration.

AGENT TOOLS — implement all of these:

Tool 1: brain_dump_nlp(text: str) -> dict
  Extracts tasks from messy user input using spaCy

Tool 2: priority_scorer(tasks: list) -> list
  ML model scores each task 0-10 urgency
  Returns tasks sorted by priority

Tool 3: schedule_builder(tasks: list, available_hours: dict) -> dict
  Builds optimal daily schedule
  Assigns tasks to specific time slots
  Considers user's peak productivity hours
  Returns: {"monday": [...], "tuesday": [...], ...}

Tool 4: conflict_detector(schedule: dict) -> list
  Finds overlapping commitments
  Returns list of conflicts with suggestions

Tool 5: crisis_activator(task: dict, minutes_available: int) -> dict
  Emergency battle plan generator
  Returns step-by-step micro-plan
  Includes AI assistance at each step

Tool 6: procrastination_tracker(user_id: str) -> dict
  Analyzes postponement patterns from MongoDB
  Returns behavioral insights and triggers

Tool 7: email_drafter(task: dict, reason: str) -> str
  Drafts professional extension request email
  Uses Gemini Pro for natural language generation

Tool 8: weekly_review_gen(user_id: str, week: str) -> dict
  Generates comprehensive weekly life review
  Includes productivity score, patterns, next week plan

Tool 9: break_task_into_steps(task: dict) -> list
  Breaks big tasks into 25-minute micro-tasks
  Returns ordered step list with time estimates

Tool 10: mood_aware_scheduler(mood: str, tasks: list) -> dict
  Adjusts daily plan based on user's current energy
  tired → easier tasks first
  energized → hardest tasks first
  stressed → micro-tasks + breaks

AGENT SYSTEM PROMPT:
"""
You are LIFEOS, an autonomous AI life operating system.
You are the user's personal Chief of Staff.
Your job is NOT to ask questions — your job is to ACT.

When a user gives you any input:
1. Extract all tasks using brain_dump_nlp tool
2. Score priorities using priority_scorer tool
3. Build today's schedule using schedule_builder tool
4. Check for conflicts using conflict_detector tool
5. Return a complete, actionable life plan

You are proactive, not reactive.
You make decisions. You build plans. You take action.
You adapt when things change without being asked.

Tone: Supportive, direct, like a brilliant friend who
      happens to be a world-class life coach.
"""

AGENT MEMORY:
- Use LangChain ConversationBufferWindowMemory
- Store last 10 conversation turns
- Persist memory to MongoDB per user session
- Agent must remember context across page refreshes

════════════════════════════════════════════════
FEATURE 3 — ML PRIORITY SCORING
════════════════════════════════════════════════

File: backend/ml/priority.py

Build a scikit-learn ML model that scores task urgency.

FEATURE VECTOR FOR EACH TASK:
[
  deadline_hours_remaining,    # hours until deadline
  category_encoded,            # 0=personal, 1=academic, 2=career, 3=finance
  estimated_hours,             # effort required
  postpone_count,              # times user has postponed this
  time_of_day,                 # current hour (0-23)
  user_peak_hour_match,        # 1 if current time = user's peak hour
  overdue_flag,                # 1 if already past deadline
  consequence_weight,          # 1=low, 2=medium, 3=high stakes
]

OUTPUT: priority_score (float 0.0 to 10.0)

TRAINING:
- Generate synthetic training data (500 samples)
- Use RandomForestRegressor or GradientBoostingRegressor
- Save model as priority_model.pkl
- Load on FastAPI startup
- Retrain weekly as real user data accumulates

════════════════════════════════════════════════
FEATURE 4 — CRISIS MODE
════════════════════════════════════════════════

File: backend/routes/crisis.py + frontend/crisis.html

TRIGGER: User clicks red "CRISIS MODE" button OR
         says "I'm dead", "help", "emergency" etc.

BACKEND LOGIC:
async def activate_crisis(task_id: str, minutes_available: int):
  task = await get_task(task_id)
  
  steps = generate_crisis_plan(task, minutes_available)
  # Use Gemini Pro to generate personalized steps
  # Each step has: title, duration_minutes, ai_help_available
  
  return {
    "crisis_plan": steps,
    "time_budget": minutes_available,
    "survival_probability": calculate_survival_score(task, minutes),
    "ai_assistance_url": f"/crisis/{task_id}/assist"
  }

CRISIS PLAN EXAMPLE OUTPUT:
{
  "task": "ML Assignment",
  "time_available": 120,
  "survival_probability": 78,
  "steps": [
    {
      "step": 1,
      "title": "Read and understand the question",
      "duration": 15,
      "ai_help": "Paste question here and I'll give you key points to cover"
    },
    {
      "step": 2,
      "title": "Write answer outline",
      "duration": 10,
      "ai_help": "I'll generate an outline structure for you instantly"
    },
    {
      "step": 3,
      "title": "Complete main content",
      "duration": 60,
      "ai_help": "Send me any section you're stuck on"
    },
    {
      "step": 4,
      "title": "Review and format",
      "duration": 25,
      "ai_help": "I'll check your work for gaps"
    },
    {
      "step": 5,
      "title": "Submit with buffer",
      "duration": 10,
      "ai_help": null
    }
  ]
}

FRONTEND (crisis.html):
- Full screen red/dark takeover UI
- Giant countdown timer (MM:SS)
- Progress bar across top
- Each step shown as card
- "Get AI Help" button on each step
  → Opens chat with Gemini for that specific step
- Dramatic but functional design
- Pulse animation on timer when < 10 mins left

════════════════════════════════════════════════
FEATURE 5 — PROCRASTINATION PSYCHOLOGY ENGINE
════════════════════════════════════════════════

File: backend/ml/patterns.py

Track and analyze user's behavioral patterns over time.

DATA COLLECTED PER USER:
- Which tasks get postponed most
- Which categories they avoid
- What time of day they complete tasks
- How many days before deadline they start
- Completion rate by category
- Streak data (consecutive productive days)

INSIGHTS GENERATED:
{
  "user_id": "abc123",
  "week": "2026-W25",
  "patterns": {
    "most_avoided_category": "academic",
    "best_productivity_hour": 9,
    "worst_productivity_hour": 15,
    "avg_procrastination_days": 2.3,
    "peak_day": "Wednesday",
    "completion_rate": 0.73,
    "procrastination_triggers": ["study", "assignment", "report"],
    "strongest_categories": ["finance", "personal"]
  },
  "recommendations": [
    "Schedule academic tasks before 11 AM — you finish them 3x faster",
    "You've postponed 'TCS Prep' 4 times — break it into 15-min sessions",
    "Your Wednesday productivity is 40% higher — front-load hard tasks"
  ],
  "intervention_needed": true,
  "intervention_message": "You've avoided academic tasks for 5 days. Let's fix that today."
}

════════════════════════════════════════════════
API ENDPOINTS — BUILD ALL OF THESE
════════════════════════════════════════════════

POST   /api/brain-dump
       Body: {"text": "raw messy user input"}
       Returns: extracted tasks array

POST   /api/agent/plan
       Body: {"user_id": "...", "context": "..."}
       Returns: complete daily/weekly plan

GET    /api/tasks/{user_id}
       Returns: all tasks sorted by priority_score

POST   /api/tasks
       Body: task object
       Returns: created task with AI-scored priority

PUT    /api/tasks/{task_id}
       Body: partial task update
       Returns: updated task

PUT    /api/tasks/{task_id}/complete
       Returns: updated streak + recalculated scores

DELETE /api/tasks/{task_id}
       Returns: confirmation

POST   /api/crisis/activate
       Body: {"task_id": "...", "minutes_available": 120}
       Returns: crisis battle plan

POST   /api/crisis/assist
       Body: {"task_id": "...", "step": 2, "question": "..."}
       Returns: AI assistance for specific step

GET    /api/insights/{user_id}
       Returns: patterns, ML insights, recommendations

POST   /api/review/generate
       Body: {"user_id": "...", "week": "2026-W25"}
       Returns: full weekly review report

POST   /api/email/draft
       Body: {"task": {...}, "reason": "..."}
       Returns: professional extension email text

GET    /api/user/{user_id}/streak
       Returns: current streak, best streak, badges

POST   /api/mood
       Body: {"user_id": "...", "mood": "tired|energized|stressed"}
       Returns: mood-adjusted schedule for today

════════════════════════════════════════════════
FRONTEND PAGES — BUILD ALL OF THESE
════════════════════════════════════════════════

PAGE 1: index.html (Landing Page)
Design: Premium SaaS landing page
Sections:
- Hero: "Stop managing time. Let AI own it."
  CTA button: "Dump Your Brain" → onboard.html
- How it works: 3 steps (Dump, Plan, Execute)
- Features grid: 6 feature cards with icons
- Testimonials: 3 fake student quotes
- Footer with GitHub link
Colors: Dark background #0F0F1A, Indigo #6366F1, Purple #8B5CF6

PAGE 2: onboard.html (Brain Dump)
Design: Full screen chat-like interface
Elements:
- Large textarea: "Tell me everything on your mind..."
- Microphone button (Web Speech API voice input)
- Submit button: "Let AI Figure It Out"
- Loading animation while NLP processes
- Results shown as beautiful task cards
- "Looks Good → Go to Dashboard" button
Colors: Same dark theme, focus on the input

PAGE 3: dashboard.html (Main Hub)
Design: Clean dark dashboard
Sections:
LEFT COLUMN:
- "Today's Mission" — top 3 priority tasks
  Each card shows: title, deadline countdown,
  priority badge, complete button
- "Crisis Mode" big red button (always visible)
- Quick add task button

RIGHT COLUMN:
- Productivity score ring chart (Chart.js doughnut)
- Current streak counter with flame emoji
- Mini calendar showing week overview
- "LIFEOS says..." — today's AI insight message

TOP BAR:
- User name, date, mood selector (😴😰🔥😕)
- Navigation links

PAGE 4: calendar.html (Calendar View)
- FullCalendar.js weekly view
- Tasks appear as color-coded events
- Red = urgent, Yellow = medium, Green = relaxed
- Click task → edit modal
- Drag to reschedule → API call to update

PAGE 5: insights.html (Analytics)
Charts (all Chart.js):
- Line chart: productivity score over 4 weeks
- Bar chart: tasks completed by category
- Heatmap-style grid: hour-by-hour productivity
- Donut: completion rate this week
- Procrastination patterns text insights
- Behavioral recommendations from ML model

PAGE 6: crisis.html (Crisis Mode)
- Full page dark red theme
- Giant MM:SS countdown timer
- Step cards with progress
- "Get AI Help" opens chat panel
- Pulse/heartbeat animation on timer

════════════════════════════════════════════════
DATABASE SCHEMA — MONGODB COLLECTIONS
════════════════════════════════════════════════

Collection: users
{
  _id: ObjectId,
  name: String,
  email: String,
  created_at: DateTime,
  productivity_score: Float (0-100),
  streak_days: Integer,
  best_streak: Integer,
  peak_hours: [Integer],
  procrastination_triggers: [String],
  mood_history: [{date, mood}],
  badges: [String]
}

Collection: tasks
{
  _id: ObjectId,
  user_id: ObjectId,
  title: String,
  description: String,
  category: "academic|career|finance|personal|health",
  priority_score: Float (0-10),
  urgency_score: Float (0-10),
  deadline: DateTime,
  deadline_confidence: "high|medium|low",
  estimated_hours: Float,
  actual_hours: Float,
  status: "pending|in_progress|completed|overdue|cancelled",
  postpone_count: Integer,
  created_at: DateTime,
  completed_at: DateTime,
  extracted_from: "brain_dump|manual|voice",
  ai_steps: [String],
  tags: [String]
}

Collection: patterns
{
  _id: ObjectId,
  user_id: ObjectId,
  week: String ("2026-W25"),
  completed_tasks: Integer,
  missed_tasks: Integer,
  postponed_tasks: Integer,
  productivity_score: Float,
  best_hour: Integer,
  worst_hour: Integer,
  most_avoided_category: String,
  completion_rate: Float,
  procrastination_score: Float,
  recommendations: [String],
  created_at: DateTime
}

Collection: sessions
{
  _id: ObjectId,
  user_id: ObjectId,
  conversation_history: [
    {role: "user|assistant", content: String, timestamp: DateTime}
  ],
  last_context: String,
  last_updated: DateTime
}

Collection: reviews
{
  _id: ObjectId,
  user_id: ObjectId,
  week: String,
  summary: String,
  score: Float,
  wins: [String],
  losses: [String],
  next_week_focus: String,
  generated_at: DateTime
}

════════════════════════════════════════════════
UI DESIGN SYSTEM — FOLLOW EXACTLY
════════════════════════════════════════════════

COLOR PALETTE:
--bg-primary: #0F0F1A       (main background)
--bg-surface: #1A1A2E       (cards, panels)
--bg-elevated: #252540      (hover states, elevated cards)
--accent-primary: #6366F1   (indigo — primary actions)
--accent-secondary: #8B5CF6 (purple — secondary)
--accent-crisis: #EF4444    (red — crisis, urgent)
--accent-success: #10B981   (green — completed, success)
--accent-warning: #F59E0B   (amber — warnings, medium priority)
--text-primary: #F8FAFC     (main text)
--text-secondary: #94A3B8   (muted text)
--text-tertiary: #64748B    (placeholder, hints)
--border: #2D2D4E           (card borders)

TYPOGRAPHY:
font-family: 'Inter', system-ui, sans-serif
Import from Google Fonts CDN

TAILWIND CLASSES TO USE HEAVILY:
- bg-[#0F0F1A], bg-[#1A1A2E]
- text-indigo-400, text-purple-400
- border-[#2D2D4E]
- rounded-xl, rounded-2xl
- backdrop-blur-sm (glassmorphism effect)
- bg-white/5 (transparent overlays)
- transition-all duration-300
- hover:bg-[#252540]
- shadow-lg shadow-indigo-500/10

COMPONENT PATTERNS:
Task Card:
<div class="bg-[#1A1A2E] border border-[#2D2D4E] rounded-xl p-4
            hover:border-indigo-500/50 transition-all duration-300">
  Priority badge (color = urgency level)
  Task title (text-white font-medium)
  Deadline countdown (text-red-400 if < 24hrs)
  Category tag (text-xs rounded-full)
  Complete button + Crisis button
</div>

ANIMATIONS TO ADD:
- Countdown timers update every second
- Priority badges pulse if overdue
- Dashboard stats count up on load
- Task cards slide in with staggered delay
- Crisis mode has heartbeat pulse animation
- Loading states with skeleton screens

════════════════════════════════════════════════
SPECIAL ENHANCEMENTS — THESE WIN THE HACKATHON
════════════════════════════════════════════════

ENHANCEMENT 1 — AMBIENT DEADLINE PRESSURE
Dashboard background color subtly shifts based on
closest deadline proximity:
7+ days → Normal dark #0F0F1A
3-7 days → Slight warm tint
1-3 days → Amber warning tint
< 24 hrs → Red danger mode
Implement via CSS custom property updated by JS

ENHANCEMENT 2 — MOOD-AWARE PLANNING
Top of dashboard has 4 mood buttons:
😴 Tired | 😰 Stressed | 🔥 Energized | 😕 Distracted

Clicking calls POST /api/mood
Agent restructures today's plan accordingly
Show before/after plan comparison briefly

ENHANCEMENT 3 — AI EXPLAINS ITS DECISIONS
Every scheduled task shows an "info" icon
Clicking reveals why AI prioritized it:
"Scheduled first because:
→ Deadline in 18 hours
→ You've postponed 3 times
→ Your peak hour starts now
→ Estimated 2 hours needed"

ENHANCEMENT 4 — VOICE BRAIN DUMP
Microphone button on onboard page
Uses Web Speech API (no external service needed)
Transcribes in real time while user speaks
Sends to brain-dump NLP when user stops talking
Works on Chrome/Edge/Safari mobile

ENHANCEMENT 5 — WEEKLY LIFE REVIEW (auto-generated)
Every Sunday at 8 PM (or on demand):
Auto-generates full weekly review
Beautiful formatted page with:
- Big productivity score with ring chart
- ✅ Wins this week (completed tasks)
- ❌ Misses this week (uncompleted)
- 🧠 Pattern detected (ML insight)
- 🎯 Focus area next week (AI recommendation)
- 🔥 Streak status

════════════════════════════════════════════════
REQUIREMENTS.TXT
════════════════════════════════════════════════

fastapi==0.111.0
uvicorn[standard]==0.29.0
python-dotenv==1.0.1
motor==3.4.0
langchain==0.2.5
langchain-google-genai==1.0.6
google-generativeai==0.7.2
spacy==3.7.5
scikit-learn==1.5.0
pandas==2.2.2
numpy==1.26.4
transformers==4.41.2
torch==2.3.0
httpx==0.27.0
pydantic==2.7.3

Download spaCy model:
python -m spacy download en_core_web_sm

════════════════════════════════════════════════
.ENV FILE TEMPLATE
════════════════════════════════════════════════

GEMINI_API_KEY=your_gemini_api_key_here
MONGODB_URI=mongodb+srv://user:pass@cluster.mongodb.net/lifeos
DATABASE_NAME=lifeos
SECRET_KEY=your_secret_key_here
ENVIRONMENT=development
FRONTEND_URL=http://localhost:3000

════════════════════════════════════════════════
MAIN.PY STRUCTURE
════════════════════════════════════════════════

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import tasks, agent, crisis, insights
from db.mongodb import connect_db

app = FastAPI(title="LIFEOS API", version="1.0.0")

app.add_middleware(CORSMiddleware, allow_origins=["*"],
                   allow_methods=["*"], allow_headers=["*"])

@app.on_event("startup")
async def startup():
    await connect_db()
    # Load ML models
    # Initialize LangChain agent
    # Download spaCy model if not exists

app.include_router(tasks.router, prefix="/api")
app.include_router(agent.router, prefix="/api")
app.include_router(crisis.router, prefix="/api")
app.include_router(insights.router, prefix="/api")

@app.get("/health")
async def health(): return {"status": "LIFEOS is alive 🚀"}

════════════════════════════════════════════════
EVALUATION CRITERIA — HOW TO SCORE 95+/100
════════════════════════════════════════════════

Problem Solving & Impact (20%):
→ Solves REAL problem millions face daily
→ Multi-persona coverage: students, professionals, freelancers
→ Measurable impact: "User missed 0 deadlines this week"

Agentic Depth (20%):
→ LangChain agent with 10 tools
→ Agent makes autonomous decisions
→ Multi-step reasoning chains
→ Memory across sessions
→ Adapts without user asking

Innovation & Creativity (20%):
→ Brain Dump NLP (nobody else has this UX)
→ Procrastination Psychology ML
→ Crisis Mode battle planner
→ Mood-aware scheduling
→ Ambient deadline pressure UI

Google Technologies (15%):
→ Gemini Pro API as LLM backbone
→ Google AI Studio for deployment
→ Gemini for email drafting
→ Gemini for crisis assistance

Product Experience (10%):
→ Dark glassmorphism UI
→ Mobile responsive
→ Smooth animations
→ Zero friction onboarding

Technical Implementation (10%):
→ FastAPI async backend
→ LangChain agents
→ spaCy NLP pipeline
→ scikit-learn ML models
→ MongoDB Atlas

Completeness (5%):
→ All 6 pages functional
→ All API endpoints working
→ Deployed with custom domain
→ README with demo video link

════════════════════════════════════════════════
7-DAY BUILD SCHEDULE
════════════════════════════════════════════════

DAY 1 (22 June):
→ Project structure setup
→ FastAPI running with health endpoint
→ MongoDB Atlas connected
→ Gemini API connected and tested
→ Landing page HTML with Tailwind (index.html)
→ Push everything to GitHub
MILESTONE: App opens, looks good, AI responds

DAY 2 (23 June):
→ Brain Dump NLP engine (brain_dump.py)
→ spaCy integration + task extraction
→ POST /api/brain-dump endpoint working
→ onboard.html with textarea + voice input
→ Task cards display extracted results
→ POST /api/tasks saving to MongoDB
MILESTONE: Type chaos → Get organized tasks

DAY 3 (24 June — MENTOR SESSION 4-6 PM):
→ LangChain agent setup (life_agent.py)
→ 5 core tools implemented
→ POST /api/agent/plan working
→ dashboard.html structure built
→ GET /api/tasks pulling from MongoDB
→ ATTEND MENTOR SESSION — ask about deployment
MILESTONE: Agent makes autonomous decisions

DAY 4 (25 June):
→ ML priority scoring model (priority.py)
→ Remaining agent tools
→ schedule_builder working
→ Dashboard fully functional
→ Countdown timers on task cards
→ Mood selector working
MILESTONE: Personalized daily plans generated

DAY 5 (26 June):
→ Crisis Mode (crisis.py + crisis.html)
→ Procrastination tracker (patterns.py)
→ Behavioral ML patterns
→ Weekly review generator
→ Insights page (insights.html)
→ All Chart.js graphs working
MILESTONE: All unique features complete

DAY 6 (27 June):
→ Calendar view (calendar.html + FullCalendar)
→ Ambient deadline pressure UI
→ AI explains decisions feature
→ Full end-to-end testing
→ Bug fixes
→ Polish all pages
→ Record demo video (5 minutes max)
MILESTONE: Smooth demo from start to finish

DAY 7 (28 June — Submit before 29th 2 PM):
→ Deploy backend to Railway
→ Deploy frontend to Vercel
→ Connect Namecheap custom domain
→ Final end-to-end test on deployed version
→ Write comprehensive README.md
→ Create Google Doc (project description)
→ Submit on BlockseBlock platform
MILESTONE: EVERYTHING SUBMITTED ✅

════════════════════════════════════════════════
README.MD MUST INCLUDE
════════════════════════════════════════════════

# LIFEOS — Your Personal Life Operating System

## 🏆 VIBE2SHIP Hackathon Submission
Problem Statement: The Last-Minute Life Saver

## 🎯 What It Does (in 30 seconds)
## 🚀 Live Demo
## 📸 Screenshots (6 screenshots)
## 🎥 Demo Video (YouTube link)
## ✨ Key Features
## 🧠 How the AI Works
## 🛠️ Tech Stack
## 🏗️ Architecture Diagram
## 📦 Installation & Setup
## 🔑 Environment Variables
## 📡 API Documentation
## 🗓️ Development Timeline
## 👤 Developer Info

════════════════════════════════════════════════
START BUILDING NOW
════════════════════════════════════════════════

When I say "Start", begin with Day 1 tasks:
1. Create the folder structure exactly as specified
2. Set up FastAPI with all route files (empty stubs OK)
3. Connect MongoDB Atlas
4. Create index.html with full landing page using Tailwind
5. Test Gemini API connection
6. Push to GitHub with proper .gitignore

Do not skip any file. Do not simplify the structure.
Build for production quality, not hackathon MVP.
Every feature should feel like a real product.

The judges should open this app and forget
it's a hackathon project. It should feel like
a funded startup's product.

so now use claude.md as the memory for what we implement and how much we far from the our goal.
so after each task i want you update claude.md to reflect the current state of the project.
and agent.md will let you know the functionalities of an agent for better undertanding ive already created an venv,.env,gitignore and .md  and requirements files 
first analyse the folder structure ive alreday create main folder and sub folders 
use two llm groq and gemini for the brain for this project we are using groq to overcome the ratelimiting of the gemini.

Ready. Let's build LIFEOS. 🚀