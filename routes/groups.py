from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models import db, StudyGroup, GroupMember, GroupMaterial, GroupDiscussion, GroupDiscussionComment, StudyMaterial, Subject, Notification
from services.auth_service import AuthService
from sqlalchemy import desc, func

groups_bp = Blueprint('groups', __name__)

@groups_bp.route('/groups')
def index():
    page = request.args.get('page', 1, type=int)
    per_page = 12
    subject_id = request.args.get('subject_id', type=int)
    search = request.args.get('search', '').strip()
    
    query = StudyGroup.query
    
    if subject_id:
        query = query.filter_by(subject_id=subject_id)
    
    if search:
        query = query.filter(StudyGroup.name.ilike(f'%{search}%') | StudyGroup.description.ilike(f'%{search}%'))
    
    if current_user.is_authenticated:
        user_group_ids = [gm.group_id for gm in GroupMember.query.filter_by(user_id=current_user.id).all()]
        query = query.filter(~StudyGroup.id.in_(user_group_ids)) if user_group_ids else query
    
    groups = query.order_by(desc(StudyGroup.created_at)).paginate(page=page, per_page=per_page, error_out=False)
    subjects = Subject.query.order_by(Subject.name).all()
    
    return render_template('groups/index.html', groups=groups, subjects=subjects, 
                           subject_id=subject_id, search=search)

@groups_bp.route('/groups/create', methods=['GET', 'POST'])
@login_required
def create():
    subjects = Subject.query.order_by(Subject.name).all()
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        subject_id = request.form.get('subject_id', type=int)
        is_private = request.form.get('is_private') == 'on'
        max_members = request.form.get('max_members', 50, type=int)
        
        errors = {}
        
        if not name:
            errors['name'] = 'Group name is required'
        elif len(name) > 100:
            errors['name'] = 'Group name must be less than 100 characters'
        
        if not subject_id:
            errors['subject_id'] = 'Subject is required'
        elif not Subject.query.get(subject_id):
            errors['subject_id'] = 'Invalid subject'
        
        if max_members < 2 or max_members > 200:
            errors['max_members'] = 'Max members must be between 2 and 200'
        
        if errors:
            for field, error in errors.items():
                flash(error, 'error')
            return render_template('groups/create.html', subjects=subjects, form_data=request.form), 400
        
        group = StudyGroup(
            name=name,
            description=description,
            subject_id=subject_id,
            creator_id=current_user.id,
            is_private=is_private,
            max_members=max_members
        )
        
        db.session.add(group)
        db.session.flush()
        
        membership = GroupMember(
            user_id=current_user.id,
            group_id=group.id,
            role='admin'
        )
        
        db.session.add(membership)
        db.session.commit()
        
        flash('Study group created successfully!', 'success')
        return redirect(url_for('groups.view', group_id=group.id))
    
    return render_template('groups/create.html', subjects=subjects)

@groups_bp.route('/groups/<int:group_id>')
def view(group_id):
    group = StudyGroup.query.get_or_404(group_id)
    
    is_member = False
    membership = None
    if current_user.is_authenticated:
        membership = GroupMember.query.filter_by(user_id=current_user.id, group_id=group_id).first()
        is_member = membership is not None
    
    if group.is_private and not is_member:
        flash('This is a private group. You need to join to view its content.', 'info')
        return render_template('groups/view.html', group=group, is_member=False)
    
    members = GroupMember.query.filter_by(group_id=group_id).order_by(GroupMember.joined_at).limit(20).all()
    materials = GroupMaterial.query.filter_by(group_id=group_id).order_by(desc(GroupMaterial.shared_at)).limit(10).all()
    discussions = GroupDiscussion.query.filter_by(group_id=group_id).order_by(desc(GroupDiscussion.created_at)).limit(10).all()
    
    return render_template('groups/view.html', 
                           group=group, 
                           is_member=is_member, 
                           membership=membership,
                           members=members,
                           materials=materials,
                           discussions=discussions)

@groups_bp.route('/groups/<int:group_id>/join', methods=['POST'])
@login_required
def join(group_id):
    group = StudyGroup.query.get_or_404(group_id)
    
    existing = GroupMember.query.filter_by(user_id=current_user.id, group_id=group_id).first()
    if existing:
        flash('You are already a member of this group.', 'info')
        return redirect(url_for('groups.view', group_id=group_id))
    
    member_count = GroupMember.query.filter_by(group_id=group_id).count()
    if member_count >= group.max_members:
        flash('This group has reached its maximum member limit.', 'error')
        return redirect(url_for('groups.view', group_id=group_id))
    
    membership = GroupMember(
        user_id=current_user.id,
        group_id=group_id,
        role='member'
    )
    
    db.session.add(membership)
    db.session.commit()
    
    AuthService.create_notification(
        group.creator_id,
        'group_join',
        'New member joined your group',
        f'{current_user.name} joined {group.name}',
        group_id,
        'group'
    )
    
    flash('You have joined the group!', 'success')
    return redirect(url_for('groups.view', group_id=group_id))

