from flask import Flask
from flask_login import LoginManager
from extensions import db
import os, json

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'stanlib-addie-secret-key-2026')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///addie_v4.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

    db.init_app(app)
    login_manager = LoginManager(app)
    login_manager.login_view = 'login'

    from models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    with app.app_context():
        db.create_all()
        # If no users exist yet (fresh PostgreSQL DB), import from JSON backup
        if not User.query.first():
            data_file = os.path.join(os.path.dirname(__file__), 'export', 'app_data.json')
            if os.path.exists(data_file):
                print(f"Importing data from {data_file}...")
                try:
                    with open(data_file) as f:
                        data = json.load(f)
                    from models import Request, Phase, Approval, KirkpatrickResult, InterviewGuide, ContentTag
                    from models import LearningStatistic, LearningUploadBatch, Cohort, AuditLog
                    from models import TrainingEvent, PhaseActivity, LNACycle
                    user_map = {}
                    for u_data in data.get('user', []):
                        u = User(email=u_data['email'], name=u_data.get('name',''), role=u_data.get('role','learning_expert'), title=u_data.get('title',''))
                        u.password_hash = u_data['password_hash']
                        db.session.add(u)
                        db.session.flush()
                        user_map[u_data['id']] = u.id
                    for r in data.get('request', []):
                        db.session.add(Request(
                            id=r['id'], title=r['title'], description=r.get('description',''),
                            priority=r.get('priority','Medium'), status=r.get('status','New'),
                            current_phase=r.get('current_phase','inbox'),
                            request_type=r.get('request_type','planned'),
                            requester_name=r.get('requester_name',''),
                            requester_department=r.get('requester_department',''),
                            business_need=r.get('business_need',''), expected_outcome=r.get('expected_outcome',''),
                            target_audience=r.get('target_audience',''), estimated_learners=r.get('estimated_learners',0),
                            deadline=r.get('deadline',None), created_at=r.get('created_at',None),
                            updated_at=r.get('updated_at',None),
                            assigned_to_id=user_map.get(r.get('assigned_to_id')),
                            escalation_level=r.get('escalation_level',0), escalation_note=r.get('escalation_note',''),
                            is_adhoc=r.get('is_adhoc',False), projected_roi=r.get('projected_roi'),
                            actual_roi=r.get('actual_roi'), allocated_cost=r.get('allocated_cost'),
                            review_status=r.get('review_status','Accepted'), review_comment=r.get('review_comment','')
                        ))
                    for p in data.get('phase', []):
                        db.session.add(Phase(
                            id=p['id'], request_id=p['request_id'], phase_name=p['phase_name'],
                            status=p.get('status','Not Started'), data=p.get('data','{}'),
                            started_at=p.get('started_at'), completed_at=p.get('completed_at'),
                            updated_at=p.get('updated_at')
                        ))
                    # Import child tables
                    for t, model_cls in [
                        ('approval', Approval), ('kirkpatrick_result', KirkpatrickResult),
                        ('interview_guide', InterviewGuide), ('content_tag', ContentTag),
                        ('learning_statistic', LearningStatistic), ('learning_upload_batch', LearningUploadBatch),
                        ('cohort', Cohort), ('audit_log', AuditLog), ('training_event', TrainingEvent),
                        ('phase_activity', PhaseActivity), ('lna_cycle', LNACycle)
                    ]:
                        for row in data.get(t, []):
                            inst = model_cls(**{k: v for k, v in row.items() if k != 'id'})
                            inst.id = row['id']
                            db.session.add(inst)
                    db.session.commit()
                    print(f"Migration complete: {len(data.get('request',[]))} requests, {len(data.get('user',[]))} users, {len(data.get('learning_statistic',[]))} learning records")
                except Exception as e:
                    db.session.rollback()
                    print(f"Migration error: {e}")
                    # Still create default users
                    _create_default_users(User, db)
            else:
                _create_default_users(User, db)

    from routes import register_routes
    register_routes(app, db)

    return app

def _create_default_users(User, db):
    if not User.query.filter_by(email='admin@addie.app').first():
        for u in [
            User(email='admin@addie.app', name='Grover Abrahams', role='learning_expert', title='Learning Strategy Lead'),
            User(email='maureen.andrews@stanlib.com', name='Maureen Andrews', role='manager', title='Systems Learning Manager'),
            User(email='hlengiwe.vilakazi@stanlib.com', name='Hlengiwe Vilakazi', role='learning_expert', title='Learning Specialist'),
            User(email='moeketsi.makhalemele@stanlib.com', name='Moeketsi Makhalemele', role='manager', title='Head of Learning'),
        ]:
            u.set_password({'admin@addie.app':'admin123','maureen.andrews@stanlib.com':'manager123','hlengiwe.vilakazi@stanlib.com':'expert123','moeketsi.makhalemele@stanlib.com':'moeketsi123'}[u.email])
            db.session.add(u)
        db.session.commit()
        print("Default users created")

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5000)
