# SURAI — Voice AI To-Do Agent

A voice-enabled AI agent powered by **Google Gemini** that manages a To-Do list using
function-calling tools and stores important interaction memories.

---

## Features

| Feature | Details |
|---|---|
| 🎙 Voice Input | Web Speech API — click the orb to speak |
| 🔊 Text-to-Speech | Browser-native TTS for agent replies |
| 🧠 Gemini Agent | Function-calling with `gemini-1.5-flash` |
| ✅ Task Management | Add / update / delete / list To-Do items |
| 🧩 Memory System | Stores & recalls important past interactions |
| 🔴 Red & Black UI | Cyberpunk-themed dark interface |

---

## Setup

### 1. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 2. Get a Gemini API Key

1. Visit https://aistudio.google.com/app/apikey
2. Create a free API key

### 3. Set your API key (choose one method)

**Option A — Environment vSURAIble (recommended):**
```bash
export GEMINI_API_KEY="your_key_here"
python app.py
```

**Option B — In the browser:**
When the app opens, paste your key in the orange banner at the top.

### 4. Run the server

```bash
python app.py
```

### 5. Open in browser

```
http://localhost:5000
```

> **Voice input requires Chrome or Edge** (Web Speech API support).

---

## Usage Examples

Speak or type any of the following:

- *"Add a task to buy groceries with high priority"*
- *"Add a meeting with the client due 2025-08-10"*
- *"Show me all my tasks"*
- *"Mark task 1 as completed"*
- *"Update task 2 title to finish the report"*
- *"Delete task 3"*
- *"Show only pending tasks"*
- *"What do you remember about groceries?"*
- *"List high priority tasks"*

---

## Project Structure

```
todo-voice-agent/
├── app.py              # Flask backend + Gemini agent + tools + memory
├── requirements.txt    # Python dependencies
├── README.md           # This file
└── templates/
    └── index.html      # Frontend (red & black theme, voice UI)
```

---

## Architecture

```
Browser (Voice/Text)
       │
       ▼
Flask Backend (app.py)
       │
       ▼
Gemini 1.5 Flash (LLM)
       │  Function calling
       ├──▶ add_todo()
       ├──▶ update_todo()
       ├──▶ delete_todo()
       ├──▶ list_todos()
       └──▶ recall_memory()
```

---

## Notes

- All data is stored in memory (resets on server restart).
- The memory system stores the last 50 interactions.
- Conversation history is kept for the last 20 turns per session.
