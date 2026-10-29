# MediBook Smart Healthcare Appointment System

MediBook is a healthcare appointment website that I developed as a Computer Science project. I built it to learn how a web application works and how different features can be connected to make a useful system.

The website allows users to create an account, log in, view doctors, book appointments, check their appointments, and cancel a booking when needed.

## What I Have Built

- User registration and login
- A home page with information about the website
- A section to view doctors and their specialities
- An appointment booking system
- Appointment date validation based on doctors' available days
- A page where users can view and cancel their appointments
- Database integration to manage application data

## Technologies I Used

- Python
- Flask
- SQLite
- Flask-SQLAlchemy
- Flask-Login
- HTML
- CSS
- Jinja2

## Project Files

The main application code is in `app.py`. The HTML pages are stored in the `templates` folder, and the website styling is in the `static` folder. The `requirements.txt` file contains the Python packages needed to run the project.

## How to Run the Project

First, download or clone this repository to your computer.

Open the project folder in the terminal and create a virtual environment.

```bash
python -m venv venv
```

Activate the environment on Windows.

```bash
venv\Scripts\activate
```

Install the required packages.

```bash
pip install -r requirements.txt
```

Start the application.

```bash
python app.py
```

Open `http://127.0.0.1:5000` in your browser to view the website.

## What I Learned

While working on MediBook, I practised building web pages, connecting the frontend with a Flask backend, working with a database, handling user authentication, and managing appointment records. I also learned how to test the main features of a web application.

## Future Improvements

I would like to add appointment time slots, improve doctor search options, and make the system more useful for patients and healthcare providers.

## About the Project

MediBook is a personal portfolio project that I developed to improve my practical programming skills and gain more experience in web development.
