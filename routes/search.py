from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from models import StudyMaterial, Subject, Doubt, Discussion, StudyGroup, Quiz, User
from sqlalchemy import or_, func

search_bp = Blueprint('search', __name__)

@search_bp.route('/search')
def index():
    query = request.args.get('q', '').strip()
    category = request.args.get('category', 'all')
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    results = {
        'materials': [],
        'subjects': [],
        'doubts': [],
        'discussions': [],
        'groups': [],
        'quizzes': [],
        'users': []
    }
    
    total_count = 0
    
    if query:
        search_term = f'%{query}%'
        
        if category in ['all', 'materials']:
            materials = StudyMaterial.query.filter(
                StudyMaterial.is_public == True,
                or_(
                    StudyMaterial.title.ilike(search_term),
                    StudyMaterial.description.ilike(search_term)
                )
            ).order_by(StudyMaterial.views.desc()).limit(per_page).all()
            results['materials'] = materials
            total_count += len(materials)
        
        if category in ['all', 'subjects']:
            subjects = Subject.query.filter(
                or_(
                    Subject.name.ilike(search_term),
                    Subject.description.ilike(search_term)
                )
            ).limit(per_page).all()
            results['subjects'] = subjects
            total_count += len(subjects)
        
        if category in ['all', 'doubts']:
            doubts = Doubt.query.filter(
                or_(
                    Doubt.title.ilike(search_term),
                    Doubt.content.ilike(search_term)
                )
            ).order_by(Doubt.created_at.desc()).limit(per_page).all()
            results['doubts'] = doubts
            total_count += len(doubts)
        
        if category in ['all', 'discussions']:
            discussions = Discussion.query.filter(
                or_(
                    Discussion.title.ilike(search_term),
                    Discussion.content.ilike(search_term)
                )
            ).order_by(Discussion.created_at.desc()).limit(per_page).all()
            results['discussions'] = discussions
            total_count += len(discussions)
        
        if category in ['all', 'groups']:
            groups = StudyGroup.query.filter(
                or_(
                    StudyGroup.name.ilike(search_term),
                    StudyGroup.description.ilike(search_term)
                )
            ).order_by(StudyGroup.created_at.desc()).limit(per_page).all()
            results['groups'] = groups
            total_count += len(groups)
        
        if category in ['all', 'quizzes']:
            quizzes = Quiz.query.filter(
                Quiz.is_public == True,
                or_(
                    Quiz.title.ilike(search_term),
                    Quiz.description.ilike(search_term)
                )
            ).order_by(Quiz.created_at.desc()).limit(per_page).all()
            results['quizzes'] = quizzes
            total_count += len(quizzes)
        
        if category in ['all', 'users'] and current_user.is_authenticated:
            users = User.query.filter(
                User.is_active == True,
                or_(
                    User.name.ilike(search_term),
                    User.email.ilike(search_term)
                )
            ).limit(per_page).all()
            results['users'] = users
            total_count += len(users)
    
    return render_template('search/index.html', 
                           results=results, 
                           query=query, 
                           category=category,
                           total_count=total_count)

@search_bp.route('/api/search/suggestions')
def suggestions():
    query = request.args.get('q', '').strip()
    
    if len(query) < 2:
        return jsonify({'suggestions': []})
    
    search_term = f'%{query}%'
    suggestions = []
    
    materials = StudyMaterial.query.filter(
        StudyMaterial.is_public == True,
        StudyMaterial.title.ilike(search_term)
    ).limit(5).all()
    
    for m in materials:
        suggestions.append({
            'type': 'material',
            'title': m.title,
            'subtitle': f'Material • {m.subject.name}',
            'url': f'/materials/{m.id}'
        })
    
    subjects = Subject.query.filter(
        Subject.name.ilike(search_term)
    ).limit(3).all()
    
    for s in subjects:
        suggestions.append({
            'type': 'subject',
            'title': s.name,
            'subtitle': 'Subject',
            'url': f'/subjects/{s.slug}'
        })
    
    doubts = Doubt.query.filter(
        Doubt.title.ilike(search_term)
    ).limit(3).all()
    
    for d in doubts:
        suggestions.append({
            'type': 'doubt',
            'title': d.title,
            'subtitle': f'Doubt • {d.subject.name}',
            'url': f'/doubts/{d.id}'
        })
    
    return jsonify({'suggestions': suggestions[:10]})