from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from models import db, Notification, Rating, StudyMaterial, Subject, User
from services.recommendation_service import recommendation_service
from sqlalchemy import desc

api_bp = Blueprint('api', __name__)

@api_bp.route('/notifications/unread-count')
@login_required
def unread_notification_count():
    count = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
    return jsonify({'count': count})

@api_bp.route('/notifications/recent')
@login_required
def recent_notifications():
    notifications = Notification.query.filter_by(user_id=current_user.id).order_by(desc(Notification.created_at)).limit(10).all()
    
    return jsonify({
        'notifications': [{
            'id': n.id,
            'type': n.type,
            'title': n.title,
            'message': n.message,
            'is_read': n.is_read,
            'created_at': n.created_at.isoformat(),
            'related_id': n.related_id,
            'related_type': n.related_type
        } for n in notifications]
    })

@api_bp.route('/materials/<int:material_id>/rating', methods=['GET'])
@login_required
def get_material_rating(material_id):
    material = StudyMaterial.query.get_or_404(material_id)
    user_rating = Rating.query.filter_by(user_id=current_user.id, material_id=material_id).first()
    
    return jsonify({
        'average_rating': material.average_rating,
        'rating_count': material.rating_count,
        'user_rating': user_rating.score if user_rating else None,
        'user_feedback': user_rating.feedback if user_rating else None
    })

@api_bp.route('/recommendations/refresh', methods=['POST'])
@login_required
def refresh_recommendations():
    recommendation_service.train()
    recommendations = recommendation_service.get_recommendations_for_user(current_user.id, 4)
    
    return jsonify({
        'materials': [{
            'id': m.id,
            'title': m.title,
            'subject': m.subject.name,
            'subject_color': m.subject.color,
            'author': m.author.name,
            'views': m.views,
            'downloads': m.downloads,
            'average_rating': m.average_rating,
            'file_extension': m.file_extension,
            'created_at': m.created_at.strftime('%b %d, %Y')
        } for m in recommendations['materials']],
        'quizzes': [{
            'id': q.id,
            'title': q.title,
            'subject': q.subject.name,
            'subject_color': q.subject.color,
            'question_count': q.question_count,
            'time_limit': q.time_limit
        } for q in recommendations['quizzes']],
        'subjects': [{
            'id': s['subject'].id,
            'name': s['subject'].name,
            'color': s['subject'].color,
            'reason': s['reason']
        } for s in recommendations['subjects']]
    })

@api_bp.route('/subjects/<int:subject_id>/stats')
def subject_stats(subject_id):
    subject = Subject.query.get_or_404(subject_id)
    
    material_count = StudyMaterial.query.filter_by(subject_id=subject_id, is_public=True).count()
    quiz_count = Quiz.query.filter_by(subject_id=subject_id, is_public=True).count()
    doubt_count = Doubt.query.filter_by(subject_id=subject_id).count()
    discussion_count = Discussion.query.filter_by(subject_id=subject_id).count()
    
    return jsonify({
        'material_count': material_count,
        'quiz_count': quiz_count,
        'doubt_count': doubt_count,
        'discussion_count': discussion_count
    })

@api_bp.route('/users/search')
@login_required
def search_users():
    query = request.args.get('q', '').strip()
    
    if len(query) < 2:
        return jsonify({'users': []})
    
    users = User.query.filter(
        User.is_active == True,
        User.id != current_user.id,
        db.or_(
            User.name.ilike(f'%{query}%'),
            User.email.ilike(f'%{query}%')
        )
    ).limit(10).all()
    
    return jsonify({
        'users': [{
            'id': u.id,
            'name': u.name,
            'email': u.email,
            'avatar': u.avatar
        } for u in users]
    })