import os
import shutil
import configparser
from getpass import getuser
from mimetypes import guess_type
import argparse
import logging as log
import distutils.util as util
import subprocess
from urllib import request, parse
from sys import platform

try:
    from bs4 import BeautifulSoup
    from PIL import Image
    folder_icons_imports = True
except ModuleNotFoundError:
    folder_icons_imports = False

CONFIG_NAME = 'SortConfig.ini'


class NyaaSort:

    def __init__(self, dir_path, log_info=None, folder_icons="False", s_dir=None, b_dir=None):
        # Set-up logging
        logger = log.getLogger('NyaaSort Logger')
        ch = log.StreamHandler()
        formatter = log.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        ch.setFormatter(formatter)

        # We check for NoneType since 0 would not trigger otherwise
        if log_info is not None:
            if log_info == 'True':
                logger.setLevel(log.INFO)
                ch.setLevel(log.INFO)
            elif log_info == 'False':
                logger.setLevel(log.WARNING)
                ch.setLevel(log.WARNING)
            else:
                logger.setLevel(log.DEBUG)
                ch.setLevel(log.DEBUG)

        # Set self.experimental to true if we want to test new features
        self.folder_icons = True if folder_icons == "True" else False
        # Start logging
        logger.addHandler(ch)
        logger.debug("Logging started")

        # Set basic values
        self.dir_path = dir_path
        self.sort_dir = s_dir
        self.backup_dir = b_dir
        self.anime_dict = {}
        self.config = configparser.ConfigParser()
        logging_level = None

        # The self.weak error variable will be used to check if the script found any errors while running
        self.weak_error = False

        # Check if this is not the first time starting
        # Get the place that the .py script is located
        if os.path.exists(self.return_ini_location()):
            logger.debug(f"Existing {CONFIG_NAME} file found")
            self.config.read(self.return_ini_location())
            exceptions = (configparser.NoOptionError, configparser.NoSectionError,
                          configparser.DuplicateSectionError, ValueError)
            try:
                # Get config settings
                # Update the dir path to whatever was in the settings
                self.dir_path = self.config.get('SORT', 'DIRECTORY')
                self.sort_dir = self.config.get('SORT', 'SORTED_DIRECTORY')
                self.backup_dir = self.config.get('SORT', 'BACKUP_PATH')
                logging_level = bool(util.strtobool(self.config.get('SORT', 'LOGGING')))
                settings_icons = bool(util.strtobool(self.config.get('SORT', 'ICONS')))

                # Since we can only save objects as strings we have to check to see if these strings are not None
                if self.sort_dir == 'None':
                    self.sort_dir = None
                if self.backup_dir == 'None':
                    self.backup_dir = None

                # Only update the value of experimental features if it has not been assigned yet
                if not self.folder_icons:
                    self.folder_icons = settings_icons

            except exceptions as e:
                logger.error(f"Encountered a {e} while trying to read the config file")
                logger.warning("Config file was corrupted, creating a new one")
                os.remove(self.return_ini_location())
                self.create_script(log_info, folder_icons)
        else:
            # If it is the first time starting it will setup all needed parameters
            # Please note that the create script function returns if the user wants logging enabled
            self.create_script(log_info, folder_icons)

        # This part triggers if the user did not use the logging flag
        # This behavior means that you can manually force the script to enable logging
        # This can be done by supplying it with a logging flag when executing
        # Since log_info will already be set than and it will thus skip this check
        if log_info is None:
            # Check if the user enabled logging in the config file
            if logging_level:
                logger.setLevel(log.INFO)
                ch.setLevel(log.INFO)
            else:
                logger.setLevel(log.ERROR)
                ch.setLevel(log.ERROR)

        logger.info(f"Logging set to {logger.getEffectiveLevel()}")

        # Set logger
        self.logger = logger

        # Check if backup dir and sort dir values are 'None', this should only apply during unit tests,
        # The ini file stores values as strings but those get converted when the values are set
        if self.sort_dir == 'None':
            self.sort_dir = None
        if self.backup_dir == 'None':
            self.backup_dir = None

    def get_anime_dict(self, folders):
        anime_dict = dict()

        # So for each folder in the folders provided
        for folder in folders:
            # Look whether there is a ] in the title, every folder created by this script will have
            # a name that starts with [group] anime
            if '] ' in folder:
                # Get the anime name by splitting the folder name in 2 from the ] icon and use everything after it
                anime = folder.split('] ', 1)[1]
                # Check if we already have this show in our folder structure
                # Ive had this happen once because of a movie i downloaded without the interference of this script
                # It's not a real issue though, for now it just uses the first folder it found
                if anime in anime_dict:
                    self.logger.warning(f"Found an anime which has 2 folders {anime}")
                    self.weak_error = True
                else:
                    # Add the show to the dictionary with the anime as key
                    anime_dict[anime] = folder

        # Update the dictionary
        self.anime_dict = anime_dict

    def move_anime(self, item, to_folder):
        try:
            # Create a copy of the anime episode
            if self.backup_dir:
                shutil.copy(os.path.join(self.dir_path, item), os.path.join(self.backup_dir, to_folder, item))
                self.logger.info(f"Created a backup of {item} and copied it to {self.backup_dir}")

            # Move the anime episode to the renamed folder
            # Check if the directory has to be the same as were the anime is located
            if self.sort_dir:
                shutil.move(os.path.join(self.dir_path, item), os.path.join(self.sort_dir, to_folder, item))
            else:
                shutil.move(os.path.join(self.dir_path, item), os.path.join(self.dir_path, to_folder, item))

            self.logger.info(f"Moved {item} to {to_folder}")

        except FileNotFoundError:
            self.logger.warning(f"Encountered an error while attempting to move {item}")
            self.logger.warning(f'from {self.dir_path} to {to_folder}')
            self.weak_error = True
        except PermissionError:
            self.logger.warning(f"Could not move {item} permission was denied")
            self.weak_error = True

    def get_folders_in_dir(self):
        # Make a list of all the folders in the sorted anime dir
        # Note this only takes the top level folders into consideration we are not interested in sub-folders
        if self.sort_dir:
            full_folders_dir = next(os.walk(self.sort_dir))[1]
        else:
            # if the sort_dir is equal to None the sorted directory is the same as the anime directory
            full_folders_dir = next(os.walk(self.dir_path))[1]
        return full_folders_dir

    def sort(self):
        # Get all anime that needs to be sorted in the unsorted anime dir
        items_in_folder = os.listdir(self.dir_path)

        # Make a list of all the folders in the sorted anime dir
        full_folders_dir = self.get_folders_in_dir()

        # Update the dictionary of all anime we have existing folders for
        self.get_anime_dict(full_folders_dir)

        for item in items_in_folder:
            # All the anime I download off Nyaa are MKV files
            # TODO add support for mp4 files
            # The mimetypes tries to guess what kind of file it is, this is to prevent other stuff with the
            # .mkv extension getting into my folders
            if item.endswith(".mkv") and 'video' in guess_type(item, strict=True)[0]:
                # Fetch the group which did the group, done by finding the first ] in the string
                nya_format = [']', '[', ' -', '] ']
                # Check if the file has all characters needed to be a matching of the nyaa format
                if all(x in item for x in nya_format):
                    try:
                        # Get the group by getting everything between the first [ and ]
                        subtitle_group = str(item.split(']', 1)[0]).replace('[', '', 1)
                        # fetch the name of the anime by taking everything after the first ] and before the last -
                        anime_name = str(item.split('] ', 1)[1]).rsplit(" -", 1)[0]
                    except IndexError:
                        # This will trigger if you create a file name containing all nya_format characters
                        # But it is not the correct format after all
                        self.logger.warning(f"Encountered an error while string slicing {item}")
                        self.weak_error = True
                        continue
                else:
                    # Executes if there is a MKV file in the directory but its not formatted in the correct way
                    self.logger.warning(f"Skipped {item} for not having the correct string format")
                    self.weak_error = True
                    continue

                # If the anime this episode belongs to already has a folder made we only have to move it in there
                if anime_name in self.anime_dict:
                    # Get the folder name associated with that anime
                    anime_path = self.anime_dict[anime_name]

                    try:
                        folder_subtitle_group = str(anime_path.split(']', 1)[0]).replace('[', '', 1)
                    except IndexError:
                        # This code should not trigger since it accounts for this error on dictionary creation
                        # Getting here means something went horribly wrong
                        self.logger.critical(f'Critical folder naming error for {anime_path}, anime: {anime_name}')
                        input('Please fix the error and then reboot the script')
                        break

                    # This check is done to see if the folder group matches the group that did the anime
                    if folder_subtitle_group == 'Multiple groups' or folder_subtitle_group == subtitle_group:

                        self.move_anime(item, anime_path)

                    else:
                        # Rename the folder so you know you have episodes done by different groups

                        self.rename_folder(item, anime_name, anime_path)
                else:
                    # If we have not have a folder for the anime we will have to make a new one
                    dirty_folder_name = f'[{subtitle_group}] {anime_name}'

                    new_folder = self.create_folder(dirty_folder_name)

                    self.logger.info(f"created a new folder for the show: {anime_name}")

                    # Append the anime to our anime list
                    try:
                        self.anime_dict[anime_name] = dirty_folder_name

                    except ValueError:
                        # A valueError should only occur if the anime in question already has an entry
                        # This should not be possible but if it happens
                        # Updating the lists will hopefully resolve this error
                        self.logger.error("Encountered an ValueError while attempting to update the dict")
                        self.weak_error = True
                        full_folders_dir = self.get_folders_in_dir()
                        self.get_anime_dict(full_folders_dir)
                        self.logger.info("Updated the lists to hopefully resolve the ValueError")

                    # Move the anime in the new folder
                    self.move_anime(item, new_folder)

        # Check if the user wanted folder icons
        if self.folder_icons:
            self.make_icons()

        # if any weak errors were encountered make sure the popup window from python does not disappear
        if self.weak_error and self.logger.getEffectiveLevel() < 30:
            input("Press any key to exit \n")

    def rename_folder(self, item, anime_name, anime_path):
        # Check if the directory of the anime file is the same as the sorting directory
        if self.sort_dir:
            # Set the path + wanted name of the anime
            rename = os.path.join(self.sort_dir, f'[Multiple groups] {anime_name}')
        else:
            rename = os.path.join(self.dir_path, f'[Multiple groups] {anime_name}')

        try:
            # Rename the folder
            if self.sort_dir:
                os.rename(os.path.join(self.sort_dir, anime_path), rename)
            else:
                os.rename(os.path.join(self.dir_path, anime_path), rename)

            # Change the name of the folder in the backup location
            if self.backup_dir:
                os.rename(os.path.join(self.backup_dir, anime_path),
                          os.path.join(self.backup_dir, f'[Multiple groups] {anime_name}'))

            self.logger.info(f"Renamed the folder for {anime_name}")

            try:
                # Change our dict so it contains the new name of the folder
                self.anime_dict.update({f'{anime_name}': f'[Multiple groups] {anime_name}'})

            except ValueError:
                # Updating the lists will hopefully resolve this error
                self.logger.error("Encountered an ValueError while attempting to update the dict")
                self.weak_error = True
                full_folders_dir = self.get_folders_in_dir()
                self.get_anime_dict(full_folders_dir)
                self.logger.info("Updated the lists to hopefully resolve the ValueError")

            # Move the anime to the new folder
            self.move_anime(item, rename)

        except FileNotFoundError:
            self.logger.error(f"Encountered an error while attempting to rename folder {anime_path}")
            self.logger.error(f'from {anime_path} to {rename}')
            self.weak_error = True

    def create_folder(self, folder_name):
        if self.sort_dir:
            new_folder_path = os.path.join(self.sort_dir, folder_name)
        else:
            new_folder_path = os.path.join(self.dir_path, folder_name)
        # I could not find a way to break os.makedir so no try except block here
        os.makedirs(new_folder_path)

        # Also create a folder in the backup location
        if self.backup_dir:
            backup_folder_path = os.path.join(self.backup_dir, folder_name)
            # I could not find a way to break os.makedir so no try except block here
            os.makedirs(backup_folder_path)

        return new_folder_path

    def create_script(self, log_info, folder_icons):
        # Technically if log_info: would also work
        if log_info is None:
            log_input = input("Do you want to enable logging?(Y/N)\n")
            logging = 'True' if log_input.upper() == 'Y' or log_input.upper() == 'YES' else 'False'
        else:
            if log_info in ["True", "False"]:
                logging = log_info
            else:
                logging = "True"

        if self.dir_path is None:
            sort_place = input("In which directory is the anime you want to sort located?\n")
            if os.path.exists(sort_place):
                self.dir_path = sort_place
            else:
                print("Unrecognised folder, using base folder of the script")
                self.dir_path = os.path.dirname(os.path.realpath(__file__))

        if self.sort_dir is None:
            sort_place = input("In which directory should the sorted anime go?\n"
                               "Keep this empty if you want the same directory as the place the anime is located\n")
            if os.path.exists(sort_place):
                self.sort_dir = sort_place
            else:
                print("Using same folder as -d")
                self.sort_dir = None

        if self.backup_dir is None:
            sort_place = input("In which directory should I backup the sorted anime?\n"
                               "Keep this empty for no backups\n")
            if os.path.exists(sort_place):
                self.backup_dir = sort_place
            else:
                print("Creating no backups")
                self.backup_dir = None

        # Get The user of this pc and the name of this file
        user_name = getuser()
        file_name = os.path.basename(__file__)

        # Get the place that the .py script is located
        py_dir = os.path.dirname(os.path.realpath(__file__))
        # Make sure the script starts on startup
        # Note we use os.name for windows since we don't care what version of windows we are running
        # sys.platform is more accurate which we need to distinguish between the other operating systems
        if os.name == 'nt':
            try:
                bat_path = f'C:\\Users\\{user_name}\\' \
                           f'AppData\\Roaming\\Microsoft\\Windows\\Start Menu\\Programs\\Startup'
                with open(bat_path + '\\' + "AnimeSort.bat", "w+") as bat_file:
                    # TODO I might need to change "python" to "start" when making this an exe file
                    bat_file.write(f'python {py_dir}\\{file_name}')
            except FileNotFoundError:
                print("Try checking your pc username") if bool(logging) else 0
                input("File directory for storing .bat file was not found")
            except Exception as e:
                input(f'While opening the bat file {e} went wrong')
        elif platform == "linux" or platform == "linux2":
            # linux
            print("The script can not automatically add itself to the boot-up process")
            print("Please copy this script to your /bin manually and add another corn job")
        elif platform == "darwin":
            # OS X
            print("The script can not automatically add itself to the boot-up process")
            print("Please make your own plist and add it to the correct location")

        # Make a Config file for the script
        try:
            self.config.add_section('SORT')
        except configparser.DuplicateSectionError:
            # If this triggers the sections were not corrupted but the value of LOGGING was
            # Nothing needs to be done if this happens
            pass

        # Set values for SORT section
        # These should all already be strings but just to be sure
        try:
            self.config['SORT']['LOGGING'] = logging
            self.config['SORT']['ICONS'] = folder_icons
            self.config['SORT']['DIRECTORY'] = self.dir_path
            self.config['SORT']['SORTED_DIRECTORY'] = str(self.sort_dir)
            self.config['SORT']['BACKUP_PATH'] = str(self.backup_dir)
        except TypeError:
            print("Critical Type error while creating config, Trying to continue")
            self.config['SORT']['LOGGING'] = str(logging)
            self.config['SORT']['ICONS'] = str(folder_icons)
            self.config['SORT']['DIRECTORY'] = str(self.dir_path)
            self.config['SORT']['SORTED_DIRECTORY'] = str(self.sort_dir)
            self.config['SORT']['BACKUP_PATH'] = str(self.backup_dir)
            print("Retry successful")

        try:
            with open(f'{py_dir}/{CONFIG_NAME}', 'w') as configfile:
                self.config.write(configfile)
        except FileNotFoundError:
            print("Try checking if your directory matches the file storage location") if logging else 0
            input("Could not find file directory for storing the config file")
        except Exception as e:
            input(f'While creating the bat file {e} went wrong')

        # I have to use in a print since self.logger does not get defined until later in the setup
        print("Created new config")

    def connect_to(self, url):
        try:
            return request.urlopen(url)
        except ConnectionError:
            self.logger.error(f"Failed to connect to {url}")
        except TimeoutError:
            self.logger.error(f"{url} took to long to respond")
        except Exception as e:
            self.logger.error(f"{e} went wrong while trying to connect to {url}")
        return False

    def make_icons(self):
        if not folder_icons_imports:
            self.logger.warning("Not all modules needed are imported, aborting")
            return

        self.logger.warning("The script that deals with setting folder icons is iffy at best, improvement is needed")
        self.logger.warning("Folder icon changes will not be displayed unless you refresh folder view")
        # TODO make it not so sensitive to edge cases, error testing

        if not os.name == 'nt':
            self.logger.error("This function will only work on windows")
            self.weak_error = True
            return

        for anime in self.anime_dict:
            if self.sort_dir:
                full_image_path = os.path.join(self.sort_dir, self.anime_dict[anime], f"{anime}.ico")
            else:
                full_image_path = os.path.join(self.dir_path, self.anime_dict[anime], f"{anime}.ico")

            if not os.path.exists(full_image_path):
                # Transfer the anime name to html speak
                url_name = parse.quote(anime)
                url = f"https://myanimelist.net/search/all?q={url_name}&cat=all"
                search_page = self.connect_to(url)
                if not search_page:
                    # If something went wrong while trying to connect just ignore this anime
                    continue

                soup = BeautifulSoup(search_page, 'html.parser')
                # We are actually looking for the first item that will pop out when you hover you mouse over it
                all_anime = soup.findAll("a", {"class": "hoverinfo_trigger"})
                mal_anime = all_anime[0]['href']

                mal_anime_page = self.connect_to(mal_anime)
                if not mal_anime_page:
                    # If something went wrong while trying to connect just ignore this anime
                    continue

                anime_soup = BeautifulSoup(mal_anime_page, 'html.parser')
                # No clue why the image class is ac but its the one we need
                anime_image_dirty = anime_soup.findAll("img", {"class": "ac"})
                anime_image = anime_image_dirty[0]['data-src']
                self.logger.info(f"{anime_image} was found for {anime}")

                # Save the image
                try:
                    request.urlretrieve(anime_image, full_image_path)
                except Exception as e:
                    self.logger.error(f"{e} went wrong while trying to save image {anime_image}")
                    continue

                # Reformat the image as .ico
                img = Image.open(full_image_path)
                img.resize((256, 256), Image.ANTIALIAS)
                if self.sort_dir:
                    ico_dir = os.path.join(self.sort_dir, self.anime_dict[anime], f"{anime}.ico")
                else:
                    ico_dir = os.path.join(self.dir_path, self.anime_dict[anime], f"{anime}.ico")
                try:
                    img.save(ico_dir, format='ICO')
                except FileNotFoundError:
                    self.logger.error(f"No directory {ico_dir}")

                # Here we call the powershell script to set the folder icon
                if self.sort_dir:
                    folder = os.path.join(self.sort_dir, self.anime_dict[anime])
                else:
                    folder = os.path.join(self.dir_path, self.anime_dict[anime])
                ec = subprocess.call(
                    ['powershell', "-ExecutionPolicy", "Unrestricted", "-File", './set_folder_ico.ps1', f'{folder}',
                     f'{anime}'])
                self.logger.info("Powershell returned: {0:d}".format(ec))

    @staticmethod
    def return_ini_location():
        # returns the location of the ini file, useful for unit tests
        py_dir = os.path.dirname(os.path.realpath(__file__))
        return os.path.join(py_dir, CONFIG_NAME)


