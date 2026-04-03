import os
from collections import Counter

from flask import (
    Blueprint, render_template, request, redirect,
    jsonify, flash, current_app, url_for, session, abort
)
from werkzeug.utils import secure_filename
from openai import OpenAI

from app import db
from app.models import LostItem, FoundItem, Feedback, User
from app.utils import CATEGORIES, LOCATIONS, statistics_data
from app.auth import login_required, admin_required

views = Blueprint("views", __name__)


def save_uploaded_file(file):
    if not file or file.filename == "":
        return None

    filename = secure_filename(file.filename)
    upload_dir = os.path.join(current_app.root_path, "static", "uploads")
    os.makedirs(upload_dir, exist_ok=True)

    save_path = os.path.join(upload_dir, filename)
    file.save(save_path)

    return "/static/uploads/" + filename


@views.route("/")
@login_required
def home():
    recent_lost = LostItem.query.order_by(LostItem.id.desc()).limit(3).all()
    recent_found = FoundItem.query.order_by(FoundItem.id.desc()).limit(3).all()

    items_recent = [
        {
            "id": i.id,
            "type": "lost",
            "name": i.name,
            "category": i.category,
            "place": i.place,
            "date": i.date,
            "image": i.image,
            "resolved": getattr(i, "resolved", False),
        }
        for i in recent_lost
    ] + [
        {
            "id": i.id,
            "type": "found",
            "name": i.name,
            "category": i.category,
            "place": i.place,
            "date": i.date,
            "image": i.image,
            "resolved": getattr(i, "resolved", False),
        }
        for i in recent_found
    ]

    total_lost = LostItem.query.count()
    total_found = FoundItem.query.count()
    pending_lost = LostItem.query.filter_by(resolved=False).count()
    pending_found = FoundItem.query.filter_by(resolved=False).count()

    stats = {
        "total_items": total_lost + total_found,
        "lost_items": total_lost,
        "found_items": total_found,
        "pending_items": pending_lost + pending_found,
    }

    return render_template(
        "index.html",
        categories=CATEGORIES,
        locations=LOCATIONS,
        items_recent=items_recent,
        stats=stats,
    )


@views.route("/register", methods=["GET", "POST"])
@login_required
def register():
    if request.method == "POST":
        item_type = request.form.get("type")
        name = request.form.get("name")
        category = request.form.get("category")
        place = request.form.get("place")
        date = request.form.get("date")
        contact = request.form.get("contact")
        description = request.form.get("description")

        image_path = save_uploaded_file(request.files.get("image"))

        if not name or not place:
            flash("필수 입력값이 누락되었습니다.", "danger")
            return redirect(url_for("views.register"))

        model = LostItem if item_type == "lost" else FoundItem
        item = model(
            name=name,
            category=category,
            place=place,
            date=date,
            contact=contact,
            description=description,
            image=image_path,
            user_id=session.get("user_id"),
            resolved=False
        )

        db.session.add(item)
        db.session.commit()
        flash("등록이 완료되었습니다!", "success")
        return redirect(url_for("views.search"))

    return render_template(
        "register.html",
        categories=CATEGORIES,
        locations=LOCATIONS
    )


@views.route("/search")
@login_required
def search():
    keyword = request.args.get("keyword", "")
    category = request.args.get("category", "")
    place = request.args.get("place", "")
    date = request.args.get("date", "")
    status = request.args.get("status", "")

    lost_q = LostItem.query
    found_q = FoundItem.query

    if keyword:
        lost_q = lost_q.filter(LostItem.name.contains(keyword))
        found_q = found_q.filter(FoundItem.name.contains(keyword))

    if category:
        lost_q = lost_q.filter_by(category=category)
        found_q = found_q.filter_by(category=category)

    if place:
        lost_q = lost_q.filter(LostItem.place.contains(place))
        found_q = found_q.filter(FoundItem.place.contains(place))

    if date:
        lost_q = lost_q.filter_by(date=date)
        found_q = found_q.filter_by(date=date)

    if status == "resolved":
        lost_q = lost_q.filter(LostItem.resolved == True)
        found_q = found_q.filter(FoundItem.resolved == True)
    elif status == "unresolved":
        lost_q = lost_q.filter(LostItem.resolved == False)
        found_q = found_q.filter(FoundItem.resolved == False)

    lost_items = lost_q.order_by(LostItem.id.desc()).all()
    found_items = found_q.order_by(FoundItem.id.desc()).all()

    results = [
        {
            "id": i.id,
            "type": "lost",
            "name": i.name,
            "category": i.category,
            "place": i.place,
            "date": i.date,
            "image": i.image,
            "resolved": i.resolved
        }
        for i in lost_items
    ] + [
        {
            "id": i.id,
            "type": "found",
            "name": i.name,
            "category": i.category,
            "place": i.place,
            "date": i.date,
            "image": i.image,
            "resolved": i.resolved
        }
        for i in found_items
    ]

    return render_template(
        "search.html",
        results=results,
        categories=CATEGORIES,
        locations=LOCATIONS,
    )


@views.route("/item/<string:item_type>/<int:item_id>")
@login_required
def item_detail(item_type, item_id):
    if item_type == "lost":
        item = LostItem.query.get_or_404(item_id)
    elif item_type == "found":
        item = FoundItem.query.get_or_404(item_id)
    else:
        abort(404)

    source = request.args.get("source", "")

    return render_template(
        "item_detail.html",
        item=item,
        item_type=item_type,
        source=source
    )


