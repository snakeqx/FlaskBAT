from datetime import datetime
import logging
from flask import render_template, session, redirect, url_for, Response, request, send_file

from . import main
from .forms import DirectoryInputForm, ShowSavedImage, LoginForm
from .algorithm.DirectoryHandler import DirectoryHandler
from .algorithm.DicomHanlder import DicomHandler
from .algorithm.ImageHandler import ImageHandler
from .. import db
from ..models import ImageDatabase


@main.route('/', methods=['GET', 'POST'])
def index():
    KV_Choices = [(1, '80'), (2, '110'), (3, '130')]
    Current_Choices = [(1, '10'), (2, '130'), (3, '240')]
    form = ShowSavedImage()
    form.Select_Current.choices = KV_Choices
    form.Select_KV.choices = Current_Choices
    return render_template('index.html', form=form)


@main.route('/DicomInput', methods=['GET', 'POST'])
def dicom_input():
    output_log = ''
    progress = 0
    current_count = 1
    form = DirectoryInputForm()
    if form.validate_on_submit():
        directory_handler = DirectoryHandler(form.Input_Directory.data)
        output_log = directory_handler.Log_Record.copy()
        directory_handler.Log_Record.clear()

        for x in directory_handler.Dicom_File_Path:
            dicom = DicomHandler(x)
            if dicom.isComplete:
                image = ImageHandler(dicom)
                if image.isImageComplete:
                    int_result_string = ';'.join([str(x) for x in image.Image_Median_Filter_Result])
                    dicom_model = ImageDatabase(Uid=dicom.Uid,
                                                Serial_number=dicom.SerialNumber,
                                                Modality = dicom.Modality,
                                                Tube_voltage=dicom.KVP,
                                                Tube_current=dicom.Current,
                                                Kernel=dicom.Kernel,
                                                Total_collimation=dicom.TotalCollimation,
                                                Slice_Thickness=dicom.SliceThickness,
                                                Instance=dicom.Instance,
                                                Integration_result=int_result_string,
                                                Date_Time=dicom.DateTime,
                                                Dicom_Save=dicom)
                    db.session.add(dicom_model)
                    try:
                        db.session.commit()
                        output_log[current_count] += ('-->' + dicom.SerialNumber + ':' + dicom.ScanMode)
                    except Exception as e:
                        output_log[current_count] += ('-->' + dicom.SerialNumber + ':' +
                                                      dicom.ScanMode+"已经存在于数据库！")
                        db.session.rollback()
                        logging.error(str(e))

                    progress = current_count / directory_handler.Total_Dicom_Quantity * 100 + 1
                    current_count += 1
        directory_handler.Dicom_File_Path.clear()
    return render_template('DicomInput.html', form=form, output_log=output_log, progress=str(progress))

