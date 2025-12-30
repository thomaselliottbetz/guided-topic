"""
Video management routes for educators and learners.

Routes are organized by functionality:
- Public/Viewing: Routes for viewing videos (learners)
- Upload: Routes for uploading videos (educators)
- Edit: Routes for editing/deleting videos (educators)
- Admin: Routes for administrative video management
"""
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


# ============================================================================
# Public/Viewing Routes (Learners)
# ============================================================================

@videos.route("/video", methods=['GET', 'POST'])
def video():
    """
    Render the sample video player page.
    
    Displays a sample video if WELCOME_VIDEO_URL is configured.
    Used for demonstration purposes.
    """
    return render_template('video.html')


@videos.route("/select_video")
@login_required
def select_video():
    """
    List non-remedial videos for learners to choose from.
    
    Shows paginated list of primary instructional videos.
    Remedial videos are shown separately via remedialvideos route.
    """
    page = request.args.get('page', 1, type=int)
    videos = Video.query.filter_by(is_remedial=False).order_by(Video.id).paginate(page=page, per_page=3)
    return render_template('selectvideo.html', title='Select Video', videos=videos)


@videos.route("/remedialvideos")
@login_required
def remedialvideos():
    """
    Display the set of remedial videos available to learners.
    
    Remedial videos are shown when learners answer questions incorrectly
    and need additional instruction before continuing.
    """
    page = request.args.get('page', 1, type=int)
    videos = Video.query.filter_by(is_remedial=1).order_by(Video.id).paginate(page=page, per_page=3)
    return render_template('remedialvideos.html', title='Remedial Videos', videos=videos)


@videos.route("/study_video/<v_id>")
@login_required
def study_video(v_id):
    """
    Serve the learner playback page with questions for a video.
    
    Args:
        v_id: Video ID
    
    Features:
        - Displays video with embedded questions
        - Tracks view count
        - Questions are ordered by pose_time (when they appear in video)
    """
    video = Video.query.get_or_404(v_id)
    questions = Question.query.filter_by(associated_video=video).order_by(Question.pose_time)
    
    # Increment view counter
    views = video.total_views + 1
    video.total_views = views
    db.session.add(video)
    db.session.commit()
    
    current_app.logger.info('%s accessing study_video route w/ v_id %s', current_user.username, v_id)
    return render_template('study_video.html', video=video, questions=questions, 
                          rp=current_app.root_path, views=views)


@videos.route("/getvideopath/<v_id>", methods=['GET', 'POST'])
@login_required
def getvideopath(v_id):
    """
    Return the stored playback URL for the requested video.
    
    Args:
        v_id: Video ID
    
    Returns:
        str: S3 URL or streaming URL for the video file
    
    Used by frontend JavaScript to fetch video URLs dynamically.
    """
    video = Video.query.filter_by(id=v_id).first()
    return video.video_file


# ============================================================================
# Upload Routes (Educators)
# ============================================================================

