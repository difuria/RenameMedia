from datetime import datetime
from sys import platform
from pathlib import Path
from tmdb_api import TMDB
import argparse, os, re, sys

if platform == "win32":
    with open("key", "r") as f:
        api_key = f.read()
elif platform == "linux":
    api_key = os.environ.get("TMDB_KEY")
else:
    print("Unsupported platform")
    sys.exit(1)

class RenameMedia:
    INVALID_EXTENSIONS = ["dat", "inf", "pdx", "txt"]
    RESOLUTIONS = "(720p|1080p|2160p)"

    def __init__(self, tmdb, debug = False, validate = False) -> None:
        self.tmdb = tmdb
        self.debug = debug
        self.validate = validate

    def convert_int_to_str(self, number):
        # TODO in the rare occassions where a season has more than 10 episodes we need to have more 0's
        if number < 10:
            return f"0{number}"
        else:
            return str(number)

    def __rename_base_folder(self, folder, name, year):
        # First rename folder
        media_folder_name = f"{name} ({year})"
        new_folder_name = os.path.join(str(Path(*Path(folder).parts[:-1])), media_folder_name) + os.path.sep
        print(f"Renaming:\n{folder}\nto:\n{new_folder_name}")

        if not os.path.exists(new_folder_name) and not self.validate:
            self.__rename(folder, new_folder_name)
                
        if not self.validate:
            folder = new_folder_name
        return folder, media_folder_name

    def __rename(self, from_location, to_location, attempts=0):
        # TODO deal with unicode or multibyte or wide character
        to_location = self.__remove_unicode(to_location)
        try:
            os.rename(from_location, to_location)
        except UnicodeEncodeError as e:
            reason = str(e)
            print(f"UnicodeEncodeError for {to_location} For:\n {reason}")
        except OSError as e:
            reason = str(e)
            print(f"OSError for {to_location} For:\n {reason}")
        except Exception as e:
            print(f"Unable to rename {from_location}:\n{e}")
        finally:
            # Raise an expection that we don't know what to do if attempts are too high
            pass

    def __remove_unicode(self, text):
        # https://www.codetable.net/unicodecharacters
        # Contains a list of characters we don't / can't use

        # Unsure as to why at the moment but can't use regex such as \xf[a-c]9 instead 
        replacements = [
            { 'from': '\u2013', 'to': '-' },
            { 'from': '\u2019', 'to': '\'' },
            { 'from': '\xf9', 'to': 'u' },
            { 'from': '\xf9', 'to': 'u' },
            { 'from': '\xfa', 'to': 'u' },
            { 'from': '\xfb', 'to': 'u' },
            { 'from': '\xfc', 'to': 'u' }
        ]

        for replacement in replacements:
            text = text.replace(replacement['from'], replacement['to'])

        return text

    def remove_invalid_characters(self, name):
        # File names accross OS's which shouldn't be used to allow interos operability
        # So give them a mapping of what to rename them to
        invalid_characters = { "<":"", ">":"", ":":" -", "\"":"", "/":"", "\\":"", "|":"", "?":".", "*":"" }

        invalid_filenames = ['AUX',
                             'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9', 'CON',
                             'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9', 
                             'NUL', 
                             'PRN']

        for character in invalid_characters:
            if character != "?" or (character == "?" and not re.search(r"\.{1,}\?", name)):
                name = name.replace(character, invalid_characters[character])
            elif character == "?":
                name = name.replace(character, "")
        
        if name in invalid_filenames:
            name += "."

        return name
    
    def show(self, item, id, show_name, year):
        show_name = self.remove_invalid_characters(f"{show_name}")

        if os.path.isdir(item):
            folder = item
            items = os.listdir(folder)
            files = []
            # Confirm we don't have any seasons folders in here
            for item in items:
                path = os.path.join(folder, item)
                if os.path.isfile(path):
                    files.append(item)
                elif os.path.isdir(path):
                    subitems = os.listdir(path)
                    for subitem in subitems:
                        files.append(os.path.join(item, subitem))

            
            show_folder, show_folder_name = self.__rename_base_folder(folder, show_name, year)
        else:
            path = os.sep.join(item.split(os.sep)[:-1])
            file_name = item.split(os.sep)[-1]
            show_folder_name = f"{show_name} ({year})"
            show_folder = os.path.join(path, show_folder_name)
            if not self.validate:
                if not os.path.isdir(show_folder):
                    os.makedirs(show_folder)
                os.rename(item, os.path.join(show_folder, file_name))
            folder = show_folder
            files = [file_name]

        for file in files:
            extension = file.split(".")[-1]

            if extension in self.INVALID_EXTENSIONS:
                continue

            # Temporarily remove extension so it's not caught by accident by anything
            file_name = re.sub(fr"\.{extension}$", "", file)
            season_episode = re.search(r"([sS](\d{2})[eE](\d{2}))", file_name)

            # Only rename shows we know the season and episode number
            if season_episode:
                season, episode = map(int, season_episode.groups()[1:3])

                resolution = re.search(rf"{self.RESOLUTIONS}", file_name)
                resolution = f" [{resolution.group(0)}]" if resolution else ""
                
                # Possibly worth adding an if not found for futurama just minus 3 seasons
                season_info = self.tmdb.get_tv_season(id, season)
                if 'status_code' in season_info and season_info['status_code'] == 404:
                    print(f"Requested season {season} for id {id} and got")
                    print(season_info["response"])
                    continue
                season_year = season_info["air_date"].split("-")[0]

                # Check that there are at least the correct number of episodes
                if len(season_info["episodes"]) < episode:
                    print(f"Episode S{self.convert_int_to_str(season)}E{self.convert_int_to_str(episode)} doesn't appear to exist, so skipping.")
                    continue
                episode_name = self.remove_invalid_characters(season_info["episodes"][episode-1]["name"])
                season_name = self.remove_invalid_characters("Specials" if season == 0 else f"Season {season}")

                season_folder_name = f"{season_name} ({season_year}){resolution}"
                new_filename = f"S{self.convert_int_to_str(season)}E{self.convert_int_to_str(episode)} - {episode_name}.{extension}"

                season_folder = os.path.join(show_folder, season_folder_name)
                if not os.path.isdir(season_folder):
                    print(f"Creating {season_folder}")
                    if not self.validate:
                        os.makedirs(season_folder)

                if not self.validate:
                    from_location = os.path.join(show_folder, f"{file_name}.{extension}")
                    to_location = os.path.join(season_folder, new_filename)
                    if not os.path.exists(os.path.join(show_folder, f"{file_name}.{extension}")):
                        from_location = os.path.join(folder, f"{file_name}.{extension}")

                    self.__rename(from_location, to_location)

                if self.debug:
                    print(show_folder_name, season_folder_name, new_filename)

            # TODO if nothing remains in an old folder delete it.

    def movie(self, item, movie_name, year):
        # First rename folder
        movie_name = self.remove_invalid_characters(movie_name)
        print(item)
        print(movie_name)
        print(year)
        if os.path.isdir(item):
            folder, movie_folder_name = self.__rename_base_folder(item, movie_name, year)
            for file in os.listdir(folder):
                # Need to check the file name is the movie
                extension = file.split(".")[-1]

                # Certain extensions we know are no good
                if extension in self.INVALID_EXTENSIONS:
                    continue

                # Temporarily remove extension so it's not caught by accident by anything
                file_name = re.sub(rf"\.{extension}$", "", file)

                resolution = self.__get_resolution(file_name, folder)

                movie_file_name = f"{movie_folder_name}{resolution}.{extension}"
                print(f"Renaming '{file}' to '{movie_file_name}'")
                if not self.validate:
                    from_location = os.path.join(folder, file)
                    to_location = os.path.join(folder, movie_file_name)
                    self.__rename(from_location, to_location)
        else:
            base_folder = os.path.dirname(item)
            original_name = os.path.basename(item)
            extension = item.split(".")[-1]
            resolution = self.__get_resolution(original_name)

            folder_name = f"{movie_name} ({year})"
            new_name = f"{folder_name}{resolution}.{extension}"

            path = os.path.join(base_folder, folder_name)
            if not os.path.exists(path) and not self.validate:
                os.mkdir(path)

            from_location = item
            to_location = os.path.join(path, new_name)
            print(f"Renaming '{from_location}' to '{to_location}'")
            if not self.validate:
                self.__rename(from_location, to_location)
    
    def __get_resolution(self, item, folder=""):
        resolution = re.search(rf"{self.RESOLUTIONS}", item)
        if not resolution:
            resolution = re.search(rf"{self.RESOLUTIONS}", os.path.basename(os.path.dirname(folder)))

        return f" [{resolution.group(0)}]" if resolution else ""

