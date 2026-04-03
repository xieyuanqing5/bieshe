from flask import Blueprint, request, jsonify, session, render_template, redirect, url_for
from app import db
from app.models import User
from functools import wraps

# 蓝图
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


# =========================
# 登录检查
# =========================
def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("auth.login_page"))
        return f(*args, **kwargs)
    return wrapper


# =========================
# 管理员权限检查
# =========================
def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("auth.login_page"))
        if not session.get("is_admin"):
            return redirect(url_for("views.home"))
        return f(*args, **kwargs)
    return wrapper


# =========================
# 注册页面
# =========================
@auth_bp.route('/register', methods=['GET'])
def register_page():
    return render_template("register_user.html")


# =========================
# 普通用户登录页面
# =========================
@auth_bp.route('/login', methods=['GET'])
def login_page():
    return render_template("login.html")


# =========================
# 注册 API
# =========================
@auth_bp.route('/api/register', methods=['POST'])
def register_api():
    data = request.get_json() or {}
    username = (data.get('username') or '').strip()
    password = data.get('password') or ''
    is_admin = bool(data.get('is_admin', False))

    if not username or not password:
        return jsonify({"error": "아이디와 비밀번호를 입력하세요"}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({"error": "이미 존재하는 사용자입니다"}), 400

    user = User(username=username, is_admin=is_admin)
    user.set_password(password)

    db.session.add(user)
    db.session.commit()

    return jsonify({"message": "회원가입 성공"}), 200


# =========================
# 普通用户登录 API
# =========================
@auth_bp.route('/api/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    username = (data.get('username') or '').strip()
    password = data.get('password') or ''

    user = User.query.filter_by(username=username).first()

    if not user or not user.check_password(password):
        return jsonify({"error": "아이디 또는 비밀번호가 틀립니다"}), 401

    session.permanent = False
    session['user_id'] = user.id
    session['username'] = user.username
    session['is_admin'] = user.is_admin

    return jsonify({
        "message": "로그인 성공",
        "is_admin": user.is_admin
    }), 200


# =========================
# 管理员登录页面
# =========================
@auth_bp.route('/admin/login', methods=['GET'])
def admin_login_page():
    return render_template("admin_login.html")


# =========================
# 管理员登录 API
# 关键修复：补上你前端正在调用的这个路由
# =========================
@auth_bp.route('/api/admin/login', methods=['POST'])
def admin_login_api():
    data = request.get_json() or {}
    username = (data.get('username') or '').strip()
    password = data.get('password') or ''

    user = User.query.filter_by(username=username).first()

    if not user or not user.check_password(password):
        return jsonify({"error": "아이디 또는 비밀번호가 틀립니다"}), 401

    if not user.is_admin:
        return jsonify({"error": "관리자 계정이 아닙니다"}), 403

    session.permanent = False
    session['user_id'] = user.id
    session['username'] = user.username
    session['is_admin'] = True

    return jsonify({
        "message": "관리자 로그인 성공",
        "is_admin": True
    }), 200


# =========================
# 登出 API
# =========================
@auth_bp.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({"message": "로그아웃 되었습니다"}), 200


# =========================
# 当前用户 API
# =========================
@auth_bp.route('/api/me', methods=['GET'])
def me():
    if 'user_id' not in session:
        return jsonify({"user": None}), 200

    return jsonify({
        "user": {
            "id": session['user_id'],
            "username": session.get('username'),
            "is_admin": session.get('is_admin')
        }
    }), 200