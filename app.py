
from datetime import date
from pathlib import Path

from flask import (
    Flask, render_template, request,
    redirect, url_for, flash
)
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    logout_user,
    current_user,
    login_required,
)
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import inspect, text

BASE_DIR = Path(__file__).resolve().parent

app = Flask(__name__)
app.config["SECRET_KEY"] = "replace-this-with-a-random-secret-before-deployment"
app.config["SQLALCHEMY_DATABASE_URI"] = (
    "sqlite:///" + (BASE_DIR / "medibook.db").as_posix()
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


class Patient(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)

    appointments = db.relationship(
        "Appointment",
        back_populates="patient",
        lazy=True
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


@login_manager.user_loader
def load_patient(patient_id):
    try:
        return db.session.get(Patient, int(patient_id))
    except (ValueError, TypeError):
        return None


class Doctor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    specialty = db.Column(db.String(100), nullable=False)
    experience = db.Column(db.Integer, default=1)
    availability = db.Column(db.String(100), default="Mon - Fri")

    appointments = db.relationship(
        "Appointment",
        backref="doctor",
        lazy=True
    )


class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_name = db.Column(db.String(100), nullable=False)
    appointment_date = db.Column(db.Date, nullable=False)

    doctor_id = db.Column(
        db.Integer,
        db.ForeignKey("doctor.id"),
        nullable=False
    )

    patient_id = db.Column(
        db.Integer,
        db.ForeignKey("patient.id"),
        nullable=True
    )

    status = db.Column(
        db.String(20),
        nullable=False,
        default="Booked"
    )

    patient = db.relationship(
        "Patient",
        back_populates="appointments"
    )


def is_doctor_available(doctor, selected_date):
    """Check the selected weekday against the doctor's schedule."""
    weekday = selected_date.weekday()  # Monday=0, Sunday=6
    availability = (doctor.availability or "").lower()
    availability = availability.replace(" ", "")

    if availability in ("mon-fri", "monday-friday"):
        return weekday <= 4

    if availability in ("mon-sat", "monday-saturday"):
        return weekday <= 5

    # If a schedule is unknown, do not accept the booking.
    return False


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for("home"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not name or len(name) > 100:
            flash("Please enter a valid name.", "error")
        elif (
            not email
            or len(email) > 120
            or "@" not in email
            or email.startswith("@")
        ):
            flash("Please enter a valid email address.", "error")
        elif len(password) < 8:
            flash("Password must be at least 8 characters.", "error")
        elif Patient.query.filter_by(email=email).first():
            flash("An account with this email already exists.", "error")
        else:
            patient = Patient(name=name, email=email)
            patient.set_password(password)

            try:
                db.session.add(patient)
                db.session.commit()
                login_user(patient)

                flash(
                    "Your account has been created successfully!",
                    "success"
                )
                return redirect(url_for("home"))

            except Exception:
                db.session.rollback()
                app.logger.exception("Patient signup failed")
                flash(
                    "We could not create your account. Please try again.",
                    "error"
                )

    return render_template("signup.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("home"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        patient = Patient.query.filter_by(email=email).first()

        if patient and patient.check_password(password):
            login_user(patient)
            flash("You have logged in successfully!", "success")
            return redirect(url_for("home"))

        flash("Invalid email or password. Please try again.", "error")

    return render_template("login.html")


@app.route("/logout", methods=["GET"])
def logout():
    if current_user.is_authenticated:
        logout_user()
        flash("You have logged out successfully.", "success")

    return redirect(url_for("home"))


@app.route("/")
def home():
    doctors = Doctor.query.order_by(Doctor.id).all()
    return render_template("index.html", doctors=doctors)


@app.route("/doctors")
def doctors_page():
    doctors = Doctor.query.order_by(Doctor.name).all()
    return render_template("doctors.html", doctors=doctors)


@app.route("/my-appointments")
@login_required
def my_appointments():
    appointments = (
        Appointment.query
        .filter_by(patient_id=current_user.id)
        .order_by(Appointment.appointment_date.desc())
        .all()
    )

    return render_template(
        "my_appointments.html",
        appointments=appointments,
        today=date.today()
    )


@app.route("/cancel-appointment/<int:appointment_id>", methods=["POST"])
@login_required
def cancel_appointment(appointment_id):
    appointment = Appointment.query.filter_by(
        id=appointment_id,
        patient_id=current_user.id
    ).first_or_404()

    if appointment.status == "Cancelled":
        flash("This appointment has already been cancelled.", "error")

    elif appointment.appointment_date < date.today():
        flash("Past appointments cannot be cancelled.", "error")

    else:
        try:
            appointment.status = "Cancelled"
            db.session.commit()
            flash("Your appointment has been cancelled.", "success")

        except Exception:
            db.session.rollback()
            app.logger.exception("Appointment cancellation failed")
            flash(
                "We could not cancel your appointment. Please try again.",
                "error"
            )

    return redirect(url_for("my_appointments"))


@app.route("/book", methods=["GET", "POST"])
@login_required
def book_page():
    doctors = Doctor.query.order_by(Doctor.name).all()
    today = date.today().isoformat()

    if request.method == "POST":
        patient_name = current_user.name
        doctor_id = request.form.get("doctor_id", "").strip()
        appointment_date = request.form.get(
            "appointment_date", ""
        ).strip()

        if not patient_name or len(patient_name) > 100:
            flash("Please enter a valid patient name.", "error")
            return render_template(
                "book.html", doctors=doctors, today=today
            )

        try:
            selected_doctor_id = int(doctor_id)
            selected_date = date.fromisoformat(appointment_date)
        except (ValueError, TypeError):
            flash("Please select a valid doctor and date.", "error")
            return render_template(
                "book.html", doctors=doctors, today=today
            )

        if selected_date < date.today():
            flash("Please select today or a future date.", "error")
            return render_template(
                "book.html", doctors=doctors, today=today
            )

        doctor = db.session.get(Doctor, selected_doctor_id)

        if doctor is None:
            flash("Please select a valid doctor.", "error")
            return render_template(
                "book.html", doctors=doctors, today=today
            )

        # Check the doctor's weekday schedule on the server.
        if not is_doctor_available(doctor, selected_date):
            flash(
                f"{doctor.name} is not available on "
                f"{selected_date.strftime('%A')}. "
                f"Availability: {doctor.availability}. "
                "Please choose another date.",
                "error"
            )
            return render_template(
                "book.html", doctors=doctors, today=today
            )

        # Only active bookings block the same doctor's date.
        existing = Appointment.query.filter(
            Appointment.doctor_id == doctor.id,
            Appointment.appointment_date == selected_date,
            Appointment.status != "Cancelled"
        ).first()

        if existing:
            flash(
                "This doctor already has a booking on that date. "
                "Please select another date.",
                "error"
            )
            return render_template(
                "book.html", doctors=doctors, today=today
            )

        try:
            appointment = Appointment(
                patient_name=patient_name,
                doctor_id=doctor.id,
                appointment_date=selected_date,
                patient_id=current_user.id,
                status="Booked"
            )

            db.session.add(appointment)
            db.session.commit()

            return render_template(
                "confirmation.html",
                appointment=appointment
            )

        except Exception:
            db.session.rollback()
            app.logger.exception("Appointment booking failed")
            flash(
                "We could not save your appointment. Please try again.",
                "error"
            )
            return render_template(
                "book.html", doctors=doctors, today=today
            )

    return render_template(
        "book.html", doctors=doctors, today=today
    )


def seed_doctors():
    if Doctor.query.count() == 0:
        doctors = [
            Doctor(
                name="Dr. Ayesha Khan",
                specialty="Cardiologist",
                experience=8,
                availability="Mon - Fri"
            ),
            Doctor(
                name="Dr. Hamza Ahmed",
                specialty="Dermatologist",
                experience=6,
                availability="Mon - Sat"
            ),
            Doctor(
                name="Dr. Sara Malik",
                specialty="Pediatrician",
                experience=7,
                availability="Mon - Fri"
            ),
            Doctor(
                name="Dr. Ali Raza",
                specialty="General Physician",
                experience=5,
                availability="Mon - Sat"
            ),
        ]
        db.session.add_all(doctors)
        db.session.commit()


with app.app_context():
    db.create_all()

    # Add missing columns safely without deleting existing records.
    appointment_columns = {
        column["name"]
        for column in inspect(db.engine).get_columns("appointment")
    }

    if "patient_id" not in appointment_columns:
        with db.engine.begin() as connection:
            connection.execute(
                text(
                    "ALTER TABLE appointment "
                    "ADD COLUMN patient_id INTEGER REFERENCES patient(id)"
                )
            )

    if "status" not in appointment_columns:
        with db.engine.begin() as connection:
            connection.execute(
                text(
                    "ALTER TABLE appointment "
                    "ADD COLUMN status VARCHAR(20) "
                    "NOT NULL DEFAULT 'Booked'"
                )
            )

    seed_doctors()


if __name__ == "__main__":
    app.run(debug=True)

