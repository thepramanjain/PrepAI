# 🚀 PrepAI

### AI-Powered Mock Interview & Career Preparation Platform

> **Practice smarter. Interview better. Get hired.**

PrepAI is a full-stack AI-powered interview preparation platform that simulates realistic technical and behavioral interviews, evaluates candidate responses, tracks performance over time, and provides personalized career guidance.

Unlike a simple chatbot, PrepAI combines **Google Gemini, OpenRouter GPT-4o, LangGraph, LiveKit, FastAPI, MongoDB, and a modern React frontend** to create a complete AI interview ecosystem.

---

## ✨ What is PrepAI?

Preparing for interviews often means jumping between question banks, coding platforms, resume reviewers, mock interview tools, and performance trackers.

**PrepAI brings everything into one platform.**

It can:

- 🎯 Generate role-specific interview questions
- 📄 Analyze resumes and tailor questions accordingly
- 💬 Conduct interactive text interviews
- 🎙️ Conduct real-time voice interviews
- 🧠 Evaluate candidate answers using AI
- 📊 Track interview performance over time
- 🔍 Identify strengths and recurring weaknesses
- 🤖 Use Agentic AI to reason over interview data
- 🧑💼 Provide personalized career coaching
- 📈 Recommend areas for improvement

The goal is simple:

> **Turn every mock interview into measurable progress.**

---

# 🌟 Key Features

| Feature | Description |
|---|---|
| 🔐 Authentication | Secure registration, login and JWT-based authentication |
| 📄 Resume Intelligence | Upload and parse resumes to personalize interviews |
| 🎯 AI Question Generation | Generate role, skill and difficulty-specific questions |
| 💬 Text Interviews | Conduct realistic interactive mock interviews |
| 🎙️ Voice Interviews | Real-time AI voice interviews using LiveKit |
| 🧠 AI Evaluation | Analyze answers and generate detailed feedback |
| 📊 Performance Analytics | Track scores, topics, strengths and weaknesses |
| 🤖 Agentic AI | LangGraph-powered intelligent workflow |
| 🧑💼 AI Career Coach | Personalized improvement recommendations |
| 🔄 Adaptive Interviews | Context-aware follow-up questions |
| 📈 Progress Tracking | Compare interview performance over time |
| 📱 Responsive UI | Modern interface designed for desktop and mobile |

---

# 🧠 AI Architecture

PrepAI uses a **hybrid multi-model architecture** instead of relying on a single AI model for everything.

### Google Gemini

Used for interview-specific intelligence:

- Question generation
- Contextual follow-up questions
- Interview evaluation
- Voice interview intelligence

### OpenRouter + GPT-4o

Used for the Agentic AI layer:

- Intent understanding
- Tool calling
- Agent orchestration
- Career coaching
- Reasoning over existing interview data

### LangGraph

Acts as the orchestration layer that connects specialized agents and tools.

### Python + MongoDB

Handles deterministic operations such as:

- Analytics
- Score calculations
- Filtering
- Aggregation
- Interview history
- Persistent data

### LiveKit

Provides the real-time communication layer for voice interviews.

---

# 🏗️ System Architecture

```text
                         ┌─────────────────────┐
                         │       USER          │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │   React + Vite      │
                         │     Frontend        │
                         └──────────┬──────────┘
                                    │
                              REST API
                                    │
                                    ▼
                     ┌───────────────────────────┐
                     │       FastAPI Backend     │
                     │                           │
                     │  Authentication           │
                     │  Interview Management     │
                     │  Resume Processing        │
                     │  AI Services              │
                     │  Agentic AI               │
                     └─────────────┬─────────────┘
                                   │
              ┌────────────────────┼────────────────────┐
              │                    │                    │
              ▼                    ▼                    ▼
        ┌───────────┐       ┌────────────┐      ┌─────────────┐
        │ MongoDB   │       │  Gemini    │      │ LangGraph   │
        │           │       │    AI      │      │             │
        └───────────┘       └────────────┘      └──────┬──────┘
                                                       │
                                                       ▼
                                                ┌─────────────┐
                                                │ OpenRouter  │
                                                │   GPT-4o    │
                                                └─────────────┘


                    VOICE INTERVIEW PIPELINE

       Candidate Microphone
                │
                ▼
          ┌──────────┐
          │ LiveKit  │
          └────┬─────┘
               │
               ▼
        ┌──────────────┐
        │ Voice Agent  │
        │   Python     │
        └──────┬───────┘
               │
               ▼
            Gemini
               │
               ▼
        AI Voice Response
```

