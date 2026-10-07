from models import db
from models import User, Subject, StudyMaterial, Doubt, Answer, Discussion, Comment
from models import StudyGroup, GroupMember, GroupMaterial, GroupDiscussion, GroupDiscussionComment
from models import Quiz, Question, QuizAttempt, Rating, UserProgress, Notification

def init_db(app):
    db.init_app(app)
    with app.app_context():
        db.create_all()
        seed_initial_data()

def seed_initial_data():
    if Subject.query.count() == 0:
        subjects = [
            Subject(name='Computer Science', slug='computer-science', description='Programming, algorithms, data structures, and software engineering', icon='code', color='#3B82F6'),
            Subject(name='Mathematics', slug='mathematics', description='Calculus, algebra, statistics, and discrete mathematics', icon='calculator', color='#10B981'),
            Subject(name='Physics', slug='physics', description='Mechanics, electromagnetism, thermodynamics, and quantum physics', icon='atom', color='#F59E0B'),
            Subject(name='Networking', slug='networking', description='Computer networks, protocols, and network security', icon='globe', color='#EF4444'),
            Subject(name='Cybersecurity', slug='cybersecurity', description='Information security, ethical hacking, and cryptography', icon='shield', color='#8B5CF6'),
            Subject(name='Data Science', slug='data-science', description='Machine learning, data analysis, and statistical modeling', icon='bar-chart', color='#EC4899'),
            Subject(name='Web Development', slug='web-development', description='Frontend, backend, and full-stack web development', icon='layout', color='#06B6D4'),
            Subject(name='Mobile Development', slug='mobile-development', description='iOS, Android, and cross-platform mobile app development', icon='smartphone', color='#84CC16'),
        ]
        for subject in subjects:
            db.session.add(subject)
        db.session.commit()
        print("Initial subjects seeded.")