import datetime
import json
import math
import os
import random
import re

import numpy as np
import requests
import cv2
import scipy

from config import constants


class Suite:
    def clear_config(self):
        self.config_json = {}

    def set_wallpaper_parser(self, source, keyword):
        self.keyword = keyword
        match source:
            case 'Reddit':
                self.wallpaper = Reddit(self.keyword)
            case 'Unsplash':
                self.wallpaper = Unsplash(self.keyword)

    def create_new_directory(self):
        self.path = os.path.join('suites', 'suite_' + datetime.datetime.now().strftime("%y%m%d_%H%M%S"))
        os.makedirs(self.path)

    def get_active_skins_from_group(self, group):
        self.active_skins_list = []
        for skin in os.listdir(os.path.join('skins', group)):
            with open(os.path.join('skins', group, skin)) as skin_json:
                self.skin_settings = json.load(skin_json)
                if self.skin_settings['value'] == 1:
                    self.active_skins_list.append(skin)

    def get_random_skin(self):
        return random.choice(self.active_skins_list)

    def append_to_config(self, config, skin):
        self.config_json[skin] = config

    def save_config_to_file(self):
        with open(os.path.join(self.path, 'config.json'), 'w') as config:

            json.dump(self.config_json, config, indent=constants.JSON_INDENT)


class Wallpaper:
    def __init__(self, keyword):
        self.keyword = re.sub(' ', '+', keyword)

    def get_image_from_link(self):
        self.parsed_image = requests.get(self.image_link, stream=True).raw
        self.image_as_numpy_array = np.asarray(bytearray(self.parsed_image.read()), dtype="uint8")
        self.image = cv2.imdecode(self.image_as_numpy_array, cv2.IMREAD_COLOR)
        self.image_y, self.image_x = self.image.shape[:2]

    def resize_image_to_fit_screen(self):
        self.screen_aspect_ratio = settings['screen_x'] / settings['screen_y']
        self.image_aspect_ratio = self.image_x / self.image_y

        if self.screen_aspect_ratio > self.image_aspect_ratio:
            self.amount_of_image_to_cut = int(
                self.image_y - settings['screen_y'] * self.image_x / settings['screen_x']) // 2
            self.wallpaper = self.image[self.amount_of_image_to_cut:-self.amount_of_image_to_cut, :]

        elif self.screen_aspect_ratio < self.image_aspect_ratio:
            self.amount_of_image_to_cut = int(
                self.image_x - settings['screen_x'] * self.image_y / settings['screen_y']) // 2
            self.wallpaper = self.image[:, self.amount_of_image_to_cut:-self.amount_of_image_to_cut]

        else:
            self.wallpaper = self.image

        self.wallpaper = cv2.resize(self.wallpaper, (settings['screen_x'], settings['screen_y']))
        self.wallpaper_in_greyscale = cv2.cvtColor(self.wallpaper, cv2.COLOR_BGR2GRAY)

    def save_image(self, path):
        cv2.imwrite(os.path.join(path, 'wallpaper.png'), self.wallpaper)
        self.icon = cv2.resize(self.wallpaper,
                               (settings['screen_x'] * constants.TREEVIEW_ROW_HEIGHT // settings['screen_y'],
                                constants.TREEVIEW_ROW_HEIGHT))
        cv2.imwrite(os.path.join(path, 'icon.png'), self.icon)

    def quantize_image(self):
        self.image_array = self.wallpaper.reshape(-1, 3)
        self.image_array = np.float32(self.image_array)
        self.criteria = (
            cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, constants.NUMBER_OF_QUANTIZATION_ITERATIONS,
            constants.QUANTIZATION_EPSILON)
        self.ret, self.label, self.center = cv2.kmeans(self.image_array, settings['clusters'], None, self.criteria, 10,
                                                       cv2.KMEANS_RANDOM_CENTERS)
        self.image_array = np.uint8(self.center)
        self.image_array = self.image_array[self.label.flatten()]
        self.quantized_image = self.image_array.reshape(self.wallpaper.shape)
        self.colors, count = np.unique(self.quantized_image.reshape(-1, 3), return_counts=True, axis=0)
    def get_dominant_color_in_range(self,array_mask):

        color_count = [np.count_nonzero(self.quantized_image[array_mask].reshape(-1, 3) == self.colors[x]) for x in range(4)]

        return self.colors[color_count.index(min(color_count))].tolist()


class Reddit(Wallpaper):
    def __init__(self, keyword):
        super().__init__(keyword)
        self.current_image_index = 0
        self.reddit_url = 'https://www.reddit.com/r/{}/search/?q={}&sort=hot'.format(settings['subreddit'], self.keyword)
        html_code = str(requests.get(self.reddit_url).content)
        regex = r'(https:\/\/i.redd.it\S{15})(jpg|png)'
        self.image_candidate_list = re.findall(regex, html_code)
        self.image_candidate_list = [link[0] + link[1] for link in self.image_candidate_list]

    def __next__(self):
        self.image_link = self.image_candidate_list[self.current_image_index]
        super().get_image_from_link()
        self.current_image_index += 1


