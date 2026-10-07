from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models import db, User, Subject, StudyMaterial, Doubt, Discussion, Quiz, QuizAttempt, UserProgress, Notification
from models import Answer, Rating
from services.recommendation_service import recommendation_service
from datetime import datetime, timedelta
from sqlalchemy import func, desc

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/dashboard')
@login_required
def index():
    stats = get_user_stats(current_user.id)
    continue_learning = get_continue_learning(current_user.id)
    recommendations = recommendation_service.get_recommendations_for_user(current_user.id, 4)
    recent_discussions = get_recent_discussions(current_user.id)
    available_quizzes = get_available_quizzes(current_user.id)
    progress_data = get_progress_data(current_user.id)
    
    return render_template('dashboard/index.html',
                           stats=stats,
                           continue_learning=continue_learning,
                           recommendations=recommendations,
                           recent_discussions=recent_discussions,
                           available_quizzes=available_quizzes,
                           progress_data=progress_data)

def get_user_stats(user_id):
    materials_viewed = db.session.query(func.count(StudyMaterial.id)).join(Rating, Rating.material_id == StudyMaterial.id).filter(Rating.user_id == user_id).scalar() or 0
    quiz_attempts = QuizAttempt.query.filter_by(user_id=user_id).count()
    
    # Calculate average percentage using database columns (percentage is a @property, not a column)
    avg_score = db.session.query(
        func.avg(QuizAttempt.correct_answers * 100.0 / QuizAttempt.total_questions)
    ).filter(
        QuizAttempt.user_id == user_id,
        QuizAttempt.total_questions > 0
    ).scalar() or 0
    
    subjects_studied = UserProgress.query.filter_by(user_id=user_id).count()
    
    streak = 0
    progress = UserProgress.query.filter_by(user_id=user_id).first()
    if progress:
        streak = progress.streak_days
    
    return {
        'materials_viewed': materials_viewed,
        'quiz_attempts': quiz_attempts,
        'average_score': round(avg_score, 1),
        'subjects_studied': subjects_studied,
        'study_streak': streak
    }

def get_continue_learning(user_id, limit=4):
    recent_ratings = Rating.query.filter_by(user_id=user_id).order_by(Rating.created_at.desc()).limit(limit).all()
    material_ids = [r.material_id for r in recent_ratings]
    
    if not material_ids:
        recent_attempts = QuizAttempt.query.filter_by(user_id=user_id).order_by(QuizAttempt.completed_at.desc()).limit(limit).all()
        quiz_ids = [a.quiz_id for a in recent_attempts]
        quizzes = Quiz.query.filter(Quiz.id.in_(quiz_ids)).all() if quiz_ids else []
        return [{'type': 'quiz', 'item': q} for q in quizzes]
    
    materials = StudyMaterial.query.filter(StudyMaterial.id.in_(material_ids)).all()
    return [{'type': 'material', 'item': m} for m in materials]

def get_recent_discussions(user_id, limit=5):
    user_subjects = db.session.query(UserProgress.subject_id).filter_by(user_id=user_id).all()
    subject_ids = [s[0] for s in user_subjects]
    
    if not subject_ids:
        subject_ids = [s.id for s in Subject.query.limit(5).all()]
    
    discussions = Discussion.query.filter(Discussion.subject_id.in_(subject_ids)).order_by(desc(Discussion.created_at)).limit(limit).all()
    return discussions

def get_available_quizzes(user_id, limit=4):
    attempted_quiz_ids = [a.quiz_id for a in QuizAttempt.query.filter_by(user_id=user_id).all()]
    
    query = Quiz.query.filter_by(is_public=True)
    if attempted_quiz_ids:
        query = query.filter(~Quiz.id.in_(attempted_quiz_ids))
    
    return query.order_by(desc(Quiz.created_at)).limit(limit).all()

def get_progress_data(user_id):
    progress = UserProgress.query.filter_by(user_id=user_id).join(Subject).all()
    
    labels = []
    scores = []
    for p in progress:
        labels.append(p.subject.name[:15])
        scores.append(p.average_score)
    
    recent_attempts = QuizAttempt.query.filter_by(user_id=user_id).order_by(desc(QuizAttempt.completed_at)).limit(10).all()
    attempt_labels = []
    attempt_scores = []
    for a in reversed(recent_attempts):
        attempt_labels.append(a.completed_at.strftime('%m/%d'))
        attempt_scores.append(a.percentage)
    
    return {
        'subject_labels': labels,
        'subject_scores': scores,
        'attempt_labels': attempt_labels,
        'attempt_scores': attempt_scores,
        'total_subjects': len(progress)
    }

@dashboard_bp.route('/notifications')
@login_required
def notifications():
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    notifications = Notification.query.filter_by(user_id=current_user.id).order_by(desc(Notification.created_at)).paginate(page=page, per_page=per_page, error_out=False)
    
    unread_count = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
    
    return render_template('dashboard/notifications.html', notifications=notifications, unread_count=unread_count)

@dashboard_bp.route('/notifications/mark-read/<int:notification_id>', methods=['POST'])
@login_required
def mark_notification_read(notification_id):
    notification = Notification.query.filter_by(id=notification_id, user_id=current_user.id).first_or_404()
    notification.is_read = True
    db.session.commit()
    return jsonify({'success': True})

@dashboard_bp.route('/notifications/mark-all-read', methods=['POST'])
@login_required
def mark_all_notifications_read():
    Notification.query.filter_by(user_id=current_user.id, is_read=False).update({'is_read': True})
    db.session.commit()
    return jsonify({'success': True})