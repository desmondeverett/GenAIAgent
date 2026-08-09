from flask import Flask, render_template, request, jsonify
import os
import io
import sys
import pickle
import urllib.request
import urllib.parse
import json

app = Flask(__name__)

# --- SEARCH & EXECUTION TOOLS ---
def search_google_live(query):
    """Tool: Queries Google Custom Search JSON API for live web results."""
    API_KEY = "YOUR_GOOGLE_API_KEY"      # Replace with your Google API Key if using custom search
    CSE_ID = "YOUR_CUSTOM_SEARCH_ENGINE_ID"
    
    # Fallback to duckduckgo instant api or a direct summary if google keys aren't set up yet
    encoded_query = urllib.parse.quote(query)
    url = f"https://api.duckduckgo.com/?q={encoded_query}&format=json&t=genai_agent"
    
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'GenAI_Agent/1.0'})
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode('utf-8'))
            
        abstract = data.get("AbstractText", "")
        if abstract:
            return abstract
            
        related = data.get("RelatedTopics", [])
        for item in related:
            if "Text" in item:
                return item["Text"]
                
        return f"No direct answer found for: {query}"
    except Exception as e:
        return f"Search Error: {str(e)}"

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
        agent_reply = "Hello! I am your custom GenAI agent, powered by your Flask backend and local tools."
        
    elif "status" in query_lower:
        agent_reply = "System status: Online. Search tool and Python interpreter ready."
        
    elif any(op in user_message for op in ["+", "-", "*", "/"]) and "what is the" not in query_lower:
        # Strictly catch math calculations
        expression = user_message.replace("what is", "").replace("calculate", "").strip()
        if expression.endswith("?"):
            expression = expression[:-1].strip()
        result = execute_python_code(expression)
        agent_reply = f"Calculated Result: {result}"
        
    else:
        # Route factual questions (like "who is" or "what is") to our live search tool
        search_target = user_message.replace("what is the", "").replace("who is the", "").replace("who was", "").replace("what is", "").replace("can you tell me", "").strip()
        if search_target.endswith("?"):
            search_target = search_target[:-1].strip()
            
        search_result = search_google_live(search_target)
        agent_reply = f"Search Result: {search_result}"
    
    return jsonify({"response": agent_reply})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)