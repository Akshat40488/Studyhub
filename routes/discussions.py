from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models import db, Discussion, Comment, Subject, Notification
from services.auth_service import AuthService
from sqlalchemy import desc, func

discussions_bp = Blueprint('discussions', __name__)

@discussions_bp.route('/discussions')
def index():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    subject_id = request.args.get('subject_id', type=int)
    sort = request.args.get('sort', 'recent')
    search = request.args.get('search', '').strip()
    
    query = Discussion.query
    
    if subject_id:
        query = query.filter_by(subject_id=subject_id)
    
    if search:
        query = query.filter(Discussion.title.ilike(f'%{search}%') | Discussion.content.ilike(f'%{search}%'))
    
    if sort == 'popular':
        query = query.outerjoin(Comment).group_by(Discussion.id).order_by(desc(func.count(Comment.id)))
    else:
        query = query.order_by(desc(Discussion.created_at))
    
    discussions = query.paginate(page=page, per_page=per_page, error_out=False)
    subjects = Subject.query.order_by(Subject.name).all()
    
    return render_template('discussions/index.html', discussions=discussions, subjects=subjects,
                           subject_id=subject_id, sort=sort, search=search)

@discussions_bp.route('/discussions/create', methods=['GET', 'POST'])
@login_required
def create():
    subjects = Subject.query.order_by(Subject.name).all()
    
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()
        subject_id = request.form.get('subject_id', type=int)
        
        errors = {}
        
        if not title:
            errors['title'] = 'Title is required'
        elif len(title) > 200:
            errors['title'] = 'Title must be less than 200 characters'
        
        if not content:
            errors['content'] = 'Content is required'
        elif len(content) < 20:
            errors['content'] = 'Content must be at least 20 characters'
        
        if not subject_id:
            errors['subject_id'] = 'Subject is required'
        elif not Subject.query.get(subject_id):
            errors['subject_id'] = 'Invalid subject'
        
        if errors:
            for field, error in errors.items():
                flash(error, 'error')
            return render_template('discussions/create.html', subjects=subjects, form_data=request.form), 400
        
        discussion = Discussion(
            title=title,
            content=content,
            author_id=current_user.id,
            subject_id=subject_id
        )
        
        db.session.add(discussion)
        db.session.commit()
        
        flash('Discussion created successfully!', 'success')
        return redirect(url_for('discussions.view', discussion_id=discussion.id))
    
    return render_template('discussions/create.html', subjects=subjects)

@discussions_bp.route('/discussions/<int:discussion_id>')
def view(discussion_id):
    discussion = Discussion.query.get_or_404(discussion_id)
    
    discussion.views += 1
    db.session.commit()
    
    comments = Comment.query.filter_by(discussion_id=discussion_id, parent_id=None).order_by(Comment.created_at).all()
    
    return render_template('discussions/view.html', discussion=discussion, comments=comments)

@discussions_bp.route('/discussions/<int:discussion_id>/comment', methods=['POST'])
@login_required
def comment(discussion_id):
    discussion = Discussion.query.get_or_404(discussion_id)
    
    if discussion.is_locked:
        flash('This discussion is locked.', 'error')
        return redirect(url_for('discussions.view', discussion_id=discussion_id))
    
    content = request.form.get('content', '').strip()
    parent_id = request.form.get('parent_id', type=int)
    
    if not content:
        flash('Comment cannot be empty.', 'error')
        return redirect(url_for('discussions.view', discussion_id=discussion_id))
    
    if len(content) < 3:
        flash('Comment must be at least 3 characters.', 'error')
        return redirect(url_for('discussions.view', discussion_id=discussion_id))
    
    comment = Comment(
        content=content,
        author_id=current_user.id,
        discussion_id=discussion_id,
        parent_id=parent_id
    )
    
    db.session.add(comment)
    db.session.commit()
    
    if parent_id:
        parent_comment = Comment.query.get(parent_id)
        if parent_comment and parent_comment.author_id != current_user.id:
            AuthService.create_notification(
                parent_comment.author_id,
                'reply',
                'New reply to your comment',
                f'{current_user.name} replied to your comment in "{discussion.title}"',
                discussion_id,
                'discussion'
            )
    elif discussion.author_id != current_user.id:
        AuthService.create_notification(
            discussion.author_id,
            'comment',
            'New comment on your discussion',
            f'{current_user.name} commented on your discussion: {discussion.title}',
            discussion_id,
            'discussion'
        )
    
    flash('Comment posted!', 'success')
    return redirect(url_for('discussions.view', discussion_id=discussion_id))

@discussions_bp.route('/discussions/<int:discussion_id>/delete', methods=['POST'])
@login_required
def delete(discussion_id):
    discussion = Discussion.query.get_or_404(discussion_id)
    
    if discussion.author_id != current_user.id:
        flash('You do not have permission to delete this discussion.', 'error')
        return redirect(url_for('dashboard.index'))
    
    db.session.delete(discussion)
    db.session.commit()
    
    flash('Discussion deleted successfully.', 'success')
    return redirect(url_for('discussions.index'))

@discussions_bp.route('/discussions/my-discussions')
@login_required
def my_discussions():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    discussions = Discussion.query.filter_by(author_id=current_user.id).order_by(desc(Discussion.created_at)).paginate(page=page, per_page=per_page, error_out=False)
    
    return render_template('discussions/my_discussions.html', discussions=discussions)