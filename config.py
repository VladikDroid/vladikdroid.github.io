import os
from dotenv import load_dotenv

# Загрузка переменных окружения из .env файла
load_dotenv()

basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # Простой путь к SQLite базе данных
    SQLALCHEMY_DATABASE_URI = 'sqlite:///slang.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Flask-Login
    LOGIN_DISABLED = False
    
    # Pagination
    WORDS_PER_PAGE = 20
    
    # Email configuration (для будущих функций)
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 587)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() == 'true'
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    ADMINS = ['admin@slangdb.local']