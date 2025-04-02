from flask import Flask, request, jsonify
import pymysql
import hashlib
import re
import random
import nltk
import cv2
import pytesseract
import numpy as np
from nltk.corpus import stopwords
import logging
import tempfile  # Use tempfile to handle temporary files

# Configure logging
logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')

# AWS RDS Database Configuration
HOST = "textquiz.cfw2s808cp18.ap-south-1.rds.amazonaws.com"
USER = "admin"
PASSWORD = "nourishesbara"
DATABASE = "textquiz"

app = Flask(__name__)

# Global database connection
db_connection = None

def initialize_db_connection():
    """Initialize a single database connection."""
    global db_connection
    try:
        db_connection = pymysql.connect(
            host=HOST,
            user=USER,
            password=PASSWORD,
            database=DATABASE,
            connect_timeout=10  # Set a connection timeout
        )
        logging.info("Database connection established successfully.")
    except pymysql.MySQLError as e:
        logging.error(f"Failed to connect to the database: {e}")
        raise Exception("Failed to connect to the database. Please check your database configuration and network connectivity.")

@app.before_request
def setup():
    """Set up the database connection before handling the first request."""
    initialize_db_connection()

@app.teardown_appcontext
def close_db_connection(exception):
    """Close the database connection when the app context is torn down."""
    global db_connection
    if db_connection:
        db_connection.close()
        db_connection = None
        logging.info("Database connection closed.")

def create_database():
    """Create the database and tables if they don't already exist."""
    try:
        conn = pymysql.connect(
            host=HOST,
            user=USER,
            password=PASSWORD,
            connect_timeout=10  # Set a connection timeout
        )
        cursor = conn.cursor()

        # Create the database if it doesn't exist
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DATABASE}")
        conn.select_db(DATABASE)

        # Create users table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(255) UNIQUE NOT NULL,
            password VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')

        # Create quiz_results table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS quiz_results (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT,
            extracted_text TEXT,
            score INT,
            total_questions INT,
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
        ''')

        # Create quiz_questions table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS quiz_questions (
            id INT AUTO_INCREMENT PRIMARY KEY,
            quiz_id INT,
            question TEXT,
            correct_answer TEXT,
            options TEXT,
            user_answer TEXT,
            FOREIGN KEY (quiz_id) REFERENCES quiz_results (id)
        )
        ''')

        conn.commit()
        conn.close()
    except pymysql.MySQLError as e:
        logging.error(f"Error connecting to the database: {e}")
        raise Exception("Failed to connect to the database. Please check your database configuration and network connectivity.")

# Flag to ensure the database is initialized only once
database_initialized = False

@app.before_request
def initialize_database():
    """Initialize the database before handling the first request."""
    global database_initialized
    if not database_initialized:
        create_database()
        database_initialized = True

def preprocess_text(text):
    """Clean and preprocess the extracted text."""
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def extract_key_sentences(text, num_sentences=20):
    """Extract important sentences from the text."""
    sentences = nltk.sent_tokenize(text)
    sentences = [s for s in sentences if len(s.split()) > 5]
    if len(sentences) <= num_sentences:
        return sentences
    return random.sample(sentences, num_sentences)

def generate_quiz_question(sentence):
    """Generate an MCQ question from a sentence."""
    tokens = nltk.word_tokenize(sentence)
    tagged = nltk.pos_tag(tokens)
    candidates = [word for word, tag in tagged if tag.startswith(('NN', 'VB', 'JJ')) and len(word) > 3]

    if not candidates:
        return None

    word_to_replace = random.choice(candidates)
    question = sentence.replace(word_to_replace, "_______")
    stop_words = set(stopwords.words('english'))
    all_words = [word for word, tag in tagged if word.lower() not in stop_words and word != word_to_replace]
    common_words = ["example", "information", "knowledge", "important", "different", "process", "system"]

    incorrect_options = []
    while len(incorrect_options) < 3:
        if all_words:
            option = random.choice(all_words)
            if option not in incorrect_options:
                incorrect_options.append(option)
        elif common_words:
            option = random.choice(common_words)
            common_words.remove(option)
            if option not in incorrect_options:
                incorrect_options.append(option)
        else:
            incorrect_options.append(f"option{len(incorrect_options) + 1}")

    options = [word_to_replace] + incorrect_options
    random.shuffle(options)

    return {
        "question": question,
        "correct_answer": word_to_replace,
        "options": options
    }

