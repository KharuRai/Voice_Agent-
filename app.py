import os
import json
import datetime
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import google.generativeai as genai

from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)
CORS(app)

# ── Configure Gemini ────────────────────────────────────────────────────────────
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "YOUR_GEMINI_API_KEY_HERE")
genai.configure(api_key=GEMINI_API_KEY)

# ── In-memory stores ────────────────────────────────────────────────────────────
todo_list: list[dict] = []
memory_store: list[dict] = []
next_id = 1


# ── Tool implementations ────────────────────────────────────────────────────────
def add_todo(title: str, priority: str = "medium", due_date: str = "") -> dict:
    global next_id
    item = {
        "id": next_id,
        "title": title,
        "priority": priority.lower(),
        "due_date": due_date,
        "completed": False,
        "created_at": datetime.datetime.now().isoformat(),
    }
    todo_list.append(item)
    next_id += 1
    _save_memory(f"User added task: '{title}' with priority {priority}")
    return {"success": True, "message": f"Added task: '{title}'", "item": item}


def update_todo(task_id: int, title: str = "", priority: str = "", completed: bool = None, due_date: str = "") -> dict:
    for item in todo_list:
        if item["id"] == task_id:
            if title:
                item["title"] = title
            if priority:
                item["priority"] = priority.lower()
            if completed is not None:
                item["completed"] = completed
            if due_date:
                item["due_date"] = due_date
            _save_memory(f"User updated task ID {task_id}")
            return {"success": True, "message": f"Updated task ID {task_id}", "item": item}
    return {"success": False, "message": f"Task ID {task_id} not found"}


def delete_todo(task_id: int) -> dict:
    global todo_list
    before = len(todo_list)
    removed = [t for t in todo_list if t["id"] == task_id]
    todo_list = [t for t in todo_list if t["id"] != task_id]
    if len(todo_list) < before:
        _save_memory(f"User deleted task ID {task_id}: '{removed[0]['title']}'")
        return {"success": True, "message": f"Deleted task ID {task_id}"}
    return {"success": False, "message": f"Task ID {task_id} not found"}


def list_todos(filter_by: str = "all") -> dict:
    if filter_by == "completed":
        items = [t for t in todo_list if t["completed"]]
    elif filter_by == "pending":
        items = [t for t in todo_list if not t["completed"]]
    elif filter_by == "high":
        items = [t for t in todo_list if t["priority"] == "high"]
    else:
        items = todo_list
    return {"success": True, "items": items, "count": len(items)}


def _save_memory(event: str):
    memory_store.append({
        "timestamp": datetime.datetime.now().isoformat(),
        "event": event,
    })
    if len(memory_store) > 50:
        memory_store.pop(0)


def recall_memory(query: str = "") -> dict:
    if not memory_store:
        return {"success": True, "memories": [], "message": "No memories stored yet"}
    if query:
        filtered = [m for m in memory_store if query.lower() in m["event"].lower()]
        return {"success": True, "memories": filtered[-10:]}
    return {"success": True, "memories": memory_store[-10:]}


# ── Gemini tool declarations ────────────────────────────────────────────────────
TOOLS = [
    {
        "function_declarations": [
            {
                "name": "add_todo",
                "description": "Add a new task to the To-Do list",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string", "description": "Task title"},
                        "priority": {"type": "string", "description": "Priority: low, medium, or high", "enum": ["low", "medium", "high"]},
                        "due_date": {"type": "string", "description": "Optional due date (YYYY-MM-DD)"},
                    },
                    "required": ["title"],
                },
            },
            {
                "name": "update_todo",
                "description": "Update an existing task by ID",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "task_id": {"type": "integer", "description": "The task ID to update"},
                        "title": {"type": "string", "description": "New title"},
                        "priority": {"type": "string", "description": "New priority"},
                        "completed": {"type": "boolean", "description": "Mark as completed or not"},
                        "due_date": {"type": "string", "description": "New due date"},
                    },
                    "required": ["task_id"],
                },
            },
            {
                "name": "delete_todo",
                "description": "Delete a task by ID",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "task_id": {"type": "integer", "description": "The task ID to delete"},
                    },
                    "required": ["task_id"],
                },
            },
            {
                "name": "list_todos",
                "description": "List all tasks, with optional filter",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "filter_by": {
                            "type": "string",
                            "description": "Filter: all, completed, pending, high",
                            "enum": ["all", "completed", "pending", "high"],
                        }
                    },
                },
            },
            {
                "name": "recall_memory",
                "description": "Recall past user interactions and important events",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Optional keyword to filter memories"},
                    },
                },
            },
        ]
    }
]

