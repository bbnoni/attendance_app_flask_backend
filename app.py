import os
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

app = Flask(__name__)
CORS(app)

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(20), default='user')  # user or supervisor

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

# Routes
@app.route('/api/attendance/record', methods=['POST'])
def record_attendance():
    data = request.get_json()
    user_id = data.get('user_id')
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

@app.route('/api/certificates/upload', methods=['POST'])
def upload_certificate():
    # This is a placeholder. You'd use Supabase's API here.
    data = request.form
    file = request.files['file']
    # TODO: Upload file to Supabase Storage and get file_url ##
    file_url = "https://supabase.storage.fakeurl/" + file.filename
    cert = Certificate(
        branch_id=data.get('branch_id'),
        month=data.get('month'),
        year=data.get('year'),
        certificate_type=data.get('certificate_type'),
        file_url=file_url,
        uploaded_by=data.get('uploaded_by')
    )
    db.session.add(cert)
    db.session.commit()
    return jsonify({'message': 'Certificate uploaded', 'file_url': file_url}), 201

if __name__ == '__main__':
    # Create tables if they don't exist
    with app.app_context():
        db.create_all()
    app.run(debug=True)