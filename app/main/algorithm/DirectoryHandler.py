#!coding=utf8
import logging
import os
import dicom


class DirectoryHandler:
    """
    The class will iterate the input directory to find target database file.
    And store each found file full path in a list of string "Database_File_Path"
    """
    Dicom_File_Path = []
    Log_Record = []
    Directory_Iterate = 1
    Tree_indicator = "|---"

    def __init__(self, input_directory):
        """
        :param input_directory:
        """
        if input_directory is not None:
            if os.path.isdir(input_directory):
                self.Log_Record.append(r"输入参数为文件夹（正确）")
            else:
                self.Log_Record.append(r"输入参数不是文件夹，请再次检查！")
                return
        absolute_path = os.path.abspath(input_directory)
        self.list_files(absolute_path)

    def list_files(self, input_directory):
        """
        :param input_directory:
        :return: no return. Directly write all target files found in Database_File_Path
        """
        dir_list = os.listdir(input_directory)
        for dl in dir_list:
            full_dl = os.path.join(input_directory, dl)
            if os.path.isfile(full_dl):
                try:
                    # try to open the dicom file.
                    dicom.read_file(full_dl)
                    self.Dicom_File_Path.append(full_dl)
                    self.Log_Record.append(self.Directory_Iterate*self.Tree_indicator + str(dl))
                except Exception as e:
                    # if it is not a dicom file, skip saving to Dicom_File_Path
                    self.Log_Record.append(self.Directory_Iterate*self.Tree_indicator + str(dl) + r"不是DICOM文件！")
            else:
                self.Log_Record.append(self.Directory_Iterate*self.Tree_indicator + str(dl) + r"\\")
                self.Directory_Iterate += 1
                self.list_files(full_dl)
        self.Directory_Iterate -= 1


if __name__ == '__main__':
    print("please do not use it individually unless of debugging.")
