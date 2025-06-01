import os
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
from datetime import datetime
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

# Load environment variables from .env
load_dotenv()

app = Flask(__name__)
CORS(app)

# Database configuration#
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Initialize Flask-Migrate
migrate = Migrate(app, db)

# Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'executive', 'cleaner', 'auditor', 'supervisor'

class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)

class Branch(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)

class Certificate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    branch_id = db.Column(db.Integer, db.ForeignKey('branch.id'), nullable=False)
    month = db.Column(db.String(20), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    certificate_type = db.Column(db.String(50), nullable=False)  # JCC, DCC, JSDN
    file_url = db.Column(db.String(200), nullable=False)  # Supabase URL
    uploaded_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

# Role-based access decorator
def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user_id = request.headers.get('X-User-Id')
            if not user_id:
                return jsonify({'message': 'Missing user ID'}), 401
            user = User.query.get(user_id)
            if not user or user.role not in roles:
                return jsonify({'message': 'Forbidden'}), 403
            # Attach user to request context if needed
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# User registration (for testing/demo)
@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    name = data.get('name')
    email = data.get('email')
    password = data.get('password')
    role = data.get('role')
    if not all([name, email, password, role]):
        return jsonify({'message': 'Missing fields'}), 400
    if User.query.filter_by(email=email).first():
        return jsonify({'message': 'Email already exists'}), 400
    user = User(
        name=name,
        email=email,
        password_hash=generate_password_hash(password),
        role=role
    )
    db.session.add(user)
    db.session.commit()
    return jsonify({'message': 'User registered successfully'}), 201

# User login
@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    user = User.query.filter_by(email=email).first()
    if user and check_password_hash(user.password_hash, password):
        return jsonify({
            'id': user.id,
            'name': user.name,
            'role': user.role
        }), 200
    return jsonify({'message': 'Invalid credentials'}), 401

# Attendance recording (cleaner only)
@app.route('/api/attendance/record', methods=['POST'])
@role_required('cleaner')
def record_attendance():
    data = request.get_json()
    user_id = request.headers.get('X-User-Id')
    latitude = data.get('latitude')
    longitude = data.get('longitude')
    if not all([user_id, latitude, longitude]):
        return jsonify({'message': 'Missing parameters'}), 400
    new_attendance = Attendance(
        user_id=user_id,
        timestamp=datetime.utcnow(),
        latitude=latitude,
        longitude=longitude
    )
    db.session.add(new_attendance)
    db.session.commit()
    return jsonify({'message': 'Attendance recorded successfully'}), 201

# Certificate upload (executive only)
@app.route('/api/certificates/upload', methods=['POST'])
@role_required('executive')
def upload_certificate():
    data = request.form
    file = request.files['file']
    # TODO: Upload file to Supabase Storage and get file_url
    file_url = "https://supabase.storage.fakeurl/" + file.filename
    user_id = request.headers.get('X-User-Id')
    cert = Certificate(
        branch_id=data.get('branch_id'),
        month=data.get('month'),
        year=data.get('year'),
        certificate_type=data.get('certificate_type'),
        file_url=file_url,
        uploaded_by=user_id
    )
    db.session.add(cert)
    db.session.commit()
    return jsonify({'message': 'Certificate uploaded', 'file_url': file_url}), 201

# Example: Auditor-only endpoint to get all attendance records
@app.route('/api/attendance/all', methods=['GET'])
@role_required('auditor')
def get_all_attendance():
    records = Attendance.query.all()
    result = []
    for r in records:
        result.append({
            'id': r.id,
            'user_id': r.user_id,
            'timestamp': r.timestamp.isoformat(),
            'latitude': r.latitude,
            'longitude': r.longitude
        })
    return jsonify(result), 200

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))