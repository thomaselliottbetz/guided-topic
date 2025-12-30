# Guided Topic

Guided Topic is a Flask application that turns instructional videos into interactive lessons. Educators can upload primary content, schedule checkpoints, and branch into remedial clips so learners receive timely feedback before resuming the main video.

## Architecture

- App factory in `guidedtopic/__init__.py` wires configuration, blueprints, and extensions.
- Blueprints for `main`, `users`, `posts`, `videos`, `qna`, and `errors` keep routes modular.
- OAuth routes in `guidedtopic/users/oauth.py` handle Google and Microsoft Entra ID authentication.
- SQLAlchemy models capture users, posts, videos, questions, and feedback.
- User model supports both password and OAuth authentication methods.
- AWS S3 uploads and playback URLs are managed via utilities in `guidedtopic/videos/utils.py`.
- Templates and static assets live under `guidedtopic/templates` and `guidedtopic/static`.
- Code is organized with clear sections, comprehensive comments, and helper functions for maintainability.

## Tech Stack

- Authlib for OAuth 2.0/OIDC integration
- boto3 for S3 integration
- Flask-Login, Flask-Bcrypt, Flask-Mail
- pytest and pytest-flask for testing
- Python 3 / Flask
- SQLAlchemy with Flask-Migrate
- WTForms & Flask-WTF

## Setup

1. Create and activate a virtual environment.
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

2. Install dependencies.
   ```bash
   pip install -r requirements.txt
   ```

3. Configure environment variables (see [Environment Variables](#environment-variables) below).
   - Only `GUIDEDTOPIC_SECRET_KEY` and `GUIDEDTOPIC_DATABASE_URI` are required
   - OAuth, mail, and S3 settings are optional depending on which features you use

4. Initialize and run database migrations.
   ```bash
   flask --app guidedtopic db init  # Only needed on first setup
   flask --app guidedtopic db upgrade
   ```

5. Run the development server.
   ```bash
   flask --app guidedtopic run
   ```

## Example Usage

```bash
# Start the Flask shell with application context
flask --app guidedtopic shell

# Perform database migrations
flask --app guidedtopic db upgrade

# Create a new migration after model changes
flask --app guidedtopic db migrate -m "Description of changes"

# Run tests
pytest

# Run a basic syntax check
PYTHONPYCACHEPREFIX=./.pycache python3 -m compileall guidedtopic
```

## Project Structure

```
guidedtopic/
├── README.md
├── DESIGN_OVERVIEW.md
├── requirements.txt
├── wsgi.py
├── .gitignore
├── instance/
│   └── .gitignore
├── migrations/
│   ├── versions/          # Database migration files
│   ├── alembic.ini
│   └── env.py
├── tests/
│   ├── __init__.py
│   └── test_oauth.py     # OAuth authentication tests
└── guidedtopic/
    ├── __init__.py
    ├── config.py
    ├── extensions.py
    ├── models.py
    ├── errors/
    ├── main/
    ├── posts/
    ├── qna/
    ├── users/
    │   ├── oauth.py       # OAuth routes and callbacks
    │   ├── routes.py
    │   ├── forms.py
    │   └── utils.py
    ├── videos/
    │   ├── routes.py
    │   ├── forms.py
    │   └── utils.py      # S3 upload utilities
    ├── templates/
    └── static/
        ├── main.css
        └── profile_pics/
            └── default.jpg
```

## Environment Variables

Populate a local `.env` file (or export variables directly) before running the app. Example values:

### Core Configuration

```
GUIDEDTOPIC_SECRET_KEY=change-me
GUIDEDTOPIC_DATABASE_URI=sqlite:///dev.db
```

### OAuth Configuration (Optional)

Google OAuth (works with consumer accounts and Google Workspace):
```
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
```

Microsoft Entra ID (Azure AD):
```
AZURE_AD_TENANT_ID=your-tenant-id          # or "common" for multi-tenant
AZURE_AD_CLIENT_ID=your-azure-client-id
AZURE_AD_CLIENT_SECRET=your-azure-client-secret
```

OAuth redirect base URL (optional, defaults to http://localhost:5000):
```
OAUTH_REDIRECT_BASE=https://yourdomain.com
```

### Email Configuration

```
GUIDEDTOPIC_MAIL_SERVER=smtp.gmail.com
GUIDEDTOPIC_MAIL_PORT=587
GUIDEDTOPIC_MAIL_USE_TLS=true
GUIDEDTOPIC_MAIL_USERNAME=
GUIDEDTOPIC_MAIL_PASSWORD=
```

### AWS S3 Configuration

```
GUIDEDTOPIC_AWS_REGION=
GUIDEDTOPIC_S3_BUCKET=
GUIDEDTOPIC_STREAMING_TEMPLATE=
```

### Other Configuration

```
GUIDEDTOPIC_SUPPORT_RECIPIENTS=
GUIDEDTOPIC_WELCOME_VIDEO_URL=
GUIDEDTOPIC_MAX_CONTENT_LENGTH=524288000
GUIDEDTOPIC_ALLOWED_EXTENSIONS=mp4,m4v,mov
```

## Authentication

The application supports multiple authentication methods that can be used together:

- Password authentication with secure bcrypt hashing and email-based password reset
- OAuth 2.0/OIDC via Google (consumer and Google Workspace)
- OAuth 2.0/OIDC via Microsoft Entra ID (Azure AD)

Users can sign in with either method, and OAuth accounts can be linked to existing email accounts.

## Testing

Run the test suite with pytest:

```bash
pytest
```

Run specific test files:

```bash
pytest tests/test_oauth.py
```

The test suite includes OAuth authentication tests that verify user creation, account linking, and provider-specific metadata handling.

## Code Quality

The codebase emphasizes maintainability with:
- Comprehensive docstrings and inline comments explaining complex logic
- Logical code organization with routes grouped by functionality
- Helper functions for repeated operations (e.g., time parsing)
- Clear variable naming and consistent patterns
- Security-focused comments explaining authentication and authorization flows

© 2025 Thomas Betz — MIT License
