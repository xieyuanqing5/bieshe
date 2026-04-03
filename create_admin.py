from app import db
from app.models import User
from app import create_app, db
from app.models import User

def create_admin():
    app = create_app()

    # 使用 app_context 包裹数据库操作
    with app.app_context():
        admin = User.query.filter_by(username="admin").first()
        if admin:
            print("管理员账号已经存在。")
        else:
            admin = User(username="admin", is_admin=True)
            admin.set_password("admin123")  # 你想设置的密码
            db.session.add(admin)
            db.session.commit()
            print("管理员账号创建成功！账号：admin，密码：admin123")

if __name__ == "__main__":
    create_admin()
