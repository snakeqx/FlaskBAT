from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import Required


class DirectoryInputForm(FlaskForm):
    Input_Directory = StringField("输入含有DICOM文件的文件夹路径：", validators=[Required()])
    Submit = SubmitField('提交')
