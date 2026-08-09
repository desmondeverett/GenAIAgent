from flask import Flask, render_template, request, jsonify
import io
import sys

app = Flask(__name__)

def execute_python_code(code_string):
    """Tool: Safely executes a string of Python code and captures the printed output."""
    old_stdout = sys.stdout
    new_stdout = io.StringIO()
    sys.stdout = new_stdout
    
    try:
        # Check if it's a direct expression (like "2+2") or print statement
        if "\n" not in code_string and "print" not in code_string:
            code_string = f"print({code_string})"
            
        exec(code_string, {})
        output = new_stdout.getvalue()
    except Exception as e:
        output = f"Execution Error: {str(e)}"
    finally:
        sys.stdout = old_stdout
        
    return output.strip()

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json()
    user_message = data.get("message", "")
    query_lower = user_message.lower()
    
    # Simple Intent Router for the Web Interface
    if "hello" in query_lower or "hi" in query_lower:
        agent_reply = "Hello! I am your custom GenAI agent. How can I help you code or calculate today?"
    elif "status" in query_lower:
        agent_reply = "System status: Online. Flask backend, Python interpreter, and agent tools are fully active."
    elif "what is" in query_lower or "calculate" in query_lower or "+" in user_message or "-" in user_message or "*" in user_message or "/" in user_message:
        # Extract math/code expression from query
        expression = user_message.replace("what is", "").replace("calculate", "").strip()
        if expression.endswith("?"):
            expression = expression[:-1].strip()
            
        # Run through Python execution tool
        result = execute_python_code(expression)
        agent_reply = f"Calculated Result: {result}"
    else:
        agent_reply = f"Agent processed your query: '{user_message}'. (Your ReAct router and tools are standing by.)"
    
    return jsonify({"response": agent_reply})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)