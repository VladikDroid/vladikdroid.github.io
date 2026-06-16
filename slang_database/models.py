from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

# Таблица многие-ко-многим для слов и тегов
word_tags = db.Table('word_tags',
    db.Column('word_id', db.Integer, db.ForeignKey('words.id'), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('tags.id'), primary_key=True)
)

# Таблица многие-ко-многим для пользователей и избранных слов
user_favorites = db.Table('user_favorites',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
    db.Column('word_id', db.Integer, db.ForeignKey('words.id'), primary_key=True)
)

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), default='user')  # 'user', 'moderator', 'admin'
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Связи
    added_words = db.relationship('Word', backref='author', lazy=True, foreign_keys='Word.author_id')
    comments = db.relationship('Comment', backref='author', lazy=True, cascade='all, delete-orphan')
    votes = db.relationship('Vote', backref='user', lazy=True, cascade='all, delete-orphan')
    favorites = db.relationship('Word', secondary=user_favorites, backref='favorited_by', lazy=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.username}>'

class Period(db.Model):
    __tablename__ = 'periods'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    decade = db.Column(db.String(20))
    description = db.Column(db.Text)
    start_year = db.Column(db.Integer)
    end_year = db.Column(db.Integer)
    color = db.Column(db.String(20), default='#667eea')  # Цвет для визуализации
    
    words = db.relationship('Word', backref='period', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Period {self.name}>'

class Category(db.Model):
    __tablename__ = 'categories'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    parent_id = db.Column(db.Integer, db.ForeignKey('categories.id'))
    color = db.Column(db.String(20), default='#6c757d')  # Цвет для визуализации
    
    # Иерархия категорий
    children = db.relationship('Category', backref=db.backref('parent', remote_side=[id]))
    words = db.relationship('Word', backref='category', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Category {self.name}>'

class Tag(db.Model):
    __tablename__ = 'tags'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False, index=True)
    color = db.Column(db.String(20), default='#6c757d')
    
    words = db.relationship('Word', secondary=word_tags, backref='tags', lazy=True)
    
    def __repr__(self):
        return f'<Tag {self.name}>'

class Word(db.Model):
    __tablename__ = 'words'
    
    id = db.Column(db.Integer, primary_key=True)
    word = db.Column(db.String(100), nullable=False, index=True)
    meaning = db.Column(db.Text, nullable=False)
    period_id = db.Column(db.Integer, db.ForeignKey('periods.id'))
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'))
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    origin = db.Column(db.String(200))
    example = db.Column(db.Text)
    synonyms = db.Column(db.Text)  # Синонимы через запятую
    antonyms = db.Column(db.Text)  # Антонимы через запятую
    popularity = db.Column(db.Integer, default=0)
    usage_frequency = db.Column(db.Integer, default=0)  # Частота использования (1-10)
    is_verified = db.Column(db.Boolean, default=False)  # Проверено экспертом
    is_archived = db.Column(db.Boolean, default=False)  # Архивное слово
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    sources = db.relationship('Source', backref='word', lazy=True, cascade='all, delete-orphan')
    comments = db.relationship('Comment', backref='word', lazy=True, cascade='all, delete-orphan')
    votes = db.relationship('Vote', backref='word', lazy=True, cascade='all, delete-orphan')
    
    def get_synonyms_list(self):
        """Возвращает список синонимов."""
        if self.synonyms:
            return [s.strip() for s in self.synonyms.split(',')]
        return []
    
    def get_antonyms_list(self):
        """Возвращает список антонимов."""
        if self.antonyms:
            return [a.strip() for a in self.antonyms.split(',')]
        return []
    
    def get_vote_score(self):
        """Возвращает рейтинг слова (сумма голосов)."""
        return sum(v.vote_type for v in self.votes)
    
    def __repr__(self):
        return f'<Word {self.word}>'

class Source(db.Model):
    __tablename__ = 'sources'
    
    id = db.Column(db.Integer, primary_key=True)
    word_id = db.Column(db.Integer, db.ForeignKey('words.id'))
    source_type = db.Column(db.String(50))  # книга, статья, сайт, фильм, музыка
    title = db.Column(db.String(200))  # Название источника
    author = db.Column(db.String(100))  # Автор
    url = db.Column(db.Text)
    year = db.Column(db.Integer)
    publisher = db.Column(db.String(100))  # Издательство
    description = db.Column(db.Text)
    is_primary = db.Column(db.Boolean, default=False)  # Основной источник
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Source {self.source_type}: {self.title}>'

class Comment(db.Model):
    __tablename__ = 'comments'
    
    id = db.Column(db.Integer, primary_key=True)
    word_id = db.Column(db.Integer, db.ForeignKey('words.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    content = db.Column(db.Text, nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('comments.id'))  # Для древовидных комментариев
    is_approved = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    replies = db.relationship('Comment', backref=db.backref('parent', remote_side=[id]))
    
    def __repr__(self):
        return f'<Comment {self.id}>'

class Vote(db.Model):
    __tablename__ = 'votes'
    
    id = db.Column(db.Integer, primary_key=True)
    word_id = db.Column(db.Integer, db.ForeignKey('words.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    vote_type = db.Column(db.Integer)  # 1 = лайк, -1 = дизлайк
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (db.UniqueConstraint('word_id', 'user_id', name='unique_word_user_vote'),)
    
    def __repr__(self):
        return f'<Vote {self.vote_type}>'

class WordHistory(db.Model):
    __tablename__ = 'word_history'
    
    id = db.Column(db.Integer, primary_key=True)
    word_id = db.Column(db.Integer, db.ForeignKey('words.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    action = db.Column(db.String(20))  # create, update, delete
    old_value = db.Column(db.Text)  # JSON старое значение
    new_value = db.Column(db.Text)  # JSON новое значение
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    word = db.relationship('Word', backref='history')
    user = db.relationship('User', backref='edit_history')
    
    def __repr__(self):
        return f'<WordHistory {self.action}>'