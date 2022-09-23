import json
import operator
import os
import threading
import tkinter as tk

from tkinter import ttk
from tkinter import messagebox
from config import constants
from scripts import generate_suite, load_suite


class MainWindow:
    """Main reDesktop window"""

    def __init__(self, master):
        """Create the main window, with 3 notebook tabs:"""

        # Set the title and size of the window
        self.master = master
        self.master.title(constants.APP_NAME + constants.APP_VERSION)
        self.master.geometry("{}x{}".format(constants.WINDOW_SIZE['x'], constants.WINDOW_SIZE['y']))

        # Define notebook widget with 3 tabs, and pack it
        self.notebook = ttk.Notebook(self.master)
        self.suites_tab = SuitesTab(self.notebook)
        self.settings_tab = SettingsTab(self.notebook)
        self.skins_tab = SkinsTab(self.notebook)
        self.notebook.pack(expand=True, fill="both")

        # Prepare the image URLs list to be parsed
        generate_suite.setup_suite_generator()


class Tab:
    """Creates the main window, with 3 notebook tabs:"""

    def __init__(self, parent, tab_name):
        """Set the name of the tab, create a frame inside"""

        self.parent = parent
        self.tab_name = tab_name

        # Create a Frame inside the tab
        self.tab = ttk.Frame(parent)

        # Set the name of the tab to self.tab_name
        self.parent.add(self.tab, text=self.tab_name)


class SuitesTab(Tab):
    def __init__(self, parent):
        """Create the content of Suites tab: Treeview with wallpapers, Scrollbar, and Buttons"""

        super().__init__(parent, 'Suites')

        # Dictionary of treeview
        self.image_icons = {}
        self.treeview_frame = ttk.Frame(self.tab)
        self.treeview_style = ttk.Style()
        self.treeview_style.configure('suites.Treeview', rowheight=constants.TREEVIEW_ROW_HEIGHT)
        self.wallpaper_treeview = ttk.Treeview(self.treeview_frame, show="tree", height=constants.TREEVIEW_ROW_COUNT,
                                               style='suites.Treeview', columns='wallpapers')
        self.wallpaper_treeview_scrollbar = ttk.Scrollbar(self.treeview_frame, orient="vertical",
                                                          command=self.wallpaper_treeview.yview)
        self.wallpaper_treeview.configure(yscrollcommand=self.wallpaper_treeview_scrollbar.set)
        self.wallpaper_treeview.column('wallpapers', width=constants.TREEVIEW_COLUMN_WIDTH)
        self.wallpaper_treeview.pack(side=tk.LEFT)
        self.wallpaper_treeview_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.treeview_frame.pack()
        self.iid_to_suite_dict = {}
        self.new_suite_list = []
        self.reload_images()

        self.load_suite_button = ttk.Button(self.tab, text="Load", state="disabled",
                                            command=lambda: load_suite.load_suite(self.iid_to_suite_dict[self.wallpaper_treeview.focus()]))
        self.load_suite_button.pack(side=tk.LEFT, anchor=tk.E, expand=True)

        self.wallpaper_treeview.bind('<ButtonRelease-1>', lambda n: self.load_suite_button.configure(
            state=tk.NORMAL))

        self.generate_suite_button = ttk.Button(self.tab, text="Generate new",command=lambda: threading.Thread(target=self.generate_suite).start())
        self.generate_suite_button.pack(side=tk.RIGHT, anchor=tk.W, expand=True)

    def generate_suite(self):

        top = tk.Toplevel()
        top.geometry("400x50")
        top.title("Generating new suite")
        top.focus_force()
        top.protocol("WM_DELETE_WINDOW", lambda: 0)

        self.parent.master.attributes('-disabled', True)

        text = ttk.Label(top, text='Please wait. This may take up to several minutes, depending on your PC')
        progressbar = ttk.Progressbar(top, orient=tk.HORIZONTAL, length=380, mode='indeterminate')
        text.pack()
        progressbar.pack(expand=True)
        progressbar.start(5)

        generate_suite.generate_new_suite()

        top.destroy()
        self.parent.master.attributes('-disabled', False)

        self.reload_images()

    def reload_images(self):

        self.suite_list = os.listdir('suites')
        self.iid_to_suite_dict = {}
        self.wallpaper_treeview.delete(*self.wallpaper_treeview.get_children())

        for suite in self.suite_list:
            self.wallpaper_path = os.path.join('suites', suite, 'wallpaper.png')
            self.icon_path = os.path.join('suites', suite, 'icon.png')
            self.image_icons[suite] = tk.PhotoImage(file=self.icon_path)
            self.skin_iid = self.wallpaper_treeview.insert('', tk.END, image=self.image_icons[suite], open=False)
            self.wallpaper_treeview.image = self.image_icons[suite]
            self.iid_to_suite_dict[self.skin_iid] = suite


