# database.py - Forest Guardian Hub
import sqlite3
from flask import g
from werkzeug.security import generate_password_hash, check_password_hash
from typing import Optional
import os

DATABASE = os.getenv('DATABASE_URL', 'forest_guardian.db').replace('sqlite:///', '')

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

def close_db(e=None):
    db = g.pop('_database', None)
    if db is not None:
        db.close()

def init_db():
    db = get_db()
    with open(os.path.join(os.path.dirname(__file__), 'schema.sql'), 'r') as f:
        db.executescript(f.read())
    db.commit()

def query_db(query, args=(), one=False):
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv

def add_user(username, email, password, full_name, phone, role):
    db = get_db()
    db.execute('INSERT INTO users (username, email, password_hash, full_name, phone, role, is_active, created_at) VALUES (?, ?, ?, ?, ?, ?, 1, CURRENT_TIMESTAMP)',
               (username, email, generate_password_hash(password), full_name, phone, role))
    db.commit()

def verify_user(username, password) -> Optional[dict]:
    user = query_db('SELECT * FROM users WHERE username = ?', [username], one=True)
    if user and check_password_hash(user['password_hash'], password):
        return dict(user)
    return None
