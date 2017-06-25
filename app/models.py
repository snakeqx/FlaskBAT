from . import db


class ImageDatabase(db.Model):
    __tablename__ = 'dicoms'
    Uid = db.Column(db.Text, primary_key=True, nullable=False)
    Serial_number = db.Column(db.Integer, nullable=False)
    Modality = db.Column(db.Text, nullable=False)
    Tube_voltage = db.Column(db.Float, nullable=False)
    Tube_current = db.Column(db.Integer, nullable=False)
    Kernel = db.Column(db.Text, nullable=False)
    Total_collimation = db.Column(db.Float, nullable=False)
    Slice_Thickness = db.Column(db.Float, nullable=False)
    Instance = db.Column(db.Integer, nullable=False)
    Integration_result = db.Column(db.Text, nullable=False)
    Date_Time = db.Column(db.Text, nullable=False)
    Dicom_Save = db.Column(db.PickleType, nullable=False)
    Comment = db.Column(db.Text)

    def __repr__(self):
        return '<ImageDatabase %r>' % (str(self.Serial_number)+self.Date_Time)

