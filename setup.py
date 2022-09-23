from config import constants
from cx_Freeze import setup, Executable

setup(
    name=constants.APP_NAME,
    version=constants.APP_VERSION,
    description='A Rainmeter widget management tool',
    executables=[Executable('__main__.py', base='Win32GUI', target_name='reDesktop.exe', icon='misc/icon/icon.ico')],
    options = {'build_exe':{'include_files':['scripts/', 'skins/', 'suites/', 'config/','README.md']}}
)