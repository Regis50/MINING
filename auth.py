"""auth.py — Session + RBAC helpers. Sessions stored in JSON file (survives restart)."""
import os, json, secrets
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify, make_response
import system_db

SESSION_COOKIE = "tj_session_v3"
SESSION_TTL = timedelta(days=7)
SESSION_FILE = os.path.join(os.path.dirname(__file__), "sessions.json")

def _load_sessions():
    try:
        with open(SESSION_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def _save_sessions(sessions):
    try:
        with open(SESSION_FILE, 'w') as f:
            json.dump(sessions, f)
    except Exception as e:
        print(f"⚠️ Failed to save sessions: {e}")

def login(username, password):
    user = system_db.find_user_by_credentials(username, password)
    if not user:
        return None, None
    token = secrets.token_urlsafe(48)
    expires = (datetime.now() + SESSION_TTL).isoformat()
    sessions = _load_sessions()
    sessions[token] = {"user_id": user["id"], "expires_at": expires}
    _save_sessions(sessions)
    return user, token

def logout(token):
    if not token:
        return
    sessions = _load_sessions()
    if token in sessions:
        del sessions[token]
        _save_sessions(sessions)

def current_user(request_obj):
    token = request_obj.cookies.get(SESSION_COOKIE)
    if not token:
        return None
    sessions = _load_sessions()
    sess = sessions.get(token)
    if not sess:
        return None
    try:
        expires = datetime.fromisoformat(sess["expires_at"])
        if datetime.now() > expires:
            del sessions[token]
            _save_sessions(sessions)
            return None
    except (KeyError, ValueError, TypeError):
        return None
    return system_db.find_user_by_id(sess["user_id"])

def require_auth(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user = current_user(request)
        if not user:
            return jsonify({"error": "Ntibyemera. Injira kandi."}), 401
        request._user = user
        return fn(*args, **kwargs)
    return wrapper

def require_owner(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user = current_user(request)
        if not user:
            return jsonify({"error": "Ntibyemera."}), 401
        if user.get("role") != "OWNER":
            return jsonify({"error": "Nta burenganzira bwo gukora ibi."}), 403
        request._user = user
        return fn(*args, **kwargs)
    return wrapper

def set_session_cookie(resp, token):
    resp.set_cookie(SESSION_COOKIE, token, httponly=True, samesite="Lax",
                    max_age=int(SESSION_TTL.total_seconds()), path="/")
    return resp


# Aliases for backward compat with app.py imports
set_server_session_cookie = set_session_cookie

def clear_server_session_cookie(resp):
    resp.delete_cookie(SESSION_COOKIE, path="/")
    return resp

# Role constants (used by app.py)
OWNER = "OWNER"
EMPLOYEE = "EMPLOYEE"
