from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
from flask_login import login_required, current_user
from models import db, Quiz, Question, QuizAttempt, Subject, UserProgress
from services.auth_service import AuthService
from sqlalchemy import desc, func
from datetime import datetime
import json
import random

quizzes_bp = Blueprint('quizzes', __name__)

@quizzes_bp.route('/quizzes')
def index():
    page = request.args.get('page', 1, type=int)
    per_page = 12
    subject_id = request.args.get('subject_id', type=int)
    
    query = Quiz.query.filter_by(is_public=True)
    
    if subject_id:
        query = query.filter_by(subject_id=subject_id)
    
    quizzes = query.order_by(desc(Quiz.created_at)).paginate(page=page, per_page=per_page, error_out=False)
    subjects = Subject.query.order_by(Subject.name).all()
    
    return render_template('quizzes/index.html', quizzes=quizzes, subjects=subjects, subject_id=subject_id)

@quizzes_bp.route('/quizzes/create', methods=['GET', 'POST'])
@login_required
def create():
    subjects = Subject.query.order_by(Subject.name).all()
    
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        subject_id = request.form.get('subject_id', type=int)
        time_limit = request.form.get('time_limit', 30, type=int)
        passing_score = request.form.get('passing_score', 60, type=int)
        is_public = request.form.get('is_public') == 'on'
        shuffle_questions = request.form.get('shuffle_questions') == 'on'
        
        errors = {}
        
        if not title:
            errors['title'] = 'Title is required'
        elif len(title) > 200:
            errors['title'] = 'Title must be less than 200 characters'
        
        if not subject_id:
            errors['subject_id'] = 'Subject is required'
        elif not Subject.query.get(subject_id):
            errors['subject_id'] = 'Invalid subject'
        
        if time_limit < 1 or time_limit > 180:
            errors['time_limit'] = 'Time limit must be between 1 and 180 minutes'
        
        if passing_score < 0 or passing_score > 100:
            errors['passing_score'] = 'Passing score must be between 0 and 100'
        
        if errors:
            for field, error in errors.items():
                flash(error, 'error')
            return render_template('quizzes/create.html', subjects=subjects, form_data=request.form), 400
        
        quiz = Quiz(
            title=title,
            description=description,
            subject_id=subject_id,
            creator_id=current_user.id,
            time_limit=time_limit,
            passing_score=passing_score,
            is_public=is_public,
            shuffle_questions=shuffle_questions
        )
        
        db.session.add(quiz)
        db.session.commit()
        
        flash('Quiz created! Now add questions.', 'success')
        return redirect(url_for('quizzes.add_question', quiz_id=quiz.id))
    
    return render_template('quizzes/create.html', subjects=subjects)

