from flask_wtf import FlaskForm
from wtforms import SubmitField, TextAreaField, SelectField, TimeField, IntegerField, StringField


class QandAForm(FlaskForm):
    """Author or edit a timed branching question for a video."""
    question = TextAreaField('Question Content:')
    # pose_time = SelectField(u'Question pose time:', validate_choice=False, coerce=int)
    pose_time = StringField(u'Question pose time:')
    # pose_time = TimeField(u'Question pose time:', format='%H:%M:%S')

    answer1 = TextAreaField('Question Response A:')
    answer1_target = SelectField('Response A Associated Video:', id='answer1_target', coerce=int, validate_choice=False)
    answer2 = TextAreaField('Question Response B:')
    answer2_target = SelectField('Response B Associated Video:', id='answer2_target', coerce=int, validate_choice=False)
    answer3 = TextAreaField('Question Response C:')
    answer3_target = SelectField('Response C Associated Video:', id='answer3_target', coerce=int, validate_choice=False)
    answer4 = TextAreaField('Question Response D:')
    answer4_target = SelectField('Response D Associated Video:', id='answer4_target', coerce=int, validate_choice=False)
    answer5 = TextAreaField('Question Response E:')
    answer5_target = SelectField('Response E Associated Video:', id='answer5_target', coerce=int, validate_choice=False)
    submit = SubmitField('Submit')
