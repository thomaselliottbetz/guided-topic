import os
import secrets
from typing import List, Optional

from PIL import Image
from flask import current_app, url_for
from flask_login import current_user
from flask_mail import Message

from guidedtopic.extensions import mail


def save_picture(form_picture):
    """Store an uploaded profile picture and return the generated filename."""
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(current_app.root_path, 'static/profile_pics', picture_fn)
    i = Image.open(form_picture)
    i.thumbnail((125, 125))
    i.save(picture_path)

    return picture_fn


def _mail_sender() -> Optional[str]:
    """Return the configured default sender address if available."""
    return current_app.config.get("MAIL_DEFAULT_SENDER") or current_app.config.get("MAIL_USERNAME")


def _support_recipients() -> List[str]:
    """Derive the list of addresses that receive upgrade requests."""
    configured = current_app.config.get("SUPPORT_RECIPIENTS", [])
    if configured:
        return configured
    sender = _mail_sender()
    return [sender] if sender else []


def send_reset_email(user):
    """Email a password reset link to the supplied user."""
    token = user.get_reset_token()
    sender = _mail_sender()
    msg = Message(
        'Password Reset Request',
        sender=sender,
        recipients=[user.email],
    )
    msg.body = (
        "Reset password link:\n"
        f"{url_for('users.reset_token', token=token, _external=True)}\n"
        "If you didn't request password reset, simply ignore this email."
    )
    mail.send(msg)


def send_upgrade_request():
    """Notify support that the current user needs additional privileges."""
    recipients = _support_recipients()
    if not recipients:
        current_app.logger.warning("Support recipients not configured; upgrade request email not sent")
        return

    msg = Message(
        'Request for Feature Upgrade - Video Upload',
        sender=_mail_sender(),
        recipients=recipients,
    )
    msg.body = (
        'The following account requests enablement of video upload capability: '
        f'{current_user.email}'
    )
    mail.send(msg)
