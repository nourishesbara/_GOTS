# Text Quiz Application  

## Overview  
The Text Quiz Application is a robust, command-line-based quiz system designed for users to answer multiple-choice questions efficiently. It includes essential features such as scoring, time tracking, and question randomization, making it an ideal tool for educational purposes, assessments, and self-improvement.  

## Features  
- Multiple-choice quiz format  
- Randomized question order to enhance engagement  
- Time tracking for each quiz session  
- Automatic score calculation and display  
- Progress tracking through interactive graphs  
- Lightweight and easy to use with no prerequisites  

## System Architecture  
- The `api.py` is hosted on an AWS EC2 instance, running 24/7 to handle quiz data and user interactions.  
- All necessary dependencies are pre-installed on the AWS environment.  
- The system is integrated with an AWS RDS database for efficient data management.  
- The EXE file includes additional features like a built-in timer and real-time progress tracking through visual graphs.  

## Technologies Used  
This application utilizes a variety of technologies to ensure a seamless user experience:  
- **Python & Flask** – Core programming language and API framework  
- **PyQt6** – GUI framework for an interactive and user-friendly interface  
- **Matplotlib** – For graphical representation of progress tracking  
- **Pytesseract & PIL** – Optical character recognition (OCR) capabilities  
- **Boto3 & AWS RDS** – Cloud integration for database storage  
- **SQLite & MySQL (via PyMySQL)** – Local and cloud database management  

## Installation and Usage  

### Setup Instructions  
No prerequisites are required for this application. Simply download and use it immediately.  

1. Google Drive link:  https://drive.google.com/file/d/1vc7kAiHnmOe1pGj2WGO3FbCVzaYfqZhu/view?usp=sharing 
2. Run the executable file for an interactive quiz experience with advanced features.  

## Future Enhancements  
- Web-based UI for a more user-friendly experience  
- Enhanced analytics and reporting features    

This application ensures a seamless quiz-taking experience with cloud-hosted support and user-friendly functionality.