## 🤖 Agentic AI Architecture

The Agentic AI layer is powered by LangGraph + OpenRouter GPT-4o.

Instead of allowing an LLM to directly access the database or execute arbitrary operations, PrepAI provides controlled tools.

```text
                         USER
                           │
                           ▼
                    ┌─────────────┐
                    │ GPT-4o      │
                    │ Orchestrator│
                    └──────┬──────┘
                           │
                ┌──────────┼──────────┐
                │          │          │
                ▼          ▼          ▼
          Question      Interview   Evaluation
            Tool          Tool         Tool
                │          │          │
                └──────────┼──────────┘
                           │
                           ▼
                       Analytics
                          Tools
                           │
                           ▼
                     Career Coach
                           │
                           ▼
                     Final Response
```

### Specialized capabilities

**🎯 Interview Agent**
Handles interview flow, questions and contextual follow-ups.

**🧠 Evaluation Agent**
Works with the existing evaluation engine to analyze completed interviews.

**📊 Analyst**
Retrieves deterministic performance analytics from MongoDB.

**🧑💼 Career Coach**
Combines interview feedback, weaknesses, topic performance and historical trends to generate personalized improvement advice.

**🎛️ Orchestrator**
Determines which tools and workflow should be used for a user's request.

---

# 🔄 Complete Interview Flow

### 1. Create Interview
```
User
 ↓
Select Role
 ↓
Select Experience
 ↓
Select Skills
 ↓
Select Interview Type
 ↓
Select Difficulty
 ↓
Optional Resume
 ↓
Optional Job Description
```

### 2. AI Question Generation
```
Interview Configuration
          ↓
       Gemini
          ↓
Role-specific Questions
          ↓
MongoDB
```
Questions can be tailored using:
- Role
- Experience
- Skills
- Difficulty
- Interview type
- Resume
- Job description

### 3. Text Interview
```
AI Question
     ↓
Candidate Answer
     ↓
Store Response
     ↓
Analyze Context
     ↓
Follow-up OR Next Question
     ↓
Repeat
```

### 4. Voice Interview
```
Candidate
    │
    ▼
Microphone
    │
    ▼
  LiveKit
    │
    ▼
Voice Agent
    │
    ▼
  Gemini
    │
    ▼
AI Voice Response
```
The voice interview maintains the same underlying interview state as the text interview.

### 5. AI Evaluation
After the interview:
```
Questions + Answers
        ↓
Gemini Evaluator
        ↓
Structured Evaluation
        ↓
MongoDB
```
The system evaluates:
- Technical knowledge
- Communication
- Problem solving
- Answer relevance
- Question-level performance
- Strengths
- Weaknesses
- Topic performance
- Improvement recommendations

---

# 📊 Performance Analytics

PrepAI calculates analytics from stored interview data.

It tracks:
- **Overall Performance:** Average score, Best score, Lowest score, Latest score
- **Total interviews:** Completed interviews
- **Performance Trends:** Score progression, Category performance, Topic performance, Difficulty performance, Role performance, Interview type performance

### Growth Analysis
PrepAI compares historical performance to determine whether the candidate is:
- 📈 Improving
- ➡️ Stable
- 📉 Declining

No LLM is required for basic statistical calculations.

---

# 🧑💼 AI Career Coach

The Career Coach is powered by the Agentic AI layer.
Instead of giving generic advice, it reasons over the candidate's actual performance.

For example:
**User:** What should I improve?
```
GPT-4o
   ↓
get_analytics()
   ↓
get_weaknesses()
   ↓
get_topic_performance()
   ↓
LangGraph
   ↓
Career Coach
```
The system can respond with:
- Key strengths
- Priority weaknesses
- Topics to practice
- Personalized recommendations
- Action plan
- Interview preparation strategy

---

# 🛠️ Technology Stack

### 🎨 Frontend
- React
- Vite
- TypeScript
- Tailwind CSS
- shadcn/ui
- React Router
- Axios
- TanStack Query
- Recharts
- Framer Motion
- Lucide React
- React Hook Form
- Zod

