from flask import Blueprint, jsonify, render_template, request

from guidedtopic.extensions import db
from guidedtopic.models import Feedback, Post

main = Blueprint('main', __name__)


@main.route("/")
@main.route("/about")
def about():
    """Display the marketing overview for Guided Topic."""
    return render_template('about.html', title='About')


@main.route("/home", methods=['GET', 'POST'])
def home():
    """Render the home page with recent announcements."""
    page = request.args.get('page', 1, type=int)
    posts = Post.query.order_by(Post.date_posted.desc()).paginate(page=page, per_page=4)
    return render_template('home.html', posts=posts)


@main.route("/feedback", methods=["POST"])
def feedback():
    """Persist quick feedback submissions from the sidebar widget."""
    if request.method == "POST":
        data = request.get_json()
        fbt = data[0]['selectedType']
        cntnt = data[1]['content']
        fb = Feedback(feedback_type=fbt, content=cntnt)
        db.session.add(fb)
        db.session.commit()
    resp = jsonify(success=True)
    return resp
