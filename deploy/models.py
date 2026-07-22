from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from extensions import db
from datetime import datetime, date
import json

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    name = db.Column(db.String(120), nullable=False)
    password_hash = db.Column(db.String(256))
    role = db.Column(db.String(20), nullable=False)
    title = db.Column(db.String(120))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    def set_password(self, password): self.password_hash = generate_password_hash(password)
    def check_password(self, password): return check_password_hash(self.password_hash, password)
    def is_learning_expert(self): return self.role == 'learning_expert'
    def is_manager(self): return self.role == 'manager'

class Request(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    priority = db.Column(db.String(20), default='Medium')
    status = db.Column(db.String(30), default='New')
    current_phase = db.Column(db.String(20), default='inbox')
    request_type = db.Column(db.String(20), default='planned')
    lna_cycle_id = db.Column(db.Integer, db.ForeignKey('lna_cycle.id'), nullable=True)
    requester_name = db.Column(db.String(120))
    requester_department = db.Column(db.String(120))
    business_need = db.Column(db.Text)
    expected_outcome = db.Column(db.Text)
    target_audience = db.Column(db.String(200))
    estimated_learners = db.Column(db.Integer)
    deadline = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    assigned_to_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    assigned_to = db.relationship('User', backref='assigned_requests')
    escalation_level = db.Column(db.Integer, default=0)
    escalation_note = db.Column(db.Text)
    is_adhoc = db.Column(db.Boolean, default=False)
    review_status = db.Column(db.String(20), default='Pending')
    review_comment = db.Column(db.Text)
    projected_roi = db.Column(db.Float)
    actual_roi = db.Column(db.Float)
    allocated_cost = db.Column(db.Float, default=0)
    phases = db.relationship('Phase', backref='request', lazy='dynamic', cascade='all, delete-orphan')
    approvals = db.relationship('Approval', backref='request', lazy='dynamic', cascade='all, delete-orphan')
    learning_stats = db.relationship('LearningStatistic', backref='request', lazy='dynamic', cascade='all,delete-orphan')
    upload_batches = db.relationship('LearningUploadBatch', backref='request', lazy='dynamic', cascade='all,delete-orphan')

    def phase_status(self, phase_name):
        phase = Phase.query.filter_by(request_id=self.id, phase_name=phase_name).first()
        return phase.status if phase else 'Not Started'
    def phase_data(self, phase_name):
        phase = Phase.query.filter_by(request_id=self.id, phase_name=phase_name).first()
        return json.loads(phase.data) if phase and phase.data else {}
    def priority_score(self):
        scores = {'Critical': 5, 'High': 4, 'Medium': 3, 'Low': 2, 'Backlog': 1}
        return scores.get(self.priority, 0)
    def days_in_phase(self):
        phase = Phase.query.filter_by(request_id=self.id, status='In Progress').first()
        if phase and phase.started_at: return (datetime.utcnow() - phase.started_at).days
        return 0
    def blockers(self):
        phases = Phase.query.filter_by(request_id=self.id).all()
        blockers = []
        for p in phases:
            data = json.loads(p.data) if p.data else {}
            if data.get('blocker'): blockers.append({'phase': p.phase_name, 'blocker': data['blocker'], 'date': p.updated_at})
        return blockers
    def avg_completion_pct(self):
        stats = self.learning_stats.all()
        if not stats: return 0
        return round(sum(s.completion_pct or 0 for s in stats) / len(stats), 1)
    def avg_score(self):
        stats = self.learning_stats.all()
        scores = [s.score for s in stats if s.score is not None]
        if not scores: return 0
        return round(sum(scores) / len(scores), 1)
    def pass_rate(self):
        stats = self.learning_stats.all()
        if not stats: return 0
        passed = sum(1 for s in stats if s.passed)
        return round(passed / len(stats) * 100, 1)

class Phase(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, db.ForeignKey('request.id'), nullable=False)
    phase_name = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(20), default='Not Started')
    data = db.Column(db.Text)
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Approval(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, db.ForeignKey('request.id'), nullable=False)
    phase_name = db.Column(db.String(20), nullable=False)
    approver_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    approver = db.relationship('User', backref='approvals')
    approver_name = db.Column(db.String(200))
    status = db.Column(db.String(20), default='Not Started')
    comments = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    decided_at = db.Column(db.DateTime)

class KirkpatrickResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, db.ForeignKey('request.id'), nullable=False)
    request = db.relationship('Request', backref='kirkpatrick_results')
    level = db.Column(db.Integer, nullable=False)
    metric_name = db.Column(db.String(200))
    metric_value = db.Column(db.Float)
    target_value = db.Column(db.Float)
    data_source = db.Column(db.String(200))
    assessed_at = db.Column(db.DateTime, default=datetime.utcnow)

class InterviewGuide(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, db.ForeignKey('request.id'), nullable=False)
    request = db.relationship('Request', backref='interview_guides')
    stakeholder_name = db.Column(db.String(120))
    stakeholder_role = db.Column(db.String(120))
    interview_date = db.Column(db.Date)
    questions = db.Column(db.Text)
    key_findings = db.Column(db.Text)
    submitted_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    submitter = db.relationship('User', backref='interview_guides')

