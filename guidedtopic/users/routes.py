from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from guidedtopic.extensions import bcrypt, db
from guidedtopic.models import Post, User
from guidedtopic.users.forms import (
    LoginForm,
    RegistrationForm,
    RequestResetForm,
    ResetPasswordForm,
    UpdateAccountForm,
)
from guidedtopic.users.utils import save_picture, send_reset_email, send_upgrade_request


users = Blueprint('users', __name__)


# ============================================================================
# Authentication Routes
# ============================================================================

@users.route("/register", methods=['GET', 'POST'])
def register():
    """Present the registration form and create a new account."""
    # Redirect if already authenticated
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        # Hash password securely before storing
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(
            username=form.username.data,
            email=form.email.data,
            password=hashed_password,
            uploadsvideo=0  # New users start without upload permissions
        )
        db.session.add(user)
        db.session.commit()
        flash('Account created for {}, you may now login'.format(form.username.data), 'success')
        return redirect(url_for('users.login'))
    
    return render_template('register.html', title='Register', form=form)


@users.route("/login", methods=['GET', 'POST'])
def login():
    """
    Authenticate a user via password.
    
    Note: OAuth authentication is handled separately in users/oauth.py.
    This route only handles password-based authentication. Users with OAuth
    accounts should use the OAuth provider buttons on the login page.
    """
    # Redirect if already authenticated
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        
        # Check password only if user exists and has a password set
        # OAuth-only users won't have a password, so this check prevents errors
        if user and user.password and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            current_app.logger.info('%s logged in successfully', user.username)
            return redirect(next_page) if next_page else redirect(url_for('main.home'))
        else:
            flash('Login unsuccessful - please check email and password', 'danger')
    
    return render_template('login.html', title='Login', form=form)


@users.route("/logout")
def logout():
    """Terminate the current user session."""
    logout_user()
    return redirect(url_for('main.home'))


@users.route("/reset_password", methods=['GET', 'POST'])
def reset_request():
    """
    Collect an email address and send a password reset link.
    
    Only works for users with password authentication. OAuth users
    should use their OAuth provider to sign in.
    """
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    
    form = RequestResetForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        
        # Only send reset email if user has a password account
        if user and user.password:
            send_reset_email(user)
            flash('Reset email sent', 'info')
        else:
            flash('No password account found. Use OAuth to sign in.', 'info')
        
        return redirect(url_for('users.login'))
    
    return render_template('reset_request.html', title='Reset Password', form=form)


@users.route("/reset_password/<token>", methods=['GET', 'POST'])
def reset_token(token):
    """
    Validate a reset token and accept the user's new password.
    
    Tokens are time-limited (30 minutes) and single-use for security.
    """
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    
    # Verify token and get associated user
    user = User.verify_reset_token(token)
    if user is None:
        flash('Invalid or expired token', 'warning')
        return redirect(url_for('users.reset_request'))
    
    form = ResetPasswordForm()
    if form.validate_on_submit():
        # Hash new password securely
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user.password = hashed_password
        db.session.commit()
        flash('Password updated, you may now login', 'success')
        return redirect(url_for('users.login'))
    
    return render_template('reset_token.html', title='Reset Password', form=form)


# ============================================================================
# Profile & Account Management Routes
# ============================================================================

@users.route("/account", methods=['GET', 'POST'])
@login_required
def account():
    """
    Allow users to update their profile details and avatar.
    
    Users can update username, email, and profile picture.
    OAuth users can still update these fields even if they don't have passwords.
    """
    form = UpdateAccountForm()
    
    if form.validate_on_submit():
        # Handle profile picture upload if provided
        if form.picture.data:
            picture_file = save_picture(form.picture.data)
            current_user.image_file = picture_file
        
        # Update user information
        current_user.username = form.username.data
        current_user.email = form.email.data
        db.session.commit()
        flash('your account has been updated', 'success')
        return redirect(url_for('users.account'))
    
    elif request.method == 'GET':
        # Pre-populate form with current user data
        form.username.data = current_user.username
        form.email.data = current_user.email
    
    # Get profile picture URL for display
    image_file = url_for('static', filename='profile_pics/' + current_user.image_file)
    return render_template('account.html', title='Account',
                           image_file=image_file, form=form)


@users.route("/user/<string:username>")
def user_posts(username):
    """List all posts authored by the specified user."""
    page = request.args.get('page', 1, type=int)
    user = User.query.filter_by(username=username).first_or_404()
    posts = Post.query.filter_by(author=user)\
        .order_by(Post.date_posted.desc())\
        .paginate(page=page, per_page=4)
    return render_template('user_posts.html', posts=posts, user=user)


@users.route("/upgrade_request", methods=['GET', 'POST'])
def upgrade_request():
    """
    Send an email requesting elevated permissions for the account.
    
    Requests video upload permissions. Support team receives the email
    and can manually enable the uploadsvideo flag for the user.
    """
    if current_user.is_authenticated:
        send_upgrade_request()
        flash('Account feature upgrade requested - check your email for info', 'success')
        return redirect(url_for('users.account'))
    
    return redirect(url_for('users.login'))
