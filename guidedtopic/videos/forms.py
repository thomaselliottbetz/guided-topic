from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, FloatField, FileField, BooleanField
from wtforms.validators import DataRequired
from flask_wtf.file import FileAllowed, FileRequired


class PostVideoForm(FlaskForm):
    """Gather metadata and media for uploading instructional videos."""
    title = StringField('Title', validators=[DataRequired()])
    description = StringField('Description')
    video = FileField('Select Video', validators=[FileRequired(), FileAllowed(['mp4', 'mov', 'm4v'])])
    duration = FloatField('Duration')
    is_remedial = BooleanField('Is Remedial')
    submit = SubmitField('Upload')
