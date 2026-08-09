from flask import Flask, render_template, request, jsonify
import os
import io
import sys
import pickle
import re
import urllib.request
import urllib.parse
import json
from collections import deque

app = Flask(__name__)

# Sliding window history buffer & active session user profile
chat_history = deque(maxlen=6)
user_profile = {"name": None}

# --- AGENT TOOLS ---

def search_wikipedia_kb(query):
    """Tool: Searches Wikipedia for the best matching page and retrieves full unlimited text."""
    print(f"\n   [TOOL ACTIVATED] Querying Wikipedia for: '{query}'...")
    
    try:
        search_api_url = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={urllib.parse.quote(query)}&format=json"
        req_search = urllib.request.Request(
            search_api_url, 
            headers={'User-Agent': 'GenAI_Agent/1.0 (contact@example.com)'}
        )
        
        with urllib.request.urlopen(req_search) as search_resp:
            search_data = json.loads(search_resp.read().decode('utf-8'))
            search_results = search_data.get("query", {}).get("search", [])
            
            if not search_results:
                return f"No information found for '{query}'."
                
            best_title = search_results[0]["title"]
            print(f"   [MATCHED WIKI PAGE]: '{best_title}'")
            
        summary_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(best_title)}"
        req_sum = urllib.request.Request(
            summary_url, 
            headers={'User-Agent': 'GenAI_Agent/1.0 (contact@example.com)'}
        )
        
        with urllib.request.urlopen(req_sum) as sum_resp:
            sum_data = json.loads(sum_resp.read().decode('utf-8'))
            extract = sum_data.get("extract", "")
            if extract:
                return extract
                
        return f"Could not retrieve details for '{best_title}'."
    except Exception as e:
        return f"Could not find information on '{query}'. Error: {str(e)}"

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
        
    query_lower = user_message.lower()
    agent_reply = ""
    
    # 1. Check for Name Introduction (handles 'im', 'i'm', 'i am', 'my name is')
    name_match = re.search(r"\b(?:im|i'm|i am|my name is)\s+([a-zA-Z]+)", query_lower)
    if name_match:
        extracted_name = name_match.group(1).capitalize()
        user_profile["name"] = extracted_name
        agent_reply += f"Nice to meet you, {extracted_name}! "
        
        cleaned_msg = user_message
        for prefix in ["im ", "i'm ", "I'm ", "Im ", "i am ", "I am ", "my name is ", "My name is "]:
            cleaned_msg = cleaned_msg.replace(prefix, "")
        cleaned_msg = re.sub(rf"^{extracted_name}[\s.,?!]*", "", cleaned_msg, flags=re.IGNORECASE).strip()
        
        if cleaned_msg:
            user_message = cleaned_msg
            query_lower = user_message.lower()
        else:
            user_message = ""

    # 2. Process remaining message content or commands with context awareness
    if user_message:
        if "what is my name" in query_lower or "who am i" in query_lower:
            if user_profile["name"]:
                agent_reply += f"Your name is {user_profile['name']}!"
            else:
                agent_reply += "You haven't told me your name yet!"
                
        elif "hello" in query_lower or "hi" in query_lower or "who are you" in query_lower:
            greeting_name = f", {user_profile['name']}" if user_profile["name"] else ""
            agent_reply += f"Hello{greeting_name}! I am Genie, your AI agent. How can I help you today?"
            
        elif "status" in query_lower:
            name_status = user_profile["name"] or "Unknown"
            agent_reply += f"System status: Online. Current User: {name_status}. Active history turns: {len(chat_history)}. Tools ready."
            
        elif "read file" in query_lower or "file" in query_lower:
            file_content = read_local_file("shakespeare.txt")
            snippet = file_content[:350] + "..." if len(file_content) > 350 else file_content
            agent_reply += f"File Content Preview:\n{snippet}"
            
        elif any(op in user_message for op in ["+", "-", "*", "/"]) and "what is the" not in query_lower:
            expression = user_message.replace("what is", "").replace("calculate", "").strip()
            if expression.endswith("?"):
                expression = expression[:-1].strip()
            result = execute_python_code(expression)
            agent_reply += f"Calculated Result: {result}"
            
        else:
            search_target = user_message.strip()
            if search_target.endswith("?"):
                search_target = search_target[:-1].strip()
                
            # Clean context blending: extract just the core active topic from recent turns if it's a follow-up
            if len(chat_history) > 0 and len(search_target.split()) < 7:
                # Look back at the last user message to see what subject was being discussed
                for hist_turn in reversed(chat_history):
                    if hist_turn["role"] == "user":
                        prev_query = hist_turn["content"].lower()
                        if "duck" in prev_query:
                            search_target = f"{search_target} duck"
                        elif "subnet" in prev_query:
                            search_target = f"{search_target} subnet"
                        elif "apple" in prev_query:
                            search_target = f"{search_target} apple"
                        break
                
            search_result = search_wikipedia_kb(search_target)
            agent_reply += f"Knowledge Base Result: {search_result}"
    elif not name_match:
        agent_reply = "Hello! How can I help you today?"

    # Append current turn to sliding window history buffer
    chat_history.append({"role": "user", "content": user_message})
    chat_history.append({"role": "assistant", "content": agent_reply})
    
    return jsonify({"response": agent_reply})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)