class ContentTag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, db.ForeignKey('request.id'), nullable=False)
    tag = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class LNACycle(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    budget_amount = db.Column(db.Float, default=0)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), default='Planning')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    requests = db.relationship('Request', backref='lna_cycle', lazy='dynamic',
        primaryjoin="LNACycle.id==Request.lna_cycle_id")
    department_budgets = db.relationship('DepartmentBudget', backref='cycle', lazy='dynamic', cascade='all,delete-orphan')

class DepartmentBudget(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    lna_cycle_id = db.Column(db.Integer, db.ForeignKey('lna_cycle.id'), nullable=False)
    department_name = db.Column(db.String(200), nullable=False)
    allocated_budget = db.Column(db.Float, default=0)
    spent_budget = db.Column(db.Float, default=0)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    def remaining(self): return self.allocated_budget - self.spent_budget
    def requests_in_department(self):
        return Request.query.filter_by(lna_cycle_id=self.lna_cycle_id, requester_department=self.department_name).all()

class LearningStatistic(db.Model):
    """Uploaded CSV/Excel learning stats for a request or cohort"""
    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, db.ForeignKey('request.id', ondelete='CASCADE'), nullable=False)
    cohort_id = db.Column(db.Integer, db.ForeignKey('cohort.id', ondelete='SET NULL'), nullable=True)
    learner_name = db.Column(db.String(200))
    learner_email = db.Column(db.String(200))
    department = db.Column(db.String(200))
    completion_status = db.Column(db.String(30), default='Not Started')
    completion_pct = db.Column(db.Float, default=0)
    score = db.Column(db.Float)
    time_spent_minutes = db.Column(db.Float)
    assessment_attempts = db.Column(db.Integer)
    passed = db.Column(db.Boolean)
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    upload_batch = db.Column(db.String(50))

class LearningUploadBatch(db.Model):
    """Tracks each CSV/Excel upload session"""
    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, db.ForeignKey('request.id', ondelete='CASCADE'), nullable=False)
    cohort_id = db.Column(db.Integer, db.ForeignKey('cohort.id', ondelete='SET NULL'), nullable=True)
    file_name = db.Column(db.String(200))
    rows_imported = db.Column(db.Integer, default=0)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    uploaded_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    uploader = db.relationship('User', backref='stat_uploads')

class Cohort(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, db.ForeignKey('request.id', ondelete='CASCADE'), nullable=True)
    request = db.relationship('Request', backref=db.backref('cohorts', cascade='all, delete-orphan'))
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    learner_count = db.Column(db.Integer, default=0)
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    status = db.Column(db.String(30), default='Planned')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    learning_stats = db.relationship('LearningStatistic', backref='cohort',
        lazy='dynamic', foreign_keys='LearningStatistic.cohort_id')
    upload_batches = db.relationship('LearningUploadBatch', backref='cohort',
        lazy='dynamic', foreign_keys='LearningUploadBatch.cohort_id')

class PhaseActivity(db.Model):
    """Activities/tasks within a phase — shown on calendar and kanban"""
    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, db.ForeignKey('request.id', ondelete='SET NULL'), nullable=True)
    request = db.relationship('Request', backref='activities')
    phase_name = db.Column(db.String(20), nullable=False)
    activity_name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    owner = db.relationship('User', backref='phase_activities')
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), default='Planned')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    user = db.relationship('User', backref='audit_logs')
    action = db.Column(db.String(200), nullable=False)
    entity_type = db.Column(db.String(50))
    entity_id = db.Column(db.Integer)
    details = db.Column(db.Text)
    ip_address = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class ResourceForecast(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref='forecasts')
    request_id = db.Column(db.Integer, db.ForeignKey('request.id'), nullable=True)
    week_start = db.Column(db.Date, nullable=False)
    week_end = db.Column(db.Date, nullable=False)
    availability_pct = db.Column(db.Float, default=100)
    allocated_pct = db.Column(db.Float, default=0)
    status = db.Column(db.String(20), default='Forecasted')
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class TrainingEvent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, db.ForeignKey('request.id'), nullable=True)
    request = db.relationship('Request', backref='training_events')
    title = db.Column(db.String(200))
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    trainer_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    trainer = db.relationship('User', backref='training_delivery')
    event_type = db.Column(db.String(20), default='planned')
    colour = db.Column(db.String(7), default='#2E86AB')
    status = db.Column(db.String(20), default='Scheduled')
    location = db.Column(db.String(200))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class ResourceAllocation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, db.ForeignKey('request.id'), nullable=False)
    request = db.relationship('Request', backref='resource_allocations')
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship('User', backref='allocations')
    accepted_at = db.Column(db.DateTime, default=datetime.utcnow)
    inferred_completion = db.Column(db.Date)
    actual_completion = db.Column(db.Date)
    status = db.Column(db.String(20), default='Allocated')
    phase_responsible = db.Column(db.String(20))
    notes = db.Column(db.Text)