@groups_bp.route('/groups/<int:group_id>/leave', methods=['POST'])
@login_required
def leave(group_id):
    group = StudyGroup.query.get_or_404(group_id)
    
    membership = GroupMember.query.filter_by(user_id=current_user.id, group_id=group_id).first()
    if not membership:
        flash('You are not a member of this group.', 'error')
        return redirect(url_for('groups.view', group_id=group_id))
    
    if membership.role == 'admin' and group.creator_id == current_user.id:
        flash('Group creator cannot leave. Transfer ownership or delete the group.', 'error')
        return redirect(url_for('groups.view', group_id=group_id))
    
    db.session.delete(membership)
    db.session.commit()
    
    flash('You have left the group.', 'success')
    return redirect(url_for('groups.view', group_id=group_id))

@groups_bp.route('/groups/<int:group_id>/share-material', methods=['POST'])
@login_required
def share_material(group_id):
    group = StudyGroup.query.get_or_404(group_id)
    
    membership = GroupMember.query.filter_by(user_id=current_user.id, group_id=group_id).first()
    if not membership:
        flash('You must be a member to share materials.', 'error')
        return redirect(url_for('groups.view', group_id=group_id))
    
    material_id = request.form.get('material_id', type=int)
    material = StudyMaterial.query.get_or_404(material_id)
    
    if material.author_id != current_user.id:
        flash('You can only share your own materials.', 'error')
        return redirect(url_for('groups.view', group_id=group_id))
    
    existing = GroupMaterial.query.filter_by(group_id=group_id, material_id=material_id).first()
    if existing:
        flash('This material is already shared in this group.', 'info')
        return redirect(url_for('groups.view', group_id=group_id))
    
    group_material = GroupMaterial(
        group_id=group_id,
        material_id=material_id,
        shared_by_id=current_user.id
    )
    
    db.session.add(group_material)
    db.session.commit()
    
    flash('Material shared with the group!', 'success')
    return redirect(url_for('groups.view', group_id=group_id))

@groups_bp.route('/groups/<int:group_id>/create-discussion', methods=['POST'])
@login_required
def create_discussion(group_id):
    group = StudyGroup.query.get_or_404(group_id)
    
    membership = GroupMember.query.filter_by(user_id=current_user.id, group_id=group_id).first()
    if not membership:
        flash('You must be a member to create discussions.', 'error')
        return redirect(url_for('groups.view', group_id=group_id))
    
    title = request.form.get('title', '').strip()
    content = request.form.get('content', '').strip()
    
    if not title or not content:
        flash('Title and content are required.', 'error')
        return redirect(url_for('groups.view', group_id=group_id))
    
    discussion = GroupDiscussion(
        title=title,
        content=content,
        group_id=group_id,
        author_id=current_user.id
    )
    
    db.session.add(discussion)
    db.session.commit()
    
    flash('Discussion created!', 'success')
    return redirect(url_for('groups.view', group_id=group_id))

@groups_bp.route('/groups/<int:group_id>/discussion/<int:discussion_id>/comment', methods=['POST'])
@login_required
def comment_discussion(group_id, discussion_id):
    group = StudyGroup.query.get_or_404(group_id)
    discussion = GroupDiscussion.query.get_or_404(discussion_id)
    
    membership = GroupMember.query.filter_by(user_id=current_user.id, group_id=group_id).first()
    if not membership:
        return jsonify({'success': False, 'error': 'Not a member'}), 403
    
    content = request.form.get('content', '').strip()
    parent_id = request.form.get('parent_id', type=int)
    
    if not content:
        return jsonify({'success': False, 'error': 'Comment cannot be empty'}), 400
    
    comment = GroupDiscussionComment(
        content=content,
        discussion_id=discussion_id,
        author_id=current_user.id,
        parent_id=parent_id
    )
    
    db.session.add(comment)
    db.session.commit()
    
    return jsonify({'success': True})

@groups_bp.route('/groups/my-groups')
@login_required
def my_groups():
    memberships = GroupMember.query.filter_by(user_id=current_user.id).join(StudyGroup).order_by(desc(StudyGroup.created_at)).all()
    
    return render_template('groups/my_groups.html', memberships=memberships)

@groups_bp.route('/groups/<int:group_id>/delete', methods=['POST'])
@login_required
def delete(group_id):
    group = StudyGroup.query.get_or_404(group_id)
    
    if group.creator_id != current_user.id:
        flash('Only the group creator can delete the group.', 'error')
        return redirect(url_for('groups.view', group_id=group_id))
    
    db.session.delete(group)
    db.session.commit()
    
    flash('Group deleted successfully.', 'success')
    return redirect(url_for('groups.index'))