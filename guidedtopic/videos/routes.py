import mimetypes
from pathlib import Path
from uuid import uuid4

from flask import (Blueprint, abort, current_app, flash, redirect,
                   render_template, request, url_for)
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

from guidedtopic.extensions import db
from guidedtopic.models import Question, Video
from guidedtopic.videos.forms import PostVideoForm
from guidedtopic.videos.utils import UploadError, build_video_url, upload_video_to_s3


videos = Blueprint('videos', __name__)


@videos.route("/video", methods=['GET', 'POST'])
def video():
    """Render the sample video player page."""
    return render_template('video.html')


@videos.route("/select_video")
@login_required
def select_video():
    """List non-remedial videos for learners to choose from."""
    page = request.args.get('page', 1, type=int)
    videos = Video.query.filter_by(is_remedial=False).order_by(Video.id).paginate(page=page, per_page=3)
    return render_template('selectvideo.html', title='Select Video', videos=videos)


@videos.route("/remedialvideos")
@login_required
def remedialvideos():
    """Display the set of remedial videos available to learners."""
    page = request.args.get('page', 1, type=int)
    videos = Video.query.filter_by(is_remedial=1).order_by(Video.id).paginate(page=page, per_page=3)
    return render_template('remedialvideos.html', title='Remedial Videos', videos=videos)


@videos.route("/study_video/<v_id>")
@login_required
def study_video(v_id):
    """Serve the learner playback page with questions for a video."""
    video = Video.query.get_or_404(v_id)
    questions = Question.query.filter_by(associated_video=video).order_by(Question.pose_time)
    views = video.total_views + 1
    video.total_views = views
    db.session.add(video)
    db.session.commit()
    current_app.logger.info('%s accessing study_video route w/ v_id %s', current_user.username, v_id)
    return render_template('study_video.html', video=video, questions=questions, rp=current_app.root_path, views=views)


@videos.route("/getvideopath/<v_id>", methods=['GET', 'POST'])
@login_required
def getvideopath(v_id):
    """Return the stored playback URL for the requested video."""
    video = Video.query.filter_by(id=v_id).first()
    return video.video_file


@videos.route("/upload_video", methods=['GET', 'POST'])
@login_required
def upload_video():
    """Handle educator uploads and store the source in S3."""
    if current_user.uploadsvideo == 0:
        flash('account not authorized for video upload: click to request video upload permission', 'info')
        return redirect(url_for('users.account'))
    form = PostVideoForm()
    if form.validate_on_submit():
        file_storage = request.files.get("video")
        if not file_storage or not file_storage.filename:
            flash("Please choose a video file to upload.", "warning")
            return redirect(url_for("videos.upload_video"))

        original_name = secure_filename(file_storage.filename)
        if not original_name:
            flash("Invalid file name.", "danger")
            return redirect(url_for("videos.upload_video"))

        extension = Path(original_name).suffix.lower().lstrip(".")
        allowed_extensions = current_app.config.get("UPLOAD_ALLOWED_EXTENSIONS", set())
        if extension not in allowed_extensions:
            flash(
                f"Unsupported file type '.{extension}'. Allowed types: {', '.join(sorted(allowed_extensions))}.",
                "danger",
            )
            return redirect(url_for("videos.upload_video"))

        storage_key = f"uploads/{current_user.id}/{uuid4().hex}{Path(original_name).suffix.lower()}"
        content_type = mimetypes.guess_type(original_name)[0] or "application/octet-stream"

        file_stream = file_storage.stream
        file_stream.seek(0)

        try:
            s3_metadata = upload_video_to_s3(file_stream, storage_key, content_type=content_type)
            playback_url = build_video_url(s3_metadata)
        except UploadError:
            current_app.logger.exception("Video upload failed for user %s", current_user.id)
            flash("Video upload failed. Please try again later.", "danger")
            return redirect(url_for("videos.upload_video"))

        vid = Video(
            title=form.title.data,
            description=form.description.data,
            is_remedial=form.is_remedial.data,
            video_file=playback_url,
            author=current_user,
            duration=-1,
        )
        db.session.add(vid)
        db.session.commit()
        current_app.logger.info('%s uploaded video titled %s', current_user.username, form.title.data)
        flash('Video upload complete', 'success')
        return redirect(url_for('main.about'))
    return render_template('upload_video.html', form=form,
                           title="Upload Video", legend='Upload Video')


@videos.route("/revise_video/<v_id>", methods=['GET', 'POST'])
@login_required
def revise_video(v_id):
    """Update the metadata flags for an existing video."""
    if current_user.uploadsvideo == 0:
        flash('account not authorized for video editing', 'info')
        return redirect(url_for('users.account'))
    form = PostVideoForm()
    if form.validate_on_submit():
        revision = Video.query.filter_by(id=v_id).first()
        revision.title = form.title.data
        revision.description = form.description.data
        revision.is_remedial = form.is_remedial.data
        db.session.commit()
        flash('Video Revision Submitted', 'success')
        return render_template('about.html')
    video = Video.query.get_or_404(v_id)
    form.title.data = video.title
    form.description.data = video.description
    form.is_remedial.data = video.is_remedial
    return render_template('revise_video.html', form=form, video=video)


@videos.route("/video/<int:video_id>/delete", methods=['POST', 'GET'])
@login_required
def delete_video(video_id):
    """Delete a video and its associated questions if authorized."""
    video = Video.query.get_or_404(video_id)
    if video.author != current_user and current_user.id != 1:
        abort(403)
    questions = Question.query.filter_by(associated_video=video).order_by(Question.pose_time)
    for question in questions:
        db.session.delete(question)
    db.session.delete(video)
    db.session.commit()
    flash('Your video has been deleted', 'success')
    return redirect(url_for('videos.course_video'))


@videos.route("/allvideos")
@login_required
def allvideos():
    """Show every video to support selecting one for question editing."""
    videos = Video.query.all()
    return render_template('allvideos.html', title='Add/Edit Questions', videos=videos)


@videos.route("/course_video")
@login_required
def course_video():
    """Paginate through all videos with their questions for admins."""
    if current_user.uploadsvideo == 0:
        flash('account not authorized for administrative activity: click to request administrative rights', 'info')
        return redirect(url_for('users.account'))
    page = request.args.get('page', 1, type=int)
    videos = Video.query.order_by(Video.id).paginate(page=page, per_page=3)
    questions = Question.query.order_by(Question.video_id).order_by(Question.pose_time)
    return render_template('course_video.html', videos=videos, questions=questions)


