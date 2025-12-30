"""
Database models for the Guided Topic application.

Defines SQLAlchemy models for:
- User: Authentication and profile information (supports password and OAuth)
- Post: Announcements/blog posts by educators
- Video: Instructional videos with metadata
- Question: Branching questions that appear during video playback
- Feedback: User feedback submissions
"""
from datetime import datetime

from flask import current_app
from flask_login import UserMixin
from itsdangerous import URLSafeTimedSerializer

from guidedtopic.extensions import db, login_manager


# ============================================================================
# Flask-Login User Loader
# ============================================================================

@login_manager.user_loader
def load_user(user_id):
    """
    Return the user instance for Flask-Login from the stored user id.
    
    This callback is required by Flask-Login to load users from the session.
    """
    return User.query.get(int(user_id))


# ============================================================================
# User Model
# ============================================================================

class User(db.Model, UserMixin):
    """
    Application user with authentication details and authored content.
    
    Supports multiple authentication methods:
    - Password authentication (bcrypt hashed)
    - OAuth 2.0/OIDC via Google
    - OAuth 2.0/OIDC via Microsoft Entra ID (Azure AD)
    
    Users can have both password and OAuth authentication enabled (account linking).
    
    Relationships:
        - posts: One-to-many with Post (user can author many posts)
        - video: One-to-many with Video (user can author many videos)
    """
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    image_file = db.Column(db.String(20), nullable=False, default="default.jpg")
    
    # Password authentication (optional - OAuth users may not have passwords)
    password = db.Column(db.String(60), nullable=True)
    
    # Profile and permissions
    uploadsvideo = db.Column(db.Boolean, default=False)  # Educator/admin flag
    
    # OAuth authentication fields
    oauth_provider = db.Column(db.String(50), nullable=True)  # 'google' or 'azure'
    oauth_id = db.Column(db.String(255), nullable=True)  # Provider's user ID
    oauth_email = db.Column(db.String(120), nullable=True)  # Email from OAuth provider
    oauth_tenant_id = db.Column(db.String(255), nullable=True)  # Azure AD tenant ID
    oauth_domain = db.Column(db.String(255), nullable=True)  # Google Workspace domain
    
    # Relationships
    posts = db.relationship('Post', backref='author', lazy=True, cascade='all, delete-orphan')
    video = db.relationship('Video', backref='author', lazy=True, cascade='all, delete-orphan')
    
    # Unique constraint: OAuth provider + OAuth ID must be unique
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
        """
        Generate a time-limited token for password reset emails.
        
        Args:
            expires_sec: Token expiration time in seconds (default: 30 minutes)
        
        Returns:
            str: URL-safe token string
        
        Security:
            - Tokens are signed with SECRET_KEY
            - Salt prevents token reuse for other purposes
            - Time-limited to prevent indefinite validity
        """
        s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
        return s.dumps({'user_id': self.id}, salt='password-reset')

    @staticmethod
    def verify_reset_token(token):
        """
        Return the user associated with a reset token, or None if invalid.
        
        Args:
            token: Token string from get_reset_token()
        
        Returns:
            User or None: User instance if token is valid, None otherwise
        
        Security:
            - Validates token signature
            - Checks token expiration (30 minutes)
            - Returns None for invalid/expired tokens
        """
        s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
        try:
            user_id = s.loads(token, salt='password-reset', max_age=1800)['user_id']
        except:
            return None
        return User.query.get(user_id)

    def __repr__(self):
        return "User({}, {}, {})".format(self.username, self.email, self.image_file)


# ============================================================================
# Content Models
# ============================================================================

class Post(db.Model):
    """
    Announcement or blog-style post authored by an educator.
    
    Used for course announcements, updates, and general communication
    to learners.
    
    Relationships:
        - author: Many-to-one with User (post belongs to one user)
    """
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    content = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def __repr__(self):
        return "Post({}, {})".format(self.title, self.date_posted)


class Video(db.Model):
    """
    Primary instructional video along with metadata and related questions.
    
    Videos are stored in AWS S3, and video_file contains the S3 URL or
    streaming URL for playback.
    
    Relationships:
        - author: Many-to-one with User (video belongs to one user/educator)
        - questions: One-to-many with Question (video can have many questions)
    """
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    description = db.Column(db.String(220))
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    video_file = db.Column(db.String(120), default="default.mp4")  # S3 URL or streaming URL
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    duration = db.Column(db.Float, default=0.0)  # Video duration in seconds
    is_remedial = db.Column(db.Boolean, default=False)  # True if this is a remedial video
    total_views = db.Column(db.Integer, default=0)  # View counter
    
    # Relationships
    questions = db.relationship('Question', backref='associated_video', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return "Video title and filename are ({}, {})".format(self.title, self.video_file)


class Question(db.Model):
    """
    Timed question presented during video playback with answer branching.
    
    Questions appear at a specific time (pose_time) during video playback.
    Each question has up to 5 answer choices (A-E), and each answer can
    redirect the learner to a different video (branching).
    
    Branching Logic:
        - If targetvid is set to a video ID, learner is redirected to that video
        - If targetvid is 0 or None, learner continues with current video
        - This enables adaptive learning paths based on learner responses
    
    Relationships:
        - associated_video: Many-to-one with Video (question belongs to one video)
    """
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)  # Question text
    pose_time = db.Column(db.Integer)  # Time in seconds when question appears
    video_id = db.Column(db.Integer, db.ForeignKey('video.id'))
    
    # Answer choices and their target videos (branching)
    contentA = db.Column(db.Text)
    targetvidA = db.Column(db.Integer)  # Video ID to redirect to if answer A is selected
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


class Feedback(db.Model):
    """
    Stores qualitative feedback submitted through the site widget.
    
    Used to collect user feedback about the platform, content, or experience.
    Feedback is sent to support team via email.
    """
    id = db.Column(db.Integer, primary_key=True)
    feedback_type = db.Column(db.Text)  # Type/category of feedback
    content = db.Column(db.Text)  # Feedback message
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return "Feedback: ({}, {}, {})".format(
            self.feedback_type,
            self.content,
            self.date_posted,
        )