### ⚙️ Backend
- Python
- FastAPI
- Pydantic
- PyMongo / Motor
- JWT Authentication
- bcrypt / Passlib

### 🧠 AI & Agentic Layer
**Google Gemini**
Used for:
- Question generation
- Follow-up questions
- Interview intelligence
- AI evaluation
- Voice interview intelligence

**OpenRouter**
Used as the LLM gateway for:
- GPT-4o
- Agentic reasoning
- Tool calling

**LangGraph**
Used for:
- Agent orchestration
- Stateful workflows
- Conditional routing
- Tool execution
- Multi-step reasoning

### 🎙️ Voice
- LiveKit
- LiveKit Agents
- Python Voice Agent
- Speech-to-Text / Voice Activity Detection through the configured LiveKit pipeline

### 🗄️ Database
**MongoDB**
Stores:
- Users
- Interviews
- Questions
- Responses
- Resumes
- Feedback
- Voice sessions
- Transcripts

### 📄 Resume Processing
- PyMuPDF
- pdfminer
- python-docx
Supports extraction from PDF and DOCX.

---

# 📁 Project Structure

```text
PrepAI/
│
├── frontend/
│   ├── app/
│   ├── components/
│   ├── lib/
│   ├── hooks/
│   ├── types/
│   └── public/
│
├── backend/
│   ├── app/
│   │   ├── ai/
│   │   │   ├── gemini_client.py
│   │   │   ├── openrouter_client.py
│   │   │   └── prompts/
│   │   │
│   │   ├── agents/
│   │   │   ├── orchestrator.py
│   │   │   ├── interview_agent.py
│   │   │   ├── evaluation_agent.py
│   │   │   └── coach_agent.py
│   │   │
│   │   ├── graph/
│   │   │   ├── state.py
│   │   │   ├── nodes.py
│   │   │   ├── edges.py
│   │   │   └── workflow.py
│   │   │
│   │   ├── tools/
│   │   │   ├── interview_tools.py
│   │   │   ├── question_tools.py
│   │   │   ├── evaluation_tools.py
│   │   │   ├── analytics_tools.py
│   │   │   └── resume_tools.py
│   │   │
│   │   ├── routes/
│   │   ├── services/
│   │   ├── models/
│   │   └── schemas/
│   │
│   └── tests/
│
├── voice-agent/
│   ├── agent.py
│   ├── config.py
│   ├── prompts.py
│   ├── transcript.py
│   └── requirements.txt
│
├── docs/
│
├── .env.example
├── .gitignore
├── docker-compose.yml
└── README.md
```

---

# 🔐 Security Architecture

Security is handled primarily on the backend.

### API Keys
Never exposed to the frontend:
- GEMINI_API_KEY
- OPENROUTER_API_KEY
- LIVEKIT_API_SECRET
- MONGODB_URI
- JWT_SECRET

### Agent Security
GPT-4o cannot:
- Execute arbitrary Python
- Execute shell commands
- Access MongoDB directly
- Access the filesystem
- Make arbitrary backend requests

Instead:
```
GPT-4o
   ↓
Approved Tool
   ↓
Backend Validation
   ↓
Service Layer
   ↓
MongoDB / AI Service
```
Every database operation is scoped to the authenticated user.

---

# 📌 Development Phases

| Phase | Feature | Status |
|---|---|---|
| 1 | Backend Foundation | 🟢 |
| 2 | Authentication | 🟢 |
| 3 | Interview Management | 🟢 |
| 4 | Resume Processing | 🟢 |
| 5 | Gemini Question Generation | 🟢 |
| 6 | Text Interview Engine | 🟢 |
| 7 | AI Evaluation & Feedback | 🟢 |
| 8 | Performance Analytics | 🟢 |
| 9 | Voice Interviews + LiveKit | 🟢 |
| 10 | Agentic AI + LangGraph + GPT-4o | 🟢 |
| 11 | Next.js/React Frontend & Integration | 🔵 |
| 12 | Deployment & Production Infrastructure | ⚪ |

**Legend:**
🟢 Completed
🔵 In Progress
⚪ Planned

---

# ⚙️ Environment Variables

Create the appropriate environment file for each service.

