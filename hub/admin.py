# admin.py - Forest Guardian Hub
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from database import query_db, add_user
from functools import wraps

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'Admin':
            flash('Admin access required.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/users')
@admin_required
def users():
    users = query_db('SELECT * FROM users')
    return render_template('admin/users.html', users=users)

@admin_bp.route('/add_user', methods=['GET', 'POST'])
@admin_required
def add_user_route():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        full_name = request.form['full_name']
        phone = request.form['phone']
        role = request.form['role']
        add_user(username, email, password, full_name, phone, role)
        flash('User added.', 'success')
        return redirect(url_for('admin.users'))
    return render_template('admin/add_user.html')

@admin_bp.route('/audit_log')
@admin_required
def audit_log():
    logs = query_db('SELECT * FROM audit_log ORDER BY timestamp DESC LIMIT 100')
    return render_template('admin/audit_log.html', logs=logs)
