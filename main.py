import sys
import os
import re
import pytesseract
import requests
import base64
from datetime import datetime
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QLineEdit, QPushButton, QMessageBox, QFileDialog,
                             QRadioButton, QButtonGroup, QProgressBar, QTableWidget,
                             QTableWidgetItem, QTextEdit, QGroupBox, QGridLayout, QStackedWidget)
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

API_BASE_URL = "http://65.0.99.243:5000"  # Replace <EC2_PUBLIC_IP> with the actual public IP of your EC2 instance

def resource_path(relative_path):
    try:
        base_dir = sys._MEIPASS
    except Exception:
        base_dir = os.path.abspath(".")

    return os.path.join(base_dir, relative_path)

"""Clean and preprocess the extracted text"""
def preprocess_text(text):
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

"""Generate a quiz based on the extracted text"""
def generate_quiz(text, num_questions=10):
    cleaned_text = preprocess_text(text)
    try:
        response = requests.post(f"{API_BASE_URL}/generate_quiz", json={"text": cleaned_text, "num_questions": num_questions}, timeout=20)
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 400:
            error_message = response.json().get("error", "Invalid request.")
            QMessageBox.warning(None, "Quiz Generation Error", f"Failed to generate quiz questions: {error_message}")
            return []
        elif response.status_code == 500:
            error_message = response.json().get("error", "Internal server error.")
            QMessageBox.critical(None, "Server Error", f"Failed to generate quiz questions: {error_message}")
            return []
        else:
            QMessageBox.warning(None, "Quiz Generation Error", f"Unexpected server response: {response.status_code}")
            return []
    except requests.exceptions.ConnectTimeout:
        QMessageBox.critical(None, "Connection Timeout", "The server took too long to respond. Please try again later.")
        return []
    except requests.exceptions.RequestException as e:
        QMessageBox.critical(None, "Connection Error", f"Failed to connect to the server: {str(e)}")
        return []

