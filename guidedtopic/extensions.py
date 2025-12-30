from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_mail import Mail
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from authlib.integrations.flask_client import OAuth


db = SQLAlchemy()
bcrypt = Bcrypt()
mail = Mail()
login_manager = LoginManager()
migrate = Migrate()
oauth = OAuth()


def init_app(app):
    """Initialise shared Flask extensions for the application."""
    db.init_app(app)
    bcrypt.init_app(app)
    mail.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    
    # Initialize OAuth
    oauth.init_app(app)
    
    # Register Google provider
    if app.config.get('GOOGLE_CLIENT_ID') and app.config.get('GOOGLE_CLIENT_SECRET'):
        oauth.register(
            name='google',
            client_id=app.config['GOOGLE_CLIENT_ID'],
            client_secret=app.config['GOOGLE_CLIENT_SECRET'],
            server_metadata_url=app.config.get('GOOGLE_DISCOVERY_URL', 'https://accounts.google.com/.well-known/openid-configuration'),
            client_kwargs={
                'scope': 'openid email profile'
            }
        )
    
    # Register Microsoft Entra ID provider
    if app.config.get('AZURE_AD_CLIENT_ID') and app.config.get('AZURE_AD_CLIENT_SECRET'):
        tenant_id = app.config.get('AZURE_AD_TENANT_ID', 'common')
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
                'scope': 'openid email profile User.Read'
            }
        )

    login_manager.login_view = "users.login"
    login_manager.login_message_category = "info"

