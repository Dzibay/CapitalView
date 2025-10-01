from . import db
from datetime import datetime

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.String, primary_key=True)
    email = db.Column(db.String, nullable=False)
    tinkoff_token = db.Column(db.String)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
