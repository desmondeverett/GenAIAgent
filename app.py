from flask import Flask, render_template, request, jsonify
import os
import io
import sys
import pickle
import re
import urllib.request
import urllib.parse
from bs4 import BeautifulSoup
from collections import deque

app = Flask(__name__)

# Sliding window history buffer & active session user profile
chat_history = deque(maxlen=6)
user_profile = {"name": None}

# --- AGENT TOOLS ---

def search_duckduckgo_web(query):
    """Tool: Scrapes live search results from DuckDuckGo's HTML endpoint."""
    print(f"\n   [TOOL ACTIVATED] Scraping live web for: '{query}'...")
    encoded_query = urllib.parse.quote(query)
    url = f"https://html.duckduckgo.com/html/?q={encoded_query}"
    
    try:
        req = urllib.request.Request(
            url, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        )
        with urllib.request.urlopen(req) as response:
            html_content = response.read().decode('utf-8')
            
        soup = BeautifulSoup(html_content, 'html.parser')
        results = []
        
        for a in soup.find_all('a', class_='result__snippet', limit=3):
            results.append(a.get_text(strip=True))
            
        if not results:
            return f"No search snippets found for: {query}"
            
        return " | ".join(results)
    except Exception as e:
        return f"Scraping Error: {str(e)}"

def execute_python_code(code_string):
    """Tool: Safely executes Python code strings and captures standard output."""
    old_stdout = sys.stdout
    new_stdout = io.StringIO()
    sys.stdout = new_stdout
    
    try:
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
    user_message = data.get("message", "").strip()
    
    if not user_message:
        return jsonify({"response": "Please enter a valid message."})
        
    chat_history.append({"role": "user", "content": user_message})
    query_lower = user_message.lower()
    
    # --- INTENT ROUTING LOGIC ---
    
    # 1. Name Introduction Detection
    name_match = re.search(r"\b(?:i'm|i am|my name is)\s+([a-zA-Z]+)", query_lower)
    if name_match:
        extracted_name = name_match.group(1).capitalize()
        user_profile["name"] = extracted_name
        agent_reply = f"Nice to meet you, {extracted_name}! I've recorded your name in my context. How can I help you code or search today?"
        
    elif "what is my name" in query_lower or "who am i" in query_lower:
        if user_profile["name"]:
            agent_reply = f"Your name is {user_profile['name']}!"
        else:
            agent_reply = "You haven't told me your name yet! Try saying 'I am [Your Name]'."
            
    # 2. Greetings
    elif "hello" in query_lower or "hi" in query_lower:
        greeting_name = f", {user_profile['name']}" if user_profile["name"] else ""
        agent_reply = f"Hello{greeting_name}! I am your custom GenAI agent, powered by your Flask backend and local tools."
        
    # 3. System Status
    elif "status" in query_lower:
        name_status = user_profile["name"] or "Unknown"
        agent_reply = f"System status: Online. Current User: {name_status}. Active history turns: {len(chat_history)}. Tools ready."
        
    # 4. Local File Reader Tool
    elif "read file" in query_lower or "file" in query_lower:
        file_content = read_local_file("shakespeare.txt")
        snippet = file_content[:350] + "..." if len(file_content) > 350 else file_content
        agent_reply = f"File Content Preview:\n{snippet}"
        
    # 5. Math & Code Calculator Tool
    elif any(op in user_message for op in ["+", "-", "*", "/"]) and "what is the" not in query_lower:
        expression = user_message.replace("what is", "").replace("calculate", "").strip()
        if expression.endswith("?"):
            expression = expression[:-1].strip()
        result = execute_python_code(expression)
        agent_reply = f"Calculated Result: {result}"
        
    # 6. Default Fallback -> Live Web Search
    else:
        search_target = user_message.replace("what is the", "").replace("who is the", "").replace("who was the", "").replace("who was", "").replace("what is", "").replace("can you tell me", "").strip()
        if search_target.endswith("?"):
            search_target = search_target[:-1].strip()
            
        search_result = search_duckduckgo_web(search_target)
        agent_reply = f"Search Result: {search_result}"
    
    chat_history.append({"role": "assistant", "content": agent_reply})
    return jsonify({"response": agent_reply})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)