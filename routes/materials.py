from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file, jsonify
from flask_login import login_required, current_user
from models import db, StudyMaterial, Subject, Rating, UserProgress
from services.file_service import FileService
from services.auth_service import AuthService
from werkzeug.utils import secure_filename
import os

materials_bp = Blueprint('materials', __name__)

@materials_bp.route('/materials/upload', methods=['GET', 'POST'])
@login_required
def upload():
    subjects = Subject.query.order_by(Subject.name).all()
    
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        subject_id = request.form.get('subject_id', type=int)
        file = request.files.get('file')
        is_public = request.form.get('is_public') == 'on'
        
        errors = {}
        
        if not title:
            errors['title'] = 'Title is required'
        elif len(title) > 200:
            errors['title'] = 'Title must be less than 200 characters'
        
        if not subject_id:
            errors['subject_id'] = 'Subject is required'
        elif not Subject.query.get(subject_id):
            errors['subject_id'] = 'Invalid subject'
        
        if not file or not file.filename:
            errors['file'] = 'File is required'
        
        if errors:
            for field, error in errors.items():
                flash(error, 'error')
            return render_template('materials/upload.html', subjects=subjects, form_data=request.form), 400
        
        file_data, error = FileService.save_material(file, current_user.id)
        
        if error:
            flash(error, 'error')
            return render_template('materials/upload.html', subjects=subjects, form_data=request.form), 400
        
        material = StudyMaterial(
            title=title,
            description=description,
            filename=file_data['filename'],
            original_filename=file_data['original_filename'],
            file_size=file_data['file_size'],
            mime_type=file_data['mime_type'],
            file_extension=file_data['extension'],
            author_id=current_user.id,
            subject_id=subject_id,
            is_public=is_public
        )
        
        db.session.add(material)
        db.session.commit()
        
        update_user_progress(current_user.id, subject_id, 'material_view')
        
        flash('Material uploaded successfully!', 'success')
        return redirect(url_for('materials.view', material_id=material.id))
    
    return render_template('materials/upload.html', subjects=subjects)

@materials_bp.route('/materials/<int:material_id>')
def view(material_id):
    material = StudyMaterial.query.get_or_404(material_id)
    
    if not material.is_public and material.author_id != current_user.id:
        if not current_user.is_authenticated:
            flash('Please log in to view this material.', 'error')
            return redirect(url_for('auth.login', next=request.url))
        flash('You do not have permission to view this material.', 'error')
        return redirect(url_for('dashboard.index'))
    
    material.views += 1
    
    user_rating = None
    if current_user.is_authenticated:
        user_rating = Rating.query.filter_by(user_id=current_user.id, material_id=material.id).first()
        update_user_progress(current_user.id, material.subject_id, 'material_view')
    
    db.session.commit()
    
    return render_template('materials/view.html', material=material, user_rating=user_rating)

@materials_bp.route('/materials/<int:material_id>/download')
@login_required
def download(material_id):
    material = StudyMaterial.query.get_or_404(material_id)
    
    if not material.is_public and material.author_id != current_user.id:
        flash('You do not have permission to download this material.', 'error')
        return redirect(url_for('dashboard.index'))
    
    file_path = FileService.get_material_path(material.filename, material.author_id)
    
    if not os.path.exists(file_path):
        flash('File not found.', 'error')
        return redirect(url_for('materials.view', material_id=material.id))
    
    material.downloads += 1
    db.session.commit()
    
    return send_file(file_path, as_attachment=True, download_name=material.original_filename)

@materials_bp.route('/materials/<int:material_id>/rate', methods=['POST'])
@login_required
def rate(material_id):
    material = StudyMaterial.query.get_or_404(material_id)
    
    if not material.is_public:
        return jsonify({'success': False, 'error': 'Cannot rate private material'}), 403
    
    score = request.form.get('score', type=int)
    feedback = request.form.get('feedback', '').strip()
    
    if not score or score < 1 or score > 5:
        return jsonify({'success': False, 'error': 'Invalid rating'}), 400
    
    existing_rating = Rating.query.filter_by(user_id=current_user.id, material_id=material_id).first()
    
    if existing_rating:
        existing_rating.score = score
        existing_rating.feedback = feedback
        existing_rating.updated_at = db.func.now()
    else:
        rating = Rating(
            user_id=current_user.id,
            material_id=material_id,
            score=score,
            feedback=feedback
        )
        db.session.add(rating)
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'average_rating': material.average_rating,
        'rating_count': material.rating_count
    })

@materials_bp.route('/materials/<int:material_id>/delete', methods=['POST'])
@login_required
def delete(material_id):
    material = StudyMaterial.query.get_or_404(material_id)
    
    if material.author_id != current_user.id:
        flash('You do not have permission to delete this material.', 'error')
        return redirect(url_for('dashboard.index'))
    
    FileService.delete_material(FileService.get_material_path(material.filename, material.author_id))
    
    db.session.delete(material)
    db.session.commit()
    
    flash('Material deleted successfully.', 'success')
    return redirect(url_for('dashboard.index'))

def update_user_progress(user_id, subject_id, activity_type):
    progress = UserProgress.query.filter_by(user_id=user_id, subject_id=subject_id).first()
    
    if not progress:
        progress = UserProgress(user_id=user_id, subject_id=subject_id)
        db.session.add(progress)
    
    if activity_type == 'material_view':
        progress.materials_viewed += 1
    elif activity_type == 'quiz_attempt':
        progress.quizzes_attempted += 1
    
    progress.last_activity = db.func.now()
    
    update_streak(progress)
    
    db.session.commit()

def update_streak(progress):
    now = db.func.now()
    if progress.last_streak_date:
        last_date = progress.last_streak_date.date()
        today = now.date()
        if last_date == today:
            return
        elif last_date == today - timedelta(days=1):
            progress.streak_days += 1
        else:
            progress.streak_days = 1
    else:
        progress.streak_days = 1
    
    progress.last_streak_date = now