from flask import Flask, request, jsonify, render_template
import requests
import os

app = Flask(__name__)

# Replace this with your n8n webhook URL
N8N_WEBHOOK_URL = "https://n8n.hirelypro.io/webhook/b74ae861-8489-47ad-8663-0086a1059588/chat"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    user_message = request.json.get('message')
    if not user_message:
        return jsonify({"error": "No message provided"}), 400

    # Send the message to n8n with the correct key
    try:
        response = requests.post(
            N8N_WEBHOOK_URL, 
            json={"chatInput": user_message}  # Correct key expected by n8n
        )
        response.raise_for_status()
        ai_response = response.json().get('response', "No response received")
        return jsonify({"response": ai_response})
    except requests.exceptions.RequestException as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))