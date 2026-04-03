from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from app.models import User, LostItem, FoundItem, Feedback
from app import db
from app.auth import admin_required

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.route("/", methods=["GET"], strict_slashes=False)
@admin_bp.route("/dashboard", methods=["GET"])
@admin_required
def dashboard():
    total_users = User.query.count()
    total_lost = LostItem.query.count()
    total_found = FoundItem.query.count()
    total_feedback = Feedback.query.count()

    recent_users = User.query.order_by(User.id.desc()).limit(5).all()
    recent_lost = LostItem.query.order_by(LostItem.id.desc()).limit(5).all()
    recent_found = FoundItem.query.order_by(FoundItem.id.desc()).limit(5).all()
    recent_feedback = Feedback.query.order_by(Feedback.id.desc()).limit(5).all()

    return render_template(
        "admin_dashboard.html",
        total_users=total_users,
        total_lost=total_lost,
        total_found=total_found,
        total_feedback=total_feedback,
        recent_users=recent_users,
        recent_lost=recent_lost,
        recent_found=recent_found,
        recent_feedback=recent_feedback
    )


@admin_bp.route("/users", methods=["GET"])
@admin_required
def users():
    q = request.args.get("q", "").strip()

    if q:
        users = User.query.filter(User.username.contains(q)).order_by(User.id.desc()).all()
    else:
        users = User.query.order_by(User.id.desc()).all()

    return render_template("admin_users.html", users=users, q=q)


@admin_bp.route("/users/<int:user_id>/toggle_admin", methods=["POST"])
@admin_required
def toggle_admin(user_id):
    if session.get("user_id") == user_id:
        return jsonify({"error": "자기 자신 권한 변경은 불가능합니다."}), 400

    user = User.query.get_or_404(user_id)
    user.is_admin = not user.is_admin
    db.session.commit()

    return jsonify({"ok": True, "is_admin": user.is_admin})


@admin_bp.route("/users/<int:user_id>/delete", methods=["POST"])
@admin_required
def delete_user(user_id):
    if session.get("user_id") == user_id:
        return jsonify({"error": "자기 자신은 삭제할 수 없습니다."}), 400

    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()

    return jsonify({"ok": True})


@admin_bp.route("/items", methods=["GET"])
@admin_required
def items():
    item_type = request.args.get("type", "all")

    if item_type == "lost":
        items = LostItem.query.order_by(LostItem.id.desc()).all()
        return render_template("admin_items.html", items=items, type="lost")

    elif item_type == "found":
        items = FoundItem.query.order_by(FoundItem.id.desc()).all()
        return render_template("admin_items.html", items=items, type="found")

    else:
        lost_items = LostItem.query.order_by(LostItem.id.desc()).all()
        found_items = FoundItem.query.order_by(FoundItem.id.desc()).all()

        return render_template(
            "admin_items.html",
            items={"lost": lost_items, "found": found_items},
            type="all"
        )


@admin_bp.route("/items/<string:item_type>/<int:item_id>/delete", methods=["POST"])
@admin_required
def delete_item(item_type, item_id):
    if item_type == "lost":
        item = LostItem.query.get_or_404(item_id)
    elif item_type == "found":
        item = FoundItem.query.get_or_404(item_id)
    else:
        return jsonify({"error": "잘못된 item_type 입니다."}), 400

    db.session.delete(item)
    db.session.commit()

    return jsonify({"ok": True})


@admin_bp.route("/items/<string:item_type>/<int:item_id>/toggle_resolved", methods=["POST"])
@admin_required
def toggle_resolved(item_type, item_id):
    if item_type == "lost":
        model = LostItem
    elif item_type == "found":
        model = FoundItem
    else:
        return jsonify({"error": "잘못된 item_type 입니다."}), 400

    item = model.query.get_or_404(item_id)

    if hasattr(item, "resolved"):
        item.resolved = not item.resolved
        db.session.commit()
        return jsonify({"ok": True, "resolved": item.resolved})

    return jsonify({"error": "모델에 resolved 필드가 없습니다."}), 400


@admin_bp.route("/stats", methods=["GET"])
@admin_required
def stats():
    total_users = User.query.count()
    total_lost = LostItem.query.count()
    total_found = FoundItem.query.count()

    recent_users = User.query.order_by(User.id.desc()).limit(5).all()
    recent_lost = LostItem.query.order_by(LostItem.id.desc()).limit(5).all()
    recent_found = FoundItem.query.order_by(FoundItem.id.desc()).limit(5).all()

    return render_template(
        "admin_stats.html",
        total_users=total_users,
        total_lost=total_lost,
        total_found=total_found,
        recent_users=recent_users,
        recent_lost=recent_lost,
        recent_found=recent_found
    )