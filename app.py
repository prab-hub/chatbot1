from flask import Flask, request, jsonify, render_template
import requests
import os
from werkzeug.exceptions import BadRequest
from mysql.connector import connect, Error
from dotenv import load_dotenv

# Load the secrets from the .env file
load_dotenv('/etc/secrets/.env')


app = Flask(__name__)

# Load MySQL credentials from environment variables
MYSQL_HOST = os.getenv('MYSQL_HOST')
MYSQL_USER = os.getenv('MYSQL_USER')
MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD')
MYSQL_DATABASE = os.getenv('MYSQL_DATABASE')

# Replace with your actual n8n webhook URL
N8N_WEBHOOK_URL = os.getenv(
    'N8N_WEBHOOK_URL', "https://n8n.hirelypro.io/webhook/b74ae861-8489-47ad-8663-0086a1059588/chat"
)

# Connect to the MySQL database
def get_db_connection():
    try:
        connection = connect(
            host=MYSQL_HOST,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DATABASE
        )
        print("Successfully connected to the database")
        return connection
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None

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
    user_message = request.json.get('message')
    if not user_message or len(user_message.strip()) == 0:
        raise BadRequest("Message is empty")

    try:
        # Send the user's message to the n8n webhook
        response = requests.post(
            N8N_WEBHOOK_URL, 
            json={"chatInput": user_message},
            timeout=60
        )
        response.raise_for_status()
        ai_response = response.json().get('response', "No response received")

        # Save question and response to the database
        save_message_to_db(user_message, ai_response)
        
        return jsonify({"response": ai_response})
    except requests.exceptions.RequestException as e:
        return jsonify({"error": "Failed to connect to n8n webhook.", "details": str(e)}), 500
    except ValueError:
        return jsonify({"error": "Invalid response from n8n webhook."}), 500

def save_message_to_db(question, answer):
    """
    Save the user's question and AI's answer to the database.
    """
    connection = get_db_connection()
    if connection:
        try:
            cursor = connection.cursor()
            cursor.execute("""
                INSERT INTO questions (question_text) VALUES (%s)
            """, (question,))
            question_id = cursor.lastrowid

            cursor.execute("""
                INSERT INTO answers (answer_text, question_id) VALUES (%s, %s)
            """, (answer, question_id))
            
            connection.commit()
        except Error as e:
            print(f"Error saving message to database: {e}")
        finally:
            connection.close()

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    print(f"Starting Flask app on port {port}...")
    app.run(host='0.0.0.0', port=port)