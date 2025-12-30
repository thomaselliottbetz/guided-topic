"""Tests for OAuth authentication functionality."""

import pytest
from guidedtopic import create_app
from guidedtopic.extensions import db
from guidedtopic.models import User
from guidedtopic.users.oauth import _find_or_create_oauth_user


@pytest.fixture
def app():
    """Create application for testing."""
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SECRET_KEY'] = 'test-secret-key'
    
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


class TestOAuthUserCreation:
    """Test OAuth user creation and account linking."""
    
    def test_create_new_oauth_user(self, app):
        """Test creating a new user from OAuth info."""
        with app.app_context():
            user_info = {
                'id': 'google-123',
                'email': 'test@example.com',
                'name': 'Test User',
            }
            
            user = _find_or_create_oauth_user('google', user_info)
            
            assert user is not None
            assert user.email == 'test@example.com'
            assert user.username == 'Test User'
            assert user.oauth_provider == 'google'
            assert user.oauth_id == 'google-123'
            assert user.password is None
            assert user.has_oauth() is True
            assert user.has_password() is False
    
    def test_find_existing_oauth_user(self, app):
        """Test finding an existing OAuth user."""
        with app.app_context():
            # Create existing OAuth user
            existing_user = User(
                username='existing',
                email='existing@example.com',
                oauth_provider='google',
                oauth_id='google-123',
                oauth_email='existing@example.com'
            )
            db.session.add(existing_user)
            db.session.commit()
            
            # Try to find/create with same OAuth ID
            user_info = {
                'id': 'google-123',
                'email': 'existing@example.com',
                'name': 'Existing User',
            }
            
            user = _find_or_create_oauth_user('google', user_info)
            
            assert user.id == existing_user.id
            assert user.email == 'existing@example.com'
    
    def test_link_oauth_to_existing_email(self, app):
        """Test linking OAuth account to existing password user."""
        with app.app_context():
            # Create existing password user
            from guidedtopic.extensions import bcrypt
            existing_user = User(
                username='passworduser',
                email='user@example.com',
                password=bcrypt.generate_password_hash('password').decode('utf-8')
            )
            db.session.add(existing_user)
            db.session.commit()
            
            # Link OAuth to existing account
            user_info = {
                'id': 'google-456',
                'email': 'user@example.com',
                'name': 'Password User',
            }
            
            user = _find_or_create_oauth_user('google', user_info)
            
            assert user.id == existing_user.id
            assert user.oauth_provider == 'google'
            assert user.oauth_id == 'google-456'
            assert user.password is not None  # Password still exists
            assert user.has_oauth() is True
            assert user.has_password() is True
    
    def test_username_uniqueness_handling(self, app):
        """Test that duplicate usernames are handled correctly."""
        with app.app_context():
            # Create user with username "testuser"
            existing_user = User(
                username='testuser',
                email='test1@example.com',
                password='hashed'
            )
            db.session.add(existing_user)
            db.session.commit()
            
            # Try to create OAuth user with same name
            user_info = {
                'id': 'google-789',
                'email': 'test2@example.com',
                'name': 'testuser',  # Same username
            }
            
            user = _find_or_create_oauth_user('google', user_info)
            
            assert user.username != 'testuser'  # Should be modified
            assert user.username.startswith('testuser')
            assert user.email == 'test2@example.com'
    
    def test_google_workspace_domain_storage(self, app):
        """Test that Google Workspace domain is stored."""
        with app.app_context():
            user_info = {
                'id': 'google-workspace-123',
                'email': 'user@company.com',
                'name': 'Workspace User',
                'hd': 'company.com'  # Google Workspace domain
            }
            
            user = _find_or_create_oauth_user('google', user_info)
            
            assert user.oauth_domain == 'company.com'
    
    def test_azure_tenant_id_storage(self, app):
        """Test that Azure AD tenant ID is stored."""
        with app.app_context():
            user_info = {
                'id': 'azure-123',
                'email': 'user@company.com',
                'name': 'Azure User',
                'tenant_id': 'tenant-abc-123'
            }
            
            user = _find_or_create_oauth_user('azure', user_info)
            
            assert user.oauth_tenant_id == 'tenant-abc-123'


class TestUserModelOAuthMethods:
    """Test User model OAuth helper methods."""
    
    def test_has_password_method(self, app):
        """Test has_password() method."""
        with app.app_context():
            # User with password
            user_with_pw = User(
                username='user1',
                email='user1@example.com',
                password='hashed'
            )
            assert user_with_pw.has_password() is True
            
            # OAuth-only user
            oauth_user = User(
                username='user2',
                email='user2@example.com',
                password=None,
                oauth_provider='google',
                oauth_id='123'
            )
            assert oauth_user.has_password() is False
    
    def test_has_oauth_method(self, app):
        """Test has_oauth() method."""
        with app.app_context():
            # OAuth user
            oauth_user = User(
                username='user1',
                email='user1@example.com',
                oauth_provider='google',
                oauth_id='123'
            )
            assert oauth_user.has_oauth() is True
            
            # Password-only user
            password_user = User(
                username='user2',
                email='user2@example.com',
                password='hashed'
            )
            assert password_user.has_oauth() is False

