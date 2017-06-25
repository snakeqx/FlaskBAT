import dicom
import numpy as np
from PIL import Image
from PIL import ImageDraw
from PIL import ImageFilter
import matplotlib.pyplot as plt
import logging

from .DicomHanlder import DicomHandler
# from DicomHanlder import DicomHandler


class ImageHandler:
    def __init__(self, dcm: DicomHandler):
        self.isImageComplete = False
        self.RescaleType = {'linear', 'logarithm'}
        self.Dicom = dcm

        try:
            # Convert to HU unit
            self.Image_HU = self.Dicom.RawData * self.Dicom.Slop + self.Dicom.Intercept
            # center is always in format (row, col)
            self.Center, self.Radius = self.calc_circle(self.Image_HU.copy())
            self.Image = self.rescale_image(self.Image_HU, (self.Dicom.WindowWidth, self.Dicom.WindowCenter))
            # Initial Image data
            # Do the initial calculation
            # define circular integration result
            self.Image_Integration_Result = np.zeros(self.Radius[0])
            self.Image_Median_Filter_Result = np.zeros(self.Radius[0])
            # main calculation
            self.integration()
        except Exception as e:
            logging.error(str(e))
            return
        self.isImageComplete = True

    @staticmethod
    def rescale_image(raw_data, window):
        """
        rescale the image to set the data in range (0~255)
        :param raw_data: a np array as raw image data, make sure to pass a copy!
        :param window: a tuple pass in as (window width, window center)
        :return: return a np array as rescaled image
        """
        window_upper = window[1] + window[0] / 2
        window_lower = window[1] - window[0] / 2
        # make filter according to center and width
        upper_filter = raw_data > window_upper
        raw_data[upper_filter] = window_upper  # set upper value
        lower_filter = raw_data < window_lower
        raw_data[lower_filter] = window_lower  # set lower value
        # rescale the data to 0~255
        min_hu_image = raw_data.min()
        if min_hu_image < 0:
            max_hu_image = raw_data.max() + abs(min_hu_image)
            image_rescale = raw_data + (0 - min_hu_image)  # get rid of minus number
        else:
            max_hu_image = raw_data.max()
            image_rescale = raw_data
        image_rescale = image_rescale * 255 / max_hu_image  # rescale the image to fit 0~255
        return image_rescale

    def calc_circle(self, raw_data):
        """
        Calculate the image center and radius
        the method is simple
        from up/down/left/right side to go into center
        the 1st number is > mean value, it's the edge
        calculate the distance from th edge to center
        :param raw_data: the image data will be calculated besure to pass a copy!
        :return: return 2 tuples which are image center and radius 
        (center row, center col),(radius in pixel, radius in cm)
        """
        # set up some local variables
        is_abnormal = False
        img_size = (self.Dicom.Rows, self.Dicom.Cols)
        center_col = img_size[0] // 2
        center_row = img_size[1] // 2
        left_distance = 0
        right_distance = 0
        up_distance = 0
        low_distance = 0
        max_allowed_deviation = 20
        # Using PIL to find edge and convert back to np array
        raw_data = self.rescale_image(raw_data.copy(), (100, 0))
        im = Image.fromarray(raw_data).convert("L").filter(ImageFilter.FIND_EDGES)
        filtered_image = np.array(im)

        # start to calculate center col
        for left_distance in range(1, img_size[1]):
            if filtered_image[center_row, left_distance] != 0:
                break
        for right_distance in range(1, img_size[1]):
            if filtered_image[center_row, img_size[1] - right_distance] != 0:
                break
        center_col += (left_distance - right_distance) // 2
        logging.debug(r"Center Col calculated as: " + str(center_col))
        # if the calculated center col deviated too much
        if (img_size[0] // 2 + max_allowed_deviation) < center_col < (img_size[0] // 2 - max_allowed_deviation):
            logging.warning(r"It seems abnormal when calculate Center Col, use image center now!")
            center_col = img_size[0] // 2
            is_abnormal = True

        # start to calculate center row
        for up_distance in range(1, img_size[0]):
            if filtered_image[up_distance, center_col] != 0:
                break
        for low_distance in range(1, img_size[0]):
            if filtered_image[img_size[0] - low_distance, center_col] != 0:
                break
        center_row += (up_distance - low_distance) // 2
        logging.debug(r"Center Row calculated as: " + str(center_row))
        # if the calculated center row deviated too much
        if (img_size[1] // 2 + max_allowed_deviation) < center_row < (img_size[1] // 2 - max_allowed_deviation):
            logging.warning(r"It seems abnormal when calculate Center row, use image center now!")
            center_row = img_size[1] // 2
            is_abnormal = True

        # set different radius according to normal/abnormal situation
        if is_abnormal is False:
            radius = (img_size[0] - left_distance - right_distance) // 2
            diameter_in_cm = radius * self.Dicom.PixSpace[0] * 2
            logging.debug(str(radius) + r"pix (radius), " + str(diameter_in_cm) +
                          r"cm(diameter)<==Calculated phantom diameter")
            # standardize the radius
            if diameter_in_cm < 250:
                radius = 233
                logging.debug(str(radius) + r"pix" + r", which is: " +
                              str(radius * self.Dicom.PixSpace[0] * 2) + r"cm <=========Radius Readjusted")
            else:
                radius = 220
                logging.debug(str(radius) + r"pix" + r", which is: " +
                              str(radius * self.Dicom.PixSpace[0] * 2) + r"cm <=========Radius Readjusted")
        else:
            logging.warning(r"Calculated center is abnormal, use 50 as radius!")
            radius = 50
            diameter_in_cm = radius * self.Dicom.PixSpace[0]

        return (center_row, center_col), (radius, diameter_in_cm)

    def bresenham(self, radius):
        x = 0
        y = radius
        d = 3 - 2 * radius
        while x < y:
            self.Image_Integration_Result[radius] = self.Image_Integration_Result[radius] + self.Image_HU[
                self.Center[0] - y, self.Center[1] + x]
            self.Image_Integration_Result[radius] = self.Image_Integration_Result[radius] + self.Image_HU[
                self.Center[0] + y, self.Center[1] + x]
            self.Image_Integration_Result[radius] = self.Image_Integration_Result[radius] + self.Image_HU[
                self.Center[0] - y, self.Center[1] - x]
            self.Image_Integration_Result[radius] = self.Image_Integration_Result[radius] + self.Image_HU[
                self.Center[0] + y, self.Center[1] - x]
            self.Image_Integration_Result[radius] = self.Image_Integration_Result[radius] + self.Image_HU[
                self.Center[0] - x, self.Center[1] + y]
            self.Image_Integration_Result[radius] = self.Image_Integration_Result[radius] + self.Image_HU[
                self.Center[0] - x, self.Center[1] - y]
            self.Image_Integration_Result[radius] = self.Image_Integration_Result[radius] + self.Image_HU[
                self.Center[0] + x, self.Center[1] + y]
            self.Image_Integration_Result[radius] = self.Image_Integration_Result[radius] + self.Image_HU[
                self.Center[0] + x, self.Center[1] - y]
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

    def save_image(self):
        if self.isImageComplete:
            # set up the output file name
            image__filename = self.Dicom.ScanMode + ".jpeg"
            image__filename__fig = self.Dicom.ScanMode + "_fig.jpeg"
            im = Image.fromarray(self.Image).convert("L")
            # save image
            try:
                # save image
                im.save(self.Dicom.ScanMode + image__filename, "png")
                # draw fig
                plt.plot(self.Image_Median_Filter_Result)
                plt.ylim((-5, 20))
                plt.xlim((0, 250))
                # draw fig image
                plt.savefig(self.Dicom.ScanMode + image__filename__fig)
            except Exception as e:
                logging.error(str(e))
                return
            finally:
                plt.close()
        else:  # if self.isShowImgReady == False
            logging.warning(r"File is not complete initialized, skip show image.")
            return

    def show_image(self):
        im = Image.fromarray(self.Image).convert("L")
        return im

    def show_integration_result(self):
        return self.Image_Median_Filter_Result


if __name__ == '__main__':
    print("please do not use it individually unless of debugging.")

    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s',
                        datefmt='%a, %d %b %Y %H:%M:%S')

    a = DicomHandler('/Users/qianxin/Downloads/add.dcm')
    img = ImageHandler(a)
    print(img.show_image())
