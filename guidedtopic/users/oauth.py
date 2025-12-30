"""
OAuth 2.0/OIDC authentication routes for Google and Microsoft Entra ID.

This module handles the OAuth authentication flow:
1. User clicks OAuth provider button -> oauth_login() initiates flow
2. User authenticates with provider (Google/Azure)
3. Provider redirects back -> oauth_callback() processes response
4. User info is extracted and user account is found/created/linked
5. User is logged in via Flask-Login
"""
from flask import Blueprint, redirect, url_for, current_app, flash
from flask_login import login_user
from guidedtopic.extensions import oauth, db
from guidedtopic.models import User

oauth_bp = Blueprint('oauth', __name__, url_prefix='/auth')

# Supported OAuth providers
SUPPORTED_PROVIDERS = ['google', 'azure']


# ============================================================================
# OAuth Flow Routes
# ============================================================================

@oauth_bp.route('/<provider>')
def oauth_login(provider):
    """
    Initiate OAuth flow with the specified provider.
    
    Args:
        provider: OAuth provider name ('google' or 'azure')
    
    Flow:
        1. Validate provider is supported
        2. Check provider is configured
        3. Generate redirect URI for callback
        4. Redirect user to provider's authorization page
    """
    # Validate provider is supported
    if provider not in SUPPORTED_PROVIDERS:
        flash('Unsupported authentication provider', 'danger')
        return redirect(url_for('users.login'))
    
    # Check provider is configured (has credentials)
    if provider not in oauth.providers:
        flash(f'{provider.title()} authentication is not configured', 'danger')
        return redirect(url_for('users.login'))
    
    # Generate callback URL and redirect to provider
    redirect_uri = url_for('oauth.oauth_callback', provider=provider, _external=True)
    return oauth.providers[provider].authorize_redirect(redirect_uri)


@oauth_bp.route('/<provider>/callback')
def oauth_callback(provider):
    """
    Handle OAuth callback from the provider after user authentication.
    
    Args:
        provider: OAuth provider name ('google' or 'azure')
    
    Flow:
        1. Validate provider
        2. Exchange authorization code for access token
        3. Fetch user info from provider's API
        4. Find existing user or create new one (with account linking)
        5. Log user in via Flask-Login
        6. Redirect to home page
    
    Errors are caught and logged without exposing sensitive information.
    """
    # Validate provider
    if provider not in SUPPORTED_PROVIDERS:
        flash('Unsupported authentication provider', 'danger')
        return redirect(url_for('users.login'))
    
    if provider not in oauth.providers:
        flash(f'{provider.title()} authentication is not configured', 'danger')
        return redirect(url_for('users.login'))
    
    try:
        # Step 1: Exchange authorization code for access token
        token = oauth.providers[provider].authorize_access_token()
        
        # Step 2: Fetch user information from provider (provider-specific)
        if provider == 'google':
            user_info = _get_google_user_info(provider)
        elif provider == 'azure':
            user_info = _get_azure_user_info(provider, token)
        else:
            flash('Unsupported provider', 'danger')
            return redirect(url_for('users.login'))
        
        # Step 3: Find existing user or create new one (handles account linking)
        user = _find_or_create_oauth_user(provider, user_info)
        
        # Step 4: Log user in via Flask-Login
        login_user(user)
        current_app.logger.info(
            '%s logged in via %s OAuth', 
            user.username, 
            provider
        )
        flash(f'Successfully signed in with {provider.title()}', 'success')
        return redirect(url_for('main.home'))
        
    except Exception as e:
        # Log error for debugging but don't expose details to user
        current_app.logger.exception('OAuth callback failed for %s: %s', provider, str(e))
        flash('Authentication failed. Please try again.', 'danger')
        return redirect(url_for('users.login'))


# ============================================================================
# Provider-Specific User Info Extraction
# ============================================================================

