from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, SelectField, PasswordField
from wtforms.validators import InputRequired


class DirectoryInputForm(FlaskForm):
    Input_Directory = StringField("输入含有DICOM文件的文件夹路径：", validators=[InputRequired(message=r'路径不能为空！')])
    Submit = SubmitField('提交')


class ShowSavedImage(FlaskForm):
    Select_KV = SelectField(r'球管电压', coerce=int)
    Select_Current = SelectField(r'球管电流', coerce=int)


class LoginForm(FlaskForm):
    username = StringField('Username')
    password = PasswordField('Password')
    Submit = SubmitField('提交')


