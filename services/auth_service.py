from models import db, User, Notification
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import re

class AuthService:
    @staticmethod
    def validate_registration(data):
        errors = {}
        
        name = data.get('name', '').strip()
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        confirm_password = data.get('confirm_password', '')
        
        if not name:
            errors['name'] = 'Name is required'
        elif len(name) < 2:
            errors['name'] = 'Name must be at least 2 characters'
        elif len(name) > 100:
            errors['name'] = 'Name must be less than 100 characters'
        
        if not email:
            errors['email'] = 'Email is required'
        elif not re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', email):
            errors['email'] = 'Invalid email format'
        elif User.query.filter_by(email=email).first():
            errors['email'] = 'Email already registered'
        
        if not password:
            errors['password'] = 'Password is required'
        elif len(password) < 8:
            errors['password'] = 'Password must be at least 8 characters'
        elif not re.search(r'[A-Z]', password):
            errors['password'] = 'Password must contain at least one uppercase letter'
        elif not re.search(r'[a-z]', password):
            errors['password'] = 'Password must contain at least one lowercase letter'
        elif not re.search(r'\d', password):
            errors['password'] = 'Password must contain at least one number'
        elif not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            errors['password'] = 'Password must contain at least one special character'
        
        if password != confirm_password:
            errors['confirm_password'] = 'Passwords do not match'
        
        return errors
    
    @staticmethod
    def validate_login(data):
        errors = {}
        
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        
        if not email:
            errors['email'] = 'Email is required'
        if not password:
            errors['password'] = 'Password is required'
        
        return errors
    
    @staticmethod
    def register_user(data):
        errors = AuthService.validate_registration(data)
        if errors:
            return None, errors
        
        user = User(
            name=data['name'].strip(),
            email=data['email'].strip().lower()
        )
        user.set_password(data['password'])
        
        db.session.add(user)
        db.session.commit()
        
        return user, None
    
    @staticmethod
    def login_user(email, password, remember=False):
        user = User.query.filter_by(email=email.lower()).first()
        
        if not user:
            return None, 'Invalid email or password'
        
        if not user.check_password(password):
            return None, 'Invalid email or password'
        
        if not user.is_active:
            return None, 'Account is deactivated'
        
        user.last_login = datetime.utcnow()
        db.session.commit()
        
        return user, None
    
    @staticmethod
    def update_profile(user, data):
        errors = {}
        
        name = data.get('name', '').strip()
        email = data.get('email', '').strip().lower()
        bio = data.get('bio', '').strip()
        
        if not name:
            errors['name'] = 'Name is required'
        elif len(name) < 2:
            errors['name'] = 'Name must be at least 2 characters'
        elif len(name) > 100:
            errors['name'] = 'Name must be less than 100 characters'
        
        if not email:
            errors['email'] = 'Email is required'
        elif not re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', email):
            errors['email'] = 'Invalid email format'
        elif email != user.email and User.query.filter_by(email=email).first():
            errors['email'] = 'Email already in use'
        
        if len(bio) > 500:
            errors['bio'] = 'Bio must be less than 500 characters'
        
        if errors:
            return False, errors
        
        user.name = name
        user.email = email
        user.bio = bio
        db.session.commit()
        
        return True, None
    
    @staticmethod
    def change_password(user, data):
        errors = {}
        
        current_password = data.get('current_password', '')
        new_password = data.get('new_password', '')
        confirm_password = data.get('confirm_password', '')
        
        if not current_password:
            errors['current_password'] = 'Current password is required'
        elif not user.check_password(current_password):
            errors['current_password'] = 'Current password is incorrect'
        
        if not new_password:
            errors['new_password'] = 'New password is required'
        elif len(new_password) < 8:
            errors['new_password'] = 'Password must be at least 8 characters'
        elif not re.search(r'[A-Z]', new_password):
            errors['new_password'] = 'Password must contain at least one uppercase letter'
        elif not re.search(r'[a-z]', new_password):
            errors['new_password'] = 'Password must contain at least one lowercase letter'
        elif not re.search(r'\d', new_password):
            errors['new_password'] = 'Password must contain at least one number'
        elif not re.search(r'[!@#$%^&*(),.?":{}|<>]', new_password):
            errors['new_password'] = 'Password must contain at least one special character'
        
        if new_password != confirm_password:
            errors['confirm_password'] = 'Passwords do not match'
        
        if errors:
            return False, errors
        
        user.set_password(new_password)
        db.session.commit()
        
        return True, None
    
    @staticmethod
    def create_notification(user_id, type, title, message, related_id=None, related_type=None):
        notification = Notification(
            user_id=user_id,
            type=type,
            title=title,
            message=message,
            related_id=related_id,
            related_type=related_type
        )
        db.session.add(notification)
        db.session.commit()
        return notification