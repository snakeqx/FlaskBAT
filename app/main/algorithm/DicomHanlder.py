import dicom
import numpy as np
import logging


class DicomHandler:
    def __init__(self, filename):
        self.isComplete = False
        self.FileName = filename

        try:
            self.Data = dicom.read_file(self.FileName)

            # system related
            self.SerialNumber = self.Data[0x0018, 0x1000].value
            self.Modality = self.Data[0x0008, 0x1090].value

            # Image related
            self.Slop = self.Data[0x0028, 0x1053].value
            self.Intercept = self.Data[0x0028, 0x1052].value
            self.Rows = self.Data[0x0028, 0x0010].value
            self.Cols = self.Data[0x0028, 0x0011].value
            self.PixSpace = self.Data[0x0028, 0x0030].value
            self.Instance = self.Data[0x0020, 0x0013].value
            self.PixSpace = self.Data[0x0028, 0x0030].value
            self.StudyDescription = self.Data[0x0008, 0x1030].value
            if self.StudyDescription != r"Band Assessment":
                logging.warning(self.FileName + " is not Band Assessment. It is: " + self.FileName)
                return

            # Recon related
            self.WindowCenter = self.Data[0x0028, 0x1050].value
            self.WindowWidth = self.Data[0x0028, 0x1051].value
            self.FOV = self.Data[0x0018, 0x1100].value
            self.RawData = np.array(self.Data.pixel_array)

            # Scan related
            self.KVP = self.Data[0x0018, 0x0060].value
            self.Current = self.Data[0x0018, 0x1151].value
            self.Kernel = self.Data[0x0018, 0x1210].value
            self.Series = self.Data[0x0020, 0x0011].value
            self.TotalCollimation = self.Data[0x0018, 0x9307].value
            self.SliceThickness = self.Data[0x0018, 0x0050].value
            self.DateTime = self.Data[0x0008, 0x002a].value
            self.ScanMode = r"{0}kV_{1}mA_{2}_{3}P{4}.{5}". \
                format(str(self.KVP),
                       str(self.Current),
                       str(self.Kernel),
                       str(self.TotalCollimation),
                       str(self.SliceThickness),
                       str(self.Instance))

            # Extra
            self.Uid = str(self.SerialNumber)+str(self.DateTime)+str(self.Instance)
        except Exception as e:
            logging.error("Dicom data parse error:" + str(e))
            return

        self.isComplete = True


if __name__ == '__main__':
    print("please do not use it individually unless of debugging.")

    a = DicomHandler(r"../../../tests/a.dcm")
    print(a.isComplete)
