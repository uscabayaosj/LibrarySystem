import os

class Config:
    _key = os.environ.get('SECRET_KEY')
    SECRET_KEY = _key if _key else os.urandom(32).hex()
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///library.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