if __name__ == '__main__':
    # Get arguments provided
    parser = argparse.ArgumentParser()
    parser.add_argument("-l", "--logging", required=False, help="Enable logging?: True/False")
    parser.add_argument("-d", "--directory", required=False, help="The folder where the anime files are located")
    parser.add_argument("-o", "--output_directory", required=False, help="The folder where the sorted anime should go,"
                                                                         "leave this blank for the same folder as -d ")
    parser.add_argument("-b", "--backup", required=False, help="If the script should store a backup of the anime "
                                                               "somewhere else")

    if folder_icons_imports:
        parser.add_argument("-i", "--icons", required=False, help="create matching folder icons?: True/False")

    args = parser.parse_args()

    if args.logging in ["True", "False"]:
        LOG_INFO = args.logging
    else:
        # Technically LOG_INFO could be anything but we don't want users to be able to do that
        LOG_INFO = None

    if folder_icons_imports:
        if args.icons in ["True", "False"]:
            icons = args.icons
        else:
            # Folder icons is optional so we could just create a class without it. But let's not do that
            icons = "False"
    else:
        icons = "False"

    if args.directory:
        if os.path.exists(args.directory):
            anime_dir = args.directory
        else:
            anime_dir = None
    else:
        anime_dir = None

    if args.output_directory:
        if os.path.exists(args.output_directory):
            sort_dir = args.output_directory
        else:
            sort_dir = None
    else:
        sort_dir = None

    if args.backup:
        if os.path.exists(args.backup):
            backup_dir = args.backup
        else:
            backup_dir = None
    else:
        backup_dir = None

    NyaaSort(dir_path=anime_dir, log_info=LOG_INFO, folder_icons=icons, s_dir=sort_dir, b_dir=backup_dir).sort()
