import os
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta, timezone
import json

from config import config
from models import db, User, Subject, StudyMaterial, Doubt, Answer, Discussion, Comment
from models import StudyGroup, GroupMember, GroupMaterial, GroupDiscussion, GroupDiscussionComment
from models import Quiz, Question, QuizAttempt, Rating, UserProgress, Notification
from database import init_db
from services.file_service import FileService
from services.auth_service import AuthService
from services.recommendation_service import RecommendationService
from routes.auth import auth_bp
from routes.dashboard import dashboard_bp
from routes.subjects import subjects_bp
from routes.materials import materials_bp
from routes.doubts import doubts_bp
from routes.discussions import discussions_bp
from routes.groups import groups_bp
from routes.quizzes import quizzes_bp
from routes.search import search_bp
from routes.progress import progress_bp
from routes.api import api_bp

def create_app(config_name='default'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    init_db(app)
    
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    @app.context_processor
    def inject_globals():
        return {
            'current_year': datetime.now(timezone.utc).year,
            'subjects': Subject.query.order_by(Subject.name).all(),
            'StudyMaterial': StudyMaterial,
            'Quiz': Quiz,
            'Doubt': Doubt,
            'Discussion': Discussion,
            'StudyGroup': StudyGroup,
            'Notification': Notification,
            'unread_notifications': Notification.query.filter_by(user_id=current_user.id, is_read=False).count() if current_user.is_authenticated else 0
        }
    
    @app.template_filter('timeago')
    def timeago_filter(date):
        if not date:
            return ''
        now = datetime.now(timezone.utc)
        # Handle offset-naive datetimes from database
        if date.tzinfo is None:
            date = date.replace(tzinfo=timezone.utc)
        diff = now - date
        if diff.days > 30:
            return date.strftime('%b %d, %Y')
        elif diff.days > 0:
            return f'{diff.days}d ago'
        elif diff.seconds > 3600:
            return f'{diff.seconds // 3600}h ago'
        elif diff.seconds > 60:
            return f'{diff.seconds // 60}m ago'
        else:
            return 'Just now'
    
    @app.template_filter('file_size')
    def file_size_filter(size):
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f'{size:.1f} {unit}'
            size /= 1024
        return f'{size:.1f} TB'
    
    @app.template_filter('file_icon')
    def file_icon_filter(extension):
        icons = {
            'pdf': 'file-text',
            'doc': 'file-text',
            'docx': 'file-text',
            'txt': 'file-text',
            'md': 'file-text',
            'ppt': 'presentation',
            'pptx': 'presentation',
            'xls': 'table',
            'xlsx': 'table',
            'png': 'image',
            'jpg': 'image',
            'jpeg': 'image',
            'gif': 'image',
        }
        return icons.get(extension.lower(), 'file')
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(subjects_bp)
    app.register_blueprint(materials_bp)
    app.register_blueprint(doubts_bp)
    app.register_blueprint(discussions_bp)
    app.register_blueprint(groups_bp)
    app.register_blueprint(quizzes_bp)
    app.register_blueprint(search_bp)
    app.register_blueprint(progress_bp)
    app.register_blueprint(api_bp)
    
    @app.route('/')
    def index():
        if current_user.is_authenticated:
            return redirect(url_for('dashboard.index'))
        return render_template('landing.html')
    
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(403)
    def forbidden_error(error):
        return render_template('errors/403.html'), 403
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template('errors/500.html'), 500
    
    return app

if __name__ == '__main__':
    app = create_app('development')
    app.run(debug=True, host='0.0.0.0', port=5000)