# Custom Widgets
"""Custom QPushButton with rounded corners"""
class RoundedButton(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setMinimumHeight(40)
        self.setMaximumWidth(150)
        self.setStyleSheet("""
            QPushButton {
                background-color: #6FA3EF;
                color: white;
                border-radius: 8px;
                padding: 10px 14px;
                font-weight: bold;
                font-size: 14px;
                border: none;
                transition: background-color 0.3s, transform 0.1s;
            }
            QPushButton:hover {
                background-color: #5A9BEF;
                transform: scale(1.05);
            }
            QPushButton:pressed {
                background-color: #4A86E8;
                transform: scale(0.98);
            }
            QPushButton:disabled {
                background-color: #A0A0A0;
                color: #E0E0E0;
            }
        """)

"""Login window for the application"""
class LoginWindow(QWidget):
    login_successful = pyqtSignal(int, str)
    register_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("TextQuiz - Login")
        self.resize(500, 500)  # Increased width
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(60, 20, 60, 20)  # Increased horizontal margins
        title_label = QLabel("TextQuiz")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("""
            font-size: 48px; 
            font-weight: bold; 
            margin: 20px 0;
            color: #333;
        """)
        form_container = QWidget()
        form_layout = QVBoxLayout(form_container)
        form_layout.setSpacing(15)
        form_layout.setContentsMargins(0, 0, 0, 0)
        username_label = QLabel("Username")
        username_label.setStyleSheet("font-weight: bold; color: #555;")
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("username")
        self.username_input.setStyleSheet("""
            QLineEdit {
                padding: 10px;
                border: 1px solid #ddd;
                border-radius: 5px;
                width: 100%;  /* Ensure full width */
            }
        """)
        password_label = QLabel("Password")
        password_label.setStyleSheet("font-weight: bold; color: #555;")
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("password")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setStyleSheet("""
            QLineEdit {
                padding: 10px;
                border: 1px solid #ddd;
                border-radius: 5px;
                width: 300%;  /* Ensure full width */
            }
        """)
        self.login_button = RoundedButton("Login")
        self.login_button.setStyleSheet("""
            QPushButton {
            background-color: #4CAF50;
            color: white;
            padding: 12px;
            border: none;
            border-radius: 5px;
            font-weight: bold;
            width: 50px;  /* Fixed width */
        }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        self.login_button.clicked.connect(self.login)
        self.register_button = QPushButton("Don't have an account? Register")
        self.register_button.setStyleSheet("""
            QPushButton {
                border: none; 
                color: #2196F3;
                background-color: transparent;
            }
            QPushButton:hover {
                text-decoration: underline;
            }
        """)
        self.register_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.register_button.clicked.connect(self.register)
        form_layout.addWidget(username_label)
        form_layout.addWidget(self.username_input)
        form_layout.addWidget(password_label)
        form_layout.addWidget(self.password_input)
        form_layout.addWidget(self.login_button)
        center_layout = QHBoxLayout()
        center_layout.addStretch(1)
        center_layout.addWidget(form_container)
        center_layout.addStretch(1)
        main_layout.addWidget(title_label)
        main_layout.addLayout(center_layout)
        main_layout.addWidget(self.register_button, alignment=Qt.AlignmentFlag.AlignCenter)
        self.setLayout(main_layout)

    def login(self):
        username = self.username_input.text().strip()
        password = self.password_input.text()
        if not username or not password:
            QMessageBox.warning(self, "Login Error", "Please enter both username and password.")
            return
        try:
            response = requests.post(f"{API_BASE_URL}/login", json={"username": username, "password": password}, timeout=10)
            if response.status_code == 200:
                data = response.json()
                self.login_successful.emit(data['user_id'], username)
            else:
                QMessageBox.warning(self, "Login Failed", response.json().get("error", "Unknown error"))
        except requests.exceptions.RequestException as e:
            QMessageBox.critical(self, "Connection Error", f"Failed to connect to the server: {str(e)}")

    def register(self):
        self.register_requested.emit()

"""Registration window for new users"""
class RegisterWindow(QWidget):
    register_successful = pyqtSignal()
    back_to_login = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("TextQuiz - Register")
        self.resize(500, 500)  # Increased width
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(60, 20, 60, 20)  # Increased horizontal margins
        title_label = QLabel("Create Account")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("""
            font-size: 36px; 
            font-weight: bold; 
            margin: 20px 0;
            color: #333;
        """)
        form_container = QWidget()
        form_layout = QVBoxLayout(form_container)
        form_layout.setSpacing(15)
        form_layout.setContentsMargins(0, 0, 0, 0)
        username_label = QLabel("Username")
        username_label.setStyleSheet("font-weight: bold; color: #555;")
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Choose a username")
        self.username_input.setStyleSheet("""
            QLineEdit {
                padding: 10px;
                border: 1px solid #ddd;
                border-radius: 5px;
                width: 300%;  /* Ensure full width */
            }
        """)
        password_label = QLabel("Password")
        password_label.setStyleSheet("font-weight: bold; color: #555;")
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("password")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setStyleSheet("""
            QLineEdit {
                padding: 10px;
                border: 1px solid #ddd;
                border-radius: 5px;
                width: 300%;  /* Ensure full width */
            }
        """)
        confirm_password_label = QLabel("Confirm Password")
        confirm_password_label.setStyleSheet("font-weight: bold; color: #555;")
        self.confirm_password_input = QLineEdit()
        self.confirm_password_input.setPlaceholderText("Confirm your password")
        self.confirm_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm_password_input.setStyleSheet("""
            QLineEdit {
                padding: 10px;
                border: 1px solid #ddd;
                border-radius: 5px;
                width: 300%;  /* Ensure full width */
            }
        """)
        self.register_button = RoundedButton("Register")
        self.register_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 12px;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        self.register_button.clicked.connect(self.register)
        self.back_button = QPushButton("Already have an account? Login")
        self.back_button.setStyleSheet("""
            QPushButton {
                border: none; 
                color: #2196F3;
                background-color: transparent;
            }
            QPushButton:hover {
                text-decoration: underline;
            }
        """)
        self.back_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.back_button.clicked.connect(self.go_back)
        form_layout.addWidget(username_label)
        form_layout.addWidget(self.username_input)
        form_layout.addWidget(password_label)
        form_layout.addWidget(self.password_input)
        form_layout.addWidget(confirm_password_label)
        form_layout.addWidget(self.confirm_password_input)
        form_layout.addWidget(self.register_button)
        center_layout = QHBoxLayout()
        center_layout.addStretch(1)
        center_layout.addWidget(form_container)
        center_layout.addStretch(1)
        main_layout.addWidget(title_label)
        main_layout.addLayout(center_layout)
        main_layout.addWidget(self.back_button, alignment=Qt.AlignmentFlag.AlignCenter)
        self.setLayout(main_layout)

    def register(self):
        username = self.username_input.text().strip()
        password = self.password_input.text()
        confirm_password = self.confirm_password_input.text()
        if not username or not password:
            QMessageBox.warning(self, "Registration Error", "Please fill all fields.")
            return
        if password != confirm_password:
            QMessageBox.warning(self, "Registration Error", "Passwords do not match.")
            return
        try:
            response = requests.post(f"{API_BASE_URL}/register", json={"username": username, "password": password}, timeout=10)
            if response.status_code == 201:
                QMessageBox.information(self, "Registration Successful", "Your account has been created successfully.")
                self.register_successful.emit()
            else:
                QMessageBox.warning(self, "Registration Error", response.json().get("error", "Unknown error"))
        except requests.exceptions.RequestException as e:
            QMessageBox.critical(self, "Connection Error", f"Failed to connect to the server: {str(e)}")

    def go_back(self):
        self.back_to_login.emit()

class HistoryWindow(QWidget):
    """Window for displaying quiz history"""
    back_requested = pyqtSignal()
    view_details_requested = pyqtSignal(int)

    def __init__(self, user_id, parent=None):
        super().__init__(parent)
        self.user_id = user_id
        self.init_ui()
        self.load_history()

    def init_ui(self):
        self.setWindowTitle("TextQuiz - Quiz History")
        self.resize(700, 500)
        main_layout = QVBoxLayout()
        title_label = QLabel("Quiz History")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("font-size: 22px; font-weight: bold; margin: 10px;")
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(3)
        self.history_table.setHorizontalHeaderLabels(["Date", "Score", "questions"])
        self.history_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.history_table.horizontalHeader().setStretchLastSection(True)
        self.history_table.setColumnWidth(0, 170)
        self.history_table.setColumnWidth(1, 100)
        self.history_table.setColumnWidth(2, 400)
        self.back_button = RoundedButton("Main Menu")
        self.back_button.clicked.connect(self.go_back)
        main_layout.addWidget(title_label)
        main_layout.addWidget(self.history_table)
        main_layout.addWidget(self.back_button)
        self.setLayout(main_layout)

    def load_history(self):
        response = requests.get(f"{API_BASE_URL}/history/{self.user_id}")
        if response.status_code == 200:
            results = response.json()
            self.history_table.setRowCount(len(results))
            for i, result in enumerate(results):
                date_item = QTableWidgetItem(result["date"])
                self.history_table.setItem(i, 0, date_item)
                score_item = QTableWidgetItem(f"{result['score']}/{result['total_questions']}")
                self.history_table.setItem(i, 1, score_item)
                text_item = QTableWidgetItem(result["extracted_text"][:50] + "...")
                self.history_table.setItem(i, 2, text_item)
        else:
            QMessageBox.warning(self, "Error", "Failed to load history.")

    def go_back(self):
        self.back_requested.emit()

class ResultsWindow(QWidget):
    """Window for displaying quiz results"""
    new_quiz_requested = pyqtSignal()
    back_to_menu_requested = pyqtSignal()

    def __init__(self, results, extracted_text, user_id, parent=None):
        super().__init__(parent)
        self.results = results
        self.extracted_text = extracted_text
        self.user_id = user_id
        self.init_ui()
        self.calculate_score()
        self.save_results()

    def init_ui(self):
        self.setWindowTitle("TextQuiz - Results")
        self.resize(700, 550)
        main_layout = QVBoxLayout()
        title_label = QLabel("Quiz Results")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("font-size: 22px; font-weight: bold; margin: 10px;")
        self.score_label = QLabel()
        self.score_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.score_label.setStyleSheet("font-size: 18px; margin: 15px; font-weight: bold;")
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(4)
        self.results_table.setHorizontalHeaderLabels(["Question", "Your Answer", "Correct Answer", "Result"])
        self.results_table.horizontalHeader().setStretchLastSection(True)
        self.results_table.setWordWrap(True)
        self.results_table.setColumnWidth(0, 280)
        self.results_table.setColumnWidth(1, 120)
        self.results_table.setColumnWidth(2, 120)
        buttons_layout = QHBoxLayout()
        self.new_quiz_button = RoundedButton("New Quiz")
        self.new_quiz_button.clicked.connect(self.new_quiz)
        self.menu_button = RoundedButton("Main Menu")
        self.menu_button.clicked.connect(self.back_to_menu)
        buttons_layout.addWidget(self.new_quiz_button)
        buttons_layout.addWidget(self.menu_button)
        main_layout.addWidget(title_label)
        main_layout.addWidget(self.score_label)
        main_layout.addWidget(self.results_table)
        main_layout.addLayout(buttons_layout)
        self.setLayout(main_layout)

    def calculate_score(self):
        correct_count = 0
        self.results_table.setRowCount(len(self.results))
        for i, result in enumerate(self.results):
            question_item = QTableWidgetItem(result["question"])
            question_item.setFlags(question_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.results_table.setItem(i, 0, question_item)
            user_answer = result["user_answer"] if result["user_answer"] else "No answer"
            user_answer_item = QTableWidgetItem(user_answer)
            user_answer_item.setFlags(user_answer_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.results_table.setItem(i, 1, user_answer_item)
            correct_answer_item = QTableWidgetItem(result["correct_answer"])
            correct_answer_item.setFlags(correct_answer_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.results_table.setItem(i, 2, correct_answer_item)
            is_correct = result["user_answer"] == result["correct_answer"]
            if is_correct:
                correct_count += 1
                result_text = "Correct"
                result_color = "green"
            else:
                result_text = "Incorrect"
                result_color = "red"
            result_item = QTableWidgetItem(result_text)
            result_item.setFlags(result_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            result_item.setForeground(Qt.GlobalColor.green if is_correct else Qt.GlobalColor.red)
            self.results_table.setItem(i, 3, result_item)
        for i in range(len(self.results)):
            self.results_table.resizeRowToContents(i)
        total_questions = len(self.results)
        self.score = correct_count
        self.total = total_questions
        score_percent = (correct_count / total_questions) * 100 if total_questions > 0 else 0
        self.score_label.setText(f"Your Score: {correct_count}/{total_questions} ({score_percent:.1f}%)")

    def save_results(self):
        data = {
            "user_id": self.user_id,
            "extracted_text": self.extracted_text,
            "score": self.score,
            "total_questions": self.total,
            "questions": self.results
        }
        response = requests.post(f"{API_BASE_URL}/results", json=data)
        if response.status_code != 201:
            QMessageBox.warning(self, "Error", "Failed to save results.")

    def new_quiz(self):
        self.new_quiz_requested.emit()

    def back_to_menu(self):
        self.back_to_menu_requested.emit()

class ImageProcessingWindow(QWidget):
    """Window for uploading and processing images"""
    quiz_ready = pyqtSignal(str)
    back_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.image_path = None
        self.extracted_text = ""
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("TextQuiz - Image Processing")
        self.resize(700, 550)

        # Main layout
        main_layout = QVBoxLayout()

        # Title
        title_label = QLabel("Text Quiz")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("font-size: 30px; font-weight: bold; margin: 10px;")

        # Image display area
        self.image_label = QLabel("No image selected")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet("border: 2px dashed #aaa; padding: 20px; background-color: #f8f9fa;")
        self.image_label.setMinimumHeight(250)

        # Upload button
        self.upload_button = RoundedButton("Upload Image")
        self.upload_button.clicked.connect(self.upload_image)

        # Process button
        self.process_button = RoundedButton("Process Image")
        self.process_button.clicked.connect(self.process_image)
        self.process_button.setEnabled(False)

        # Text preview
        text_preview_label = QLabel("Extracted Text:")
        self.text_preview = QTextEdit()
        self.text_preview.setReadOnly(True)
        self.text_preview.setMinimumHeight(100)

        # Continue button
        self.continue_button = RoundedButton("Start Quiz")
        self.continue_button.clicked.connect(self.start_quiz)
        self.continue_button.setEnabled(False)

        # Back button
        self.back_button = RoundedButton("Main Menu")
        self.back_button.clicked.connect(self.go_back)

        # Add widgets to main layout
        main_layout.addWidget(title_label)
        main_layout.addWidget(self.image_label)

        # Buttons layout
        buttons_layout = QHBoxLayout()
        buttons_layout.addWidget(self.upload_button)
        buttons_layout.addWidget(self.process_button)
        main_layout.addLayout(buttons_layout)

        main_layout.addWidget(text_preview_label)
        main_layout.addWidget(self.text_preview)
        main_layout.addWidget(self.continue_button)
        main_layout.addWidget(self.back_button)

        self.setLayout(main_layout)

    def upload_image(self):
        file_dialog = QFileDialog()
        file_path, _ = file_dialog.getOpenFileName(
            self, "Select Image", "", "Image Files (*.png *.jpg *.jpeg *.bmp)"
        )

        if file_path:
            self.image_path = file_path

            # Display image
            pixmap = QPixmap(file_path)
            if not pixmap.isNull():
                pixmap = pixmap.scaled(
                    self.image_label.width(), self.image_label.height(),
                    Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
                )
                self.image_label.setPixmap(pixmap)
                self.process_button.setEnabled(True)
            else:
                QMessageBox.warning(self, "Image Error", "Failed to load the image.")
                self.image_label.setText("No image selected")
                self.process_button.setEnabled(False)

    def process_image(self):
        # Set Tesseract path for Linux
        pytesseract.pytesseract.tesseract_cmd = "/usr/bin/tesseract"

        if not self.image_path:
            return

        try:
            # Read the image and encode it in base64
            with open(self.image_path, "rb") as image_file:
                image_base64 = base64.b64encode(image_file.read()).decode('utf-8')

            # Send the image to the API for processing
            response = requests.post(f"{API_BASE_URL}/process_image", json={"image": image_base64}, timeout=10)

            if response.status_code == 200:
                self.extracted_text = response.json().get("extracted_text", "")
                self.text_preview.setText(self.extracted_text)

                # Enable continue button if text was extracted
                if self.extracted_text:
                    self.continue_button.setEnabled(True)
                    QMessageBox.information(self, "Processing Complete", "Text extraction completed successfully.")
                else:
                    QMessageBox.warning(self, "Processing Warning", "No text was extracted from the image.")
            else:
                error_message = response.json().get("error", "Unknown error occurred.")
                QMessageBox.critical(self, "Processing Error", error_message)
        except requests.exceptions.RequestException as e:
            QMessageBox.critical(self, "Connection Error", f"Failed to connect to the server: {str(e)}")

    def start_quiz(self):
        if self.extracted_text.strip():
            self.quiz_ready.emit(self.extracted_text)
        else:
            QMessageBox.warning(self, "Error", "No text available for quiz generation.")

    def go_back(self):
        self.back_requested.emit()

class QuizWindow(QWidget):
    """Window for taking the quiz with a timer"""
    quiz_completed = pyqtSignal(list, str)
    back_requested = pyqtSignal()

    def __init__(self, extracted_text, parent=None, time_limit=30):
        super().__init__(parent)
        self.extracted_text = extracted_text
        self.questions = []
        self.current_question = 0
        self.selected_answers = []
        self.time_limit = time_limit  # Time limit in seconds per question
        self.remaining_time = self.time_limit
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_timer)
        self.init_ui()
        self.generate_quiz()

    def init_ui(self):
        self.setWindowTitle("TextQuiz - Quiz")
        self.resize(700, 500)

        # Main layout
        main_layout = QVBoxLayout()

        # Title
        title_label = QLabel("Quiz")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("font-size: 22px; font-weight: bold; margin: 10px;")

        # Progress indicator
        self.progress_label = QLabel("Question 0/0")
        self.progress_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Timer display
        self.timer_label = QLabel(f"Time Remaining: {self.time_limit} seconds")
        self.timer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.timer_label.setStyleSheet("font-size: 16px; color: red; margin: 10px;")

        # Question display
        self.question_label = QLabel("Generating questions...")
        self.question_label.setWordWrap(True)
        self.question_label.setStyleSheet("font-size: 16px; margin: 15px 0;")

        # Options group
        self.options_group = QGroupBox("Select your answer:")
        self.options_layout = QVBoxLayout()
        self.options_group.setLayout(self.options_layout)

        # Navigation buttons
        nav_layout = QHBoxLayout()
        self.prev_button = QPushButton("Previous")
        self.prev_button.clicked.connect(self.prev_question)
        self.prev_button.setEnabled(False)

        self.next_button = QPushButton("Next")
        self.next_button.clicked.connect(self.next_question)

        self.submit_button = RoundedButton("Submit Quiz")
        self.submit_button.clicked.connect(self.submit_quiz)
        self.submit_button.setVisible(False)

        nav_layout.addWidget(self.prev_button)
        nav_layout.addWidget(self.next_button)

        # Back button
        self.back_button = RoundedButton("Main Menu")
        self.back_button.clicked.connect(self.confirm_back)

        # Add widgets to main layout
        main_layout.addWidget(title_label)
        main_layout.addWidget(self.progress_label)
        main_layout.addWidget(self.timer_label)
        main_layout.addWidget(self.question_label)
        main_layout.addWidget(self.options_group)
        main_layout.addLayout(nav_layout)
        main_layout.addWidget(self.submit_button, alignment=Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.back_button)

        self.setLayout(main_layout)

    def start_timer(self):
        """Start the timer for the current question."""
        self.remaining_time = self.time_limit
        self.update_timer_label()
        self.timer.start(1000)

    def update_timer(self):
        """Update the timer and handle timeout."""
        self.remaining_time -= 1
        self.update_timer_label()
        if self.remaining_time <= 0:
            self.timer.stop()
            QMessageBox.warning(self, "Time's Up", "You ran out of time for this question!")
            self.next_question()

    def update_timer_label(self):
        """Update the timer label with the remaining time."""
        self.timer_label.setText(f"Time Remaining: {self.remaining_time} seconds")

    def generate_quiz(self):
        # Show progress or loading indicator
        self.question_label.setText("Generating questions... Please wait.")
        QApplication.processEvents()

        # Generate quiz questions
        try:
            self.questions = generate_quiz(self.extracted_text, num_questions=5)

            if not self.questions:
                QMessageBox.warning(self, "Quiz Generation Error",
                                    "Failed to generate quiz questions from the extracted text. "
                                    "The text might be too short or not contain enough meaningful content.")
                self.back_requested.emit()
                return

            # Initialize selected answers list
            self.selected_answers = [None] * len(self.questions)

            # Display first question
            self.current_question = 0
            self.display_question()

        except Exception as e:
            QMessageBox.critical(self, "Quiz Generation Error",
                                 f"An error occurred while generating the quiz: {str(e)}")
            self.back_requested.emit()

    def display_question(self):
        # Clear previous options
        while self.options_layout.count():
            item = self.options_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.option_buttons = []
        self.option_group = QButtonGroup(self)

        # Update progress label
        self.progress_label.setText(f"Question {self.current_question + 1}/{len(self.questions)}")

        # Get current question
        question_data = self.questions[self.current_question]

        # Set question text
        self.question_label.setText(question_data["question"])

        # Add options
        for i, option in enumerate(question_data["options"]):
            radio = QRadioButton(option)
            self.option_buttons.append(radio)
            self.option_group.addButton(radio, i)
            self.options_layout.addWidget(radio)

        # Restore previous selection if any
        if self.selected_answers[self.current_question] is not None:
            selected_idx = question_data["options"].index(self.selected_answers[self.current_question])
            if 0 <= selected_idx < len(self.option_buttons):
                self.option_buttons[selected_idx].setChecked(True)

        # Update navigation buttons
        self.prev_button.setEnabled(self.current_question > 0)

        if self.current_question == len(self.questions) - 1:
            self.next_button.setVisible(False)
            self.submit_button.setVisible(True)
        else:
            self.next_button.setVisible(True)
            self.submit_button.setVisible(False)

        self.start_timer()  # Start the timer for the current question

    def next_question(self):
        # Stop the timer before moving to the next question
        self.timer.stop()
        # Save current answer
        selected_button = self.option_group.checkedButton()
        if selected_button:
            selected_idx = self.option_group.id(selected_button)
            self.selected_answers[self.current_question] = self.questions[self.current_question]["options"][
                selected_idx]

        # Move to next question
        if self.current_question < len(self.questions) - 1:
            self.current_question += 1
            self.display_question()

    def prev_question(self):
        # Stop the timer before moving to the previous question
        self.timer.stop()
        # Save current answer
        selected_button = self.option_group.checkedButton()
        if selected_button:
            selected_idx = self.option_group.id(selected_button)
            self.selected_answers[self.current_question] = self.questions[self.current_question]["options"][
                selected_idx]

        # Move to previous question
        if self.current_question > 0:
            self.current_question -= 1
            self.display_question()

    def submit_quiz(self):
        # Stop the timer when submitting the quiz
        self.timer.stop()
        # Save answer for the last question
        selected_button = self.option_group.checkedButton()
        if selected_button:
            selected_idx = self.option_group.id(selected_button)
            self.selected_answers[self.current_question] = self.questions[self.current_question]["options"][
                selected_idx]

        # Check if all questions are answered
        if None in self.selected_answers:
            unanswered = self.selected_answers.count(None)
            reply = QMessageBox.question(
                self,
                "Incomplete Quiz",
                f"You have {unanswered} unanswered question(s). Do you want to submit anyway?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )

            if reply == QMessageBox.StandardButton.No:
                # Find the first unanswered question
                self.current_question = self.selected_answers.index(None)
                self.display_question()
                return

        # Build result data with questions and answers
        result_data = []
        for i, question_data in enumerate(self.questions):
            result_data.append({
                "question": question_data["question"],
                "correct_answer": question_data["correct_answer"],
                "options": question_data["options"],
                "user_answer": self.selected_answers[i] if i < len(self.selected_answers) else None
            })

        # Emit signal with quiz results
        self.quiz_completed.emit(result_data, self.extracted_text)

    def confirm_back(self):
        # Stop the timer when confirming to go back
        self.timer.stop()
        reply = QMessageBox.question(
            self,
            "Leave Quiz",
            "Are you sure you want to leave? Your progress will be lost.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.back_requested.emit()

class QuizDetailsWindow(QWidget):
    """Window for displaying details of a specific quiz"""
    back_requested = pyqtSignal()

    def __init__(self, quiz_id, parent=None):
        super().__init__(parent)
        self.quiz_id = quiz_id
        self.init_ui()
        self.load_details()

    def init_ui(self):
        self.setWindowTitle("TextQuiz - Quiz Details")
        self.resize(700, 550)

        # Main layout
        main_layout = QVBoxLayout()

        # Title
        title_label = QLabel("Quiz Details")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("font-size: 22px; font-weight: bold; margin: 10px;")

        # Quiz metadata
        self.meta_label = QLabel()
        self.meta_label.setStyleSheet("font-size: 16px; margin: 10px;")

        # Text preview
        text_group = QGroupBox("Extracted Text")
        text_layout = QVBoxLayout()
        self.text_preview = QTextEdit()
        self.text_preview.setReadOnly(True)
        text_layout.addWidget(self.text_preview)
        text_group.setLayout(text_layout)

        # Questions and answers
        questions_group = QGroupBox("Questions and Answers")
        self.questions_layout = QVBoxLayout()
        questions_group.setLayout(self.questions_layout)

        # Back button
        self.back_button = RoundedButton("History")
        self.back_button.clicked.connect(self.go_back)

        # Add widgets to main layout
        main_layout.addWidget(title_label)
        main_layout.addWidget(self.meta_label)
        main_layout.addWidget(text_group)
        main_layout.addWidget(questions_group)
        main_layout.addWidget(self.back_button)

        self.setLayout(main_layout)

    def load_details(self):
        response = requests.get(f"{API_BASE_URL}/history/{self.quiz_id}")
        if response.status_code == 200:
            data = response.json()

            # Display metadata
            date_str = datetime.fromisoformat(data['date']).strftime("%Y-%m-%d %H:%M")
            score_percent = (data['score'] / data['total_questions']) * 100 if data['total_questions'] > 0 else 0
            self.meta_label.setText(f"Date: {date_str}  |  Score: {data['score']}/{data['total_questions']} ({score_percent:.1f}%)")

            # Display text
            self.text_preview.setText(data['extracted_text'])

            # Display questions
            for question in data['questions']:
                q_group = QGroupBox("Question")
                q_layout = QVBoxLayout()

                # Question text
                q_label = QLabel(question['question'])
                q_label.setWordWrap(True)
                q_layout.addWidget(q_label)

                # Options
                options_layout = QVBoxLayout()
                for option in question['options']:
                    option_label = QLabel(f"• {option}")
                    if option == question['correct_answer']:
                        option_label.setStyleSheet("color: green; font-weight: bold;")
                    elif option == question['user_answer']:
                        option_label.setStyleSheet("color: red; font-weight: bold;")
                    options_layout.addWidget(option_label)
                q_layout.addLayout(options_layout)

                # Result
                result_label = QLabel(f"Result: {'Correct' if question['user_answer'] == question['correct_answer'] else 'Incorrect'}")
                result_label.setStyleSheet("color: green;" if question['user_answer'] == question['correct_answer'] else "color: red;")
                q_layout.addWidget(result_label)

                q_group.setLayout(q_layout)
                self.questions_layout.addWidget(q_group)
        else:
            QMessageBox.warning(self, "Error", "Failed to load quiz details.")

    def go_back(self):
        self.back_requested.emit()

class ProgressWindow(QWidget):
    """Window for displaying user progress"""
    back_requested = pyqtSignal()

    def __init__(self, user_id, parent=None):
        super().__init__(parent)
        self.user_id = user_id
        self.init_ui()
        self.load_progress()

    def init_ui(self):
        self.setWindowTitle("TextQuiz - Progress")
        self.resize(800, 600)

        # Main layout
        main_layout = QVBoxLayout()

        # Title
        title_label = QLabel("Your Progress")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("""
            font-size: 28px; 
            font-weight: bold; 
            margin: 20px 0;
            color: #333;
        """)

        # Progress table
        self.progress_table = QTableWidget()
        self.progress_table.setColumnCount(3)
        self.progress_table.setHorizontalHeaderLabels(["Date", "Score", "Total Questions"])
        self.progress_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.progress_table.horizontalHeader().setStretchLastSection(True)
        self.progress_table.setAlternatingRowColors(True)
        self.progress_table.setStyleSheet("""
            QTableWidget {
                border: 1px solid #ddd;
                gridline-color: #ccc;
                font-size: 14px;
            }
            QHeaderView::section {
                background-color: #f0f0f0;
                font-weight: bold;
                border: 1px solid #ddd;
            }
            QTableWidget::item {
                padding: 10px;
            }
            QTableWidget::item:selected {
                background-color: #6FA3EF;
                color: white;
            }
        """)

        # Graph area
        self.figure = plt.figure()
        self.canvas = FigureCanvas(self.figure)

        # Back button
        self.back_button = RoundedButton("Back")
        self.back_button.setMinimumHeight(50)
        self.back_button.clicked.connect(self.go_back)
        self.back_button.setStyleSheet("""
            QPushButton {
                background-color: #FF5722;
                color: white;
                font-size: 16px;
                font-weight: bold;
                border-radius: 8px;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background-color: #E64A19;
            }
        """)

        # Add widgets to layout
        main_layout.addWidget(title_label)
        main_layout.addWidget(self.progress_table)
        main_layout.addWidget(self.canvas)
        main_layout.addWidget(self.back_button, alignment=Qt.AlignmentFlag.AlignCenter)

        self.setLayout(main_layout)

    def load_progress(self):
        response = requests.get(f"{API_BASE_URL}/progress/{self.user_id}")
        if response.status_code == 200:
            results = response.json()
            self.progress_table.setRowCount(len(results))
            dates = []
            scores = []
            totals = []

            for i, result in enumerate(results):
                date_item = QTableWidgetItem(result["date"])
                date_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.progress_table.setItem(i, 0, date_item)

                score_item = QTableWidgetItem(f"{result['score']}/{result['total_questions']}")
                score_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.progress_table.setItem(i, 1, score_item)

                total_item = QTableWidgetItem(str(result["total_questions"]))
                total_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.progress_table.setItem(i, 2, total_item)

                # Collect data for the graph
                dates.append(result["date"])
                scores.append(result["score"])
                totals.append(result["total_questions"])

            self.progress_table.resizeColumnsToContents()
            self.progress_table.resizeRowsToContents()

            # Plot the graph
            self.plot_progress(dates, scores, totals)
        else:
            QMessageBox.warning(self, "Error", "Failed to load progress.")

    def plot_progress(self, dates, scores, totals):
        self.figure.clear()
        ax = self.figure.add_subplot(111)

        # Plot scores with a blue line and fill the area under the curve
        ax.plot(dates, scores, label="Score", marker="o", color="blue", linewidth=2)
        ax.fill_between(dates, scores, color="blue", alpha=0.2)

        # Plot total questions with a green line and fill the area under the curve
        ax.plot(dates, totals, label="Total Questions", marker="o", color="green", linewidth=2)
        ax.fill_between(dates, totals, color="green", alpha=0.2)

        # Add title, labels, legend, and grid
        ax.set_title("Progress Over Time", fontsize=10, fontweight="bold")
        ax.set_xlabel("Date", fontsize=1)
        ax.set_ylabel("Score / Total Questions", fontsize=10)
        ax.legend(loc="upper left", fontsize=10)
        ax.grid(True, linestyle="--", alpha=0.6)

        # Rotate x-axis labels for better readability
        ax.tick_params(axis="x", rotation=90)

        self.canvas.draw()

    def go_back(self):
        self.back_requested.emit()

class MainMenuWindow(QWidget):
    """Main menu window for the application"""
    logout_requested = pyqtSignal()
    start_quiz_requested = pyqtSignal()
    view_history_requested = pyqtSignal()
    view_progress_requested = pyqtSignal()

    def __init__(self, user_id, username, parent=None):
        super().__init__(parent)
        self.user_id = user_id
        self.username = username
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("TextQuiz - Main Menu")
        self.resize(600, 450)

        # Main layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(40, 20, 40, 20)

        # Welcome message
        welcome_label = QLabel(f"Welcome, {self.username}!")
        welcome_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        welcome_label.setStyleSheet("""
            font-size: 28px; 
            font-weight: bold; 
            margin: 20px 0;
            color: #333;
        """)

        # Container for main buttons
        buttons_container = QWidget()
        buttons_layout = QVBoxLayout(buttons_container)
        buttons_layout.setSpacing(25)
        buttons_layout.setContentsMargins(0, 0, 0, 0)

        # Horizontal layout for Start Quiz and View History
        quiz_buttons_layout = QHBoxLayout()
        quiz_buttons_layout.setSpacing(25)

        # Start Quiz button
        self.start_quiz_button = RoundedButton("New Quiz")
        self.start_quiz_button.setMinimumHeight(80)
        self.start_quiz_button.setMinimumWidth(200)
        self.start_quiz_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 10px;
                font-size: 18px;
                font-weight: bold;
                padding: 15px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        self.start_quiz_button.clicked.connect(self.start_quiz)

        # View History button
        self.view_history_button = RoundedButton("Quiz History")
        self.view_history_button.setMinimumHeight(80)
        self.view_history_button.setMinimumWidth(200)
        self.view_history_button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 10px;
                font-size: 18px;
                font-weight: bold;
                padding: 15px;
            }
            QPushButton:hover {
                background-color: #1E88E5;
            }
        """)
        self.view_history_button.clicked.connect(self.view_history)

        # View Progress button
        self.view_progress_button = RoundedButton("View Progress")
        self.view_progress_button.setMinimumHeight(80)
        self.view_progress_button.setMinimumWidth(200)
        self.view_progress_button.setStyleSheet("""
            QPushButton {
                background-color: #FFC107;
                color: white;
                border: none;
                border-radius: 10px;
                font-size: 18px;
                font-weight: bold;
                padding: 15px;
            }
            QPushButton:hover {
                background-color: #FFB300;
            }
        """)
        self.view_progress_button.clicked.connect(self.view_progress)

        # Add quiz buttons to horizontal layout
        quiz_buttons_layout.addWidget(self.start_quiz_button)
        quiz_buttons_layout.addWidget(self.view_history_button)
        quiz_buttons_layout.addWidget(self.view_progress_button)

        # Logout button
        self.logout_button = RoundedButton("Logout")
        self.logout_button.setMinimumHeight(60)
        self.logout_button.setMinimumWidth(250)
        self.logout_button.setStyleSheet("""
            QPushButton {
                color: #d9534f;
                border: 2px solid #d9534f;
                border-radius: 10px;
                font-size: 16px;
                font-weight: bold;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #d9534f;
                color: white;
            }
        """)
        self.logout_button.clicked.connect(self.logout)

        # Create a horizontal layout to center the logout button
        logout_center_layout = QHBoxLayout()
        logout_center_layout.addStretch(1)
        logout_center_layout.addWidget(self.logout_button)
        logout_center_layout.addStretch(1)

        # Add layouts to buttons container
        buttons_layout.addLayout(quiz_buttons_layout)
        buttons_layout.addLayout(logout_center_layout)

        # Create a horizontal layout to center the buttons container
        center_layout = QHBoxLayout()
        center_layout.addStretch(1)
        center_layout.addWidget(buttons_container)
        center_layout.addStretch(1)

        # Add widgets to main layout
        main_layout.addWidget(welcome_label)
        main_layout.addLayout(center_layout)

        self.setLayout(main_layout)

    def start_quiz(self):
        self.start_quiz_requested.emit()

    def view_history(self):
        self.view_history_requested.emit()

    def view_progress(self):
        self.view_progress_requested.emit()

    def logout(self):
        reply = QMessageBox.question(self, 'Logout', 'Are you sure you want to logout?',
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.Yes:
            self.logout_requested.emit()

class MainApplication(QMainWindow):
    """Main application class"""

    def __init__(self):
        super().__init__()
        self.init_ui()
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.stacked_layout = QStackedWidget()
        main_layout = QVBoxLayout(self.central_widget)
        main_layout.addWidget(self.stacked_layout)
        self.login_window = LoginWindow()
        self.login_window.login_successful.connect(self.handle_login)
        self.login_window.register_requested.connect(self.show_register)
        self.stacked_layout.addWidget(self.login_window)
        self.register_window = RegisterWindow()
        self.register_window.register_successful.connect(self.show_login)
        self.register_window.back_to_login.connect(self.show_login)
        self.stacked_layout.addWidget(self.register_window)
        self.show_login()

    def init_ui(self):
        self.setWindowTitle("TextQuiz")
        self.resize(800, 600)
        self.setMinimumSize(600, 450)

    def show_login(self):
        self.stacked_layout.setCurrentWidget(self.login_window)

    def show_register(self):
        self.stacked_layout.setCurrentWidget(self.register_window)

    def handle_login(self, user_id, username):
        self.main_menu = MainMenuWindow(user_id, username)
        self.main_menu.logout_requested.connect(self.handle_logout)
        self.main_menu.start_quiz_requested.connect(self.start_new_quiz)
        self.main_menu.view_history_requested.connect(self.view_history)
        self.main_menu.view_progress_requested.connect(self.view_progress)
        self.stacked_layout.addWidget(self.main_menu)
        self.stacked_layout.setCurrentWidget(self.main_menu)
        self.current_user_id = user_id
        self.current_username = username

    def handle_logout(self):
        current_widget = self.stacked_layout.currentWidget()
        if current_widget != self.login_window and current_widget != self.register_window:
            self.stacked_layout.removeWidget(current_widget)
            current_widget.deleteLater()
        self.show_login()
        self.current_user_id = None
        self.current_username = None

    def start_new_quiz(self):
        self.image_processor = ImageProcessingWindow()
        self.image_processor.back_requested.connect(self.back_to_main_menu)
        self.image_processor.quiz_ready.connect(self.start_quiz)
        self.stacked_layout.addWidget(self.image_processor)
        self.stacked_layout.setCurrentWidget(self.image_processor)

    def start_quiz(self, extracted_text):
        self.quiz_window = QuizWindow(extracted_text)
        self.quiz_window.back_requested.connect(self.back_to_main_menu)
        self.quiz_window.quiz_completed.connect(self.show_results)
        self.stacked_layout.addWidget(self.quiz_window)
        self.stacked_layout.setCurrentWidget(self.quiz_window)

    def show_results(self, results, extracted_text):
        self.results_window = ResultsWindow(results, extracted_text, self.current_user_id)
        self.results_window.new_quiz_requested.connect(self.start_new_quiz)
        self.results_window.back_to_menu_requested.connect(self.back_to_main_menu)
        self.stacked_layout.addWidget(self.results_window)
        self.stacked_layout.setCurrentWidget(self.results_window)

    def view_history(self):
        self.history_window = HistoryWindow(self.current_user_id)
        self.history_window.back_requested.connect(self.back_to_main_menu)
        self.history_window.view_details_requested.connect(self.view_quiz_details)
        self.stacked_layout.addWidget(self.history_window)
        self.stacked_layout.setCurrentWidget(self.history_window)

    def view_quiz_details(self, quiz_id):
        self.details_window = QuizDetailsWindow(quiz_id)
        self.details_window.back_requested.connect(self.back_to_history)
        self.stacked_layout.addWidget(self.details_window)
        self.stacked_layout.setCurrentWidget(self.details_window)

    def view_progress(self):
        self.progress_window = ProgressWindow(self.current_user_id)
        self.progress_window.back_requested.connect(self.back_to_main_menu)
        self.stacked_layout.addWidget(self.progress_window)
        self.stacked_layout.setCurrentWidget(self.progress_window)

    def back_to_main_menu(self):
        current_widget = self.stacked_layout.currentWidget()
        if current_widget != self.main_menu:
            self.stacked_layout.removeWidget(current_widget)
            current_widget.deleteLater()
        if not hasattr(self, 'main_menu') or self.main_menu is None:
            self.main_menu = MainMenuWindow(self.current_user_id, self.current_username)
            self.main_menu.logout_requested.connect(self.handle_logout)
            self.main_menu.start_quiz_requested.connect(self.start_new_quiz)
            self.main_menu.view_history_requested.connect(self.view_history)
            self.main_menu.view_progress_requested.connect(self.view_progress)
            self.stacked_layout.addWidget(self.main_menu)
        self.stacked_layout.setCurrentWidget(self.main_menu)

    def back_to_history(self):
        self.stacked_layout.removeWidget(self.details_window)
        self.details_window.deleteLater()
        self.stacked_layout.setCurrentWidget(self.history_window)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    main_app = MainApplication()
    main_app.show()
    sys.exit(app.exec())