from datetime import datetime
from flask import render_template, session, redirect, url_for

from . import main
from .forms import DirectoryInputForm
from .algorithm.DirectoryHandler import DirectoryHandler
from .. import db
from ..models import ImageDatabase


@main.route('/', methods=['GET', 'POST'])
def index():
    return render_template('index.html')


@main.route('/DicomInput', methods=['GET', 'POST'])
def dicom_input():
    output_log = ''
    form = DirectoryInputForm()
    if form.validate_on_submit():
        directory_handler = DirectoryHandler(form.Input_Directory.data)
        output_log = directory_handler.Log_Record.copy()
        directory_handler.Log_Record.clear()
    return render_template('DicomInput.html', form=form, output_log=output_log)