SYSTEM_PROMPT = """You are SURAI — an intelligent voice-enabled AI assistant specialized in managing To-Do lists.

PERSONALITY:
- Concise, friendly, and efficient
- Use natural conversational language suitable for voice output
- Keep responses short (1-3 sentences for confirmations, slightly longer for lists)
- Never use markdown, bullet symbols, or special characters in responses

CAPABILITIES:
1. Add tasks with priority and due dates
2. Update, complete, or modify existing tasks
3. Delete tasks by ID or name
4. List and filter tasks
5. Recall important past interactions from memory

BEHAVIOR RULES:
- Always use tools for task operations — never simulate them
- For listing tasks, format them naturally: "You have 3 tasks: first is X, second is Y..."
- When completing a task, call update_todo with completed=true
- If the user mentions something memorable (appointments, goals), call recall_memory or note it
- Be proactive: if tasks seem overdue or high priority, mention it

Current date: """ + datetime.datetime.now().strftime("%B %d, %Y")


TOOL_FUNCTIONS = {
    "add_todo": add_todo,
    "update_todo": update_todo,
    "delete_todo": delete_todo,
    "list_todos": list_todos,
    "recall_memory": recall_memory,
}

# ── Conversation history (in-memory per session) ────────────────────────────────
conversation_history = []


def run_agent(user_message: str) -> str:
    global conversation_history

    conversation_history.append({"role": "user", "parts": [user_message]})

    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash-lite",
        system_instruction=SYSTEM_PROMPT,
        tools=TOOLS,
    )

    # Keep last 20 turns
    history_to_send = conversation_history[-20:]

    response = model.generate_content(history_to_send)

    # Handle function calls in a loop
    max_rounds = 5
    for _ in range(max_rounds):
        candidate = response.candidates[0]
        parts = candidate.content.parts

        has_function_call = any(hasattr(p, "function_call") and p.function_call.name for p in parts)

        if not has_function_call:
            break

        # Execute all function calls
        tool_results = []
        for part in parts:
            if hasattr(part, "function_call") and part.function_call.name:
                fn_name = part.function_call.name
                fn_args = dict(part.function_call.args)
                fn = TOOL_FUNCTIONS.get(fn_name)
                if fn:
                    result = fn(**fn_args)
                else:
                    result = {"error": f"Unknown function: {fn_name}"}
                tool_results.append({
                    "function_response": {
                        "name": fn_name,
                        "response": result,
                    }
                })

        # Add model response + tool results to history
        conversation_history.append({"role": "model", "parts": parts})
        conversation_history.append({"role": "user", "parts": tool_results})

        history_to_send = conversation_history[-20:]
        response = model.generate_content(history_to_send)

    # Extract final text
    final_text = ""
    for part in response.candidates[0].content.parts:
        if hasattr(part, "text"):
            final_text += part.text

    conversation_history.append({"role": "model", "parts": [final_text]})
    return final_text.strip()


# ── API Routes ──────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.json
    user_message = data.get("message", "").strip()
    if not user_message:
        return jsonify({"error": "Empty message"}), 400
    try:
        reply = run_agent(user_message)
        return jsonify({"reply": reply, "todos": todo_list, "memories": memory_store[-5:]})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/todos", methods=["GET"])
def get_todos():
    return jsonify({"todos": todo_list})


@app.route("/api/memory", methods=["GET"])
def get_memory():
    return jsonify({"memories": memory_store})


@app.route("/api/set_key", methods=["POST"])
def set_key():
    data = request.json
    key = data.get("key", "").strip()
    if key:
        genai.configure(api_key=key)
        return jsonify({"success": True})
    return jsonify({"error": "No key provided"}), 400


@app.route("/api/reset", methods=["POST"])
def reset():
    global todo_list, memory_store, conversation_history, next_id
    todo_list = []
    memory_store = []
    conversation_history = []
    next_id = 1
    return jsonify({"success": True, "message": "Reset complete"})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
