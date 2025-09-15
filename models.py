from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default='user')
    banned = db.Column(db.Boolean, default=False)
    online = db.Column(db.Boolean, default=False)

    sent_messages = db.relationship('Message', foreign_keys='Message.sender_id', backref='sender', lazy=True)
    received_messages = db.relationship('Message', foreign_keys='Message.receiver_id', backref='receiver', lazy=True)
    groups = db.relationship('GroupMembers', backref='user', lazy=True)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'))  # For private messages
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'))    # For group messages
    room = db.Column(db.String(50))                                 # For public room messages
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=db.func.current_timestamp())
    read = db.Column(db.Boolean, default=False)

class Group(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    members = db.relationship('GroupMembers', backref='group', lazy=True)
    messages = db.relationship('Message', backref='group', lazy=True)

class GroupMembers(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
