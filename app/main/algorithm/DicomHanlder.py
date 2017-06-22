import dicom
import numpy as np
from PIL import Image
from PIL import ImageDraw
from PIL import ImageFilter
import matplotlib.pyplot as plt
import logging


class DicomHandler:

    """
    This is the main class to deal with single dicom image.
    And it will calculate the circular integration of the image.
    Finally the low pass the integration to get a feeling that how the image quality is.
    Function description:
    __imi__: to initialize Dicom file and call other functions to calculate circular integration
    calc_circle: to find the phantom center and find the radius. Normally it has 2 kinds of phantom,
                 20cm and 30cm (diameter)
    bresenham: draw a circle on the image with a radius. return the sum of the points that on the edge of the circle
    integration: this function do 2 parts:
        part 1: call bresenham with different radius (from 1 to phantom radius). And then calculate the
                integration. The integration must be weighted average number because when radius is bigger,
                the number of points is bigger
        part 2: low pass the integration result to more visible.
    """

    def __init__(self, filename, center=0, width=100):
        # set up some basic date
        self.isShowImgReady = False
        self.Center_Col = 256
        self.Center_Row = 256
        self.Radius = 200
        self.Dicom_File_Name = filename
        # open the dicom file
        logging.debug(r"Opening file:" + filename)

        # Initial Dicom data
        try:
            self.Dicom_File = dicom.read_file(filename)
            self.Dicom_Station_Name = self.Dicom_File[0x0018, 0x1000].value
            logging.debug(str(self.Dicom_Station_Name) + r"<==System Serial No")
            self.Dicom_StudyDescription = self.Dicom_File[0x0008, 0x1030].value
            if self.Dicom_StudyDescription != r"Band Assessment":
                logging.error(self.Dicom_File_Name + " is not Band Assessment")
                logging.debug(self.Dicom_File_Name + ":" + self.Dicom_StudyDescription + r"<==Study Description is:")
                return
            self.Dicom_Slop = self.Dicom_File[0x0028, 0x1053].value
            self.Dicom_Intercept = self.Dicom_File[0x0028, 0x1052].value
            self.Image_Data_Raw = np.array(self.Dicom_File.pixel_array)
            self.Dicom_Rows = self.Dicom_File[0x0028, 0x0010].value
            self.Dicom_Cols = self.Dicom_File[0x0028, 0x0011].value
            self.Dicom_Pix_Space = self.Dicom_File[0x0028, 0x0030].value
            self.Dicom_KVP = self.Dicom_File[0x0018, 0x0060].value
            self.Dicom_Current = self.Dicom_File[0x0018, 0x1151].value
            self.Dicom_Kernel = self.Dicom_File[0x0018, 0x1210].value
            self.Dicom_Series = self.Dicom_File[0x0020, 0x0011].value
            self.Dicom_Total_Collimation = self.Dicom_File[0x0018, 0x9307].value
            self.Dicom_Slice_Thickness = self.Dicom_File[0x0018, 0x0050].value
            self.Dicom_Instance = self.Dicom_File[0x0020, 0x0013].value
            self.Dicom_Mode = r"{0}KV_{1}mA_{2}_{3}I{4}.{5}".format(str(self.Dicom_KVP),
                                                                    str(self.Dicom_Current),
                                                                    str(self.Dicom_Kernel),
                                                                    str(self.Dicom_Total_Collimation),
                                                                    str(self.Dicom_Slice_Thickness),
                                                                    str(self.Dicom_Instance))
            logging.debug(r"Image Mode: " + self.Dicom_Mode)
            self.Dicom_Pix_Space = self.Dicom_File[0x0028, 0x0030].value
            self.Dicom_Date = self.Dicom_File[0x0008, 0x002a].value
        except Exception as e:
            logging.error(e)
            return

        # Initial Image data
        # Do the initial calculation
        self.Image_HU = self.Image_Data_Raw * self.Dicom_Slop + self.Dicom_Intercept  # Convert to HU unit
        self.Dicom_Window_Upper = center + width / 2
        self.Dicom_Window_Lower = center - width / 2
        # make filter according to center and width
        upper_filter = self.Image_HU > self.Dicom_Window_Upper
        self.Image_HU[upper_filter] = self.Dicom_Window_Upper  # set upper value
        lower_filter = self.Image_HU < self.Dicom_Window_Lower
        self.Image_HU[lower_filter] = self.Dicom_Window_Lower  # set lower value
        # rescale the data to 0~255
        min_hu_image = self.Image_HU.min()
        self.Image_rescale = self.Image_HU + (0 - min_hu_image)  # get rid of minus number
        max_image_rescale = self.Image_rescale.max()
        self.Image_rescale = self.Image_rescale * 255 / max_image_rescale  # rescale the image to fit 0~255
        # try to calculate radius and center col / row
        self.calc_circle(self.Image_HU.copy())
        # define circular integration result
        self.Image_Integration_Result = np.zeros(self.Radius)
        self.Image_Median_Filter_Result = np.zeros(self.Radius)
        # main calculation
        self.integration()
        self.isShowImgReady = True

    def calc_circle(self, dicom_pixel_data):
        # remove the pixel if the pixel is low
        remove_rate = 1.2  # define rate
        remove_low_value = dicom_pixel_data < self.Dicom_Window_Upper / remove_rate  # set up the filter
        dicom_pixel_data[remove_low_value] = 0  # remove the low values
        # convert the np array to image, then use PIL to find image edge
        im = Image.fromarray(dicom_pixel_data).convert("L").filter(ImageFilter.FIND_EDGES)
        # convert image back to np array
        filtered_image = np.array(im)
        # use filtered image to re-calculate center and radius
        # the method is simple
        # from up/down/left/right side to go into center
        # the 1st number is > mean value, it's the edge
        # calculate the distance from th edge to center
        abnormal = False  # set up the flag to store if calculation is abnormal
        left_distance = 0
        right_distance = 0
        up_distance = 0
        low_distance = 0

        # start to calculate center col
        for left_distance in range(1, im.size[1]):
            if filtered_image[self.Center_Row, left_distance] != 0:
                break
        for right_distance in range(1, im.size[1]):
            if filtered_image[self.Center_Row, im.size[1] - right_distance] != 0:
                break
        self.Center_Col += (left_distance - right_distance) // 2
        logging.debug(r"Center Col calculated as: " + str(self.Center_Col))
        # if the calculated center col deviated too much
        deviation = 20
        if (self.Center_Col > self.Dicom_Cols // 2 + deviation) or (self.Center_Col < self.Dicom_Cols // 2 - deviation):
            logging.warning(r"It seems abnormal when calculate Center Col, use image center now!")
            self.Center_Col = self.Dicom_Cols // 2
            abnormal = True

        # start to calculate center row
        for up_distance in range(1, im.size[0]):
            if filtered_image[up_distance, self.Center_Col] != 0:
                break
        for low_distance in range(1, im.size[1]):
            if filtered_image[im.size[1] - low_distance, self.Center_Col] != 0:
                break
        self.Center_Row += (up_distance - low_distance) // 2
        logging.debug(r"Center Row calculated as: " + str(self.Center_Row))
        # if the calculated center row deviated too much
        if (self.Center_Row > self.Dicom_Rows // 2 + deviation) or (self.Center_Row < self.Dicom_Rows // 2 - deviation):
            logging.warning(r"It seems abnormal when calculate Center row, use image center now!")
            self.Center_Row = self.Dicom_Rows // 2
            abnormal = True

        # set different radius according to normal/abnormal situation
        if abnormal is False:
            self.Radius = (im.size[0] - left_distance - right_distance) // 2
            diameter_in_cm = self.Radius * self.Dicom_Pix_Space[0] * 2
            logging.debug(str(self.Radius) + r"pix (radius), " + str(diameter_in_cm) +
                          r"cm(diameter)<==Calculated phantom diameter")
            # standardize the radius
            if diameter_in_cm < 250:
                self.Radius = 233
                logging.debug(str(self.Radius) + r"pix" + r", which is: " +
                              str(self.Radius * self.Dicom_Pix_Space[0] * 2) + r"cm <=========Radius Readjusted")
            else:
                self.Radius = 220
                logging.debug(str(self.Radius) + r"pix" + r", which is: " +
                              str(self.Radius * self.Dicom_Pix_Space[0] * 2) + r"cm <=========Radius Readjusted")
        else:
            logging.warning(r"Calculated center is abnormal, use 50 as radius!")
            self.Radius = 50

    def bresenham(self, radius):
        x = 0
        y = radius
        d = 3 - 2 * radius
        while x < y:
            self.Image_Integration_Result[radius] = self.Image_Integration_Result[radius] + self.Image_HU[
                self.Center_Row - y, self.Center_Col + x]
            self.Image_Integration_Result[radius] = self.Image_Integration_Result[radius] + self.Image_HU[
                self.Center_Row + y, self.Center_Col + x]
            self.Image_Integration_Result[radius] = self.Image_Integration_Result[radius] + self.Image_HU[
                self.Center_Row - y, self.Center_Col - x]
            self.Image_Integration_Result[radius] = self.Image_Integration_Result[radius] + self.Image_HU[
                self.Center_Row + y, self.Center_Col - x]
            self.Image_Integration_Result[radius] = self.Image_Integration_Result[radius] + self.Image_HU[
                self.Center_Row - x, self.Center_Col + y]
            self.Image_Integration_Result[radius] = self.Image_Integration_Result[radius] + self.Image_HU[
                self.Center_Row - x, self.Center_Col - y]
            self.Image_Integration_Result[radius] = self.Image_Integration_Result[radius] + self.Image_HU[
                self.Center_Row + x, self.Center_Col + y]
            self.Image_Integration_Result[radius] = self.Image_Integration_Result[radius] + self.Image_HU[
                self.Center_Row + x, self.Center_Col - y]
            if d < 0:
                d = d + 4 * x + 6
            else:
                d = d + 4 * (x - y) + 10
                y -= 1
            x += 1

    def integration(self):
        for index in range(1, len(self.Image_Integration_Result)):
            self.bresenham(index)
            self.Image_Integration_Result[index] /= (index * 2 * 3.14)
        # calculate data by using Median
        factor = 3
        # the 1st and 2nd data = factor * md3() - md5()
        self.Image_Median_Filter_Result[0] = np.median(self.Image_Integration_Result[:3]) * factor - np.median(
            self.Image_Integration_Result[:5])
        self.Image_Median_Filter_Result[1] = np.median(self.Image_Integration_Result[:3]) * factor - np.median(
            self.Image_Integration_Result[:5])

        # the last and 2nd last data = factor * md3() - md5()
        self.Image_Median_Filter_Result[-1] = np.median(self.Image_Integration_Result[-3:]) * factor - np.median(
            self.Image_Integration_Result[-5:])
        self.Image_Median_Filter_Result[-2] = np.median(self.Image_Integration_Result[-3:]) * factor - np.median(
            self.Image_Integration_Result[-5:])
        for index in range(3, len(self.Image_Integration_Result) - 2):
            self.Image_Median_Filter_Result[index] = np.median(self.Image_Integration_Result[index - 3:index + 3])

    def show_image(self):
        if self.isShowImgReady:
            # set up the output file name
            image__filename = self.Dicom_Mode + ".jpeg"
            image__filename__fig = self.Dicom_Mode + "_fig.jpeg"
            im = Image.fromarray(self.Image_rescale).convert("L")
            # prepare to drawing the image
            draw_surface = ImageDraw.Draw(im)
            point = self.Radius
            # draw the radius circle
            bounding_box = (self.Center_Col - point, self.Center_Row - point,
                            self.Center_Col + point, self.Center_Row + point)
            draw_surface.ellipse(bounding_box)
            # save image
            try:
                # save image
                im.save(self.Dicom_File_Name + image__filename, "png")
                # draw fig
                plt.plot(self.Image_Median_Filter_Result)
                plt.ylim((-5, 20))
                plt.xlim((0, 250))
                # draw fig image
                plt.savefig(self.Dicom_File_Name + image__filename__fig)
            except Exception as e:
                logging.error(str(e))
                return
            finally:
                plt.close()
        else:  # if self.isShowImgReady == False
            logging.warning(r"File is not complete initialized, skip show image.")
            return


if __name__ == '__main__':
    print("please do not use it individually unless of debugging.")
    # below codes for debug
    # define the logging config, output in file
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s',
                        datefmt='%a, %d %b %Y %H:%M:%S',
                        filename=r'./log/DirectoryHandler.log',
                        filemode='w')
    # define a stream that will show log level > Warning on screen also
    console = logging.StreamHandler()
    console.setLevel(logging.WARNING)
    formatter = logging.Formatter('%(levelname)-8s %(message)s')
    console.setFormatter(formatter)
    logging.getLogger('').addHandler(console)

    a = DicomHandler(r"./test/CS108041.CT.Band_Assessment.102.1.2016.12.08.16.26.58.415.17016262.dcm")
    a.show_image()
