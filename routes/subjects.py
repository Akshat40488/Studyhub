from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models import db, Subject, StudyMaterial, Quiz, Doubt, Discussion, UserProgress
from sqlalchemy import func, desc

subjects_bp = Blueprint('subjects', __name__)

@subjects_bp.route('/subjects')
def index():
    page = request.args.get('page', 1, type=int)
    per_page = 12
    search = request.args.get('search', '').strip()
    
    query = Subject.query
    
    if search:
        query = query.filter(Subject.name.ilike(f'%{search}%') | Subject.description.ilike(f'%{search}%'))
    
    subjects = query.order_by(Subject.name).paginate(page=page, per_page=per_page, error_out=False)
    
    return render_template('subjects/index.html', subjects=subjects, search=search)

@subjects_bp.route('/subjects/<slug>')
def show(slug):
    subject = Subject.query.filter_by(slug=slug).first_or_404()
    
    materials = StudyMaterial.query.filter_by(subject_id=subject.id, is_public=True).order_by(desc(StudyMaterial.created_at)).limit(6).all()
    quizzes = Quiz.query.filter_by(subject_id=subject.id, is_public=True).order_by(desc(Quiz.created_at)).limit(6).all()
    doubts = Doubt.query.filter_by(subject_id=subject.id).order_by(desc(Doubt.created_at)).limit(5).all()
    discussions = Discussion.query.filter_by(subject_id=subject.id).order_by(desc(Discussion.created_at)).limit(5).all()
    
    user_progress = None
    if current_user.is_authenticated:
        user_progress = UserProgress.query.filter_by(user_id=current_user.id, subject_id=subject.id).first()
    
    material_count = StudyMaterial.query.filter_by(subject_id=subject.id, is_public=True).count()
    quiz_count = Quiz.query.filter_by(subject_id=subject.id, is_public=True).count()
    doubt_count = Doubt.query.filter_by(subject_id=subject.id).count()
    discussion_count = Discussion.query.filter_by(subject_id=subject.id).count()
    
    return render_template('subjects/show.html',
                           subject=subject,
                           materials=materials,
                           quizzes=quizzes,
                           doubts=doubts,
                           discussions=discussions,
                           user_progress=user_progress,
                           material_count=material_count,
                           quiz_count=quiz_count,
                           doubt_count=doubt_count,
                           discussion_count=discussion_count)

@subjects_bp.route('/subjects/<slug>/materials')
def materials(slug):
    subject = Subject.query.filter_by(slug=slug).first_or_404()
    page = request.args.get('page', 1, type=int)
    per_page = 12
    sort = request.args.get('sort', 'recent')
    file_type = request.args.get('type', '')
    
    query = StudyMaterial.query.filter_by(subject_id=subject.id, is_public=True)
    
    if file_type:
        query = query.filter(StudyMaterial.file_extension == file_type)
    
    if sort == 'popular':
        query = query.order_by(desc(StudyMaterial.views), desc(StudyMaterial.downloads))
    elif sort == 'rating':
        query = query.outerjoin(Rating).group_by(StudyMaterial.id).order_by(desc(func.avg(Rating.score)))
    else:
        query = query.order_by(desc(StudyMaterial.created_at))
    
    materials = query.paginate(page=page, per_page=per_page, error_out=False)
    
    file_types = db.session.query(StudyMaterial.file_extension, func.count(StudyMaterial.id)).filter_by(subject_id=subject.id, is_public=True).group_by(StudyMaterial.file_extension).all()
    
    return render_template('subjects/materials.html',
                           subject=subject,
                           materials=materials,
                           sort=sort,
                           file_type=file_type,
                           file_types=file_types)

@subjects_bp.route('/subjects/<slug>/quizzes')
def quizzes(slug):
    subject = Subject.query.filter_by(slug=slug).first_or_404()
    page = request.args.get('page', 1, type=int)
    per_page = 12
    
    quizzes = Quiz.query.filter_by(subject_id=subject.id, is_public=True).order_by(desc(Quiz.created_at)).paginate(page=page, per_page=per_page, error_out=False)
    
    return render_template('subjects/quizzes.html', subject=subject, quizzes=quizzes)

@subjects_bp.route('/subjects/<slug>/doubts')
def doubts(slug):
    subject = Subject.query.filter_by(slug=slug).first_or_404()
    page = request.args.get('page', 1, type=int)
    per_page = 10
    filter_type = request.args.get('filter', 'all')
    
    query = Doubt.query.filter_by(subject_id=subject.id)
    
    if filter_type == 'unanswered':
        query = query.filter_by(is_resolved=False)
    elif filter_type == 'resolved':
        query = query.filter_by(is_resolved=True)
    
    doubts = query.order_by(desc(Doubt.created_at)).paginate(page=page, per_page=per_page, error_out=False)
    
    return render_template('subjects/doubts.html', subject=subject, doubts=doubts, filter_type=filter_type)

@subjects_bp.route('/subjects/<slug>/discussions')
def discussions(slug):
    subject = Subject.query.filter_by(slug=slug).first_or_404()
    page = request.args.get('page', 1, type=int)
    per_page = 10
    sort = request.args.get('sort', 'recent')
    
    query = Discussion.query.filter_by(subject_id=subject.id)
    
    if sort == 'popular':
        query = query.outerjoin(Comment).group_by(Discussion.id).order_by(desc(func.count(Comment.id)))
    else:
        query = query.order_by(desc(Discussion.created_at))
    
    discussions = query.paginate(page=page, per_page=per_page, error_out=False)
    
    return render_template('subjects/discussions.html', subject=subject, discussions=discussions, sort=sort)