import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def create_app():
    app = Flask(__name__)

    app.config["SECRET_KEY"] = "your-secret-key"
    app.config["SESSION_PERMANENT"] = False

    db_path = os.path.join(app.root_path, "lostfound.db")
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + db_path
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)

    # 注册蓝图
    from .views import views
    from .auth import auth_bp
    from .ai_match import ai_bp

    app.register_blueprint(views)
    app.register_blueprint(auth_bp)
    app.register_blueprint(ai_bp)

    # 建表 + 创建默认管理员
    with app.app_context():
        db.create_all()

        from app.models import User

        admin = User.query.filter_by(username="admin").first()
        if not admin:
            admin = User(username="admin", is_admin=True)
            admin.set_password("admin123")

            db.session.add(admin)
            db.session.commit()

            print("✅ 默认管理员：admin / admin123")

    return app