class Unsplash(Wallpaper):
    def __init__(self, keyword):
        super().__init__(keyword)
        self.image_link = 'https://source.unsplash.com/random/{}x{}/?'.format(settings['screen_x'],
                                                                              settings['screen_y']) + self.keyword

    def __next__(self):
        super().get_image_from_link()


class Skin:

    def __init__(self, group, skin):
        self.skin = skin
        with open(os.path.join('skins', group, self.skin), 'r') as skin_config_json:
            self.skin_config = json.load(skin_config_json)
        self.config_dict = {}
        self.mask = np.zeros((settings['screen_y'], settings['screen_x']), dtype=bool)

    def save_data(self):
        self.config_dict['position'] = [self.position_x, self.position_y]
        for variable in self.skin_config:
            match variable:
                case 'color':
                    self.config_dict[variable] = self.base_color[2],self.base_color[1],self.base_color[0]
                case 'rotation':
                    self.config_dict[variable] = self.deg_angle
                case 'width':
                    self.config_dict[variable] = self.rainmeter_width
        return self.config_dict


class Clock(Skin):
    def __init__(self, skin):
        super().__init__('Clock', skin)
        self.diversity_array = np.array([])
        self.summed_diversity_array = np.array([])
        self.blob_list = []

    def get_best_position(self, wallpaper):

        CELL_COUNT_X = settings['screen_x'] // constants.CELL_SIZE
        CELL_COUNT_Y = settings['screen_y'] // constants.CELL_SIZE

        def count_unique(zone_x, zone_y):
            diversity_index = 0
            for y in range(constants.CELL_SIZE):
                for x in range(constants.CELL_SIZE):
                    current_x = zone_x * constants.CELL_SIZE + x
                    current_y = zone_y * constants.CELL_SIZE + y
                    try:
                        if not np.array_equal(wallpaper.quantized_image[current_y, current_x],
                                              wallpaper.quantized_image[current_y, current_x + 1]):
                            diversity_index += 1
                        if not np.array_equal(wallpaper.quantized_image[current_y, current_x],
                                              wallpaper.quantized_image[current_y + 1, current_x]):
                            diversity_index += 1
                        if not np.array_equal(wallpaper.quantized_image[current_y, current_x],
                                              wallpaper.quantized_image[current_y + 1, current_x + 1]):
                            diversity_index += 1
                    except IndexError:
                        pass
            return diversity_index

        mod_array = np.zeros((CELL_COUNT_Y, CELL_COUNT_X))
        mod_array[:, (CELL_COUNT_X-self.skin_config['skin_x']) // 2:(CELL_COUNT_X+self.skin_config['skin_x']) // 2] = settings['modifier_middle']
        mod_array[(CELL_COUNT_Y-self.skin_config['skin_y']) // 2:(CELL_COUNT_Y+self.skin_config['skin_y']) // 2, :] = settings['modifier_middle']
        mod_array[0:1, 0:1] = settings['modifier_corner']
        mod_array[CELL_COUNT_Y - 2:CELL_COUNT_Y, 0:1] = settings['modifier_corner']
        mod_array[CELL_COUNT_Y - 2:CELL_COUNT_Y, CELL_COUNT_X - 2:CELL_COUNT_X] = settings['modifier_corner']
        mod_array[0:1, CELL_COUNT_X - 2:CELL_COUNT_X] = settings['modifier_corner']

        mod_array[CELL_COUNT_Y // 2:CELL_COUNT_Y // 2 + 1,
                  CELL_COUNT_X // 2:CELL_COUNT_X // 2 + 1] = settings['modifier_center']

        for y in range(CELL_COUNT_Y):
            for x in range(CELL_COUNT_X):
                unique = count_unique(x, y) + mod_array[y, x]

                self.diversity_array = np.append(self.diversity_array, unique)

        self.diversity_array = np.reshape(self.diversity_array, (-1, CELL_COUNT_X))

        for y in range(CELL_COUNT_Y - self.skin_config['skin_y']):
            for x in range(CELL_COUNT_X - self.skin_config['skin_x']):
                self.summed_background_diversity = np.sum(self.diversity_array[y:y + self.skin_config['skin_y'], x:x + self.skin_config['skin_x']])
                self.summed_diversity_array = np.append(self.summed_diversity_array, self.summed_background_diversity)

        self.summed_diversity_array = np.reshape(self.summed_diversity_array, (-1, CELL_COUNT_X - self.skin_config['skin_x']))
        self.summed_diversity_array[self.summed_diversity_array == np.amin(self.summed_diversity_array)] = 1
        self.summed_diversity_array[self.summed_diversity_array > np.amin(self.summed_diversity_array)] = 0

        im, number_of_objects = scipy.ndimage.label(self.summed_diversity_array)

        for object in range(number_of_objects):
            self.point_list = np.column_stack(np.where(im == object + 1))
            self.blob_list.append((len(self.point_list), self.point_list))

        self.biggest_blob = max(self.blob_list, key=lambda x: x[0])[1]

        self.position_x = int(np.amin(self.biggest_blob[:, 1]) + np.amax(
            self.biggest_blob[:, 1])) // 2 * constants.CELL_SIZE
        self.position_y = int(np.amin(self.biggest_blob[:, 0]) + np.amax(
            self.biggest_blob[:, 0])) // 2 * constants.CELL_SIZE

    def get_pixels_for_dominant_colors(self):
        self.mask[self.position_y:self.position_y + self.skin_config['skin_y'], self.position_x:self.position_x + self.skin_config['skin_x']] = 1
        return self.mask


class Visualiser(Skin):
    def __init__(self, skin):
        super().__init__('Visualiser', skin)
        self.line_list = []

    def get_best_position(self, wallpaper):
        def line_segment_detection(image):
            lsd = cv2.createLineSegmentDetector(0)
            detected_lines = lsd.detect(image)[0]
            return detected_lines

        def hough_transform(image):
            image_canny = cv2.Canny(image, settings['canny_threshold_low'], settings['canny_threshold_up'],
                                    apertureSize=settings['canny_aperture'])
            return cv2.HoughLinesP(image_canny, constants.HOUGH_RHO, math.pi / constants.HOUGH_THETA,
                                   threshold=settings['hough_threshold'],
                                   minLineLength=settings['min_line_length'], maxLineGap=settings['hough_max_line_gap'])

        if settings['line_detection_method'] == "Line Segment Detection":
            self.detected_lines = line_segment_detection(wallpaper.wallpaper_in_greyscale)
        elif settings['line_detection_method'] == "Hough Transform":
            self.detected_lines = hough_transform(wallpaper.wallpaper_in_greyscale)

        self.detected_lines = [(int(point[0][2]), int(point[0][3]), int(point[0][0]), int(point[0][1]))
                               if point[0][0] > point[0][2] else
                               (int(point[0][0]), int(point[0][1]), int(point[0][2]), int(point[0][3]))
                               for point in self.detected_lines]
        self.line_list = [(point, math.sqrt((point[2] - point[0]) ** 2 + (point[3] - point[1]) ** 2))
                          for point in self.detected_lines]
        self.line = max(self.line_list, key=lambda x: x[1])

        self.translate_line_coordinates_to_rainmeter()

    def translate_line_coordinates_to_rainmeter(self):
        def to_radians(angle_in_degrees):
            return angle_in_degrees * math.pi / 180

        def to_degrees(angle_in_radians):
            return angle_in_radians * 180 / math.pi

        (x1, y1, x2, y2), visualiser_width = self.line

        try:
            self.angle = math.atan(-(y2 - y1) / (x2 - x1))
        except ZeroDivisionError:
            self.angle = to_radians(90)

        if self.angle >= 0:
            self.position_y = int(y1 - 140 * math.cos(self.angle) - visualiser_width * math.cos(to_radians(90) - self.angle))
            self.position_x = int(x1 - 140 * math.sin(self.angle))
        else:
            self.position_y = int(y1 - 140 * math.cos(self.angle))
            self.position_x = int(x1)
            self.angle += to_radians(360)

        self.rainmeter_width = visualiser_width // 18
        self.deg_angle = int(to_degrees(self.angle))

    def get_pixels_for_dominant_colors(self):
        for x in range(self.line[0][2] - self.line[0][0]):
            try:
                self.mask[round(self.line[0][1]-3, self.line[0][0])] = 1
            except IndexError:
                pass
        return self.mask


def setup_suite_generator():
    global settings
    global suite

    suite = Suite()
    with open(os.path.join('config', 'preferences.json'), 'r') as json_text:
        settings_json = json.load(json_text)
        settings = {}
        for setting in settings_json:
            settings[setting] = settings_json[setting]['value']

    suite.set_wallpaper_parser(settings['wallpaper_source'], settings['keyword'])


def generate_new_suite():
    suite.clear_config()
    suite.create_new_directory()
    next(suite.wallpaper)
    suite.wallpaper.resize_image_to_fit_screen()
    suite.wallpaper.save_image(suite.path)
    suite.wallpaper.quantize_image()

    for group in os.listdir('skins'):
        suite.get_active_skins_from_group(group)
        match group:
            case 'Clock':
                skin = Clock(suite.get_random_skin())
            case 'Visualiser':
                skin = Visualiser(suite.get_random_skin())
        skin.get_best_position(suite.wallpaper)
        skin.base_color = suite.wallpaper.get_dominant_color_in_range(skin.get_pixels_for_dominant_colors())
        suite.append_to_config(skin.save_data(), skin.skin)
    suite.save_config_to_file()
    print("ok")
