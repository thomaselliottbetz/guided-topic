"""
Question and Answer management routes for educators.

Handles creation, editing, and deletion of branching questions that appear
during video playback. Questions can redirect learners to different videos
based on their answers.
"""
from flask import Blueprint, abort, current_app, flash, render_template, request
from flask_login import current_user, login_required

from guidedtopic.extensions import db
from guidedtopic.models import Question, Video
from guidedtopic.qna.forms import QandAForm


qna = Blueprint('qna', __name__)


# ============================================================================
# Helper Functions
# ============================================================================

def _parse_time_string_to_seconds(time_string):
    """
    Convert time string in HH:MM:SS format to total seconds.
    
    Args:
        time_string: Time string in format "HH:MM:SS" (e.g., "01:23:45")
    
    Returns:
        int: Total seconds
    
    Example:
        "01:23:45" -> 5025 seconds (1 hour + 23 minutes + 45 seconds)
    """
    # Extract hours, minutes, seconds from string
    # Format: "HH:MM:SS" where indices are [0:2], [3:5], [6:8]
    hours = int(time_string[:2])
    minutes = int(time_string[3:5])
    seconds = int(time_string[6:8])
    
    return seconds + (60 * minutes) + (60 * 60 * hours)


def _format_seconds_to_time_string(total_seconds):
    """
    Convert total seconds to time string in HH:MM:SS format.
    
    Args:
        total_seconds: Total number of seconds
    
    Returns:
        str: Time string in format "HH:MM:SS"
    
    Example:
        5025 seconds -> "01:23:45"
    """
    hours = int(total_seconds / 3600)
    minutes = int((total_seconds - hours * 3600) / 60)
    seconds = total_seconds - hours * 3600 - minutes * 60
    
    # Format with leading zeros
    hours_str = f"{hours:02d}"
    minutes_str = f"{minutes:02d}"
    seconds_str = f"{seconds:02d}"
    
    return f"{hours_str}:{minutes_str}:{seconds_str}"


# ============================================================================
# Question Management Routes
# ============================================================================

@qna.route("/question_editor/<v_id>", methods=['GET', 'POST'])
def question_editor(v_id):
    """
    Create a new question for the selected video at a specific time.
    
    Args:
        v_id: Video ID to create question for
    
    Flow:
        1. Validate user has educator permissions
        2. Load all videos for answer target selection
        3. On submit: Parse time string, create question with branching answers
        4. Each answer can redirect to a different video (targetvidA-E)
    
    Branching Logic:
        Questions have up to 5 answer choices (A-E), each with:
        - content: Answer text displayed to learner
        - targetvid: Video ID to redirect to if this answer is selected
        - If targetvid is 0 or None, continue with current video
    """
    # Authorization check: only educators can create questions
    if current_user.uploadsvideo == 0:
        abort(403)
    
    form = QandAForm()
    allvideos = Video.query.all()
    
    if form.validate_on_submit():
        # Parse time string (HH:MM:SS) to seconds for storage
        time_string = form.pose_time.raw_data[0]
        pose_time_seconds = _parse_time_string_to_seconds(time_string)
        
        # Create question with all answer choices and their target videos
        q = Question(
            content=form.question.data,
            video_id=v_id,
            pose_time=pose_time_seconds,
            contentA=form.answer1.data,
            targetvidA=form.answer1_target.data,
            contentB=form.answer2.data,
            targetvidB=form.answer2_target.data,
            contentC=form.answer3.data,
            targetvidC=form.answer3_target.data,
            contentD=form.answer4.data,
            targetvidD=form.answer4_target.data,
            contentE=form.answer5.data,
            targetvidE=form.answer5_target.data
        )
        
        db.session.add(q)
        db.session.commit()
        
        # Return to question list for this video
        video = Video.query.get_or_404(v_id)
        questions = Question.query.filter_by(associated_video=video).order_by(Question.pose_time)
        flash('Q&A addition complete', 'success')
        return render_template('showallquestions.html', questions=questions, video=video, videos=allvideos)
    
    # Pre-populate form with video choices for answer targets
    video = Video.query.get_or_404(v_id)
    all_vid_choices = [(v.id, v.title) for v in allvideos]
    form.answer1_target.choices = all_vid_choices
    form.answer2_target.choices = all_vid_choices
    form.answer3_target.choices = all_vid_choices
    form.answer4_target.choices = all_vid_choices
    form.answer5_target.choices = all_vid_choices
    
    return render_template(
        'question_editor.html',
        video=video,
        form=form,
        allvideos=allvideos,
        legend=f'Question Editor: {video.title}',
    )


