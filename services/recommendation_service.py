import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.decomposition import TruncatedSVD
from models import db, User, StudyMaterial, Subject, Quiz, QuizAttempt, UserProgress, Rating, Question
from datetime import datetime, timedelta
import json

class RecommendationService:
    def __init__(self):
        self.material_vectorizer = TfidfVectorizer(max_features=1000, stop_words='english', ngram_range=(1, 2))
        self.quiz_vectorizer = TfidfVectorizer(max_features=500, stop_words='english', ngram_range=(1, 2))
        self.user_item_matrix = None
        self.material_similarity = None
        self.quiz_similarity = None
        self.material_features = None
        self.quiz_features = None
        self.last_trained = None
    
    def get_user_activity(self, user_id):
        materials_viewed = db.session.query(StudyMaterial.id).join(Rating, Rating.material_id == StudyMaterial.id).filter(Rating.user_id == user_id).all()
        materials_viewed = [m[0] for m in materials_viewed]
        
        quiz_attempts = QuizAttempt.query.filter_by(user_id=user_id).all()
        quiz_ids = [qa.quiz_id for qa in quiz_attempts]
        
        progress = UserProgress.query.filter_by(user_id=user_id).all()
        subject_scores = {p.subject_id: p.average_score for p in progress}
        
        return {
            'materials_viewed': materials_viewed,
            'quiz_attempts': quiz_ids,
            'subject_scores': subject_scores
        }
    
    def get_material_features(self):
        materials = StudyMaterial.query.filter_by(is_public=True).all()
        if not materials:
            return None, None
        
        texts = []
        material_ids = []
        for m in materials:
            text = f"{m.title} {m.description or ''} {m.subject.name}"
            texts.append(text)
            material_ids.append(m.id)
        
        features = self.material_vectorizer.fit_transform(texts)
        return features, material_ids
    
    def get_quiz_features(self):
        quizzes = Quiz.query.filter_by(is_public=True).all()
        if not quizzes:
            return None, None
        
        texts = []
        quiz_ids = []
        for q in quizzes:
            questions = Question.query.filter_by(quiz_id=q.id).all()
            question_text = ' '.join([q.question_text for q in questions])
            text = f"{q.title} {q.description or ''} {q.subject.name} {question_text}"
            texts.append(text)
            quiz_ids.append(q.id)
        
        features = self.quiz_vectorizer.fit_transform(texts)
        return features, quiz_ids
    
    def train(self):
        self.material_features, self.material_ids = self.get_material_features()
        self.quiz_features, self.quiz_ids = self.get_quiz_features()
        
        if self.material_features is not None and self.material_features.shape[0] > 1:
            self.material_similarity = cosine_similarity(self.material_features)
        
        if self.quiz_features is not None and self.quiz_features.shape[0] > 1:
            self.quiz_similarity = cosine_similarity(self.quiz_features)
        
        self.last_trained = datetime.utcnow()
    
    def get_content_based_material_recommendations(self, user_id, limit=5):
        if self.material_features is None:
            self.train()
        
        if self.material_features is None or self.material_similarity is None:
            return self.get_popular_materials(limit)
        
        activity = self.get_user_activity(user_id)
        viewed_materials = activity['materials_viewed']
        
        if not viewed_materials:
            return self.get_popular_materials(limit)
        
        viewed_indices = [i for i, mid in enumerate(self.material_ids) if mid in viewed_materials]
        if not viewed_indices:
            return self.get_popular_materials(limit)
        
        user_profile = np.mean(self.material_similarity[viewed_indices], axis=0)
        scores = user_profile.flatten()
        
        viewed_set = set(viewed_indices)
        scored_indices = [(i, scores[i]) for i in range(len(scores)) if i not in viewed_set]
        scored_indices.sort(key=lambda x: x[1], reverse=True)
        
        recommended_ids = [self.material_ids[i] for i, _ in scored_indices[:limit]]
        return StudyMaterial.query.filter(StudyMaterial.id.in_(recommended_ids)).all()
    
    def get_content_based_quiz_recommendations(self, user_id, limit=5):
        if self.quiz_features is None:
            self.train()
        
        if self.quiz_features is None or self.quiz_similarity is None:
            return self.get_popular_quizzes(limit)
        
        activity = self.get_user_activity(user_id)
        attempted_quizzes = activity['quiz_attempts']
        
        if not attempted_quizzes:
            return self.get_popular_quizzes(limit)
        
        attempted_indices = [i for i, qid in enumerate(self.quiz_ids) if qid in attempted_quizzes]
        if not attempted_indices:
            return self.get_popular_quizzes(limit)
        
        user_profile = np.mean(self.quiz_similarity[attempted_indices], axis=0)
        scores = user_profile.flatten()
        
        attempted_set = set(attempted_indices)
        scored_indices = [(i, scores[i]) for i in range(len(scores)) if i not in attempted_set]
        scored_indices.sort(key=lambda x: x[1], reverse=True)
        
        recommended_ids = [self.quiz_ids[i] for i, _ in scored_indices[:limit]]
        return Quiz.query.filter(Quiz.id.in_(recommended_ids)).all()
    
    def get_collaborative_recommendations(self, user_id, limit=5):
        activity = self.get_user_activity(user_id)
        
        if not activity['quiz_attempts'] and not activity['materials_viewed']:
            return self.get_popular_materials(limit)
        
        all_users = User.query.filter(User.id != user_id).all()
        if not all_users:
            return self.get_popular_materials(limit)
        
        user_similarities = []
        for other_user in all_users:
            other_activity = self.get_user_activity(other_user.id)
            
            common_quizzes = set(activity['quiz_attempts']) & set(other_activity['quiz_attempts'])
            common_materials = set(activity['materials_viewed']) & set(other_activity['materials_viewed'])
            
            if common_quizzes or common_materials:
                similarity = len(common_quizzes) * 2 + len(common_materials)
                user_similarities.append((other_user.id, similarity))
        
        if not user_similarities:
            return self.get_popular_materials(limit)
        
        user_similarities.sort(key=lambda x: x[1], reverse=True)
        top_users = [uid for uid, _ in user_similarities[:10]]
        
        recommended_materials = set()
        for uid in top_users:
            other_activity = self.get_user_activity(uid)
            for mid in other_activity['materials_viewed']:
                if mid not in activity['materials_viewed']:
                    recommended_materials.add(mid)
            if len(recommended_materials) >= limit:
                break
        
        return StudyMaterial.query.filter(StudyMaterial.id.in_(list(recommended_materials)[:limit])).all()
    
    def get_weak_subject_recommendations(self, user_id, limit=3):
        progress = UserProgress.query.filter_by(user_id=user_id).all()
        if not progress:
            subjects = Subject.query.order_by(Subject.name).limit(limit).all()
            return [{'subject': s, 'reason': 'Start learning'} for s in subjects]
        
        weak_subjects = sorted(progress, key=lambda p: p.average_score)[:limit]
        recommendations = []
        for p in weak_subjects:
            if p.average_score < 70:
                subject = Subject.query.get(p.subject_id)
                if subject:
                    recommendations.append({
                        'subject': subject,
                        'reason': f'Current average: {p.average_score}% - Needs improvement'
                    })
        
        if not recommendations:
            strong_subjects = sorted(progress, key=lambda p: p.average_score, reverse=True)[:limit]
            for p in strong_subjects:
                subject = Subject.query.get(p.subject_id)
                if subject:
                    recommendations.append({
                        'subject': subject,
                        'reason': f'Strong subject (avg: {p.average_score}%) - Continue mastering'
                    })
        
        return recommendations
    
    def get_popular_materials(self, limit=5):
        return StudyMaterial.query.filter_by(is_public=True).order_by(StudyMaterial.views.desc(), StudyMaterial.downloads.desc()).limit(limit).all()
    
    def get_popular_quizzes(self, limit=5):
        return Quiz.query.filter_by(is_public=True).order_by(Quiz.created_at.desc()).limit(limit).all()
    
    def get_recommendations_for_user(self, user_id, limit=5):
        if self.last_trained is None or (datetime.utcnow() - self.last_trained).days >= 1:
            self.train()
        
        activity = self.get_user_activity(user_id)
        
        if not activity['materials_viewed'] and not activity['quiz_attempts']:
            return {
                'materials': self.get_popular_materials(limit),
                'quizzes': self.get_popular_quizzes(limit),
                'subjects': self.get_weak_subject_recommendations(user_id, 3)
            }
        
        content_materials = self.get_content_based_material_recommendations(user_id, limit)
        collab_materials = self.get_collaborative_recommendations(user_id, limit)
        
        all_material_ids = set()
        combined_materials = []
        for m in content_materials + collab_materials:
            if m.id not in all_material_ids:
                combined_materials.append(m)
                all_material_ids.add(m.id)
            if len(combined_materials) >= limit:
                break
        
        return {
            'materials': combined_materials[:limit],
            'quizzes': self.get_content_based_quiz_recommendations(user_id, limit),
            'subjects': self.get_weak_subject_recommendations(user_id, 3)
        }

recommendation_service = RecommendationService()