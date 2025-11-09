from flask import Blueprint, render_template

errors = Blueprint('errors', __name__)

@errors.app_errorhandler(404)
def error_404(error):
    """Render the custom 404 page when a route is not found."""
    return render_template('404.html'), 404

@errors.app_errorhandler(403)
def error_403(error):
    """Render the 403 page when access is forbidden."""
    return render_template('403.html'), 403

@errors.app_errorhandler(500)
def error_500(error):
    """Render the fallback error page for unhandled exceptions."""
    return render_template('500.html'), 500
