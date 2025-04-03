import logging
from flask import Flask, request, jsonify
import sqlite3
import hashlib
import random
import nltk
import re
from datetime import datetime
import boto3
import pymysql
import pytesseract
from PIL import Image
import io
import base64
import os

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

nltk.download('punkt')
nltk.download('averaged_perceptron_tagger')
nltk.download('punkt_tab')
nltk.download('averaged_perceptron_tagger_eng')
app = Flask(__name__)

# AWS RDS Configuration
RDS_HOST = "textquiz.cfw2s808cp18.ap-south-1.rds.amazonaws.com"
RDS_USER = "admin"
RDS_PASSWORD = "nourishesbara"
RDS_DB = "textquiz"

# Establish RDS connection
def get_db_connection():
    return pymysql.connect(
        host=RDS_HOST,
        user=RDS_USER,
        password=RDS_PASSWORD,
        database=RDS_DB,
        cursorclass=pymysql.cursors.DictCursor
    )

# User Registration
@app.route('/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({"error": "Username and password are required"}), 400

    hashed_password = hashlib.sha256(password.encode()).hexdigest()

    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, hashed_password))
        conn.commit()
        return jsonify({"message": "User registered successfully"}), 201
    except pymysql.IntegrityError:
        return jsonify({"error": "Username already exists"}), 409
    finally:
        conn.close()

# User Login
@app.route('/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({"error": "Username and password are required"}), 400

    hashed_password = hashlib.sha256(password.encode()).hexdigest()

    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT id FROM users WHERE username = %s AND password = %s", (username, hashed_password))
            user = cursor.fetchone()
        if user:
            return jsonify({"message": "Login successful", "user_id": user['id']}), 200
        else:
            return jsonify({"error": "Invalid username or password"}), 401
    finally:
        conn.close()

# Fetch Quiz History
@app.route('/history/<int:user_id>', methods=['GET'])
def get_history(user_id):
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM quiz_results WHERE user_id = %s ORDER BY date DESC", (user_id,))
            history = cursor.fetchall()
        return jsonify(history), 200
    finally:
        conn.close()

# Save Quiz Results
@app.route('/results', methods=['POST'])
def save_results():
    data = request.json
    user_id = data.get('user_id')
    extracted_text = data.get('extracted_text')
    score = data.get('score')
    total_questions = data.get('total_questions')
    questions = data.get('questions')

    if not user_id or not extracted_text or score is None or total_questions is None or not questions:
        return jsonify({"error": "Invalid data"}), 400

    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO quiz_results (user_id, extracted_text, score, total_questions) VALUES (%s, %s, %s, %s)",
                (user_id, extracted_text[:500], score, total_questions)
            )
            quiz_id = cursor.lastrowid

            for question in questions:
                cursor.execute(
                    "INSERT INTO quiz_questions (quiz_id, question, correct_answer, options, user_answer) VALUES (%s, %s, %s, %s, %s)",
                    (quiz_id, question['question'], question['correct_answer'], ','.join(question['options']), question['user_answer'])
                )
        conn.commit()
        return jsonify({"message": "Results saved successfully"}), 201
    finally:
        conn.close()

# Ensure required NLTK data is downloaded


# Generate Quiz Questions with Difficulty Levels and Question Types
@app.route('/generate_quiz', methods=['POST'])
def generate_quiz():
    data = request.json
    text = data.get('text')
    num_questions = data.get('num_questions', 5)
    question_type = data.get('question_type', 'mcq')  # Default to MCQ
    difficulty = data.get('difficulty', 'medium')  # Default to medium difficulty

    if not text:
        return jsonify({"error": "Text is required"}), 400

    def preprocess_text(text):
        return re.sub(r'\s+', ' ', text).strip()

    def extract_key_sentences(text, num_sentences=20):
        sentences = nltk.sent_tokenize(text)
        sentences = [s for s in sentences if len(s.split()) > 5]
        return random.sample(sentences, min(num_sentences, len(sentences)))

    def generate_question(sentence, question_type):
        tokens = nltk.word_tokenize(sentence)
        tagged = nltk.pos_tag(tokens)
        candidates = [word for word, tag in tagged if tag.startswith(('NN', 'VB', 'JJ')) and len(word) > 3]

        if not candidates:
            return None

        word_to_replace = random.choice(candidates)

        if question_type == 'short_answer':
            return {"question": f"What is the meaning of '{word_to_replace}' in the context of the sentence?", "correct_answer": word_to_replace, "options": []}
        elif question_type == 'fill_in_the_blank':
            question = sentence.replace(word_to_replace, "_______")
            return {"question": question, "correct_answer": word_to_replace, "options": []}
        else:  # mcq
            question = sentence.replace(word_to_replace, "_______")
            options = [word_to_replace] + random.sample(candidates, min(3, len(candidates)))
            random.shuffle(options)
            return {"question": question, "correct_answer": word_to_replace, "options": options}

    try:
        logging.debug("Preprocessing text for quiz generation.")
        cleaned_text = preprocess_text(text)
        key_sentences = extract_key_sentences(cleaned_text)
        logging.debug(f"Extracted {len(key_sentences)} key sentences.")

        questions = [generate_question(s, question_type) for s in key_sentences if generate_question(s, question_type)]
        logging.debug(f"Generated {len(questions)} questions.")

        if not questions:
            return jsonify({"error": "Failed to generate quiz questions. The text might not contain enough meaningful content."}), 400

        return jsonify(questions[:num_questions]), 200
    except Exception as e:
        logging.error(f"Error generating quiz: {str(e)}", exc_info=True)
        return jsonify({"error": f"Failed to generate quiz: {str(e)}"}), 500

# Progress Tracking
@app.route('/progress/<int:user_id>', methods=['GET'])
def get_progress(user_id):
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT date, score, total_questions FROM quiz_results WHERE user_id = %s ORDER BY date DESC", (user_id,))
            progress = cursor.fetchall()
        return jsonify(progress), 200
    finally:
        conn.close()

# OCR Image Processing
@app.route('/process_image', methods=['POST'])
def process_image():
    # Set Tesseract path for Linux
    pytesseract.pytesseract.tesseract_cmd = "/usr/bin/tesseract"

    data = request.json
    image_base64 = data.get('image')

    if not image_base64:
        return jsonify({"error": "Image data is required"}), 400

    try:
        # Decode the base64 image
        image_data = base64.b64decode(image_base64)
        image = Image.open(io.BytesIO(image_data))

        # Perform OCR using pytesseract
        extracted_text = pytesseract.image_to_string(image)

        # Clean and preprocess the extracted text
        def preprocess_text(text):
            return re.sub(r'\s+', ' ', text).strip()

        cleaned_text = preprocess_text(extracted_text)

        return jsonify({"extracted_text": cleaned_text}), 200
    except Exception as e:
        return jsonify({"error": f"Failed to process image: {str(e)}"}), 500

if __name__ == '__main__':
    # Bind to all network interfaces to make the API accessible externally
    app.run(host="0.0.0.0", port=5000, debug=True)
