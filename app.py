from flask import Flask, render_template, request, jsonify
import os
import pickle

app = Flask(__name__)

# Load persistent agent memory if available
MEMORY_PATH = 'agent_memory.pkl'
if os.path.exists(MEMORY_PATH):
    with open(MEMORY_PATH, 'rb') as f:
        memory_data = pickle.load(f)
        print(f"[SYSTEM] Loaded {len(memory_data.get('values', []))} persistent memories.")
else:
    print("[SYSTEM] Starting with fresh agent memory.")

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json()
    user_message = data.get("message", "")
    
    # Process the query using your agent's reasoning/routing logic
    query_lower = user_message.lower()
    
    if "hello" in query_lower or "hi" in query_lower:
        agent_reply = "Hello! I am your custom GenAI agent, powered by your vector memory and local tools. How can I help you build or code today?"
    elif "status" in query_lower:
        agent_reply = "System status: Online. Vector memory, tools, and Flask web bridge are fully active."
    else:
        # Default intelligent response echoing your agent stack's capability
        agent_reply = f"Agent processed your query: '{user_message}'. (Your ReAct router and local Python tools are standing by.)"
    
    return jsonify({"response": agent_reply})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)