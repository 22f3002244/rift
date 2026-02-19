from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json

db = SQLAlchemy()


class UploadSession(db.Model):
    __tablename__ = 'upload_sessions'
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    upload_time = db.Column(db.DateTime, default=datetime.utcnow)
    total_transactions = db.Column(db.Integer, default=0)
    total_accounts = db.Column(db.Integer, default=0)
    processing_time = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(50), default='processing')

    transactions = db.relationship('Transaction', backref='session', lazy=True, cascade='all, delete-orphan')
    fraud_rings = db.relationship('FraudRing', backref='session', lazy=True, cascade='all, delete-orphan')
    suspicious_accounts = db.relationship('SuspiciousAccount', backref='session', lazy=True, cascade='all, delete-orphan')


class Transaction(db.Model):
    __tablename__ = 'transactions'
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('upload_sessions.id'), nullable=False)
    transaction_id = db.Column(db.String(100))
    sender_id = db.Column(db.String(100))
    receiver_id = db.Column(db.String(100))
    amount = db.Column(db.Float)
    timestamp = db.Column(db.DateTime)


class FraudRing(db.Model):
    __tablename__ = 'fraud_rings'
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('upload_sessions.id'), nullable=False)
    ring_id = db.Column(db.String(50))
    pattern_type = db.Column(db.String(50))
    risk_score = db.Column(db.Float)
    member_accounts_json = db.Column(db.Text)

    @property
    def member_accounts(self):
        return json.loads(self.member_accounts_json or '[]')

    @member_accounts.setter
    def member_accounts(self, value):
        self.member_accounts_json = json.dumps(value)


class SuspiciousAccount(db.Model):
    __tablename__ = 'suspicious_accounts'
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('upload_sessions.id'), nullable=False)
    account_id = db.Column(db.String(100))
    suspicion_score = db.Column(db.Float)
    detected_patterns_json = db.Column(db.Text)
    ring_id = db.Column(db.String(50))
    ai_explanation = db.Column(db.Text)

    @property
    def detected_patterns(self):
        return json.loads(self.detected_patterns_json or '[]')

    @detected_patterns.setter
    def detected_patterns(self, value):
        self.detected_patterns_json = json.dumps(value)