# 兼容旧链接：/item/1
@views.route("/item/<int:item_id>")
@login_required
def item_detail_legacy(item_id):
    source = request.args.get("source", "")

    lost_item = LostItem.query.get(item_id)
    if lost_item:
        return redirect(
            url_for(
                "views.item_detail",
                item_type="lost",
                item_id=item_id,
                source=source
            )
        )

    found_item = FoundItem.query.get(item_id)
    if found_item:
        return redirect(
            url_for(
                "views.item_detail",
                item_type="found",
                item_id=item_id,
                source=source
            )
        )

    flash("해당 물품을 찾을 수 없습니다.", "danger")
    return redirect(url_for("views.search"))


@views.route("/edit/<string:item_type>/<int:item_id>", methods=["GET", "POST"])
@login_required
def edit_item(item_type, item_id):
    if item_type == "lost":
        item = LostItem.query.get_or_404(item_id)
    elif item_type == "found":
        item = FoundItem.query.get_or_404(item_id)
    else:
        abort(404)

    source = request.args.get("source", "")

    if request.method == "POST":
        item.name = request.form.get("name")
        item.category = request.form.get("category")
        item.place = request.form.get("place")
        item.date = request.form.get("date")
        item.contact = request.form.get("contact")
        item.description = request.form.get("description")

        new_img = save_uploaded_file(request.files.get("image"))
        if new_img:
            item.image = new_img

        db.session.commit()
        flash("수정이 완료되었습니다!", "success")

        if source:
            return redirect(url_for("views.item_detail", item_type=item_type, item_id=item.id, source=source))
        return redirect(url_for("views.item_detail", item_type=item_type, item_id=item.id))

    return render_template(
        "edit_item.html",
        item=item,
        item_type=item_type,
        source=source
    )


@views.route("/delete/<string:item_type>/<int:item_id>", methods=["POST"])
@login_required
def delete_item(item_type, item_id):
    if item_type == "lost":
        item = LostItem.query.get_or_404(item_id)
    elif item_type == "found":
        item = FoundItem.query.get_or_404(item_id)
    else:
        abort(404)

    source = request.args.get("source", "")

    db.session.delete(item)
    db.session.commit()
    flash("삭제되었습니다!", "info")

    if source == "ai":
        return redirect(url_for("views.ai_page"))
    return redirect(url_for("views.search"))


@views.route("/item/<string:item_type>/<int:item_id>/resolve", methods=["POST"])
@login_required
def resolve_item(item_type, item_id):
    if item_type == "lost":
        item = LostItem.query.get_or_404(item_id)
    elif item_type == "found":
        item = FoundItem.query.get_or_404(item_id)
    else:
        return jsonify({"ok": False, "msg": "잘못된 타입"}), 400

    if item.user_id != session.get("user_id"):
        return jsonify({"ok": False, "msg": "권한 없음"}), 403

    item.resolved = True
    db.session.commit()

    return jsonify({"ok": True})


@views.route("/ai", methods=["GET", "POST"])
@login_required
def ai_page():
    ai_answer = None

    if request.method == "POST":
        question = request.form.get("question", "").strip()

        if not question:
            ai_answer = "질문이 비어 있습니다."
        else:
            try:
                api_key = os.getenv("OPENAI_API_KEY")

                if not api_key:
                    ai_answer = "OPENAI_API_KEY가 설정되지 않았습니다."
                else:
                    client = OpenAI(api_key=api_key)
                    resp = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[
                            {"role": "system", "content": "친절한 AI 분실물 도움 도우미입니다."},
                            {"role": "user", "content": question}
                        ]
                    )
                    ai_answer = resp.choices[0].message.content

            except Exception as e:
                ai_answer = f"오류 발생: {e}"

    return render_template("ai_search.html", ai_answer=ai_answer)


@views.route("/api/chat", methods=["POST"])
def api_chat():
    data = request.get_json() or {}
    message = data.get("message", "").strip()

    if not message:
        return jsonify({"error": "메시지가 비었습니다."}), 400

    try:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return jsonify({"error": "OPENAI_API_KEY가 설정되지 않았습니다."}), 500

        client = OpenAI(api_key=api_key)
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "친절한 AI 분실물 안내 도우미입니다."},
                {"role": "user", "content": message}
            ]
        )
        answer = resp.choices[0].message.content
        return jsonify({"message": answer})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@views.route("/contact", methods=["GET", "POST"])
@login_required
def contact():
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        message = request.form.get("message")

        fb = Feedback(name=name, email=email, message=message)
        db.session.add(fb)
        db.session.commit()

        return render_template("contact.html", success=True)

    return render_template("contact.html")


@views.route("/statistics")
@login_required
def statistics_page():
    total_lost, total_found, lost_stats, found_stats, location_stats = statistics_data()

    # 统一分类标签，避免 lost_stats 和 found_stats 的 key 顺序或内容不一致
    all_categories = sorted(set(lost_stats.keys()) | set(found_stats.keys()))
    lost_labels = all_categories
    lost_values = [lost_stats.get(category, 0) for category in all_categories]
    found_values = [found_stats.get(category, 0) for category in all_categories]

    # 统一地点统计，保证前端拿到的数据结构稳定
    safe_location_stats = {}
    for place, values in location_stats.items():
        safe_location_stats[place] = {
            "lost": values.get("lost", 0),
            "found": values.get("found", 0)
        }

    # Top 5 最常丢失物品
    all_lost_items = LostItem.query.all()
    name_counter = Counter()

    for item in all_lost_items:
        item_name = (item.name or "").strip()
        if item_name:
            name_counter[item_name] += 1

    top5 = name_counter.most_common(5)
    top_lost_labels = [name for name, count in top5]
    top_lost_values = [count for name, count in top5]

    return render_template(
        "statistics.html",
        lost_count=total_lost,
        found_count=total_found,
        lost_labels=lost_labels,
        lost_values=lost_values,
        found_values=found_values,
        location_stats=safe_location_stats,
        top_lost_labels=top_lost_labels,
        top_lost_values=top_lost_values
    )