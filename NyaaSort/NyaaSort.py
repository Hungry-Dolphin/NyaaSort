import os
import shutil
import configparser
import getpass
import mimetypes

CONFIG_NAME = 'SortConfig.ini'


class NyaaSort:

    def __init__(self, dir_path):
        self.dir_path = dir_path
        self.config = configparser.ConfigParser()
        self.weak_errors = False

        # Check if this is not the first time starting
        if os.path.exists(os.path.join(dir_path, CONFIG_NAME)):
            self.config.read(os.path.join(dir_path, CONFIG_NAME))
            try:
                # Get config settings
                logging = bool(self.config.get('SORT', 'LOGGING'))
                self.logging = logging
            except configparser.NoOptionError or configparser.NoSectionError or configparser.DuplicateSectionError:
                print("Config file was corrupted, creating a new one")
                os.remove(os.path.join(dir_path, CONFIG_NAME))
                self.logging = self.create_script()
        else:
            # If it is the first time starting it will setup all needed parameters
            print("Creating new config")
            # Please note that the create script sets up everything and returns if the user wants logging enabled
            self.logging = self.create_script()

    def get_anime_dict(self, folders):
        anime_dict = dict()

        for folder in folders:
            if '] ' in folder:
                anime = folder.split('] ', 1)[1]
                if anime in anime_dict:
                    input(f"Found an anime which has 2 folders {anime}") if self.logging else 0
                else:
                    anime_dict[anime] = folder
        return anime_dict

    def move_anime(self, item, to_folder):
        try:
            # Move the anime to the renamed folder
            shutil.move(os.path.join(self.dir_path, item), os.path.join(self.dir_path, to_folder, item))
        except FileNotFoundError:
            print(f"Encountered an error while attempting to move {item}") if self.logging else 0
            print(f'from {self.dir_path} to {to_folder}') if self.logging else 0
            self.weak_errors = True if self.logging else False

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
                        print(f"Encountered an error while string slicing {item}") if self.logging else 0
                        self.weak_errors = True if self.logging else False
                        continue
                else:
                    print(f"Skipped {item} for not having the correct string format") if self.logging else 0
                    self.weak_errors = True if self.logging else False
                    continue

                if anime_name in anime_dict:
                    anime_path = anime_dict[anime_name]

                    if ']' in anime_path and '[' in anime_path:
                        folder_subtitle_group = str(anime_path.split(']', 1)[0]).replace('[', '', 1)
                    else:
                        input(f'Critical folder naming error, the folder for {anime_name} has a faulty name')
                        continue

                    # This check is done to see if the folder group matches the group that did the anime
                    if folder_subtitle_group == 'Multiple groups' or folder_subtitle_group == subtitle_group:

                        self.move_anime(item, anime_path)

                    else:
                        # Rename the folder so you know you have episodes from different groups
                        rename = os.path.join(self.dir_path, f'[Multiple groups] {anime_name}')

                        try:
                            # Rename the folder
                            os.rename(os.path.join(self.dir_path, anime_path), rename)
                            print(f'Renamed the folder of {anime_name}') if self.logging else 0

                            try:
                                # Change our dict so it contains the new name of the folder
                                anime_dict.update({f'{anime_name}': f'[Multiple groups] {anime_name}'})
                            except ValueError:
                                print("Encountered an ValueError while attempting to update the dict") if self.logging else 0
                                # Update the lists to hopefully resolve this error
                                full_folders_dir = next(os.walk(self.dir_path))[1]
                                anime_dict = self.get_anime_dict(full_folders_dir)

                            self.move_anime(item, rename)

                        except FileNotFoundError:
                            print(f"Encountered an error while attempting to rename folder {anime_path}") if self.logging else 0
                            print(f'from {anime_path} to {rename}') if self.logging else 0
                            self.weak_errors = True if self.logging else False
                else:
                    # If we have not have a folder for the anime we will have to make a new one
                    dirty_folder_name = f'[{subtitle_group}] {anime_name}'
                    new_folder = os.path.join(self.dir_path, dirty_folder_name)
                    # I could not find a way to break os.makedir so no try except block here
                    os.makedirs(new_folder)
                    print(f"created a new folder for the show: {anime_name}") if self.logging else 0
                    # Append the anime to our anime list
                    try:
                        anime_dict[anime_name] = dirty_folder_name
                    except ValueError:
                        # A valueError should only occur if the anime in question already has an entry
                        # This should not be possible but if it is
                        # Update the lists to hopefully resolve this error
                        full_folders_dir = next(os.walk(self.dir_path))[1]
                        anime_dict = self.get_anime_dict(full_folders_dir)
                        print(f'Encountered a value error while trying to add {anime_name} to dict') if self.logging else 0
                        self.weak_errors = True if self.logging else False

                    # Move the anime in the new folder
                    self.move_anime(item, new_folder)

        # if any weak errors were encountered make sure the popup window from python does not disappear
        if self.weak_errors:
            input('')

    def create_script(self):
        # TODO add support for entering if you want logging in the command line
        log = input("Do you want to enable logging?(Y/N)\n")
        logging = 'True' if log.upper() == 'Y' or log.upper() == 'YES' else 'False'
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
            print("Try checking your pc username") if logging else 0
            input("File directory for storing .bat file was not found")
        except Exception as e:
            input(f'While opening the bat file {e} went wrong')

        # Make a Config file for the script
        self.config.add_section('SORT')
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
        return bool(logging)


if __name__ == '__main__':
    # Find out the place were this script is and run the sorting
    place = os.path.dirname(os.path.realpath(__file__))
    NyaaSort(place).sort()