@qna.route("/revise_question/<q_id>", methods=['GET', 'POST'])
def revise_question(q_id):
    """
    Edit an existing branching question for a given video.
    
    Args:
        q_id: Question ID to edit
    
    Allows editing all question fields including:
        - Question content
        - Pose time (when question appears in video)
        - Answer choices and their target videos
    """
    form = QandAForm()
    allvideos = Video.query.all()
    
    if form.validate_on_submit():
        # Update question record
        record = Question.query.filter_by(id=q_id).first()
        record.content = form.question.data
        
        # Parse and update pose time
        time_string = form.pose_time.raw_data[0]
        pose_time_seconds = _parse_time_string_to_seconds(time_string)
        record.pose_time = pose_time_seconds
        
        # Update all answer choices and targets
        record.contentA = form.answer1.data
        record.targetvidA = form.answer1_target.data
        record.contentB = form.answer2.data
        record.targetvidB = form.answer2_target.data
        record.contentC = form.answer3.data
        record.targetvidC = form.answer3_target.data
        record.contentD = form.answer4.data
        record.targetvidD = form.answer4_target.data
        record.contentE = form.answer5.data
        record.targetvidE = form.answer5_target.data
        
        db.session.commit()
        flash('Q & A revision completed', 'success')
        
        # Return to course video admin view
        page = request.args.get('page', 1, type=int)
        vids = Video.query.order_by(Video.id).paginate(page=page, per_page=3)
        qs = Question.query.order_by(Question.video_id).order_by(Question.pose_time)
        return render_template('course_video.html', videos=vids, questions=qs)
    
    # Handle validation errors
    if request.method == 'POST':
        flash('Failed Validation')
        time_string = form.pose_time.raw_data[0]
        pose_time_seconds = _parse_time_string_to_seconds(time_string)
    
    # Load existing question and pre-populate form
    question = Question.query.get_or_404(q_id)
    video = question.associated_video
    
    # Set video choices for answer targets
    all_vid_choices = [(v.id, v.title) for v in allvideos]
    form.answer1_target.choices = all_vid_choices
    form.answer2_target.choices = all_vid_choices
    form.answer3_target.choices = all_vid_choices
    form.answer4_target.choices = all_vid_choices
    form.answer5_target.choices = all_vid_choices
    
    # Pre-populate form fields with existing question data
    form.question.data = question.content
    
    # Convert pose_time (seconds) back to HH:MM:SS format for display
    pose_time_string = _format_seconds_to_time_string(question.pose_time)
    
    form.answer1.data = question.contentA
    form.answer1_target.data = question.targetvidA
    form.answer2.data = question.contentB
    form.answer2_target.data = question.targetvidB
    form.answer3.data = question.contentC
    form.answer3_target.data = question.targetvidC
    form.answer4.data = question.contentD
    form.answer4_target.data = question.targetvidD
    form.answer5.data = question.contentE
    form.answer5_target.data = question.targetvidE
    
    return render_template(
        'question_editor.html',
        q_id=q_id,
        video=video,
        form=form,
        allvideos=allvideos,
        legend=f'Revise question for video titled "{video.title}"',
        pose_time_hint=pose_time_string,
    )


@qna.route("/showallquestions/<v_id>")
def showallquestions(v_id):
    """
    List all questions associated with a video for quick review.
    
    Args:
        v_id: Video ID
    
    Shows all questions for the video ordered by pose_time (when they appear).
    Used by educators to review and manage questions for a specific video.
    """
    # Authorization check
    if current_user.uploadsvideo == 0:
        abort(403)
    
    video = Video.query.get_or_404(v_id)
    videos = Video.query.all()
    blank = 'blank'  # Used in template for display logic
    questions = Question.query.filter_by(associated_video=video).order_by(Question.pose_time)
    return render_template('showallquestions.html', questions=questions, video=video, videos=videos, blank=blank)


@qna.route("/question/<int:q_id>/delete/", methods=['GET', 'POST'])
@login_required
def delete_question(q_id):
    """
    Remove a question and refresh the authoring dashboard.
    
    Args:
        q_id: Question ID to delete
    
    After deletion, returns to the question list for the video.
    """
    # Authorization check
    if current_user.uploadsvideo == 0:
        abort(403)
    
    v_id = request.args.get('v_id')
    question = Question.query.get_or_404(q_id)
    
    db.session.delete(question)
    db.session.commit()
    
    # Return to question list for the video
    video = Video.query.get_or_404(v_id)
    videos = Video.query.all()
    questions = Question.query.filter_by(associated_video=video).order_by(Question.pose_time)
    flash('Question has been deleted', 'success')
    return render_template('showallquestions.html', questions=questions, video=video, videos=videos)