class SettingsTab(Tab):
    def __init__(self, parent):
        super().__init__(parent, 'Settings')
        with open(constants.SETTINGS_PATH, 'r') as settings_json:
            self.settings = json.load(settings_json)
        for key, setting in self.settings.items():
            match setting['input_type']:
                case 'entry':
                    self.widget = Entry(self.tab, (key,), constants.SETTINGS_PATH)
                case 'combobox':
                    self.widget = Combobox(self.tab, (key,), constants.SETTINGS_PATH)
                case 'checkbutton':
                    self.widget = Checkbutton(self.tab, (key,), constants.SETTINGS_PATH)
            self.widget.setting_pack()


class Widget:
    def __init__(self, parent, keys, path):
        self.path = path
        with open(path, 'r') as read:
            self.json = json.load(read)
        self.parent = parent
        self.keys = keys
        self.frame = tk.Frame(self.parent)
        self.widget_selected_value = tk.StringVar()
        self.setting = self.json
        for key in self.keys:
            self.setting = self.setting[key]
        self.widget_selected_value.set(self.setting['value'])
        self.widget_selected_value.trace_add('write', lambda *_: threading.Thread(target=self.update).start())

    def update(self):
        with open(self.path, 'r+') as self.write:
            try:
                self.value = int(self.widget_selected_value.get())
            except ValueError:
                self.value = self.widget_selected_value.get()

            self.setting = self.json

            for key in self.keys:
                self.setting = self.setting[key]
            self.setting['value'] = self.value
            self.write.seek(0)
            json.dump(self.json, self.write, indent=constants.JSON_INDENT)
            self.write.truncate()
        generate_suite.setup_suite_generator()

    def setting_pack(self):
        self.description = tk.Label(self.frame, text=self.setting['ui_name'] + ':')
        self.description.pack(side=tk.LEFT, fill=tk.X)
        self.widget.pack(side=tk.RIGHT, fill=tk.X)
        self.frame.pack(fill=tk.X)


class Entry(Widget):
    def __init__(self, parent, keys, path):
        super().__init__(parent, keys, path)
        self.widget = tk.Entry(self.frame, textvariable=self.widget_selected_value)


class Combobox(Widget):
    def __init__(self, parent, keys, path):
        super().__init__(parent, keys, path)
        self.widget = ttk.Combobox(self.frame, textvariable=self.widget_selected_value, state='readonly')
        self.widget['values'] = self.setting['possible_values']


class Checkbutton(Widget):
    def __init__(self, parent, keys, path):
        super().__init__(parent, keys, path)
        self.widget = ttk.Checkbutton(self.frame, variable=self.widget_selected_value)


class SkinsTab(Tab):
    def __init__(self, parent):
        super().__init__(parent, 'Skins')

        for group in os.listdir('skins'):
            self.skin_info = tk.Label(self.tab, text=group + ':')
            self.skin_info.pack()
            for skin in os.listdir(os.path.join('skins', group)):
                widget = Checkbutton(self.tab, (), os.path.join('skins', group, skin))
                widget.setting_pack()

def start():
    if os.path.isfile('config/first_launch'):
        os.popen('notepad.exe README.md')
        os.remove('config/first_launch')

    root = tk.Tk()
    main_window = MainWindow(root)
    root.mainloop()
    messagebox.showerror(title='reDesktop error', message=type(err).__name__+': '+str(err))
