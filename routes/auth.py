from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from models import db, User
from services.auth_service import AuthService
from services.file_service import FileService

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    
    if request.method == 'POST':
        data = {
            'name': request.form.get('name', ''),
            'email': request.form.get('email', ''),
            'password': request.form.get('password', ''),
            'confirm_password': request.form.get('confirm_password', '')
        }
        
        user, errors = AuthService.register_user(data)
        
        if errors:
            for field, error in errors.items():
                flash(error, 'error')
            return render_template('auth/register.html', form_data=data), 400
        
        flash('Registration successful! Welcome to StudyHub.', 'success')
        login_user(user)
        return redirect(url_for('dashboard.index'))
    
    return render_template('auth/register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    
    if request.method == 'POST':
        data = {
            'email': request.form.get('email', ''),
            'password': request.form.get('password', '')
        }
        
        remember = request.form.get('remember') == 'on'
        
        errors = AuthService.validate_login(data)
        if errors:
            for field, error in errors.items():
                flash(error, 'error')
            return render_template('auth/login.html', form_data=data), 400
        
        user, error = AuthService.login_user(data['email'], data['password'], remember)
        
        if error:
            flash(error, 'error')
            return render_template('auth/login.html', form_data=data), 401
        
        login_user(user, remember=remember)
        flash(f'Welcome back, {user.name}!', 'success')
        
        next_page = request.args.get('next')
        return redirect(next_page or url_for('dashboard.index'))
    
    return render_template('auth/login.html')

@auth_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        if 'avatar' in request.files:
            file = request.files['avatar']
            if file and file.filename:
                filename, error = FileService.save_avatar(file, current_user.id)
                if error:
                    flash(error, 'error')
                else:
                    current_user.avatar = filename
                    db.session.commit()
                    flash('Profile picture updated!', 'success')
            return redirect(url_for('auth.profile'))
        
        data = {
            'name': request.form.get('name', ''),
            'email': request.form.get('email', ''),
            'bio': request.form.get('bio', '')
        }
        
        success, errors = AuthService.update_profile(current_user, data)
        
        if errors:
            for field, error in errors.items():
                flash(error, 'error')
        else:
            flash('Profile updated successfully!', 'success')
        
        return redirect(url_for('auth.profile'))
    
    return render_template('auth/profile.html')

@auth_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        data = {
            'current_password': request.form.get('current_password', ''),
            'new_password': request.form.get('new_password', ''),
            'confirm_password': request.form.get('confirm_password', '')
        }
        
        success, errors = AuthService.change_password(current_user, data)
        
        if errors:
            for field, error in errors.items():
                flash(error, 'error')
        else:
            flash('Password changed successfully!', 'success')
        
        return redirect(url_for('auth.change_password'))
    
    return render_template('auth/change_password.html')