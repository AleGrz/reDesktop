import ctypes
import json
import os
import re
import time

from config import constants

def load_suite(suite):

    with open(os.path.join('config', 'preferences.json'), 'r') as json_text:
        settings_json = json.load(json_text)
        settings = {}
        for setting in settings_json:
            settings[setting] = settings_json[setting]['value']

    os.popen('"{}/Rainmeter.exe" !LoadLayout "reDesktop"'.format(settings['rainmeter_path']))

    suite_path = os.path.join('suites', suite)

    ctypes.windll.user32.SystemParametersInfoW(constants.SPI_SETDESKTOPWALLPAPER, 0,
                                               os.path.join(os.getcwd(), suite_path, 'wallpaper.png'))

    with open(os.path.join(suite_path, 'config.json')) as config_json:
        config = json.load(config_json)

    for skin in config:

        for root, dirs, files in os.walk('skins'):
            if skin in files:
                path = os.path.join(root, skin)

        with open(path) as skin_config_json:
            skin_config = json.load(skin_config_json)

        for variable in config[skin]:



            if variable != 'position':

                with open(os.path.join(settings['skins_path'], skin_config[variable]["config_path"]), "r") as skin_ini:
                    skin_file = skin_ini.read()

                search_iterator = re.finditer(r'(?<={}=).*(?=\n)'.format(skin_config[variable]['name']), skin_file)

                for _ in range(skin_config[variable]['index'] + 1):
                    current_search = next(search_iterator)

                skin_file_list = list(skin_file)
                skin_file_list[current_search.span()[0]:current_search.span()[1]] = re.sub('\\[|\\]', '',
                                                                                           str(config[skin][variable]))
                skin_file = ''.join(skin_file_list)

                with open(os.path.join(settings['skins_path'], skin_config[variable]["config_path"]), "w") as skin_ini:
                    skin_ini.write(skin_file)

            else:

                x_position = config[skin]['position'][0]
                y_position = config[skin]['position'][1]

        regex_pattern = r'(\\)(?!.*\\)'
        split_script_path = re.split(regex_pattern, skin_config["script_path"])

        os.popen('"{}/Rainmeter.exe" !ActivateConfig "{}" "{}"'.format(settings['rainmeter_path'],split_script_path[0],
                                                                       split_script_path[2]))
        time.sleep(0.1)
        os.popen('"{}/Rainmeter.exe" !RefreshApp'.format(settings['rainmeter_path']))
        time.sleep(0.1)
        os.popen('"{}/Rainmeter.exe" !Move "{}" "{}" "{}"'.format(settings['rainmeter_path'], x_position, y_position,
                                                                  split_script_path[0]))
