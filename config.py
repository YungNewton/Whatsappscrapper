import os
from datetime import timedelta

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "super_secret_key")
    SESSION_COOKIE_SAMESITE = "None"  # Allows cross-origin cookies
    SESSION_COOKIE_SECURE = False     # Set to True if using HTTPS
    SESSION_PERMANENT = True
    PERMANENT_SESSION_LIFETIME = timedelta(days=30)  # 30-days timeout
    SQLALCHEMY_DATABASE_URI = "sqlite:///db.sqlite"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
