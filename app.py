from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

@app.route("/")
def index():
    # Renders your index.html file from the 'templates' folder
    return render_template("index.html")

@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json()
    user_message = data.get("message", "")
    
    # Here is where you can plug in your agent core response function!
    # For now, let's return a test response to verify the frontend-backend bridge:
    agent_reply = f"Agent received your message: '{user_message}'"
    
    return jsonify({"response": agent_reply})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)