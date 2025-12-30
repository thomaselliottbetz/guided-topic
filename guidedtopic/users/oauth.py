from flask import Blueprint, redirect, url_for, current_app, flash
from flask_login import login_user
from guidedtopic.extensions import oauth, db
from guidedtopic.models import User

oauth_bp = Blueprint('oauth', __name__, url_prefix='/auth')


@oauth_bp.route('/<provider>')
def oauth_login(provider):
    """Initiate OAuth flow with Google or Azure AD."""
    if provider not in ['google', 'azure']:
        flash('Unsupported authentication provider', 'danger')
        return redirect(url_for('users.login'))
    
    if provider not in oauth.providers:
        flash(f'{provider.title()} authentication is not configured', 'danger')
        return redirect(url_for('users.login'))
    
    redirect_uri = url_for('oauth.oauth_callback', provider=provider, _external=True)
    return oauth.providers[provider].authorize_redirect(redirect_uri)


@oauth_bp.route('/<provider>/callback')
def oauth_callback(provider):
    """Handle OAuth callback from Google or Azure AD."""
    if provider not in ['google', 'azure']:
        flash('Unsupported authentication provider', 'danger')
        return redirect(url_for('users.login'))
    
    if provider not in oauth.providers:
        flash(f'{provider.title()} authentication is not configured', 'danger')
        return redirect(url_for('users.login'))
    
    try:
        # Get token from provider
        token = oauth.providers[provider].authorize_access_token()
        
        # Get user info (provider-specific)
        if provider == 'google':
            user_info = _get_google_user_info(provider)
        elif provider == 'azure':
            user_info = _get_azure_user_info(provider, token)
        else:
            flash('Unsupported provider', 'danger')
            return redirect(url_for('users.login'))
        
        # Find or create user
        user = _find_or_create_oauth_user(provider, user_info)
        
        # Login user
        login_user(user)
        current_app.logger.info(
            '%s logged in via %s OAuth', 
            user.username, 
            provider
        )
        flash(f'Successfully signed in with {provider.title()}', 'success')
        return redirect(url_for('main.home'))
        
    except Exception as e:
        current_app.logger.exception('OAuth callback failed for %s: %s', provider, str(e))
        flash('Authentication failed. Please try again.', 'danger')
        return redirect(url_for('users.login'))


def _get_google_user_info(provider):
    """Extract user info from Google token response."""
    resp = oauth.google.get('https://www.googleapis.com/oauth2/v2/userinfo')
    resp.raise_for_status()
    user_data = resp.json()
    
    return {
        'id': str(user_data['id']),
        'email': user_data['email'],
        'name': user_data.get('name', user_data['email'].split('@')[0]),
        'picture': user_data.get('picture'),
        'verified_email': user_data.get('verified_email', False),
        'hd': user_data.get('hd')  # Google Workspace domain (if applicable)
    }


def _get_azure_user_info(provider, token):
    """Extract user info from Microsoft Entra ID token response."""
    resp = oauth.azure.get('https://graph.microsoft.com/v1.0/me')
    resp.raise_for_status()
    user_data = resp.json()
    
    # Extract tenant ID from config or token
    tenant_id = current_app.config.get('AZURE_AD_TENANT_ID')
    if tenant_id == 'common':
        tenant_id = None  # Multi-tenant, can't determine specific tenant
    
    # Try to get tenant from user's email domain or token claims if available
    if not tenant_id and 'id_token_claims' in token:
        tenant_id = token.get('id_token_claims', {}).get('tid')
    
    return {
        'id': user_data['id'],  # Object ID in Entra ID
        'email': user_data.get('mail') or user_data.get('userPrincipalName'),
        'name': user_data.get('displayName', ''),
        'given_name': user_data.get('givenName', ''),
        'family_name': user_data.get('surname', ''),
        'tenant_id': tenant_id,
    }


def _find_or_create_oauth_user(provider, user_info):
    """Find existing user or create new one from OAuth info."""
    # Check if OAuth account already exists
    user = User.query.filter_by(
        oauth_provider=provider,
        oauth_id=user_info['id']
    ).first()
    
    if user:
        return user
    
    # Check if email already exists (link OAuth to existing account)
    existing_user = User.query.filter_by(email=user_info['email']).first()
    
    if existing_user:
        # Link OAuth to existing account
        existing_user.oauth_provider = provider
        existing_user.oauth_id = user_info['id']
        existing_user.oauth_email = user_info['email']
        if provider == 'azure' and user_info.get('tenant_id'):
            existing_user.oauth_tenant_id = user_info['tenant_id']
        elif provider == 'google' and user_info.get('hd'):
            existing_user.oauth_domain = user_info['hd']
        db.session.commit()
        flash('OAuth account linked to your existing account', 'info')
        return existing_user
    
    # Create new user
    username = user_info.get('name') or user_info['email'].split('@')[0]
    # Ensure username uniqueness and length
    username = username[:20]  # Max length is 20
    base_username = username
    counter = 1
    while User.query.filter_by(username=username).first():
        suffix = str(counter)
        username = (base_username[:20-len(suffix)] + suffix)[:20]
        counter += 1
    
    user = User(
        username=username,
        email=user_info['email'],
        password=None,  # OAuth-only user
        oauth_provider=provider,
        oauth_id=user_info['id'],
        oauth_email=user_info['email'],
        image_file='default.jpg',
        uploadsvideo=False
    )
    
    # Add provider-specific metadata
    if provider == 'azure' and user_info.get('tenant_id'):
        user.oauth_tenant_id = user_info['tenant_id']
    elif provider == 'google' and user_info.get('hd'):
        user.oauth_domain = user_info['hd']
    
    db.session.add(user)
    db.session.commit()
    
    return user

