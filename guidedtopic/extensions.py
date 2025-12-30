"""
Flask extension initialization and configuration.

This module initializes all Flask extensions used by the application:
- SQLAlchemy: Database ORM
- Bcrypt: Password hashing
- Mail: Email sending
- LoginManager: User session management
- Migrate: Database migrations
- OAuth: OAuth 2.0/OIDC authentication (Google, Microsoft Entra ID)
"""
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_mail import Mail
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from authlib.integrations.flask_client import OAuth


# ============================================================================
# Extension Instances
# ============================================================================

# Initialize extension instances (not yet bound to app)
db = SQLAlchemy()
bcrypt = Bcrypt()
mail = Mail()
login_manager = LoginManager()
migrate = Migrate()
oauth = OAuth()


# ============================================================================
# Extension Initialization
# ============================================================================

def init_app(app):
    """
    Initialize all Flask extensions with the application instance.
    
    Args:
        app: Flask application instance
    
    This function is called during app factory creation to bind all
    extensions to the Flask app. OAuth providers are registered
    conditionally based on configuration.
    """
    # Initialize core extensions
    db.init_app(app)
    bcrypt.init_app(app)
    mail.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    
    # ========================================================================
    # OAuth Provider Registration
    # ========================================================================
    
    # Initialize OAuth client
    oauth.init_app(app)
    
    # Register Google OAuth provider (if configured)
    # Works with both consumer Google accounts and Google Workspace
    if app.config.get('GOOGLE_CLIENT_ID') and app.config.get('GOOGLE_CLIENT_SECRET'):
        oauth.register(
            name='google',
            client_id=app.config['GOOGLE_CLIENT_ID'],
            client_secret=app.config['GOOGLE_CLIENT_SECRET'],
            server_metadata_url=app.config.get(
                'GOOGLE_DISCOVERY_URL',
                'https://accounts.google.com/.well-known/openid-configuration'
            ),
            client_kwargs={
                'scope': 'openid email profile'  # Request access to user profile and email
            }
        )
    
    # Register Microsoft Entra ID (Azure AD) provider (if configured)
    # Supports both single-tenant and multi-tenant configurations
    if app.config.get('AZURE_AD_CLIENT_ID') and app.config.get('AZURE_AD_CLIENT_SECRET'):
        tenant_id = app.config.get('AZURE_AD_TENANT_ID', 'common')
        
        # Build discovery URL based on tenant configuration
        # 'common' = multi-tenant, specific ID = single-tenant
        discovery_url = app.config.get(
            'AZURE_AD_DISCOVERY_URL',
            f"https://login.microsoftonline.com/{tenant_id}/v2.0/.well-known/openid-configuration"
        )
        
        oauth.register(
            name='azure',
            client_id=app.config['AZURE_AD_CLIENT_ID'],
            client_secret=app.config['AZURE_AD_CLIENT_SECRET'],
            server_metadata_url=discovery_url,
            client_kwargs={
                'scope': 'openid email profile User.Read'  # Request access to user profile and email
            }
        )
    
    # ========================================================================
    # Flask-Login Configuration
    # ========================================================================
    
    # Set the login view for unauthorized access attempts
    login_manager.login_view = "users.login"
    login_manager.login_message_category = "info"