class IdentifyMedia:
    SUPPORTED_TYPES = ['movie', 'tv']

    def __init__(self, tmdb, item, name = None, year = None, type = None, debug = False) -> None:
        self.tmdb = tmdb
        self.item = item

        self.id = None
        self.name = name
        self.year = year
        self.type = type

        self.identity = None
        self.media = False # We don't want to be renaming non media files.
        self.results = []
        self.potential = []

        self.debug = debug

    def identify(self):
        if not self.item:
            raise Exception('Folder has not been specified.')
        
        if self.identity:
            response = None
            accepted_responses = ['y', 'n']
            
            while not response in accepted_responses:
                if response != None and not response in accepted_responses:
                    print(f'Invalid response of {response}.')
                potential_responses = '/'.join(accepted_responses)
                response = input(f'This media is currently identified as "{self.name}" "{self.year}". Would you like to try to identify again ({potential_responses})?')
        else:
            response = 'y'

        if response == 'n':
            return
        else:
            self.identity = None
        
        if not self.name:
            self.enquire()
        else:
            self.search_media(self.name)

        while not self.identity:
            print(f'\nNo identity could be located the following: {self.item}')
            print('So the following informaiton is required:')

            self.name = input('What is the title of the media? ')

            self.year = None
            while self.year == None:
                self.year = input('What is the year of release? ')
                if re.search(r'^\d{4}$', self.year):
                    self.year = int(self.year)
                else:
                    print(f"Year should be an integer.")
                    self.year = None
            
            self.type = None
            while self.type == None:
                self.type = input('What type of media is it (tv/movie)? ').lower()
                types = "/".join(self.SUPPORTED_TYPES)
                if self.type.lower() in self.SUPPORTED_TYPES:
                    self.type = self.type.lower()
                else:
                    print(f"Type should be one of {types}.")
                    self.type = None

            results, name = self.search_media(self.name)
            if results:
                self.__evaluate_results(results)
                self.confirm_identity()
                if self.identity:
                    self.results = results

    def __remove_unicode(self, text):
        # https://www.codetable.net/unicodecharacters
        # Contains a list of characters we don't / can't use

        # Unsure as to why at the moment but can't use regex such as \xf[a-c]9 instead 
        replacements = [
            { 'from': '\u2013', 'to': '-' },
            { 'from': '\u2019', 'to': '\'' },
            { 'from': '\xf9', 'to': 'u' },
            { 'from': '\xf9', 'to': 'u' },
            { 'from': '\xfa', 'to': 'u' },
            { 'from': '\xfb', 'to': 'u' },
            { 'from': '\xfc', 'to': 'u' }
        ]

        for replacement in replacements:
            text = text.replace(replacement['from'], replacement['to'])

        return text

    def confirm_identity(self):
        for result in self.potential:
            if ('media_type' in result and result['media_type'] == 'tv') or self.type == 'tv':
                date = 'first_air_date'
                name = 'name'
            elif ('media_type' in result and result['media_type'] == 'movie') or self.type == 'movie':
                date = 'release_date'
                name = "title"
            else:
                if self.debug:
                    print(f'Unsupported media type: {result["media_type"]}')
                continue
            response = ''
            title = ''
            valid_responses = ['y', 'n', 's']
            while response not in valid_responses:
                print(f'\nFor "{self.item}"')
                title = self.__remove_unicode(result[name])
                if self.type == None:
                    response = input(f'Is "{title}" "{result[date]}" "{result["media_type"]}" correct? ')
                else:
                    response = input(f'Is "{title}" "{result[date]}" "{self.type}" correct? ')

                if not response.lower() in valid_responses:
                    print(f'Invlaid response of {response}')
                else:
                    response = response.lower()
            
            if response == 'n':
                continue
            elif response == 's':
                print('Skipping')
                break

            self.identity = result
            self.id = result['id']
            self.name = title
            self.year = datetime.strptime(result[date], '%Y-%M-%d').year
            if self.type == None:
                self.type = result['media_type']
            break

    def search_media(self, potential_name:str):
        name = self.name if self.name else potential_name
        if self.debug:
            print(f"Searching for {name}")
        if self.type == "tv":
            results = self.tmdb.search_tv(name, first_air_date_year = self.year)
        elif self.type == "movie":
            results = self.tmdb.search_movies(name, year = self.year)
        else:
            results = self.tmdb.search_multi(name)
        
        return results, name
    
    def __evaluate_results(self, results, original_folder_name):
        '''
        When checking results ensure there is something there
        '''
        if 'results' in results:
            self.potential = []
            for result in results['results']:
                if result['media_type'] not in self.SUPPORTED_TYPES:
                    # e.g. A person may have the same name as a movie or tv show.
                    if self.debug:
                        print(f'Result is not a supported type:\n{result}')
                elif ('name' in result and not result['name']) or \
                   ('title' in result and not result['title']):
                    if self.debug:
                        print('No name specified for result')
                        continue
                elif ('release_date' in result and not result['release_date']) or \
                    ('first_air_date' in result and not result['first_air_date']):
                    if self.debug:
                        print(f'Unable to locate a release date for:\n{result}')
                        continue
                else:
                    year = None
                    if 'release_date' in result and result['release_date']:
                        year = result['release_date']
                    elif 'first_air_date' in result and result['first_air_date']:
                        year = result['first_air_date']

                    # If the year is folder name move it to the top of the list as it'll be the most likely
                    if year == None:
                        print(result)
                    year = datetime.strptime(year, '%Y-%M-%d').year
                    if re.search(rf".*{year}.*", original_folder_name):
                        self.potential.insert(0, result)
                    else:
                        self.potential.append(result)

    def enquire(self):
        name = os.path.basename(self.item)
        original_folder_name = name

        tidy_up_text_attempts = [
            ["(\.|\s)([sS]\d{2,}|(720|1080|2160)p)(\.|\s).*", ""],
            ["\.", " "],
            ["(\.|\s)[sS]\d{2,}[eE]\d{2,}.*", ""], # Remove and potential series and episode identifiers 
            ["(\.|\s)\d{4}.*", ""], # Remove any potential Dates
            ["(\.|\s)[sS]\d{2,}[eE]\d{2,}.*", ""], # Remove and potential series and episode identifiers (Again TODO to look into why it needs to be done again) 
            ["(\.|\s)\(\d{4}\).*", ""], # Remove any dates in braces
            ["(s|S)\d{2,}(-|_)(s|S)\d{2,}", ""], # Remove any season to season information
            ["(s|S)\d{2,}(e|E)\d{2,}.*", ""], # Remove any potential season episode information
            ["(s|S)\d{2,}", ""] # Remove any potential lone season information
        ]
        
        for attempt in tidy_up_text_attempts:
            if not self.results or not self.results["results"]:
                name = re.sub(rf"{attempt[0]}", rf"{attempt[1]}", name)
                results, name = self.search_media(name)
                if results:
                    self.__evaluate_results(results, original_folder_name)
                    self.confirm_identity()
                    if self.identity:
                        self.results = results
                        break
            else:
                break

