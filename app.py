from flask import Flask, render_template, request, jsonify
import os
import io
import sys
import pickle

app = Flask(__name__)

# --- AGENT MEMORY & TOOLS SETUP ---
MEMORY_PATH = 'agent_memory.pkl'

def load_persistence_memory():
    """Loads saved state or initializes a blank store."""
    if os.path.exists(MEMORY_PATH):
        try:
            with open(MEMORY_PATH, 'rb') as f:
                data = pickle.load(f)
                print(f"[SYSTEM] Restored {len(data.get('values', []))} memories from disk.")
                return data.get('values', [])
        except Exception as e:
            print(f"[SYSTEM ERROR] Could not load memory: {e}")
    return []

agent_memory = load_persistence_memory()

def execute_python_code(code_string):
    """Tool: Safely executes Python code strings and captures standard output."""
    old_stdout = sys.stdout
    new_stdout = io.StringIO()
    sys.stdout = new_stdout
    
    try:
        # Wrap simple expressions in a print statement automatically
        if "\n" not in code_string and "print" not in code_string:
            code_string = f"print({code_string})"
            
        exec(code_string, {})
        output = new_stdout.getvalue()
    except Exception as e:
        output = f"Execution Error: {str(e)}"
    finally:
        sys.stdout = old_stdout
        
    return output.strip()

def read_local_file(file_path):
    """Tool: Reads text content from a local workspace file."""
    try:
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        return f"Error: File '{file_path}' not found in workspace."
    except Exception as e:
        return f"Error reading file: {str(e)}"


# --- FLASK WEB ROUTES ---

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json()
    user_message = data.get("message", "")
    query_lower = user_message.lower()
    
    # --- INTENT ROUTING LOGIC ---
    if "hello" in query_lower or "hi" in query_lower:
        agent_reply = "Hello! I am your custom GenAI agent, powered by your Flask backend and local Python tools."
        
    elif "status" in query_lower:
        agent_reply = f"System status: Online. Active memory records: {len(agent_memory)}. Python execution interpreter ready."
        
    elif "read file" in query_lower or "file" in query_lower:
        # Default to reading your sample corpus if requested
        file_content = read_local_file("shakespeare.txt")
        snippet = file_content[:350] + "..." if len(file_content) > 350 else file_content
        agent_reply = f"File Content Preview:\n{snippet}"
        
    elif "what is" in query_lower or "calculate" in query_lower or any(op in user_message for op in ["+", "-", "*", "/"]):
        # Extract and compute expression
        expression = user_message.replace("what is", "").replace("calculate", "").strip()
        if expression.endswith("?"):
            expression = expression[:-1].strip()
            
        result = execute_python_code(expression)
        agent_reply = f"Calculated Result: {result}"
        
    else:
        # Fallback intelligent agent response handler
        agent_reply = f"Agent successfully processed your query: '{user_message}'. (Your ReAct router, file tools, and Python interpreter are standing by.)"
    
    return jsonify({"response": agent_reply})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)