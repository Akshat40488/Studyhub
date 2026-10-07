from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models import db, Doubt, Answer, Subject, Notification
from services.auth_service import AuthService
from sqlalchemy import desc, func

doubts_bp = Blueprint('doubts', __name__)

@doubts_bp.route('/doubts')
def index():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    subject_id = request.args.get('subject_id', type=int)
    filter_type = request.args.get('filter', 'all')
    search = request.args.get('search', '').strip()
    
    query = Doubt.query
    
    if subject_id:
        query = query.filter_by(subject_id=subject_id)
    
    if filter_type == 'unanswered':
        query = query.filter_by(is_resolved=False)
    elif filter_type == 'resolved':
        query = query.filter_by(is_resolved=True)
    
    if search:
        query = query.filter(Doubt.title.ilike(f'%{search}%') | Doubt.content.ilike(f'%{search}%'))
    
    doubts = query.order_by(desc(Doubt.created_at)).paginate(page=page, per_page=per_page, error_out=False)
    subjects = Subject.query.order_by(Subject.name).all()
    
    return render_template('doubts/index.html', doubts=doubts, subjects=subjects, 
                           subject_id=subject_id, filter_type=filter_type, search=search)

@doubts_bp.route('/doubts/ask', methods=['GET', 'POST'])
@login_required
def ask():
    subjects = Subject.query.order_by(Subject.name).all()
    
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()
        subject_id = request.form.get('subject_id', type=int)
        tags = request.form.get('tags', '').strip()
        
        errors = {}
        
        if not title:
            errors['title'] = 'Title is required'
        elif len(title) > 200:
            errors['title'] = 'Title must be less than 200 characters'
        
        if not content:
            errors['content'] = 'Content is required'
        elif len(content) < 10:
            errors['content'] = 'Content must be at least 10 characters'
        
        if not subject_id:
            errors['subject_id'] = 'Subject is required'
        elif not Subject.query.get(subject_id):
            errors['subject_id'] = 'Invalid subject'
        
        if errors:
            for field, error in errors.items():
                flash(error, 'error')
            return render_template('doubts/ask.html', subjects=subjects, form_data=request.form), 400
        
        doubt = Doubt(
            title=title,
            content=content,
            author_id=current_user.id,
            subject_id=subject_id
        )
        
        db.session.add(doubt)
        db.session.commit()
        
        flash('Your doubt has been posted!', 'success')
        return redirect(url_for('doubts.view', doubt_id=doubt.id))
    
    return render_template('doubts/ask.html', subjects=subjects)

@doubts_bp.route('/doubts/<int:doubt_id>')
def view(doubt_id):
    doubt = Doubt.query.get_or_404(doubt_id)
    
    doubt.views += 1
    db.session.commit()
    
    answers = Answer.query.filter_by(doubt_id=doubt_id).order_by(desc(Answer.is_accepted), desc(Answer.created_at)).all()
    
    return render_template('doubts/view.html', doubt=doubt, answers=answers)

@doubts_bp.route('/doubts/<int:doubt_id>/answer', methods=['POST'])
@login_required
def answer(doubt_id):
    doubt = Doubt.query.get_or_404(doubt_id)
    content = request.form.get('content', '').strip()
    
    if not content:
        flash('Answer cannot be empty.', 'error')
        return redirect(url_for('doubts.view', doubt_id=doubt_id))
    
    if len(content) < 10:
        flash('Answer must be at least 10 characters.', 'error')
        return redirect(url_for('doubts.view', doubt_id=doubt_id))
    
    answer = Answer(
        content=content,
        author_id=current_user.id,
        doubt_id=doubt_id
    )
    
    db.session.add(answer)
    db.session.commit()
    
    AuthService.create_notification(
        doubt.author_id,
        'new_answer',
        'New answer to your doubt',
        f'{current_user.name} answered your doubt: {doubt.title}',
        doubt_id,
        'doubt'
    )
    
    flash('Your answer has been posted!', 'success')
    return redirect(url_for('doubts.view', doubt_id=doubt_id))

@doubts_bp.route('/doubts/<int:doubt_id>/accept/<int:answer_id>', methods=['POST'])
@login_required
def accept_answer(doubt_id, answer_id):
    doubt = Doubt.query.get_or_404(doubt_id)
    answer = Answer.query.get_or_404(answer_id)
    
    if doubt.author_id != current_user.id:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    if answer.doubt_id != doubt_id:
        return jsonify({'success': False, 'error': 'Invalid answer'}), 400
    
    previous_accepted = Answer.query.filter_by(doubt_id=doubt_id, is_accepted=True).first()
    if previous_accepted:
        previous_accepted.is_accepted = False
    
    answer.is_accepted = True
    doubt.is_resolved = True
    doubt.accepted_answer_id = answer_id
    
    db.session.commit()
    
    AuthService.create_notification(
        answer.author_id,
        'answer_accepted',
        'Your answer was accepted!',
        f'Your answer to "{doubt.title}" was marked as the accepted solution.',
        doubt_id,
        'doubt'
    )
    
    return jsonify({'success': True})

@doubts_bp.route('/doubts/<int:doubt_id>/delete', methods=['POST'])
@login_required
def delete(doubt_id):
    doubt = Doubt.query.get_or_404(doubt_id)
    
    if doubt.author_id != current_user.id:
        flash('You do not have permission to delete this doubt.', 'error')
        return redirect(url_for('dashboard.index'))
    
    db.session.delete(doubt)
    db.session.commit()
    
    flash('Doubt deleted successfully.', 'success')
    return redirect(url_for('doubts.index'))

@doubts_bp.route('/doubts/my-doubts')
@login_required
def my_doubts():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    doubts = Doubt.query.filter_by(author_id=current_user.id).order_by(desc(Doubt.created_at)).paginate(page=page, per_page=per_page, error_out=False)
    
    return render_template('doubts/my_doubts.html', doubts=doubts)