from flask import Blueprint, abort, current_app, flash, render_template, request
from flask_login import current_user, login_required

from guidedtopic.extensions import db
from guidedtopic.models import Question, Video
from guidedtopic.qna.forms import QandAForm


qna = Blueprint('qna', __name__)


@qna.route("/question_editor/<v_id>", methods=['GET', 'POST'])
def question_editor(v_id):
    """Create a new question for the selected video at a specific time."""
    if current_user.uploadsvideo == 0:
        abort(403)
    form = QandAForm()
    allvideos = Video.query.all()
    if form.validate_on_submit():
        rd = form.pose_time.raw_data[0]
        secs = int(rd[6:]) + 60 * int(rd[3:5]) + 60 * 60 * int(rd[:2])
        q = Question(content=form.question.data, video_id=v_id, pose_time=secs,
                     contentA=form.answer1.data, targetvidA=form.answer1_target.data,
                     contentB=form.answer2.data, targetvidB=form.answer2_target.data,
                     contentC=form.answer3.data, targetvidC=form.answer3_target.data,
                     contentD=form.answer4.data, targetvidD=form.answer4_target.data,
                     contentE=form.answer5.data, targetvidE=form.answer5_target.data)
        db.session.add(q)
        db.session.commit()
        video = Video.query.get_or_404(v_id)
        questions = Question.query.filter_by(associated_video=video).order_by(Question.pose_time)
        flash('Q&A addition complete', 'success')
        return render_template('showallquestions.html', questions=questions, video=video, videos=allvideos)
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
    """Edit an existing branching question for a given video."""
    form = QandAForm()
    allvideos = Video.query.all()
    if form.validate_on_submit():
        record = Question.query.filter_by(id=q_id).first()
        record.content = form.question.data
        rd = form.pose_time.raw_data[0]
        secs = int(rd[6:]) + 60 * int(rd[3:5]) + 60 * 60 * int(rd[:2])
        record.pose_time = secs
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
        page = request.args.get('page', 1, type=int)
        vids = Video.query.order_by(Video.id).paginate(page=page, per_page=3)
        qs = Question.query.order_by(Question.video_id).order_by(Question.pose_time)
        return render_template('course_video.html', videos=vids, questions=qs)
    if request.method == 'POST':
        flash('Failed Validation')
        rd = form.pose_time.raw_data[0]
        secs = int(rd[6:]) + 60 * int(rd[3:5]) + 60 * 60 * int(rd[:2])
    question = Question.query.get_or_404(q_id)
    video = question.associated_video
    all_vid_choices = [(v.id, v.title) for v in allvideos]
    form.answer1_target.choices = all_vid_choices
    form.answer2_target.choices = all_vid_choices
    form.answer3_target.choices = all_vid_choices
    form.answer4_target.choices = all_vid_choices
    form.answer5_target.choices = all_vid_choices
    form.question.data = question.content
    cpt = question.pose_time
    hrs = int(cpt / 3600)
    shrs = "0" + str(hrs)
    mins = int((cpt - hrs * 3600) / 60)
    smin = str(mins) if mins > 9 else "0" + str(mins)
    secs = cpt - hrs * 3600 - mins * 60
    ssecs = str(secs) if secs > 9 else "0" + str(secs)
    ts = shrs + ":" + smin + ":" + ssecs
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
        pose_time_hint=ts,
    )


@qna.route("/showallquestions/<v_id>")
def showallquestions(v_id):
    """List all questions associated with a video for quick review."""
    if current_user.uploadsvideo == 0:
        abort(403)
    video = Video.query.get_or_404(v_id)
    videos = Video.query.all()
    blank = 'blank'
    questions = Question.query.filter_by(associated_video=video).order_by(Question.pose_time)
    return render_template('showallquestions.html', questions=questions, video=video, videos=videos, blank=blank)


@qna.route("/question/<int:q_id>/delete/", methods=['GET', 'POST'])
@login_required
def delete_question(q_id):
    """Remove a question and refresh the authoring dashboard."""
    if current_user.uploadsvideo == 0:
        abort(403)
    v_id = request.args.get('v_id')
    question = Question.query.get_or_404(q_id)
    db.session.delete(question)
    db.session.commit()
    video = Video.query.get_or_404(v_id)
    videos = Video.query.all()
    questions = Question.query.filter_by(associated_video=video).order_by(Question.pose_time)
    flash('Question has been deleted', 'success')
    return render_template('showallquestions.html', questions=questions, video=video, videos=videos)
