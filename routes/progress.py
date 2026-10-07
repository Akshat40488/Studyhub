from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from models import db, UserProgress, QuizAttempt, StudyMaterial, Subject, Rating
from sqlalchemy import func, desc
from datetime import datetime, timedelta
import json

progress_bp = Blueprint('progress', __name__)

@progress_bp.route('/progress')
@login_required
def index():
    progress_data = get_user_progress(current_user.id)
    quiz_history = get_quiz_history(current_user.id)
    activity_data = get_activity_data(current_user.id)
    weak_areas = get_weak_areas(current_user.id)
    
    return render_template('progress/index.html',
                           progress_data=progress_data,
                           quiz_history=quiz_history,
                           activity_data=activity_data,
                           weak_areas=weak_areas)

def get_user_progress(user_id):
    progress = UserProgress.query.filter_by(user_id=user_id).join(Subject).all()
    
    subjects = []
    for p in progress:
        subjects.append({
            'id': p.subject_id,
            'name': p.subject.name,
            'color': p.subject.color,
            'materials_viewed': p.materials_viewed,
            'quizzes_attempted': p.quizzes_attempted,
            'average_score': p.average_score,
            'study_time': p.study_time,
            'streak_days': p.streak_days
        })
    
    total_materials = sum(s['materials_viewed'] for s in subjects)
    total_quizzes = sum(s['quizzes_attempted'] for s in subjects)
    overall_avg = sum(s['average_score'] for s in subjects) / len(subjects) if subjects else 0
    
    return {
        'subjects': subjects,
        'total_materials': total_materials,
        'total_quizzes': total_quizzes,
        'overall_average': round(overall_avg, 1),
        'subject_count': len(subjects)
    }

def get_quiz_history(user_id, limit=20):
    attempts = QuizAttempt.query.filter_by(user_id=user_id).order_by(desc(QuizAttempt.completed_at)).limit(limit).all()
    
    history = []
    for a in attempts:
        quiz = a.quiz
        history.append({
            'id': a.id,
            'quiz_title': quiz.title,
            'subject': quiz.subject.name,
            'subject_color': quiz.subject.color,
            'score': a.score,
            'total': a.total_questions,
            'percentage': a.percentage,
            'passed': a.passed,
            'time_taken': format_time(a.time_taken),
            'date': a.completed_at.strftime('%b %d, %Y')
        })
    
    return history

def get_activity_data(user_id, days=30):
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    attempts = QuizAttempt.query.filter(
        QuizAttempt.user_id == user_id,
        QuizAttempt.completed_at >= start_date
    ).all()
    
    ratings = Rating.query.filter(
        Rating.user_id == user_id,
        Rating.created_at >= start_date
    ).all()
    
    activity_by_date = {}
    current = start_date
    while current <= end_date:
        date_str = current.strftime('%Y-%m-%d')
        activity_by_date[date_str] = {'quizzes': 0, 'materials': 0}
        current += timedelta(days=1)
    
    for a in attempts:
        date_str = a.completed_at.strftime('%Y-%m-%d')
        if date_str in activity_by_date:
            activity_by_date[date_str]['quizzes'] += 1
    
    for r in ratings:
        date_str = r.created_at.strftime('%Y-%m-%d')
        if date_str in activity_by_date:
            activity_by_date[date_str]['materials'] += 1
    
    labels = []
    quiz_data = []
    material_data = []
    
    for date_str, data in sorted(activity_by_date.items()):
        labels.append(datetime.strptime(date_str, '%Y-%m-%d').strftime('%m/%d'))
        quiz_data.append(data['quizzes'])
        material_data.append(data['materials'])
    
    return {
        'labels': labels,
        'quizzes': quiz_data,
        'materials': material_data
    }

def get_weak_areas(user_id):
    progress = UserProgress.query.filter_by(user_id=user_id).join(Subject).all()
    
    weak_subjects = []
    for p in progress:
        if p.quizzes_attempted >= 3 and p.average_score < 70:
            weak_subjects.append({
                'subject': p.subject.name,
                'color': p.subject.color,
                'average_score': p.average_score,
                'quizzes_attempted': p.quizzes_attempted,
                'gap': 70 - p.average_score
            })
    
    weak_subjects.sort(key=lambda x: x['gap'], reverse=True)
    
    return weak_subjects[:5]

def format_time(seconds):
    if seconds < 60:
        return f'{seconds}s'
    elif seconds < 3600:
        return f'{seconds // 60}m {seconds % 60}s'
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f'{hours}h {minutes}m'

@progress_bp.route('/api/progress/chart-data')
@login_required
def chart_data():
    progress_data = get_user_progress(current_user.id)
    activity_data = get_activity_data(current_user.id)
    
    subject_labels = [s['name'] for s in progress_data['subjects']]
    subject_scores = [s['average_score'] for s in progress_data['subjects']]
    subject_colors = [s['color'] for s in progress_data['subjects']]
    
    return jsonify({
        'subjects': {
            'labels': subject_labels,
            'scores': subject_scores,
            'colors': subject_colors
        },
        'activity': activity_data
    })