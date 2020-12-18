import os
import shutil
import configparser
import getpass
import mimetypes
import argparse
import logging as log
import distutils.util as util

CONFIG_NAME = 'SortConfig.ini'


class NyaaSort:

    def __init__(self, dir_path, log_info=None):
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

        logger.addHandler(ch)
        logger.debug("Logging started")

        # Set basic values
        self.dir_path = dir_path
        self.config = configparser.ConfigParser()
        self.weak_error = False

        # Check if this is not the first time starting
        if os.path.exists(os.path.join(dir_path, CONFIG_NAME)):
            logger.debug(f"Existing {CONFIG_NAME} file found")
            self.config.read(os.path.join(dir_path, CONFIG_NAME))
            try:
                # Get config settings
                logging = bool(util.strtobool(self.config.get('SORT', 'LOGGING')))
                enable_logging = logging
            except configparser.NoOptionError or configparser.NoSectionError or configparser.DuplicateSectionError:
                logger.warning("Config file was corrupted, creating a new one")
                os.remove(os.path.join(dir_path, CONFIG_NAME))
                enable_logging = self.create_script(log_info)
        else:
            # If it is the first time starting it will setup all needed parameters
            # Please note that the create script sets up everything and returns if the user wants logging enabled
            enable_logging = self.create_script(log_info)
            if not enable_logging:
                # A bit sloppy way to only print if the user wanted logging
                logger.info("Created new config")

        # If the user disabled logging only show errors
        if log_info is None:
            if enable_logging:
                logger.setLevel(log.INFO)
                ch.setLevel(log.INFO)
            else:
                logger.setLevel(log.ERROR)
                ch.setLevel(log.ERROR)

        logger.info(f"Logging set to {logger.getEffectiveLevel()}")

        # Set logger
        self.logger = logger

    def get_anime_dict(self, folders):
        anime_dict = dict()

        for folder in folders:
            if '] ' in folder:
                anime = folder.split('] ', 1)[1]
                if anime in anime_dict:
                    self.logger.warning(f"Found an anime which has 2 folders {anime}")
                    self.weak_error = True
                else:
                    anime_dict[anime] = folder
        return anime_dict

    def move_anime(self, item, to_folder):
        try:
            # Move the anime to the renamed folder
            shutil.move(os.path.join(self.dir_path, item), os.path.join(self.dir_path, to_folder, item))
            self.logger.info(f"Moved {item} to {to_folder}")
        except FileNotFoundError:
            self.logger.warning(f"Encountered an error while attempting to move {item}")
            self.logger.warning(f'from {self.dir_path} to {to_folder}')
            self.weak_error = True

    def sort(self):
        # Get all items in this directory
        items_in_folder = os.listdir(self.dir_path)

        # Make a list of all the folders in this directory
        # Note this only takes the top level folders into consideration we are not interested in sub-folders
        full_folders_dir = next(os.walk(self.dir_path))[1]

        # A list of all anime we have folders of
        anime_dict = self.get_anime_dict(full_folders_dir)

        for item in items_in_folder:
            # All the anime I download ends with mkv
            # TODO add support for mp4 files
            # The mimetypes tries to guess what kind of file it is, this is to prevent other stuff with the
            # .mkv extension getting into my folders
            if item.endswith(".mkv") and 'video' in mimetypes.guess_type(item, strict=True)[0]:
                # fetch the group which did the group, done by finding the first ] in the string
                nya_format = [']', '[', ' -', '] ']
                if all(x in item for x in nya_format):
                    try:
                        subtitle_group = str(item.split(']', 1)[0]).replace('[', '', 1)
                        # fetch the name of the anime by taking everything after the first ] and before the last -
                        anime_name = str(item.split('] ', 1)[1]).rsplit(" -", 1)[0]
                    except IndexError:
                        self.logger.warning(f"Encountered an error while string slicing {item}")
                        self.weak_error = True
                        continue
                else:
                    self.logger.warning(f"Skipped {item} for not having the correct string format")
                    self.weak_error = True
                    continue

                if anime_name in anime_dict:
                    # Get the folder name associated with that anime
                    anime_path = anime_dict[anime_name]

                    if ']' in anime_path and '[' in anime_path:
                        folder_subtitle_group = str(anime_path.split(']', 1)[0]).replace('[', '', 1)
                    else:
                        # This part of the code should not trigger since it filters for these sings on dict creation
                        # Getting here means something went horribly wrong
                        self.logger.critical(f'Critical folder naming error for {anime_path}, anime: {anime_name}')
                        input('Please fix the error and then reboot the script')
                        break

                    # This check is done to see if the folder group matches the group that did the anime
                    if folder_subtitle_group == 'Multiple groups' or folder_subtitle_group == subtitle_group:

                        self.move_anime(item, anime_path)

                    else:
                        # Rename the folder so you know you have episodes from different groups
                        rename = os.path.join(self.dir_path, f'[Multiple groups] {anime_name}')

                        try:
                            # Rename the folder
                            os.rename(os.path.join(self.dir_path, anime_path), rename)
                            self.logger.info(f"Renamed the folder for {anime_name}")

                            try:
                                # Change our dict so it contains the new name of the folder
                                anime_dict.update({f'{anime_name}': f'[Multiple groups] {anime_name}'})
                            except ValueError:
                                self.logger.error("Encountered an ValueError while attempting to update the dict")
                                self.weak_error = True

                                # Update the lists to hopefully resolve this error
                                full_folders_dir = next(os.walk(self.dir_path))[1]
                                anime_dict = self.get_anime_dict(full_folders_dir)
                                self.logger.info("Updated the lists to hopefully remove the error")

                            # Move the anime to the new folder
                            self.move_anime(item, rename)

                        except FileNotFoundError:
                            self.logger.error(f"Encountered an error while attempting to rename folder {anime_path}")
                            self.logger.error(f'from {anime_path} to {rename}')
                            self.weak_error = True
                else:
                    # If we have not have a folder for the anime we will have to make a new one
                    dirty_folder_name = f'[{subtitle_group}] {anime_name}'
                    new_folder = os.path.join(self.dir_path, dirty_folder_name)
                    # I could not find a way to break os.makedir so no try except block here
                    os.makedirs(new_folder)
                    self.logger.info(f"created a new folder for the show: {anime_name}")
                    # Append the anime to our anime list
                    try:
                        anime_dict[anime_name] = dirty_folder_name
                    except ValueError:
                        # A valueError should only occur if the anime in question already has an entry
                        # This should not be possible but if it is
                        # Update the lists to hopefully resolve this error
                        self.logger.error("Encountered an ValueError while attempting to update the dict")
                        self.weak_error = True
                        full_folders_dir = next(os.walk(self.dir_path))[1]
                        anime_dict = self.get_anime_dict(full_folders_dir)
                        self.logger.info("Updated the lists to hopefully remove the error")

                    # Move the anime in the new folder
                    self.move_anime(item, new_folder)

        # if any weak errors were encountered make sure the popup window from python does not disappear
        if self.weak_error and self.logger.getEffectiveLevel() < 30:
            input("Press any key to exit \n")

    def create_script(self, log_info):
        # Technically if log_info: would also work
        if log_info is None:
            log_input = input("Do you want to enable logging?(Y/N)\n")
            logging = 'True' if log_input.upper() == 'Y' or log_input.upper() == 'YES' else 'False'
        else:
            if log_info in ["True", "False"]:
                logging = log_info
            else:
                logging = "True"

        # Get The user of this pc and the name of this file
        user_name = getpass.getuser()
        file_name = os.path.basename(__file__)

        # Make sure the script starts on startup
        try:
            bat_path = f'C:\\Users\\{user_name}\\AppData\\Roaming\\Microsoft\\Windows\\Start Menu\\Programs\\Startup'
            with open(bat_path + '\\' + "AnimeSort.bat", "w+") as bat_file:
                # TODO I might need to change "python" to "start" when making this an exe file
                bat_file.write(f'python {self.dir_path}\\{file_name}')
        except FileNotFoundError:
            print("Try checking your pc username") if bool(logging) else 0
            input("File directory for storing .bat file was not found")
        except Exception as e:
            input(f'While opening the bat file {e} went wrong')

        # Make a Config file for the script
        try:
            self.config.add_section('SORT')
        except configparser.DuplicateSectionError:
            # If this triggers the sections were not corrupted but the value of LOGGING was
            pass

        self.config['SORT']['LOGGING'] = logging
        try:
            with open(f'{self.dir_path}/{CONFIG_NAME}', 'w') as configfile:
                self.config.write(configfile)
        except FileNotFoundError:
            print("Try checking if your directory matches the file storage location") if logging else 0
            input("Could not find file directory for storing the config file")
        except Exception as e:
            input(f'While creating the bat file {e} went wrong')

        # Return if the user wanted logging enabled or not
        return bool(util.strtobool(logging))


if __name__ == '__main__':
    # Get arguments provided
    parser = argparse.ArgumentParser()
    parser.add_argument("-l", "--logging", required=False, help="Enable logging?: True/False")
    args = parser.parse_args()
    if args.logging in ["True", "False"]:
        LOG_INFO = args.logging
    else:
        # Technically LOG_INFO could be anything but we don't want users to be able to do that
        LOG_INFO = None

    # Find out the place were this script is and run the sorting
    place = os.path.dirname(os.path.realpath(__file__))
    NyaaSort(place, LOG_INFO).sort()
