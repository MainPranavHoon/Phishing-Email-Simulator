# models.py
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash,check_password_hash


db = SQLAlchemy()


class AdminLogin(db.Model):
    __tablename__="admin_login"
    id=db.Column(db.Integer,primary_key=True)
    username=db.Column(db.String(255),nullable=False,unique=True)
    password_hash=db.Column(db.String(255),nullable=False,unique=True)
    campaigns = db.relationship('Campaign', backref='admin', lazy=True)

    @property#Python decorator that makes a method behave like an attribute admin.password instead of admin.password()
    def password(self): #prevents anyone from reading the password
        raise AttributeError("password is not a readable attribute")
    
    @password.setter#tells Python When someone tries to assign a value to admin.password, use the method below.”
    def password(self,password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self,password):
        return check_password_hash(self.password_hash,password)    

class Campaign(db.Model):
    __tablename__ = 'campaigns'
    campaign_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    admin_id = db.Column(db.Integer, db.ForeignKey('admin_login.id'), nullable=False)

    campaign_name = db.Column(db.String(100), nullable=False)
    email_subject = db.Column(db.String(255))
    email_body = db.Column(db.Text, nullable=False)

    template_id = db.Column(db.Integer, db.ForeignKey('email_template.id'), nullable=True)
    template = db.relationship("EmailTemplate", backref="campaigns")

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    mail_logs = db.relationship('MailLog', backref='campaign', lazy=True)


class UserEmail(db.Model):
    __tablename__ = 'user_emails'
    user_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    email = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(100))
    mail_logs = db.relationship('MailLog', backref='user', lazy=True)

class MailLog(db.Model):
    __tablename__ = 'mail_logs'
    mail_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey('campaigns.campaign_id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user_emails.user_id'), nullable=False)
    sent_at = db.Column(db.DateTime, default=datetime.utcnow)
    tracking_url = db.Column(db.String(255))
    click_logs = db.relationship('ClickLog', backref='mail', lazy=True)
    opened_at = db.Column(db.DateTime, nullable=True)


class ClickLog(db.Model):
    __tablename__ = 'click_logs'
    click_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    mail_id = db.Column(db.Integer, db.ForeignKey('mail_logs.mail_id'), nullable=False)
    clicked_at = db.Column(db.DateTime, default=datetime.utcnow)
    ip_address = db.Column(db.String(50))
    user_agent = db.Column(db.String(255))
    awareness_logs = db.relationship('AwarenessLog', backref='click', lazy=True)

class AwarenessLog(db.Model):
    __tablename__ = 'awareness_logs'
    awareness_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    click_id = db.Column(db.Integer, db.ForeignKey('click_logs.click_id'), nullable=False)
    sent_at = db.Column(db.DateTime, default=datetime.utcnow)
    material_link = db.Column(db.String(255))

class EmailTemplate(db.Model):
    __tablename__ = "email_template"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    subject = db.Column(db.String(200), nullable=False)
    body = db.Column(db.Text, nullable=False)
    description = db.Column(db.String(300), nullable=True)
