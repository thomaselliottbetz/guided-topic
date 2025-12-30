from datetime import datetime

from flask import current_app
from flask_login import UserMixin
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer

from guidedtopic.extensions import db, login_manager


@login_manager.user_loader
def load_user(user_id):
    """Return the user instance for Flask-Login from the stored user id."""
    return User.query.get(int(user_id))


class User(db.Model, UserMixin):
    """Application user with authentication details and authored content."""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    image_file = db.Column(db.String(20), nullable=False,
                           default="default.jpg")
    password = db.Column(db.String(60), nullable=True)  # Optional for OAuth users
    posts = db.relationship('Post', backref='author', lazy=True)
    video = db.relationship('Video', backref='author', lazy=True)
    uploadsvideo = db.Column(db.Boolean, default=False)
    
    # OAuth fields
    oauth_provider = db.Column(db.String(50), nullable=True)  # 'google' or 'azure'
    oauth_id = db.Column(db.String(255), nullable=True)
    oauth_email = db.Column(db.String(120), nullable=True)
    oauth_tenant_id = db.Column(db.String(255), nullable=True)  # For Azure AD tenant
    oauth_domain = db.Column(db.String(255), nullable=True)  # For Google Workspace domain
    
    __table_args__ = (
        db.UniqueConstraint('oauth_provider', 'oauth_id', name='uq_oauth_provider_id'),
    )
    
    def has_password(self):
        """Check if user has password authentication enabled."""
        return self.password is not None
    
    def has_oauth(self):
        """Check if user has OAuth authentication enabled."""
        return self.oauth_provider is not None

    def get_reset_token(self, expires_sec=1800):
        """Generate a time-limited token for password reset emails."""
        s = Serializer(current_app.config['SECRET_KEY'], expires_sec)
        return s.dumps({'user_id': self.id}).decode('utf-8')

    @staticmethod
    def verify_reset_token(token):
        """Return the user associated with a reset token, or None if invalid."""
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            user_id = s.loads(token)['user_id']
        except:
            return None
        return User.query.get(user_id)

    def __repr__(self):
        return "User({}, {}, {})".format(self.username, self.email,
                                         self.image_file)


class Post(db.Model):
    """Announcement or blog-style post authored by an educator."""
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    date_posted = db.Column(db.DateTime, nullable=False,
                            default=datetime.utcnow)
    content = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def __repr__(self):
        return "Post({}, {})".format(self.title, self.date_posted)


class Video(db.Model):
    """Primary instructional video along with metadata and related questions."""
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    description = db.Column(db.String(220))
    date_posted = db.Column(db.DateTime, nullable=False,
                            default=datetime.utcnow)
    video_file = db.Column(db.String(120), default="default.mp4")
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    duration = db.Column(db.Float, default=0.0)
    is_remedial = db.Column(db.Boolean, default=False)
    questions = db.relationship('Question', backref='associated_video', lazy=True)
    total_views = db.Column(db.Integer, default=0) 

    def __repr__(self):
        return "Video title and filename are ({}, {})".format(self.title, self.video_file)

class Feedback(db.Model):
    """Stores qualitative feedback submitted through the site widget."""
    id = db.Column(db.Integer, primary_key=True)
    feedback_type = db.Column(db.Text)
    content = db.Column(db.Text)
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return "Feedback: ({}, {}, {})".format(
            self.feedback_type,
            self.content,
            self.date_posted,
        )


class Question(db.Model):
    """Timed question presented during video playback with answer branching."""
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    pose_time = db.Column(db.Integer)
    video_id = db.Column(db.Integer, db.ForeignKey('video.id'))
    contentA = db.Column(db.Text)
    targetvidA = db.Column(db.Integer)
    contentB = db.Column(db.Text)
    targetvidB = db.Column(db.Integer)
    contentC = db.Column(db.Text)
    targetvidC = db.Column(db.Integer)
    contentD = db.Column(db.Text)
    targetvidD = db.Column(db.Integer)
    contentE = db.Column(db.Text)
    targetvidE = db.Column(db.Integer)

    def __repr__(self):
        return "Question, id, and video are ({}, {}, {})".format(self.content, self.id, self.video_id)