**Backend (`backend/.env`)**
```env
MONGODB_URI=
JWT_SECRET=
GEMINI_API_KEY=
OPENROUTER_API_KEY=
OPENROUTER_MODEL=openai/gpt-4o
OPENROUTER_SITE_URL=http://localhost:3000
OPENROUTER_APP_NAME=PrepAI
LIVEKIT_URL=
LIVEKIT_API_KEY=
LIVEKIT_API_SECRET=
FRONTEND_URL=http://localhost:3000
```

**Frontend (`frontend/.env`)**
Only expose public configuration:
```env
VITE_API_URL=http://localhost:8000/api
VITE_LIVEKIT_URL=
```
> **Note:** Never put Gemini, OpenRouter, MongoDB, JWT secrets, or LiveKit API secrets in frontend environment variables.

---

# 🚀 Local Development

### Prerequisites
Install:
- Node.js 18+
- Python 3.10+
- MongoDB / MongoDB Atlas
- Git
- OpenRouter API key
- Google Gemini API key
- LiveKit account or local LiveKit server

### 1️⃣ Start Backend
```bash
cd backend
python -m venv .venv

# Windows
.venv\Scripts\activate
# Linux / macOS
source .venv/bin/activate

# Install dependencies:
pip install -r requirements.txt

# Start FastAPI:
uvicorn app.main:app --reload
```
- Backend: http://localhost:8000
- Swagger: http://localhost:8000/docs

### 2️⃣ Start Frontend
```bash
cd frontend
npm install
npm run dev
```
- Frontend: http://localhost:3000

### 3️⃣ Start Voice Agent
```bash
cd voice-agent
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python agent.py start
```

---

# 🧪 Testing

**Backend:**
```bash
cd backend
python -m pytest tests/ -v
```

**Frontend:**
```bash
cd frontend
npm run build
```

Before considering the project complete, verify the complete user journey:
```
Register
   ↓
Login
   ↓
Dashboard
   ↓
Create Interview
   ↓
Generate Questions
   ↓
Text / Voice Interview
   ↓
Complete Interview
   ↓
AI Evaluation
   ↓
Feedback
   ↓
Analytics
   ↓
AI Career Coach
```

---

# 🔄 End-to-End AI Flow

The complete AI ecosystem works like this:

```text
                    ┌──────────────┐
                    │    USER      │
                    └──────┬───────┘
                           │
                           ▼
                    React Frontend
                           │
                           ▼
                    FastAPI Backend
                           │
          ┌────────────────┼────────────────┐
          │                │                │
          ▼                ▼                ▼
       Gemini          LangGraph          LiveKit
          │                │                │
          │             GPT-4o              │
          │                │             Voice Agent
          │                │                │
          ▼                ▼                ▼
     Interview AI       AI Agents        Voice AI
          │                │                │
          └────────────────┼────────────────┘
                           │
                           ▼
                        MongoDB
                           │
                           ▼
                    Analytics + Coach
```

---

# 💡 Why PrepAI?

Most interview preparation platforms focus on only one part of the preparation process.
PrepAI combines: **Practice + AI + Voice + Evaluation + Analytics + Agentic Coaching** into one platform.

The system is designed around an important principle:
> **AI should not only ask questions — it should understand your performance and help you improve.**

---

# 🔮 Future Roadmap

Potential future enhancements:
- 🎯 Personalized interview difficulty adaptation
- 🧑💼 Job-description matching
- 📚 AI-generated study plans
- 🧠 Long-term candidate memory
- 🔗 Job application tracking
- 💻 Coding interview environment
- 🗣️ Advanced voice analytics
- 📹 Interview recording and playback
- 📈 Advanced skill progression
- ☁️ Production deployment
- 📱 Mobile application

---

# 🏆 Project Highlights

PrepAI demonstrates practical implementation of:
- Full-stack development
- REST API architecture
- JWT authentication
- MongoDB
- Generative AI
- Prompt engineering
- Multi-model AI architecture
- Agentic AI
- LangGraph
- Tool calling
- Structured AI outputs
- Real-time voice AI
- LiveKit
- Performance analytics
- Resume processing

---

# 💻 Built By

**Praman Jain**  
B.Tech — Computer Science & Business Systems  
MITS Gwalior  

**Prince Saxena**  
B.Tech — Computer Science & Business Systems  
MITS Gwalior 

❤️ Built With: React · FastAPI · Python · MongoDB · Google Gemini · OpenRouter · GPT-4o · LangGraph · LiveKit · Tailwind CSS

PrepAI — Turn every interview into progress.