def generate_quiz(text, num_questions=5):
    """Generate a quiz based on the extracted text."""
    cleaned_text = preprocess_text(text)
    key_sentences = extract_key_sentences(cleaned_text)
    questions = []
    attempts = 0
    max_attempts = min(30, len(key_sentences) * 2)

    while len(questions) < num_questions and attempts < max_attempts:
        if not key_sentences:
            break
        sentence = random.choice(key_sentences)
        key_sentences.remove(sentence)
        question = generate_quiz_question(sentence)
        if question:
            questions.append(question)
        attempts += 1

    return questions

@app.route('/api/preprocess', methods=['POST'])
def preprocess():
    data = request.json
    if 'text' not in data:
        return jsonify({'error': 'Text is required'}), 400
    cleaned_text = preprocess_text(data['text'])
    return jsonify({'cleaned_text': cleaned_text})

@app.route('/api/generate_quiz', methods=['POST'])
def generate_quiz_api():
    data = request.json
    if 'text' not in data or 'num_questions' not in data:
        return jsonify({'error': 'Text and num_questions are required'}), 400
    try:
        questions = generate_quiz(data['text'], data['num_questions'])
        return jsonify({'questions': questions})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/process_image', methods=['POST'])
def process_image():
    """Process an image and extract text using OCR."""
    try:
        file = request.files.get('image')
        if not file:
            return jsonify({'error': 'No image provided'}), 400

        # Save the image to a temporary file
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as temp_file:
            temp_path = temp_file.name
            file.save(temp_path)

        # Load and process the image
        image = cv2.imread(temp_path)
        if image is None:
            return jsonify({'error': 'Failed to load the image. Ensure it is a valid image file.'}), 400

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        denoised = cv2.bilateralFilter(gray, 9, 75, 75)
        adaptive_thresh = cv2.adaptiveThreshold(
            denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2
        )
        coords = np.column_stack(np.where(adaptive_thresh > 0))
        angle = cv2.minAreaRect(coords)[-1]
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle
        (h, w) = adaptive_thresh.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(adaptive_thresh, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        processed = cv2.morphologyEx(rotated, cv2.MORPH_CLOSE, kernel)
        processed = cv2.morphologyEx(processed, cv2.MORPH_OPEN, kernel)

        # Extract text using Tesseract
        pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'  # Update path if needed
        custom_config = r'--oem 3 --psm 6'
        extracted_text = pytesseract.image_to_string(processed, config=custom_config)

        # Clean up temporary file
        temp_file.close()

        if not extracted_text.strip():
            return jsonify({'error': 'OCR failed to extract text. Ensure the image contains readable text.'}), 400

        return jsonify({'extracted_text': extracted_text.strip()})
    except Exception as e:
        logging.error(f"Error processing image: {str(e)}")
        return jsonify({'error': f"Internal server error: {str(e)}"}), 500

@app.route('/api/users', methods=['GET'])
def get_users():
    """Fetch all users."""
    global db_connection
    cursor = db_connection.cursor(pymysql.cursors.DictCursor)
    cursor.execute("SELECT id, username, created_at FROM users")
    users = cursor.fetchall()
    return jsonify({'users': users})

@app.route('/api/register', methods=['POST'])
def register():
    """Register a new user."""
    global db_connection
    data = request.json
    if not data or 'username' not in data or 'password' not in data:
        return jsonify({'error': 'Username and password are required'}), 400

    username = data['username'].strip()
    password = data['password']

    if not username or not password:
        return jsonify({'error': 'Username and password cannot be empty'}), 400

    hashed_password = hashlib.sha256(password.encode()).hexdigest()
    cursor = db_connection.cursor()

    try:
        cursor.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, hashed_password))
        db_connection.commit()
        return jsonify({'message': 'User registered successfully'}), 201
    except pymysql.IntegrityError:
        return jsonify({'error': 'Username already exists'}), 409
    except Exception as e:
        logging.error(f"Error during registration: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/login', methods=['POST'])
def login():
    """Authenticate a user."""
    global db_connection
    data = request.json
    if 'username' not in data or 'password' not in data:
        return jsonify({'error': 'Username and password are required'}), 400

    username = data['username'].strip()
    password = data['password']
    hashed_password = hashlib.sha256(password.encode()).hexdigest()

    cursor = db_connection.cursor()
    try:
        cursor.execute("SELECT id FROM users WHERE username = %s AND password = %s", (username, hashed_password))
        user = cursor.fetchone()

        if user:
            return jsonify({'message': 'Login successful', 'user_id': user['id']}), 200
        else:
            return jsonify({'error': 'Invalid username or password'}), 401
    except Exception as e:
        logging.error(f"Error during login: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/quiz_results', methods=['POST'])
def save_quiz_results():
    """Save quiz results and questions."""
    global db_connection
    data = request.json
    try:
        user_id = data['user_id']
        extracted_text = data['extracted_text']
        score = data['score']
        total_questions = data['total_questions']
        results = data['results']

        cursor = db_connection.cursor()

        # Save quiz result
        cursor.execute(
            "INSERT INTO quiz_results (user_id, extracted_text, score, total_questions) VALUES (%s, %s, %s, %s)",
            (user_id, extracted_text[:500], score, total_questions)
        )
        quiz_id = cursor.lastrowid

        # Save individual questions
        for result in results:
            cursor.execute(
                "INSERT INTO quiz_questions (quiz_id, question, correct_answer, options, user_answer) VALUES (%s, %s, %s, %s, %s)",
                (
                    quiz_id,
                    result["question"],
                    result["correct_answer"],
                    ','.join(result["options"]),
                    result["user_answer"] if result["user_answer"] else ""
                )
            )

        db_connection.commit()
        return jsonify({"message": "Quiz results saved successfully"}), 200
    except Exception as e:
        db_connection.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/api/quiz_results', methods=['GET'])
def get_quiz_results():
    """Fetch quiz history for a user."""
    global db_connection
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({'error': 'User ID is required'}), 400
    try:
        cursor = db_connection.cursor(pymysql.cursors.DictCursor)
        cursor.execute(
            "SELECT id, date, score, total_questions, extracted_text FROM quiz_results WHERE user_id = %s ORDER BY date DESC",
            (user_id,)
        )
        results = cursor.fetchall()
        return jsonify({"quiz_results": results}), 200
    except Exception as e:
        logging.error(f"Error fetching quiz results: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/quiz_details/<int:quiz_id>', methods=['GET'])
def get_quiz_details(quiz_id):
    """Fetch quiz details by quiz ID."""
    global db_connection
    try:
        cursor = db_connection.cursor(pymysql.cursors.DictCursor)

        # Fetch quiz metadata
        cursor.execute(
            "SELECT date, score, total_questions, extracted_text FROM quiz_results WHERE id = %s",
            (quiz_id,)
        )
        quiz_metadata = cursor.fetchone()

        if not quiz_metadata:
            return jsonify({'error': 'Quiz not found'}), 404

        # Fetch quiz questions
        cursor.execute(
            "SELECT question, correct_answer, options, user_answer FROM quiz_questions WHERE quiz_id = %s",
            (quiz_id,)
        )
        questions = cursor.fetchall()

        return jsonify({'quiz_metadata': quiz_metadata, 'questions': questions}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8080, debug=True)