def _get_google_user_info(provider):
    """
    Extract user information from Google's OAuth response.
    
    Args:
        provider: Provider name (must be 'google')
    
    Returns:
        dict: User information with keys:
            - id: Google user ID (as string)
            - email: User's email address
            - name: Display name (falls back to email username)
            - picture: Profile picture URL (optional)
            - verified_email: Email verification status
            - hd: Google Workspace domain (if applicable)
    
    Uses Google's userinfo v2 API endpoint.
    """
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
    """
    Extract user information from Microsoft Entra ID's OAuth response.
    
    Args:
        provider: Provider name (must be 'azure')
        token: OAuth token containing access token and claims
    
    Returns:
        dict: User information with keys:
            - id: Entra ID object ID
            - email: User's email or userPrincipalName
            - name: Display name
            - given_name: First name (optional)
            - family_name: Last name (optional)
            - tenant_id: Azure AD tenant ID (if available)
    
    Uses Microsoft Graph API to fetch user profile.
    """
    resp = oauth.azure.get('https://graph.microsoft.com/v1.0/me')
    resp.raise_for_status()
    user_data = resp.json()
    
    # Extract tenant ID from config or token
    tenant_id = current_app.config.get('AZURE_AD_TENANT_ID')
    if tenant_id == 'common':
        # Multi-tenant mode - can't determine specific tenant from config
        tenant_id = None
    
    # Try to get tenant from token claims if not in config
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


# ============================================================================
# User Account Management
# ============================================================================

def _find_or_create_oauth_user(provider, user_info):
    """
    Find existing user or create new one from OAuth information.
    
    This function implements account linking logic:
    1. If OAuth account already exists (provider + oauth_id match) -> return user
    2. If email matches existing account -> link OAuth to that account
    3. Otherwise -> create new user account
    
    Args:
        provider: OAuth provider name ('google' or 'azure')
        user_info: Dictionary of user information from provider
    
    Returns:
        User: User instance (existing or newly created)
    
    Account Linking:
        - If user signs in with OAuth but email matches existing password account,
          the OAuth credentials are linked to the existing account
        - This allows users to use either authentication method
    """
    # Step 1: Check if OAuth account already exists
    # (User has signed in with this provider before)
    user = User.query.filter_by(
        oauth_provider=provider,
        oauth_id=user_info['id']
    ).first()
    
    if user:
        return user
    
    # Step 2: Check if email already exists (account linking)
    # (User has account with password, now signing in with OAuth)
    existing_user = User.query.filter_by(email=user_info['email']).first()
    
    if existing_user:
        # Link OAuth credentials to existing account
        existing_user.oauth_provider = provider
        existing_user.oauth_id = user_info['id']
        existing_user.oauth_email = user_info['email']
        
        # Store provider-specific metadata
        if provider == 'azure' and user_info.get('tenant_id'):
            existing_user.oauth_tenant_id = user_info['tenant_id']
        elif provider == 'google' and user_info.get('hd'):
            existing_user.oauth_domain = user_info['hd']
        
        db.session.commit()
        flash('OAuth account linked to your existing account', 'info')
        return existing_user
    
    # Step 3: Create new user account
    # Generate username from name or email
    username = user_info.get('name') or user_info['email'].split('@')[0]
    
    # Ensure username uniqueness and length constraints
    # Username max length is 20 characters
    username = username[:20]
    base_username = username
    counter = 1
    
    # If username exists, append number suffix
    while User.query.filter_by(username=username).first():
        suffix = str(counter)
        # Ensure total length doesn't exceed 20
        username = (base_username[:20-len(suffix)] + suffix)[:20]
        counter += 1
    
    # Create new user (OAuth-only, no password)
    user = User(
        username=username,
        email=user_info['email'],
        password=None,  # OAuth-only user
        oauth_provider=provider,
        oauth_id=user_info['id'],
        oauth_email=user_info['email'],
        image_file='default.jpg',
        uploadsvideo=False  # New users start without upload permissions
    )
    
    # Add provider-specific metadata
    if provider == 'azure' and user_info.get('tenant_id'):
        user.oauth_tenant_id = user_info['tenant_id']
    elif provider == 'google' and user_info.get('hd'):
        user.oauth_domain = user_info['hd']
    
    db.session.add(user)
    db.session.commit()
    
    return user
