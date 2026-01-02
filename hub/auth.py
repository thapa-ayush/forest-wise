# auth.py - Forest Guardian Hub
from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
from werkzeug.security import check_password_hash, generate_password_hash
from database import query_db, add_user, get_db
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from config import Config
from datetime import datetime

login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'
limiter = Limiter(key_func=get_remote_address, default_limits=[Config.RATELIMIT_DEFAULT])

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

class User(UserMixin):
    def __init__(self, user_row):
        self.id = user_row['id']
        self.username = user_row['username']
        self.role = user_row['role']
        self._is_active = user_row['is_active']
    
    @property
    def is_active(self):
        return bool(self._is_active)

@login_manager.user_loader
def load_user(user_id):
    user = query_db('SELECT * FROM users WHERE id = ?', [user_id], one=True)
    return User(user) if user else None

@auth_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per 15 minutes")
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = query_db('SELECT * FROM users WHERE username = ?', [username], one=True)
        if user and check_password_hash(user['password_hash'], password):
            login_user(User(user))
            # Log login attempt
            query_db('INSERT INTO login_attempts (username, ip_address, success, timestamp) VALUES (?, ?, 1, ?)',
                     [username, request.remote_addr, datetime.utcnow()])
            return redirect(url_for('index'))
        else:
            query_db('INSERT INTO login_attempts (username, ip_address, success, timestamp) VALUES (?, ?, 0, ?)',
                     [username, request.remote_addr, datetime.utcnow()])
            flash('Invalid credentials', 'danger')
    return render_template('auth/login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))

@auth_bp.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        old = request.form['old_password']
        new = request.form['new_password']
        user = query_db('SELECT * FROM users WHERE id = ?', [current_user.id], one=True)
        if user and check_password_hash(user['password_hash'], old):
            query_db('UPDATE users SET password_hash = ? WHERE id = ?',
                     [generate_password_hash(new), current_user.id])
            flash('Password changed.', 'success')
        else:
            flash('Incorrect old password.', 'danger')
    return render_template('auth/change_password.html')