def valid_year(y):
    '''Validate the year parsed is in an expected year format'''
    if re.search(r"^(19\d{2}|2[0-2]\d{2})$", y):
        return int(y)
    else:
        raise argparse.ArgumentTypeError(f"Not a valid year: {y}")

def standardise_path(path:str) -> str:
    '''Ensure all slashes are the same'''
    path = path.replace("/", os.path.sep).replace("\\", os.path.sep)
    # Remove all tailing seperators
    while (path.strip()[-1] == os.path.sep):
        path = path.strip()[:-1]

    return path

def check_directory_exists(path):
    if not os.path.isdir(path):
        print(f"{path} doesn't exist.")
        sys.exit(3)

def check_file_exists_and_is_supported(file):
    # https://support.plex.tv/articles/203824396-what-media-formats-are-supported/
    supported_extensions = ['asf', 'avi', 'mov', 'mp4', 'mpeg', 'mpegts', 'ts', 'mkv', 'wmv']
    if not os.path.exists(file):
        print(f"{path} does not exist")
        sys.exist(3)
    
    extension = file.split(".")[-1]
    if extension.lower() not in supported_extensions and args.debug:
        print(f"{extension} is not supported.")
        return False
    
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process Inputs")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('-d', '--directory', help="Directory where multiple media items exist. Year, name cannot be supplied when using this flag.")
    group.add_argument('-f', '--folder', help="Folder Where Content is found")
    group.add_argument('-i', '--item', help="Media item")
    parser.add_argument('-t', '--type', help="Type of contents to be analysed. Default is tv", choices={"movie", "tv"})
    parser.add_argument('-n', '--name', help="Name of the movie/ tv show. If not supplied the script will try to work this out from the folder name.")
    parser.add_argument('-y', '--year', type=valid_year, default=-1,
                        help="The year the content was originally aired (helps to determine the correct content). If not supplied the script will try to calculate this from the results.")
    parser.add_argument('-v', '--validate', type=bool, default=False, choices={True, False}, help='View what would happen without actually making the changes.')
    parser.add_argument('-debug', type=bool, default=False, choices={True, False}, help="Add any debugging messages.")

    if len(sys.argv) <= 1:
        print("No arguments supplied")
        sys.exit(1) 

    try:
        parser.parse_args(sys.argv[1:])
    except:
        sys.exit(2)

    args = parser.parse_args()
    tmdb = TMDB(api_key, debug=args.debug)

    items = []
    if args.folder:
        check_directory_exists(args.folder)
        args.folder = standardise_path(args.folder)
        items = [args.folder]
    elif args.item:
        if not check_file_exists_and_is_supported(args.item):
            sys.exit(0)

        items = [args.item]
    elif args.directory:
        check_directory_exists(args.directory)
        errors = []
        if args.year > -1:
            errors.append("year")
        if args.name:
            errors.append("name")

        if errors:
            msg = " and ".join(errors)
            print(f'Cannot supply {msg} with the directory flag')
            sys.exit(3)        

        args.directory = standardise_path(args.directory)
        for directory in os.listdir(args.directory):
            path = os.path.join(args.directory, directory)
            if os.path.isdir(path):
                items.append(path)
            elif check_file_exists_and_is_supported(path):
                items.append(path)

    objects = []
    # First identify all media
    for i, item in enumerate(items):
        objects.append({
            'Item':item,
            'Identity': IdentifyMedia(tmdb, item, args.name, args.year, args.type, args.debug),
            'Rename': RenameMedia(tmdb, args.debug, args.validate)
        })

        objects[i]['Identity'].identify()

    for object in objects:
        if not object['Identity'].identity:
            continue

        if object['Identity'].type == 'tv':
            object['Rename'].show(object['Identity'].item, object['Identity'].id, object['Identity'].name, object['Identity'].year)
        elif object["Identity"].type == 'movie':
            object['Rename'].movie(object['Identity'].item, object['Identity'].name, object['Identity'].year)