@videos.route("/upload_video", methods=['GET', 'POST'])
@login_required
def upload_video():
    """
    Handle educator uploads and store the source in S3.
    
    Upload Flow:
        1. Check user has upload permissions
        2. Validate file exists and has valid name
        3. Validate file extension against whitelist
        4. Generate unique storage key (user-scoped)
        5. Upload to S3 with proper content type
        6. Create Video record with S3 URL
        7. Store metadata in database
    
    Security:
        - Filename sanitization prevents path traversal
        - Extension whitelist prevents malicious file uploads
        - User-scoped storage keys prevent collisions
        - File size limits enforced by MAX_CONTENT_LENGTH config
    """
    # Authorization check: only users with uploadsvideo flag can upload
    if current_user.uploadsvideo == 0:
        flash('account not authorized for video upload: click to request video upload permission', 'info')
        return redirect(url_for('users.account'))
    
    form = PostVideoForm()
    if form.validate_on_submit():
        # Step 1: Validate file was uploaded
        file_storage = request.files.get("video")
        if not file_storage or not file_storage.filename:
            flash("Please choose a video file to upload.", "warning")
            return redirect(url_for("videos.upload_video"))
        
        # Step 2: Sanitize filename to prevent path traversal attacks
        original_name = secure_filename(file_storage.filename)
        if not original_name:
            flash("Invalid file name.", "danger")
            return redirect(url_for("videos.upload_video"))
        
        # Step 3: Validate file extension against whitelist
        extension = Path(original_name).suffix.lower().lstrip(".")
        allowed_extensions = current_app.config.get("UPLOAD_ALLOWED_EXTENSIONS", set())
        if extension not in allowed_extensions:
            flash(
                f"Unsupported file type '.{extension}'. Allowed types: {', '.join(sorted(allowed_extensions))}.",
                "danger",
            )
            return redirect(url_for("videos.upload_video"))
        
        # Step 4: Generate unique storage key (user-scoped to prevent collisions)
        # Format: uploads/{user_id}/{uuid}.{ext}
        storage_key = f"uploads/{current_user.id}/{uuid4().hex}{Path(original_name).suffix.lower()}"
        content_type = mimetypes.guess_type(original_name)[0] or "application/octet-stream"
        
        # Step 5: Prepare file stream for upload
        file_stream = file_storage.stream
        file_stream.seek(0)
        
        # Step 6: Upload to S3 and get playback URL
        try:
            s3_metadata = upload_video_to_s3(file_stream, storage_key, content_type=content_type)
            playback_url = build_video_url(s3_metadata)
        except UploadError:
            current_app.logger.exception("Video upload failed for user %s", current_user.id)
            flash("Video upload failed. Please try again later.", "danger")
            return redirect(url_for("videos.upload_video"))
        
        # Step 7: Create Video record in database
        vid = Video(
            title=form.title.data,
            description=form.description.data,
            is_remedial=form.is_remedial.data,
            video_file=playback_url,  # Store S3 URL, not local path
            author=current_user,
            duration=-1,  # Duration not calculated on upload
        )
        db.session.add(vid)
        db.session.commit()
        
        current_app.logger.info('%s uploaded video titled %s', current_user.username, form.title.data)
        flash('Video upload complete', 'success')
        return redirect(url_for('main.about'))
    
    return render_template('upload_video.html', form=form,
                           title="Upload Video", legend='Upload Video')


# ============================================================================
# Edit Routes (Educators)
# ============================================================================

@videos.route("/revise_video/<v_id>", methods=['GET', 'POST'])
@login_required
def revise_video(v_id):
    """
    Update the metadata flags for an existing video.
    
    Args:
        v_id: Video ID to revise
    
    Allows editing:
        - Title
        - Description
        - Remedial flag
    
    Note: Video file itself cannot be changed (would require new upload).
    """
    # Authorization check
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
    
    # Pre-populate form with existing video data
    video = Video.query.get_or_404(v_id)
    form.title.data = video.title
    form.description.data = video.description
    form.is_remedial.data = video.is_remedial
    return render_template('revise_video.html', form=form, video=video)


@videos.route("/video/<int:video_id>/delete", methods=['POST', 'GET'])
@login_required
def delete_video(video_id):
    """
    Delete a video and its associated questions if authorized.
    
    Args:
        video_id: Video ID to delete
    
    Authorization:
        - Video author can delete their own videos
        - User with ID 1 (admin) can delete any video
    
    Cascading:
        - All questions associated with the video are also deleted
    """
    video = Video.query.get_or_404(video_id)
    
    # Authorization check: only author or admin (user ID 1) can delete
    if video.author != current_user and current_user.id != 1:
        abort(403)
    
    # Delete all associated questions first (cascade delete)
    questions = Question.query.filter_by(associated_video=video).order_by(Question.pose_time)
    for question in questions:
        db.session.delete(question)
    
    # Delete video
    db.session.delete(video)
    db.session.commit()
    
    flash('Your video has been deleted', 'success')
    return redirect(url_for('videos.course_video'))


# ============================================================================
# Admin Routes
# ============================================================================

@videos.route("/allvideos")
@login_required
def allvideos():
    """
    Show every video to support selecting one for question editing.
    
    Used by educators to select a video when creating/editing questions.
    All videos are shown regardless of remedial flag.
    """
    videos = Video.query.all()
    return render_template('allvideos.html', title='Add/Edit Questions', videos=videos)


@videos.route("/course_video")
@login_required
def course_video():
    """
    Paginate through all videos with their questions for admins.
    
    Administrative dashboard showing all videos and their associated questions.
    Used for content management and review.
    
    Authorization:
        - Requires uploadsvideo flag (educator/admin access)
    """
    # Authorization check
    if current_user.uploadsvideo == 0:
        flash('account not authorized for administrative activity: click to request administrative rights', 'info')
        return redirect(url_for('users.account'))
    
    page = request.args.get('page', 1, type=int)
    videos = Video.query.order_by(Video.id).paginate(page=page, per_page=3)
    questions = Question.query.order_by(Question.video_id).order_by(Question.pose_time)
    return render_template('course_video.html', videos=videos, questions=questions)
