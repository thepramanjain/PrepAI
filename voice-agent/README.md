# PrepAI Voice Agent

Phase 9 — Real-Time Voice Interview Engine

The voice agent connects to a LiveKit room and conducts a real interview conversation using the Gemini Live API (speech-to-speech). It reads the prepared questions from the PrepAI backend and stores candidate responses + transcript after each exchange.

---

## Architecture

```
Candidate (browser/app)
       │  WebRTC audio
       ▼
  LiveKit Room
       │
       ├──► Voice Agent (this process)
       │         │
       │         │  HTTP
       │         ▼
       │    PrepAI Backend (FastAPI)
       │         │
       │         ▼
       │    MongoDB Atlas
       │
       └──► Candidate hears AI interviewer (Gemini Live audio)
```

**Gemini integration:** `gemini-2.5-flash-native-audio-preview`  
This is a native speech-to-speech model — it handles STT, LLM, and TTS in a single call through the Gemini Live API. No separate Whisper/Deepgram or TTS service is needed.

---

## Prerequisites

- Python 3.10+
- A [LiveKit Cloud](https://cloud.livekit.io) account (free tier)
- Your existing `GEMINI_API_KEY` from the backend

---

## Setup

### 1. Create a virtual environment

```bash
cd voice-agent
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment

```bash
cp .env.example .env
```

Edit `.env` and fill in:

| Variable | Where to get it |
|----------|----------------|
| `LIVEKIT_URL` | LiveKit Cloud dashboard → Project Settings |
| `LIVEKIT_API_KEY` | LiveKit Cloud dashboard → API Keys |
| `LIVEKIT_API_SECRET` | LiveKit Cloud dashboard → API Keys |
| `GOOGLE_API_KEY` | Same as `GEMINI_API_KEY` in your backend `.env` |
| `PREPAI_BACKEND_URL` | `http://localhost:8000` for local dev |

> **Security:** Never commit `.env` to version control. The `.gitignore` already excludes it.

---

## Running Locally

### Terminal 1 — Start the PrepAI backend

```bash
cd backend
.venv\Scripts\activate
uvicorn app.main:app --reload
```

### Terminal 2 — Start the voice agent

```bash
cd voice-agent
.venv\Scripts\activate
python agent.py dev
```

`dev` mode connects the agent to your LiveKit Cloud project and registers it as a worker. The agent waits for jobs (rooms with participants).

---

## Testing the Full Flow via Swagger

1. Open `http://127.0.0.1:8000/docs`
2. Login → Authorize
3. `POST /api/interviews` — create an interview
4. `POST /api/interviews/{id}/generate-questions` — generate questions with Gemini
5. `POST /api/interviews/{id}/voice/session` — create voice session, receive `token` + `room_name`
6. `POST /api/interviews/{id}/voice/start` — mark session active
7. Connect to the LiveKit room using the token (see below)
8. The voice agent joins automatically and begins the interview
9. `POST /api/interviews/{id}/voice/end` — end the session
10. `GET /api/interviews/{id}/voice/transcript` — view transcript
11. `POST /api/interviews/{id}/evaluate` — run Phase 7 AI evaluation

---

## Connecting to the LiveKit Room

Since the frontend is not implemented yet (Phase 10), you can test the audio connection using:

- **LiveKit Playground**: https://agents-playground.livekit.io  
  Enter your `LIVEKIT_URL` and the `token` returned by `POST /voice/session`

- **LiveKit CLI**:
  ```bash
  lk room join --url $LIVEKIT_URL --token <your_participant_token>
  ```

---

## Voice Session Lifecycle

```
POST /voice/session   →  status: "created"   (token generated)
POST /voice/start     →  status: "active"    (interview begins)
[voice conversation]
POST /voice/end       →  status: "completed" (transcript + responses stored)
POST /evaluate        →  AI evaluation (Phase 7)
```

---

## Room Metadata

The PrepAI backend passes context to the voice agent via LiveKit room metadata:

```json
{
  "interview_id": "...",
  "jwt_token": "..."
}
```

The agent reads this at startup to load interview context and authenticate backend calls.

> **Note:** In the current implementation, room metadata is not yet set automatically by the backend (the token endpoint returns the token and room_name, but doesn't inject metadata). This is a manual step for now — set it in your LiveKit Cloud dashboard or via the LiveKit API when creating the room. Full automation is planned for Phase 10.

---

## Security

| Rule | Implementation |
|------|---------------|
| `LIVEKIT_API_SECRET` | Only in this process, never in backend responses |
| `GOOGLE_API_KEY` | Only in this process, never sent to client |
| Backend calls | Use candidate's JWT token from room metadata |
| Room access | Requires signed participant token (backend generates it) |
| Transcript ownership | Backend enforces via JWT on every append call |

---

## Free-Tier Notes

| Service | Free Tier |
|---------|-----------|
| LiveKit Cloud | Free developer tier available — no credit card required for testing |
| Gemini Live API | Uses your existing `GOOGLE_API_KEY` — subject to Google AI Studio free tier limits |

---

## Troubleshooting

**Agent doesn't join the room:**  
→ Check `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET` in `.env`  
→ Ensure the agent is running (`python agent.py dev`) before connecting

**No audio from AI:**  
→ Verify `GOOGLE_API_KEY` is valid and has access to `gemini-2.5-flash-native-audio-preview`  
→ Check the agent logs for Gemini API errors

**Transcript not saving:**  
→ Ensure `PREPAI_BACKEND_URL` is correct and the backend is running  
→ Check that the JWT token in room metadata is still valid (1 hour TTL)
