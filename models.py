# database table models

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    e = db.Column(db.BigInteger, nullable=False)
    n = db.Column(db.BigInteger, nullable=False)

class Message(db.Model):
    __tablename__ = 'messages'
    id = db.Column(db.Integer, primary_key=True)
    sender = db.Column(db.String(50), nullable=False)
    receiver = db.Column(db.String(50), nullable=False)
    session_label = db.Column(db.String(100), nullable=False)
    encrypted_text = db.Column(db.Text, nullable=False)

class Session(db.Model):
    __tablename__ = 'sessions'
    id = db.Column(db.Integer, primary_key=True)
    from_user = db.Column(db.String(50), nullable=False)
    to_user = db.Column(db.String(50), nullable=False)
    label = db.Column(db.String(100), nullable=False)
    encrypted_for_sender = db.Column(db.BigInteger, nullable=False)
    encrypted_for_receiver = db.Column(db.BigInteger, nullable=False)
