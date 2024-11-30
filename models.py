from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash
from flask_login import UserMixin

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

    def __init__(self, email, password):
        self.email = email
        self.password = generate_password_hash(password)

def init_db(app):
    db.init_app(app)
    with app.app_context():
        db.create_all()

        # Add default admin user if not exists
        if not User.query.filter_by(email="admin@user.com").first():
            admin_user = User(email="admin@user.com", password="adminpassword")
            db.session.add(admin_user)
            db.session.commit()
