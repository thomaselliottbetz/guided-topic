# Guided Topic

Guided Topic is a Flask application that turns instructional videos into interactive lessons. Educators can upload primary content, schedule checkpoints, and branch into remedial clips so learners receive timely feedback before resuming the main video.

## Setup

1. Create and activate a virtual environment.
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
2. Install dependencies.
   ```bash
   pip install -r requirements.txt
   ```
3. Export environment variables (database URI, mail settings, S3 bucket, etc.).
4. Run the development server.
   ```bash
   flask --app guidedtopic run
   ```

## Example Usage

```bash
# Start the Flask shell with application context
flask --app guidedtopic shell

# Perform database migrations (once configured)
flask --app guidedtopic db upgrade

# Run a basic syntax check
PYTHONPYCACHEPREFIX=./.pycache python3 -m compileall guidedtopic
```

## Architecture

- App factory in `guidedtopic/__init__.py` wires configuration, blueprints, and extensions.
- Blueprints for `main`, `users`, `posts`, `videos`, and `qna` keep routes modular.
- SQLAlchemy models capture users, posts, videos, questions, and feedback.
- AWS S3 uploads and playback URLs are managed via utilities in `guidedtopic/videos/utils.py`.
- Templates and static assets live under `guidedtopic/templates` and `guidedtopic/static`.

## Tech Stack

- Python 3 / Flask
- SQLAlchemy with Flask-Migrate
- WTForms & Flask-WTF
- Flask-Login, Flask-Bcrypt, Flask-Mail
- boto3 for S3 integration

## Project Structure

```
guidedtopic_retrieved2511/
├── README.md
├── DESIGN_OVERVIEW.md
├── requirements.txt
├── wsgi.py
├── .gitignore
├── instance/
│   └── .gitignore
├── migrations/
│   └── .gitkeep
├── tests/
│   └── __init__.py
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
    ├── videos/
    ├── templates/
    └── static/
```

## Environment Variables

Populate a local `.env` file (or export variables directly) before running the app. Example values:

```bash
GUIDEDTOPIC_SECRET_KEY=change-me
GUIDEDTOPIC_DATABASE_URI=sqlite:///dev.db

GUIDEDTOPIC_MAIL_SERVER=smtp.gmail.com
GUIDEDTOPIC_MAIL_PORT=587
GUIDEDTOPIC_MAIL_USE_TLS=true
GUIDEDTOPIC_MAIL_USERNAME=
GUIDEDTOPIC_MAIL_PASSWORD=

GUIDEDTOPIC_AWS_REGION=
GUIDEDTOPIC_S3_BUCKET=
GUIDEDTOPIC_STREAMING_TEMPLATE=

GUIDEDTOPIC_SUPPORT_RECIPIENTS=
GUIDEDTOPIC_WELCOME_VIDEO_URL=
GUIDEDTOPIC_MAX_CONTENT_LENGTH=524288000
GUIDEDTOPIC_ALLOWED_EXTENSIONS=mp4,m4v,mov
```

© 2025 Thomas Betz — MIT License
