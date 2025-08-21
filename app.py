from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from decouple import config
import pyotp
import qrcode
import io
import base64

app = Flask(__name__)
app.config['SECRET_KEY'] = config('FLASK_SECRET_KEY', default='your-secret-key-fallback')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///sociafam.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = config('FLASK_SECRET_KEY', default='your-secret-key-fallback')

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
jwt = JWTManager(app)
CORS(app)

# User Model
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    bio = db.Column(db.Text, nullable=True)
    profile_pic = db.Column(db.String(200), nullable=True)
    is_2fa_enabled = db.Column(db.Boolean, default=False)
    totp_secret = db.Column(db.String(32), nullable=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routes
@app.route('/')
def home():
    return render_template('home.html', user=current_user)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            if user.is_2fa_enabled:
                return render_template('login.html', email=email, password=password, show_2fa=True)
            login_user(user)
            return redirect(url_for('home'))
        flash('Invalid email or password')
    return render_template('login.html')

@app.route('/verify_2fa', methods=['POST'])
def verify_2fa():
    email = request.form['email']
    password = request.form['password']
    token = request.form['token']
    user = User.query.filter_by(email=email).first()
    if user and user.check_password(password):
        totp = pyotp.TOTP(user.totp_secret)
        if totp.verify(token):
            login_user(user)
            return redirect(url_for('home'))
        flash('Invalid 2FA token')
    flash('Invalid credentials')
    return render_template('login.html', email=email, show_2fa=True)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    if request.method == 'POST':
        email = request.form['email']
        username = request.form['username']
        password = request.form['password']
        if User.query.filter_by(email=email).first():
            flash('Email already registered')
            return render_template('signup.html')
        user = User(email=email, username=username)
        user.set_password(password)
        user.totp_secret = pyotp.random_base32()
        db.session.add(user)
        db.session.commit()
        flash('Registration successful! Please log in.')
        return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route('/api/enable_2fa', methods=['POST'])
@login_required
@jwt_required()
def enable_2fa():
    if current_user.is_2fa_enabled:
        return jsonify({'error': '2FA already enabled'}), 400
    totp = pyotp.TOTP(current_user.totp_secret)
    uri = totp.provisioning_uri(current_user.email, issuer_name="SociaFam")
    img = qrcode.make(uri)
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    qr_code = base64.b64encode(buffer.getvalue()).decode('utf-8')
    current_user.is_2fa_enabled = True
    db.session.commit()
    return jsonify({'qr_code': qr_code, 'secret': current_user.totp_secret})

@app.route('/api/profile', methods=['GET', 'PUT'])
@login_required
@jwt_required()
def profile():
    if request.method == 'GET':
        return jsonify({
            'email': current_user.email,
            'username': current_user.username,
            'bio': current_user.bio,
            'profile_pic': current_user.profile_pic
        })
    elif request.method == 'PUT':
        data = request.get_json()
        current_user.username = data.get('username', current_user.username)
        current_user.bio = data.get('bio', current_user.bio)
        # Handle profile_pic upload in future phases
        db.session.commit()
        return jsonify({'message': 'Profile updated'})

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
