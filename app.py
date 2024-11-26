from flask import Flask, request, jsonify, render_template
import requests
import os
from werkzeug.exceptions import BadRequest


app = Flask(__name__)

# Replace this with your actual n8n webhook URL
N8N_WEBHOOK_URL = os.environ.get('N8N_WEBHOOK_URL', "https://n8n.hirelypro.io/webhook/b74ae861-8489-47ad-8663-0086a1059588/chat")

@app.route('/')
def index():
    """
    Render the homepage.
    """
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    """
    Handle chat messages from the frontend and interact with the n8n webhook.
    """
    # Get the user's message from the POST request
    user_message = request.json.get('message')
    
    if not user_message or len(user_message.strip()) == 0:
        raise BadRequest("Message is empty")

    try:
        # Send the user's message to the n8n webhook
        response = requests.post(
            N8N_WEBHOOK_URL, 
            json={"chatInput": user_message},  # Key matches n8n expectations
            timeout=60  # Timeout for the request
        )
        response.raise_for_status()  # Raise an error for HTTP codes >= 400
        
        # Extract and return the AI response
        ai_response = response.json().get('response', "No response received")
        return jsonify({"response": ai_response})
    except requests.exceptions.RequestException as e:
        # Handle connection or other request-related errors
        return jsonify({"error": "Failed to connect to n8n webhook.", "details": str(e)}), 500
    except ValueError:
        # Handle JSON decoding errors
        return jsonify({"error": "Invalid response from n8n webhook."}), 500

if __name__ == '__main__':
    # Define port and host settings
    port = int(os.environ.get('PORT', 5000))
    print(f"Starting Flask app on port {port}...")
    app.run(host='0.0.0.0', port=port)