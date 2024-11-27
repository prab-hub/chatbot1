from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from flask_bcrypt import Bcrypt
from flask_session import Session
import requests
import os
from werkzeug.exceptions import BadRequest
from mysql.connector import connect, Error
from dotenv import load_dotenv

# Load the secrets from the .env file
load_dotenv('/etc/secrets/cred')

app = Flask(__name__)
bcrypt = Bcrypt(app)

# Enable debugging mode
app.config['DEBUG'] = True

# Session configuration
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'default_secret_key')
Session(app)

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
    # Check if the user is logged in
    if 'userid' in session:
        return render_template('chat.html', username=session['username'])  # Show the chat page if logged in
    return render_template('login.html')  # Show login page if not logged in


@app.route('/signup', methods=["POST", "GET"])
def signup():
    if request.method == "GET":
        return render_template('signup.html')
    
    # Handle user signup for POST method
    try:
        data = request.get_json()  # Parse the incoming JSON data


        if not data:
            raise BadRequest("Invalid JSON payload")
        
        username = data.get('username', '').strip().lower()
        password = data.get('password', '').strip()

        if not username or not password:
            raise BadRequest("Username and password are required.")
        
        password_hash = bcrypt.generate_password_hash(password).decode('utf-8')
        
        # DB connection and insert user
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute("""
            INSERT INTO users (username, password_hash) VALUES (%s, %s)
        """, (username, password_hash))
        connection.commit()

        return jsonify({"success": True}), 200  # Return JSON response indicating success
    
    except Exception as e:
        # Log the exception for debugging
        print(f"Error during signup: {str(e)}")
        return jsonify({"error": str(e)}), 500  # Return error details as JSON
    
    finally:
        if connection:
            connection.close()

@app.route('/login', methods=['POST', 'GET'])
def login():
    if request.method == "GET":
        return render_template('login.html')

    try:
        data = request.get_json()

        if not data:
            raise BadRequest("Invalid JSON payload")

        username = data.get('username', '').strip().lower()
        password = data.get('password', '').strip()

        if not username or not password:
            raise BadRequest("Username and password are required.")

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
        print(f"Query result: {user}")

        if not user:
            print(f"User {username} not found in database.")
            return jsonify({"error": "Username not found."}), 401

        if bcrypt.check_password_hash(user['password_hash'], password):
            session['userid'] = user['id']
            session['username'] = user['username']
            return jsonify({"success": True}), 200

        print("Password hash mismatch.")
        return jsonify({"error": "Password hash mismatch."}), 401

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        connection.close()

@app.route('/logout', methods=['POST'])
def logout():
    session.clear()  # Clear session data
    return redirect(url_for('index'))  # Redirect to the login page

@app.route('/chat', methods=['POST'])
def chat():
    if 'userid' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    user_message = request.json.get('message')
    if not user_message or len(user_message.strip()) == 0:
        raise BadRequest("Message is empty")

    try:
        response = requests.post(
            N8N_WEBHOOK_URL, 
            json={"chatInput": user_message},
            timeout=60
        )
        response.raise_for_status()
        ai_response = response.json().get('response', "No response received")

        save_message_to_db(user_message, ai_response, session['userid'])
        return jsonify({"response": ai_response})
    except requests.exceptions.RequestException as e:
        return jsonify({"error": "Failed to connect to n8n webhook.", "details": str(e)}), 500


def save_message_to_db(question, answer, userid):
    connection = get_db_connection()
    if connection:
        try:
            cursor = connection.cursor()
            cursor.execute("""
                INSERT INTO questions (questiontext, userid) VALUES (%s, %s)
            """, (question, userid))
            question_id = cursor.lastrowid

            cursor.execute("""
                INSERT INTO answers (answertext, questionid, userid) VALUES (%s, %s, %s)
            """, (answer, question_id, userid))
            connection.commit()
        except Error as e:
            print(f"Error saving message to database: {e}")
        finally:
            connection.close()

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    print(f"Starting Flask app on port {port}...")
    app.run(host='0.0.0.0', port=port)