@quizzes_bp.route('/quizzes/<int:quiz_id>/add-question', methods=['GET', 'POST'])
@login_required
def add_question(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    
    if quiz.creator_id != current_user.id:
        flash('You do not have permission to edit this quiz.', 'error')
        return redirect(url_for('dashboard.index'))
    
    if request.method == 'POST':
        question_text = request.form.get('question_text', '').strip()
        option_a = request.form.get('option_a', '').strip()
        option_b = request.form.get('option_b', '').strip()
        option_c = request.form.get('option_c', '').strip()
        option_d = request.form.get('option_d', '').strip()
        correct_answer = request.form.get('correct_answer', '').strip().upper()
        explanation = request.form.get('explanation', '').strip()
        
        errors = {}
        
        if not question_text:
            errors['question_text'] = 'Question text is required'
        if not option_a:
            errors['option_a'] = 'Option A is required'
        if not option_b:
            errors['option_b'] = 'Option B is required'
        if not option_c:
            errors['option_c'] = 'Option C is required'
        if not option_d:
            errors['option_d'] = 'Option D is required'
        if correct_answer not in ['A', 'B', 'C', 'D']:
            errors['correct_answer'] = 'Please select a correct answer'
        
        if errors:
            for field, error in errors.items():
                flash(error, 'error')
            return render_template('quizzes/add_question.html', quiz=quiz, form_data=request.form), 400
        
        question_count = Question.query.filter_by(quiz_id=quiz_id).count()
        
        question = Question(
            quiz_id=quiz_id,
            question_text=question_text,
            option_a=option_a,
            option_b=option_b,
            option_c=option_c,
            option_d=option_d,
            correct_answer=correct_answer,
            explanation=explanation,
            order=question_count
        )
        
        db.session.add(question)
        db.session.commit()
        
        flash('Question added!', 'success')
        
        if request.form.get('action') == 'finish':
            return redirect(url_for('quizzes.view', quiz_id=quiz_id))
        
        return redirect(url_for('quizzes.add_question', quiz_id=quiz_id))
    
    return render_template('quizzes/add_question.html', quiz=quiz)

@quizzes_bp.route('/quizzes/<int:quiz_id>')
def view(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    
    if not quiz.is_public and quiz.creator_id != current_user.id:
        if not current_user.is_authenticated:
            flash('Please log in to view this quiz.', 'error')
            return redirect(url_for('auth.login', next=request.url))
        flash('You do not have permission to view this quiz.', 'error')
        return redirect(url_for('dashboard.index'))
    
    questions = Question.query.filter_by(quiz_id=quiz_id).order_by(Question.order).all()
    attempt_count = QuizAttempt.query.filter_by(quiz_id=quiz_id).count()
    
    user_attempts = []
    if current_user.is_authenticated:
        user_attempts = QuizAttempt.query.filter_by(user_id=current_user.id, quiz_id=quiz_id).order_by(desc(QuizAttempt.completed_at)).all()
    
    return render_template('quizzes/view.html', quiz=quiz, questions=questions, 
                           attempt_count=attempt_count, user_attempts=user_attempts)

@quizzes_bp.route('/quizzes/<int:quiz_id>/start')
@login_required
def start(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    
    if not quiz.is_public and quiz.creator_id != current_user.id:
        flash('You do not have permission to take this quiz.', 'error')
        return redirect(url_for('dashboard.index'))
    
    questions = Question.query.filter_by(quiz_id=quiz_id).order_by(Question.order).all()
    
    if not questions:
        flash('This quiz has no questions yet.', 'error')
        return redirect(url_for('quizzes.view', quiz_id=quiz_id))
    
    if quiz.shuffle_questions:
        questions = list(questions)
        random.shuffle(questions)
    
    session['quiz_data'] = {
        'quiz_id': quiz_id,
        'questions': [{'id': q.id, 'question_text': q.question_text, 'option_a': q.option_a, 
                       'option_b': q.option_b, 'option_c': q.option_c, 'option_d': q.option_d} for q in questions],
        'start_time': db.func.now()
    }
    
    return render_template('quizzes/take.html', quiz=quiz, questions=questions)

@quizzes_bp.route('/quizzes/<int:quiz_id>/submit', methods=['POST'])
@login_required
def submit(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    
    if 'quiz_data' not in session or session['quiz_data']['quiz_id'] != quiz_id:
        flash('Quiz session expired. Please start again.', 'error')
        return redirect(url_for('quizzes.view', quiz_id=quiz_id))
    
    quiz_data = session['quiz_data']
    questions_data = quiz_data['questions']
    
    answers = {}
    correct_count = 0
    
    for i, q_data in enumerate(questions_data):
        question_id = q_data['id']
        user_answer = request.form.get(f'question_{question_id}', '').strip().upper()
        answers[str(question_id)] = user_answer
        
        question = Question.query.get(question_id)
        if question and user_answer == question.correct_answer:
            correct_count += 1
    
    total_questions = len(questions_data)
    percentage = round((correct_count / total_questions) * 100, 1) if total_questions > 0 else 0
    
    time_taken = 0
    if 'start_time' in quiz_data:
        time_taken = int((db.func.now() - quiz_data['start_time']).total_seconds())
    
    attempt = QuizAttempt(
        user_id=current_user.id,
        quiz_id=quiz_id,
        score=correct_count,
        total_questions=total_questions,
        correct_answers=correct_count,
        time_taken=time_taken,
        answers=answers
    )
    
    db.session.add(attempt)
    db.session.commit()
    
    progress = UserProgress.query.filter_by(user_id=current_user.id, subject_id=quiz.subject_id).first()
    if not progress:
        progress = UserProgress(user_id=current_user.id, subject_id=quiz.subject_id)
        db.session.add(progress)
    
    progress.quizzes_attempted += 1
    progress.total_score += percentage
    progress.last_activity = db.func.now()
    
    db.session.commit()
    
    session.pop('quiz_data', None)
    
    return redirect(url_for('quizzes.result', attempt_id=attempt.id))

@quizzes_bp.route('/quizzes/attempt/<int:attempt_id>')
@login_required
def result(attempt_id):
    attempt = QuizAttempt.query.get_or_404(attempt_id)
    
    if attempt.user_id != current_user.id:
        flash('You do not have permission to view this result.', 'error')
        return redirect(url_for('dashboard.index'))
    
    quiz = Quiz.query.get(attempt.quiz_id)
    questions = Question.query.filter_by(quiz_id=quiz.id).order_by(Question.order).all()
    
    return render_template('quizzes/result.html', attempt=attempt, quiz=quiz, questions=questions)

@quizzes_bp.route('/quizzes/my-attempts')
@login_required
def my_attempts():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    attempts = QuizAttempt.query.filter_by(user_id=current_user.id).order_by(desc(QuizAttempt.completed_at)).paginate(page=page, per_page=per_page, error_out=False)
    
    return render_template('quizzes/my_attempts.html', attempts=attempts)

@quizzes_bp.route('/quizzes/<int:quiz_id>/delete', methods=['POST'])
@login_required
def delete(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    
    if quiz.creator_id != current_user.id:
        flash('You do not have permission to delete this quiz.', 'error')
        return redirect(url_for('dashboard.index'))
    
    db.session.delete(quiz)
    db.session.commit()
    
    flash('Quiz deleted successfully.', 'success')
    return redirect(url_for('quizzes.index'))