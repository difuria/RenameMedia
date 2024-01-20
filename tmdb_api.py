from datetime import datetime
import os, re, requests, urllib

# https://developers.themoviedb.org/
class TMDB():    
    def __init__(self, api_key:str, api_version = 3, debug=False):
        '''
        Mandatory Arguments:
            api_key: The API key obtained from The Movie Database

        Optional Keyword Arguments:
            api_version: The version of the API to use. Default is version 3 (currently only version 3 is supported).
            debug:       Whether or not to include extra debug messages in the output.
        '''
        supported_versions = [3]
        if api_version in supported_versions:
            self.api_version = api_version
        else:
            raise ValueError(f"API version '{api_version}' is not supported. Must be {' or '.join(supported_versions)}")
        self.debug = debug
        self.set_api_key(api_key)

    def set_api_key(self, api_key:str):
        '''
        Checks the api key supplied is a valid one to save hassle later. 
        '''
        self.api_key = api_key
        output = self.get_movie(550)
        if "status_code" in output and output["status_code"] == 401:
            self.api_key = ""
            raise ValueError(output["response"]["status_message"])

    # Validation Functions
    def __valid_date(self, date:str, params: dict, format="%Y/%m/%d", key="date"):
        '''
        Checks to see if the date is in the desired format
        '''
        if date:
            try:
                datetime.strptime(date, format)
                params[key] = date
            except:
                raise ValueError(f"{date} is in the incorrect format it should be {format}")

        return params

    def __valid_float(self, value:float, params:dict, key:str):
        if value:
            try:
                value = float(value)
                if value >= 0:
                    params[key] = value
            except:
                raise ValueError(f"{value} should be an number")
        return params
    
    def __valid_int(self, value:int, params:dict, key:str):
        if value:
            try:
                value = int(value)
                if value >= 0:
                    params[key] = value
            except:
                raise ValueError(f"{value} should be an integer")
        return params

    def __valid_language(self, language:str, params:dict):
        '''
        Checks to see if the language supplied is a valid ISO 639-1 code.
        '''
        if language:
            format = "^[a-z]{2}-[A-Z]{2}$"
            if not re.search(format, language):
                raise ValueError(f"{language} is not in the correct format of '{format}'")
            for lang in self.get_languages():
                if language[:2] == lang["iso_639_1"]:
                    for country in self.get_countries():
                        if language[-2:] == country["iso_3166_1"]:
                            params["language"] = language
                            return params
            raise ValueError(f"{language} is not a valid language code.")

        return params

    def __valid_page_number(self, page:int, params:dict):
        '''
        Checks to see if the page number supplied is valid. 
        '''
        if page >= 0:
            if self.api_version == 3:
                if 1 <= page <= 1000:
                    params["page"] = page
                else:
                    raise ValueError("Page number should be inclusive of 1 and 1000")
            elif self.api_version == 4:
                if 1 <= page:
                    params["page"] = page
                else:
                    raise ValueError("Page number should be greater than 1")
        return params

    def __valid_region(self, region:str, params:dict):
        if region:
            format = "^[A-Z]{2}$"
            if not re.search(format, region):
                raise ValueError(f"{region} is not of the format {format}")
            for reg in self.get_regions():
                if region == reg['iso_3166_1']:
                    params["region"] = region
                    return params
            raise ValueError(f"{region} is not a valid region.")
        return params

    def __valid_sort_by(self, sort_by:str, params:dict, type = ""):
        '''
        Checks to see if the sort_by parameter is valid
        '''
        if self.api_version == 3:
            allowed_values = ["created_at.asc", "created_at.desc"]
        elif self.api_version == 4:
            if type == "tv":
                allowed_values = ["first_air_date.asc", "first_air_date.desc", "name.asc", "name.desc", "vote_average.asc", "vote_average.desc"]
            elif type == "movie":
                allowed_values = ["created_at.asc", "created_at.desc", "release_date.asc", "release_date.desc", "title.asc", "title.desc", "vote_average.asc", "vote_average.desc"]
            else:
                raise ValueError(f"Invalid type supplied {type}.")
        else:
            # Should never really reach here
            raise ValueError(f"Invalid api_version is being used '{self.api_version}.")

        if sort_by in allowed_values:
            params["sort_by"] = sort_by
        else:
            raise ValueError(f"Sort by should be {' or '.join(allowed_values)}")
        return params

    # ACCOUNT
    def get_account(self, session_id:str):
        '''
        Get your account details.
        https://developers.themoviedb.org/3/account/get-account-details
        '''
        return self.request("/account", { "session_id": session_id })

    def get_created_lists(self, session_id:str, account_id = -1, language = "", page = -1):
        '''
        Get all of the lists created by an account. Will include private lists if you are the owner.
        https://developers.themoviedb.org/3/account/get-created-lists
        '''
        resource = f"/account/{account_id}/lists"
        params = { "session_id": session_id }

        params = self.__valid_language(language, params)
        params = self.__valid_page_number(page, params)
        
        return self.request(resource, params)

    def get_favourite_movies(self, session_id:str, account_id = -1, sort_by = "", language =  "", page = -1):
        '''
        Get the list of your favorite movies.
        https://developers.themoviedb.org/3/account/get-favorite-movies
        '''
        return self.__get_favourite(session_id, account_id, sort_by, language, page, "movies" )

    def get_favourite_tv_shows(self, session_id:str, account_id = -1, sort_by = "", language =  "", page = -1):
        '''
        Get the list of your favorite TV shows.
        https://developers.themoviedb.org/3/account/get-favorite-movies
        '''
        return self.__get_favourite(session_id, account_id, sort_by, language, page, "tv")

    def __get_favourite(self, session_id:str, account_id:int, sort_by:str, language:str, page:int, type:str):
        '''
        get_favourite_movies, get_favourite_tv_shows differ only in the url, so this is a wrapper for executing them.
        When calling either of them should be called instead of this
        '''
        account_id = "{account_id}" if account_id == -1 else account_id
        resource = f"/account/{account_id}/favorite/{type}"

        params = { "session_id": session_id }
        
        params = self.__valid_language(language, params)
        params = self.__valid_sort_by(sort_by, params)
        params = self.__valid_page_number(page, params)
        
        return self.request(resource, params)

    def mark_as_favourite(self, session_id:str, media_type:str, media_id:str, favourite = True, content_type = "application/json;charset=utf-8", account_id = -1 ):
        '''
        This method allows you to mark a movie or TV show as a favorite item.
        https://developers.themoviedb.org/3/account/mark-as-favorite
        '''
        account_id = "{account_id}" if account_id == -1 else account_id
        resource = f"/account/{account_id}/favorite"
        params = { "session_id": session_id }
        headers = { "Content-Type": content_type}
        data = {
            "media_type": media_type,
            "media_id": media_id,
            "favourite": favourite
        }

        return self.request(resource, params, headers, data, action = "POST")

    def get_rated_movies(self, session_id:str, account_id = -1, sort_by = "", language = "", page = -1):
        '''
        Get a list of all the movies you have rated.
        https://developers.themoviedb.org/3/account/get-rated-movies
        '''
        return self.__get_rated(session_id, account_id, sort_by, language, page, "movies")

    def get_rated_tv_shows(self, session_id:str, account_id = -1, sort_by = "", language = "", page = -1):
        '''
        Get a list of all the movies you have rated.
        https://developers.themoviedb.org/3/account/get-rated-tv-shows
        '''
        return self.__get_rated(session_id, account_id, sort_by, language, page, "tv" )

    def get_rated_tv_episodes(self, session_id:str, account_id = -1, sort_by = "", language = "", page = ""):
        '''
        Get a list of all the TV episodes you have rated.
        https://developers.themoviedb.org/3/account/get-rated-tv-episodes
        '''
        return self.__get_rated(session_id, account_id, sort_by, language, page, "tv/episodes")

    def __get_rated(self, session_id:str, account_id:int, sort_by:str, language:str, page:int, type:str):
        '''
        get_rated_movies, get_rated_tv_shows and get_rated_tv_episodes differ only in the url, so this is a wrapper for executing them.
        When calling either of them should be called instead of this
        '''
        account_id = "{account_id}" if account_id == -1 else account_id

        resource = f"/account/{account_id}/rated/{type}"

        params = { "session_id": session_id }

        params = self.__valid_language(language, params)
        params = self.__valid_page_number(page, params)
        params = self.__valid_sort_by(sort_by, params)

        return self.request(resource, params)

    def get_movie_watchlist(self, session_id:str, account_id = -1, sort_by = "", language = "", page = -1):
        '''
        Get a list of all the movies you have added to your watchlist.
        https://developers.themoviedb.org/3/account/get-movie-watchlist
        '''
        return self.__get_watchlist(session_id, account_id, sort_by, language, page, "movies")  
  
    def get_tv_show_watchlist(self, session_id:str, account_id = -1, sort_by = "", language = "", page = -1):
        '''
        Get a list of all the TV shows you have added to your watchlist.
        https://developers.themoviedb.org/3/account/get-tv-show-watchlist
        '''
        return self.__get_watchlist(session_id, account_id, sort_by, language, page, "tv")
    
    def __get_watchlist(self, session_id:str, account_id:int, sort_by:str, language:str, page:int, type:str):
        '''
        get_movie_watchlist, get_tv_show_watchlist differ only in the url, so this is a wrapper for executing them.
        When calling either of them should be called instead of this
        '''
        account_id = "{account_id}" if account_id == -1 else account_id
        resource = f"/account/{account_id}/watchlist/{type}"

        params = { "session_id": session_id }

        params = self.__valid_language(language, params)
        params = self.__valid_sort_by(sort_by, params)
        params = self.__valid_page_number(page, params, type)

        return self.request(resource, params)

    def add_to_watchlist(self, session_id:str, media_type:str, media_id:int, account_id = -1, content_type = "application/json;charset=utf-8"):
        '''
        Add a movie or TV show to your watchlist.
        https://developers.themoviedb.org/3/account/add-to-watchlist
        '''
        return self.__amend_item_on_watchlist(session_id, media_type, media_id, account_id, content_type, True)

    def remove_from_watchlist(self, session_id:str, media_type:str, media_id:int, account_id = -1, content_type = "application/json;charset=utf-8"):
        '''
        Add a movie or TV show to your watchlist.
        https://developers.themoviedb.org/3/account/add-to-watchlist
        '''
        return self.__amend_item_on_watchlist(session_id, media_type, media_id, account_id, content_type, False)

    def __amend_item_on_watchlist(self, session_id:str, media_type:str, media_id:int, account_id:int, content_type:str, add:bool):
        '''
        To make the naming of add_to_watchlist and remove_from_watchlist more obvious to the user they have been seperated but as the action is similar, they are actioned here.
        '''
        account_id = "{account_id}" if account_id == -1 else account_id
        resource = f"/account/{account_id}/watchlist"

        params = { "session_id": session_id }

        headers = { "Content-Type": content_type}
        data = {
            "media_type": media_type,
            "media_id": media_id,
            "watchlist": add
        }

        return self.request(resource, params, headers, data, action = "POST")

    # AUTHENTICATION
    def create_guest_session(self):
        '''
        This method will let you create a new guest session. 
        Guest sessions are a type of session that will let a user rate movies and TV shows but not require them to have a TMDB user account.

        Please note, you should only generate a single guest session per user (or device) as you will be able to attach the ratings to a TMDB user account in the future.
        There is also IP limits in place so you should always make sure it's the end user doing the guest session actions.
        If a guest session is not used for the first time within 24 hours, it will be automatically deleted.
        https://developers.themoviedb.org/3/authentication/create-guest-session
        '''
        return self.request("/authentication/guest_session/new")

    def create_request_token(self):
        '''
        Create a temporary request token that can be used to validate a TMDB user login.
        https://developers.themoviedb.org/3/authentication/create-request-token
        '''
        return self.request("/authentication/token/new")

    def create_session(self, request_token:str):
        '''
        You can use this method to create a fully valid session ID once a user has validated the request token. 
        https://developers.themoviedb.org/3/authentication/create-session
        '''
        data = {
            "request_token": request_token
        }
        return self.request("/authentication/session/new", data=data, action="POST")

    def create_session_with_login(self, username:str, password:str, request_token:str):
        '''
        This method allows an application to validate a request token by entering a username and password.
        Not all applications have access to a web view so this can be used as a substitute.
        Please note, the preferred method of validating a request token is to have a user authenticate the request via the TMDB website.
        https://developers.themoviedb.org/3/authentication/validate-request-token
        '''
        data = {
            "username": username,
            "password": password,
            "request_token": request_token
        }
        return self.request("/authentication/token/validate_with_login", data=data, action="POST")

    def create_v3_session_with_v4_access_token(self, access_token:str):
        '''
        Use this method to create a v3 session ID if you already have a valid v4 access token.
        The v4 token needs to be authenticated by the user. Your standard "read token" will not validate to create a session ID.
        https://developers.themoviedb.org/3/authentication/create-session-from-v4-access-token
        '''
        data = {
            "access_token": access_token
        }
        return self.request("/authentication/session/convert/4", data=data, action="POST")

    def delete_session(self, session_id:str):
        '''
        If you would like to delete (or "logout") from a session, call this method with a valid session ID.
        https://developers.themoviedb.org/3/authentication/delete-session
        '''
        data = {
            "session_id":session_id
        }
        return self.request("/authentication/session", data=data, action="DELETE")

    # CERTIFICATIONS
    def get_movie_certifications(self):
        '''
        Get an up to date list of the officially supported movie certifications on TMDB.
        https://developers.themoviedb.org/3/certifications/get-movie-certifications
        '''
        return self.request("/certification/movie/list")

    def get_tv_certifications(self):
        '''
        Get an up to date list of the officially supported TV show certifications on TMDB.
        https://developers.themoviedb.org/3/certifications/get-tv-certifications
        '''
        return self.request("/certification/tv/list")

    # CHANGES
    def get_movie_change_list(self, end_date = "", start_date = "", page = -1):
        '''
        Get a list of all of the movie ids that have been changed in the past 24 hours.
        You can query it for up to 14 days worth of changed IDs at a time with the start_date and end_date query parameters. 100 items are returned per page.
        https://developers.themoviedb.org/3/changes/get-movie-change-list
        '''
        return self.__get_change_list(end_date, start_date, page, "/movie/changes")

    def get_tv_change_list(self, end_date = "", start_date = "", page = -1):
        '''
        Get a list of all of the person ids that have been changed in the past 24 hours.
        You can query it for up to 14 days worth of changed IDs at a time with the start_date and end_date query parameters. 100 items are returned per page.
        https://developers.themoviedb.org/3/changes/get-tv-change-list
        '''
        return self.__get_change_list(end_date, start_date, page, "/tv/changes")
    
    def get_person_change_list(self, end_date = "", start_date = "", page = -1):
        '''
        Get a list of all of the person ids that have been changed in the past 24 hours.
        You can query it for up to 14 days worth of changed IDs at a time with the start_date and end_date query parameters. 100 items are returned per page.
        https://developers.themoviedb.org/3/changes/get-person-change-list
        '''
        return self.__get_change_list(end_date, start_date, page, "/person/changes")

    def __get_change_list(self, end_date:str, start_date:str, page:int, resource:str):
        params = self.__valid_date(end_date, {}, key="end_date")
        params = self.__valid_date(start_date, params, key="start_date")
        params = self.__valid_page_number(page, params)
        return self.request(resource, params)

    # COLLECTIONS
    def get_collection(self, collection_id:int, language = ""):
        '''
        Get collection details by id.
        https://developers.themoviedb.org/3/collections/get-collection-details
        '''
        return self.request(f"/collection/{collection_id}", self.__valid_language(language, {}))

    def get_collection_images(self, collection_id:int, language = ""):
        '''
        Get the images for a collection by id.
        https://developers.themoviedb.org/3/collections/get-collection-images
        '''
        return self.request(f"/collection/{collection_id}/images", self.__valid_language(language, {}))

    def get_collection_translations(self, collection_id:int, language = ""):
        '''
        Get the list translations for a collection by id.
        https://developers.themoviedb.org/3/collections/get-collection-translations
        '''
        return self.request(f"/collection/{collection_id}/images", self.__valid_language(language, {}))

    # COMPANIES
    def get_company(self, company_id:int):
        '''
        Get a companies details by id.
        https://developers.themoviedb.org/3/companies/get-company-details
        '''
        return self.request(f"/company/{company_id}", { "company_id": company_id })

    def get_alternative_company_name(self, company_id:int):
        '''
        Get the alternative names of a company.
        https://developers.themoviedb.org/3/companies/get-company-alternative-names
        '''
        return self.request(f"/company/{company_id}/alternative_names", { "company_id": company_id })

    def get_company_logos(self, company_id:int):
        '''
        Get a companies logos by id.
        https://developers.themoviedb.org/3/companies/get-company-images
        '''
        return self.request(f"/company/{company_id}/images", { "company_id": company_id })

    # CONFIGURATION
    def get_configuration_information(self):
        '''
        Get the system wide configuration information. Some elements of the API require some knowledge of this configuration data.
        The purpose of this is to try and keep the actual API responses as light as possible.
        It is recommended you cache this data within your application and check for updates every few days.
        https://developers.themoviedb.org/3/configuration/get-api-configuration
        '''
        return self.request("/configuration")

    def get_countries(self):
        '''
        Get the list of countries (ISO 3166-1 tags) used throughout TMDB.
        https://developers.themoviedb.org/3/configuration/get-countries
        '''
        return self.request("/configuration/countries")

    def get_jobs(self):
        '''
        Get a list of the jobs and departments we use on TMDB.
        https://developers.themoviedb.org/3/configuration/get-jobs
        '''
        return self.request("/configuration/jobs")

    def get_languages(self):
        '''
        Get the list of languages (ISO 639-1 tags) used throughout TMDB.
        https://developers.themoviedb.org/3/configuration/get-languages
        '''       
        return self.request("/configuration/languages")

    def get_primary_translations(self):
        '''
        Get a list of the officially supported translations on TMDB.
        https://developers.themoviedb.org/3/configuration/get-primary-translations
        '''
        return self.request("/configuration/primary_translations")

    def get_timezones(self):
        '''
        Get the list of timezones used throughout TMDB.
        https://developers.themoviedb.org/3/configuration/get-timezones
        '''
        return self.request("/configuration/timezones")

    # CREDITS
    def get_credit(self, credit_id:str):
        '''
        Get a movie or TV credit details by id.
        https://developers.themoviedb.org/3/credits/get-credit-details
        '''
        return self.request(f"/credit/{credit_id}")

    # DISCOVER
    def discover_movie(self, language = "", region = "", sort_by = "",
                             certification_country = "", certification = "", certification_greater_than = "", certification_less_than = "",
                             include_adult = True, include_video = True, page = -1,
                             primary_release_year = -1, primary_release_date_greater_than = "", primary_release_date_less_than = "",
                             release_date_greater_than = "", release_date_less_than = "",
                             with_release_type = -1, year = -1,
                             vote_count_greater_than = -1, vote_count_less_than = -1,
                             vote_average_greater_than = -1, vote_average_less_than = -1,
                             with_cast = "", with_crew = "", with_people = "", with_companies = "",
                             with_genres = "", without_genres = "", with_keywords = "", without_keywords = "",
                             with_runtime_greater_than = -1, with_runtime_less_than = -1, 
                             with_original_language = "", with_watch_providers = "", watch_region = "", with_watch_monetization_types = ""):
        '''
        Discover movies by different types of data like average rating, number of votes, genres and certifications.
        https://developers.themoviedb.org/3/discover/movie-discover
        '''
        params = { "include_adult": include_adult, "include_video": include_video }
        params = self.__valid_language(language, params)
        params = self.__valid_page_number(page, params)
        params = self.__valid_region(region, params)
        
        # TODO sort_by does differ it seems and isn't covered here
        if sort_by:
            params["sort_by"] = sort_by
        
        if certification_country:
            params["certification_country"] = certification_country

        if certification:
            params["certification"] = certification
        
        if certification_greater_than:
            params["certification.gte"] = certification_greater_than

        if certification_less_than:
            params["certification.lte"] = certification_less_than
        
        params = self.__valid_int(primary_release_year, params, "primary_release_year")        
        params = self.__valid_date(primary_release_date_greater_than, params, key="primary_release_date.gte")
        params = self.__valid_date(primary_release_date_less_than, params, key="primary_release_date.lte")
        params = self.__valid_date(release_date_greater_than, params, key="release_date.gte")
        params = self.__valid_date(release_date_less_than, params, key="release_date.lte")

        if with_release_type:
            params["with_release_type"] = with_release_type

        params = self.__valid_int(year, params, "year")
        params = self.__valid_int(vote_count_greater_than, params, "vote_count.gte")
        params = self.__valid_int(vote_count_less_than, params, "vote_count.lte")

        params = self.__valid_float(vote_average_greater_than, params, "vote_average.gte")
        params = self.__valid_float(vote_average_less_than, params, "vote_average.lte")

        if with_cast:
            params["with_case"] = with_cast
        
        if with_companies:
            params["with_companies"] = with_companies

        if with_crew:
            params["with_crew"] = with_crew

        if with_genres:
            params["with_genres"] = with_genres

        if with_people:
            params["with_people"] = with_people

        if without_genres:
            params["without_genres"] = without_genres

        if with_keywords:
            params["with_keywords"] = with_keywords

        if without_keywords:
            params["without_keywords"] = without_keywords

        params = self.__valid_int(with_runtime_greater_than, params, "with_runtime.gte")
        params = self.__valid_int(with_runtime_less_than, params, "with_runtime.lte")

        if with_original_language:
            params["with_original_language"] = with_original_language

        if with_watch_providers:
            params["with_watch_providers"] = with_watch_providers

        if watch_region:
            params["watch_region"] = watch_region

        if with_watch_monetization_types:
            params["with_watch_monetization_types"] = with_watch_monetization_types

        return self.request("/discover/movie", params)

    def discover_tv(self, language = "", sort_by = "", page = -1, timezone = "",
                          air_date_greater_than = "", air_date_less_than = "",
                          first_air_date_greater_than = "", first_air_date_less_than = "", first_air_date_year = -1,
                          vote_average_greater_than = -1, vote_count_greater_than = -1,
                          with_genres = "", with_networks = "", without_genres = "",
                          with_runtimes_greater_than = -1, with_runtimes_less_than = -1,
                          include_null_first_air_dates = True, 
                          with_original_language = "", without_keywords = "",
                          screened_theatrically = True,
                          with_companies = "", with_keywords = "", with_watch_providers = "", watch_region = "", with_watch_monetization_types = ""):
        '''
        Discover TV shows by different types of data like average rating, number of votes, genres, the network they aired on and air dates.
        https://developers.themoviedb.org/3/discover/tv-discover
        '''
        params = { "include_null_first_air_dates":include_null_first_air_dates, "screened_theatrically": screened_theatrically }
        params = self.__valid_language(language, params)
        params = self.__valid_page_number(page, params)

        if sort_by:
            params["sort_by"] = sort_by

        if air_date_greater_than:
            params["air_date.gte"] = air_date_greater_than

        if air_date_less_than:
            params["air_date.lte"] = air_date_less_than

        if first_air_date_greater_than:
            params["first_air_date.gte"] = first_air_date_greater_than

        if first_air_date_less_than:
            params["first_air_date.lte"] = first_air_date_less_than

        params = self.__valid_int(first_air_date_year, params, "first_air_date_year")

        if timezone:
            params["timezone"] = timezone

        params = self.__valid_float(vote_average_greater_than, params, "vote_average.gte")
        params = self.__valid_int(vote_count_greater_than, params, "vote_count.gte")

        if with_genres:
            params["with_genres"] = with_genres

        if with_networks:
            params["with_networks"] = with_networks
        
        if without_genres:
            params["without_genres"] = without_genres

        params = self.__valid_int(with_runtimes_greater_than, params, "with_runtime.gte")
        params = self.__valid_int(with_runtimes_less_than, params, "with_runtime.lte")

        if with_original_language:
            params["with_original_language"] = with_original_language

        if without_keywords:
            params["without_keywords"] = without_keywords

        if with_companies:
            params["with_companies"] = with_companies

        if with_keywords:
            params["with_keywords"] = with_keywords

        if with_watch_providers:
            params["with_watch_providers"] = with_watch_providers

        if watch_region:
            params["watch_region"] = watch_region

        if with_watch_monetization_types:
            params["with_watch_monetization_types"] = with_watch_monetization_types

        return self.request("/discover/tv", params)

    # FIND
    def find_by_id(self, external_id:str, external_source:str, language = ""):
        '''
        The find method makes it easy to search for objects in our database by an external id.
        https://developers.themoviedb.org/3/find/find-by-id
        '''
        params = { "external_source": external_source }
        params = self.__valid_language(language, params)

        return self.request(f"/find/{external_id}", params)

    # GENRES
    def get_movie_genres(self, language = ""):
        '''
        Get the list of official genres for movies.
        https://developers.themoviedb.org/3/genres/get-movie-list
        '''
        return self.request(f"/genre/movie/list", self.__valid_language(language, {}))

    def get_tv_genres(self, language = ""):
        '''
        Get the list of official genres for TV shows.
        https://developers.themoviedb.org/3/genres/get-tv-list
        '''
        return self.request(f"/genre/tv/list", self.__valid_language(language, {}))

    # GUEST SESSIONS
    def get_guest_sessions_rated_movies(self, guest_session_id:str, language = "", sort_by = ""):
        '''
        Get the rated movies for a guest session.
        https://developers.themoviedb.org/3/guest-sessions/get-guest-session-rated-movies
        '''
        params = self.__valid_language(language, {})
        params = self.__valid_sort_by(sort_by, params)

        return self.request(f"/guest_session/{guest_session_id}/rated/movies", params)

    def get_guest_sessions_rated_tv_shows(self, guest_session_id:str, language = "", sort_by = ""):
        '''
        Get the rated TV shows for a guest session.
        https://developers.themoviedb.org/3/guest-sessions/get-guest-session-rated-movies
        '''
        params = self.__valid_language(language, {})
        params = self.__valid_sort_by(sort_by, params)

        return self.request(f"/guest_session/{guest_session_id}/rated/tv", params)

    def get_guest_sessions_rated_tv_episodes(self, guest_session_id:str, language = "", sort_by = ""):
        '''
        Get the rated TV episodes for a guest session.
        https://developers.themoviedb.org/3/guest-sessions/get-gest-session-rated-tv-episodes
        '''
        params = self.__valid_language(language, {})
        params = self.__valid_sort_by(sort_by, params)

        return self.request(f"/guest_session/{guest_session_id}/rated/tv/episodes", params)

    # KEYWORDS
    def get_keyword(self, keyword_id:int):
        '''
        https://developers.themoviedb.org/3/keywords/get-keyword-details
        '''
        self.discover_movie
        return self.request(f"/keyword/{keyword_id}")

    def get_movies_from_keyword(self, keyword_id:int):
        '''
        Get the movies that belong to a keyword.
        It is highly recommend using "movie discover (self.discover_movie)" instead of this method as it is much more flexible.
        https://developers.themoviedb.org/3/keywords/get-movies-by-keyword
        '''
        self.get_list()
        return self.request(f"/keyword/{keyword_id}/movies")

    # LISTS
    def get_list(self, list_id:int, language = ""):
        '''
        Get the details of a list.
        https://developers.themoviedb.org/3/lists/get-list-details
        '''
        return self.request(f"/list/{list_id}", self.__valid_language(language, {}))

    def get_list_item_status(self, list_id:int, movie_id:int):
        '''
        You can use this method to check if a movie has already been added to the list.
        https://developers.themoviedb.org/3/lists/check-item-status
        '''
        return self.request(f"/list/{list_id}/item_status", { "movie_id": movie_id })

    def create_a_list(self, session_id:str, content_type = "application/json;charset=utf-8"):
        '''
        Create a list.
        https://developers.themoviedb.org/3/lists/create-list
        '''
        if not content_type:
            raise ValueError("content_type must be populated")

        return self.request("/list", {"session_id": session_id}, {"Content-Type": content_type}, action="POST")

    def add_movie_to_list(self, list_id:int, session_id:str, content_type = "application/json;charset=utf-8"):
        '''
        Add a movie to a list.
        https://developers.themoviedb.org/3/lists/add-movie
        '''
        if not content_type:
            raise ValueError("content_type must be populated")

        return self.request(f"/list/{list_id}/add_item", {"session_id": session_id}, {"Content-Type": content_type}, action="POST")

    def remove_movie_from_list(self, list_id:int, session_id:str, meida_id:int, content_type = "application/json;charset=utf-8"):
        '''
        Remove a movie from a list.
        https://developers.themoviedb.org/3/lists/remove-movie
        '''
        if not content_type:
            raise ValueError("content_type must be populated")

        return self.request(f"/list/{list_id}/remove_item", {"session_id": session_id}, {"Content-Type": content_type}, {"media_id":meida_id}, action="POST")

    def clear_list(self, list_id:int, session_id, confirm = False):
        '''
        Clear all of the items from a list.
        https://developers.themoviedb.org/3/lists/clear-list
        '''
        return self.request(f"/list/{list_id}/clear", {"confirm": confirm, "session_id":session_id}, action="POST")

    def delete_list(self, list_id:int, session_id:str):
        '''
        Delete a list.
        https://developers.themoviedb.org/3/lists/delete-list
        '''
        return self.request(f"/list/{list_id}", {"session_id":session_id}, action="DELETE")

    # MOVIES
    def get_movie(self, movie_id:int, language = "", append_to_reponse = ""):
        '''
        Get the primary information about a movie.
        https://developers.themoviedb.org/3/movies/get-movie-details
        '''
        params = self.__valid_language(language, {})
        if append_to_reponse:
            params["append_to_response"] = append_to_reponse

        return self.request(f"/movie/{movie_id}", params)

    def get_movie_account_states(self, movie_id:int, session_id:str, guest_session_id = ""):
        '''
            Grab the following account states for a session:
                Movie rating
                If it belongs to your watchlist
                If it belongs to your favourite list
            https://developers.themoviedb.org/3/movies/get-movie-account-states
        '''
        params = { "session_id": session_id }
        if guest_session_id:
            params["guest_session_id"] = guest_session_id

        return self.request(f"/movie/{movie_id}/account_states", params)

    def get_alternative_movie_titles(self, movie_id:int, country = ""):
        '''
        Get all of the alternative titles for a movie.
        https://developers.themoviedb.org/3/movies/get-movie-alternative-titles
        '''
        params = {}
        if country:
            params["country"] = country

        return self.request(f"/movie/{movie_id}/alternative_titles", params)

    def get_movie_changes(self, movie_id:int, start_date = "", end_date = "", page = -1):
        '''
        Get the changes for a movie. By default only the last 24 hours are returned.
        https://developers.themoviedb.org/3/movies/get-movie-changes
        '''
        params = self.__valid_date(start_date, {})
        params = self.__valid_date(end_date, params)
        params = self.__valid_page_number(page, params)

        return self.request(f"/movie/{movie_id}/changes", params)
    
    def get_movie_credits(self, movie_id:int, language = ""):
        '''
        Get the cast and crew for a movie.
        https://developers.themoviedb.org/3/movies/get-movie-credits
        '''
        return self.request(f"/movie/{movie_id}/credits", self.__valid_language(language, {}))

    def get_movie_external_ids(self, movie_id:int):
        '''
        Get the external ids for a movie. We currently support the following external sources.
        https://developers.themoviedb.org/3/movies/get-movie-external-ids
        '''
        return self.request(f"/movie/{movie_id}/external_ids")

    def get_movie_images(self, movie_id:int, language = "", include_image_language = ""):
        '''
        Get the images that belong to a movie.
        https://developers.themoviedb.org/3/movies/get-movie-images
        '''
        params = self.__valid_language(language, {})
        if include_image_language:
            params["include_image_language"] = include_image_language

        return self.request(f"/movie/{movie_id}/images")

    def get_movie_keywords(self, movie_id:int):
        '''
        Get the keywords that have been added to a movie.
        https://developers.themoviedb.org/3/movies/get-movie-keywords
        '''
        return self.request(f"/movie/{movie_id}/keywords")

    def get_movie_lists(self, movie_id:int, language = "", page = -1):
        '''
        Get a list of lists that this movie belongs to.
        https://developers.themoviedb.org/3/movies/get-movie-lists
        '''
        params = self.__valid_language(language, {})
        params = self.__valid_page_number(page, params)
        return self.request(f"/movie/{movie_id}/lists", params)

    def get_movie_recommendations(self, movie_id:int, language = "", page = -1):
        '''
        Get a list of recommended movies for a movie.
        https://developers.themoviedb.org/3/movies/get-movie-recommendations
        '''
        params = self.__valid_language(language, {})
        params = self.__valid_page_number(page, params)
        return self.requests(f"/movie/{movie_id}/recommendations", params)

    def get_movie_release_dates(self, movie_id:int):
        '''
        Get the release date along with the certification for a movie.
        https://developers.themoviedb.org/3/movies/get-movie-release-dates
        '''
        return self.request(f"/movie/{movie_id}/release_dates")

    def get_movie_reviews(self, movie_id:int, language = "", page = -1):
        '''
        Get the user reviews for a movie.
        https://developers.themoviedb.org/3/movies/get-movie-reviews
        '''
        params = self.__valid_language(language, {})
        params = self.__valid_page_number(page, params)
        return self.requests(f"/movie/{movie_id}/reviews", params)

    def get_similar_movies(self, movie_id:int, language = "", page = -1):
        '''
        Get a list of similar movies.
        https://developers.themoviedb.org/3/movies/get-similar-movies
        '''
        params = self.__valid_language(language, {})
        params = self.__valid_page_number(page, params)
        return self.requests(f"/movie/{movie_id}/similar", params)

    def get_movie_translations(self, movie_id:int):
        '''
        Get a list of translations that have been created for a movie.
        https://developers.themoviedb.org/3/movies/get-movie-translations
        '''
        return self.request(f"/movie/{movie_id}/translations")

    def get_movie_videos(self, movie_id:int, language = ""):
        '''
        Get the videos that have been added to a movie.
        https://developers.themoviedb.org/3/movies/get-movie-videos
        '''
        return self.request(f"/movie/{movie_id}/videos", self.__valid_language(language, {}))

    def get_movie_watch_providers(self, movie_id:int):
        '''
        Powered by our partnership with JustWatch, you can query this method to get a list of the availabilities per country by provider.
        https://developers.themoviedb.org/3/movies/get-movie-watch-providers
        '''
        return self.request(f"/movie/{movie_id}/watch/providers")

    def rate_movie(self, movie_id:int, value:float, content_type = "application/json;charset=utf-8", session_id = "", guest_session_id = ""):
        '''
        Rate a movie.
        https://developers.themoviedb.org/3/movies/rate-movie
        '''
        params = self.__valid_float(value, {})

        if not content_type:
            ValueError("content_type must be supplied")
        else:
            params["Content-Type"] = content_type
        
        if session_id:
            params["session_id"] = session_id

        if guest_session_id:
            params["guest_session_id"] = guest_session_id

        return self.request(f"/movie/{movie_id}/rating", params, data={"value": value}, action="POST")

    def delete_move_rating(self, movie_id:int, content_type = "application/json;charset=utf-8", session_id = "", guest_session_id = ""):
        '''
        Remove your rating for a movie.
        https://developers.themoviedb.org/3/movies/delete-movie-rating
        '''
        params = {}
        if not content_type:
            ValueError("content_type must be supplied")
        else:
            params["Content-Type"] = content_type
        
        if session_id:
            params["session_id"] = session_id

        if guest_session_id:
            params["guest_session_id"] = guest_session_id

        return self.request(f"/movie/{movie_id}/rating", params, action="DELETE")

    def get_newest_movie(self, language = ""):
        '''
        Get the most newly created movie. This is a live response and will continuously change.
        https://developers.themoviedb.org/3/movies/get-latest-movie
        '''
        return self.request("/movie/latest", self.__valid_language(language, {}))

    def get_now_playing_movies(self, language = "", page = -1, region = ""):
        '''
        Get a list of movies in theatres. This is a release type query that looks for all movies that have a release type of 2 or 3 within the specified date range.
        https://developers.themoviedb.org/3/movies/get-now-playing
        '''
        params = self.__valid_language(language, {})
        params = self.__valid_page_number(page, params)      
        params = self.__valid_region(region , params)  
        return self.request("/movie/now_playing", params)

    def get_popular_movies(self, language = "", page = -1, region = ""):
        '''
        Get a list of the current popular movies on TMDB. This list updates daily.
        https://developers.themoviedb.org/3/movies/get-popular-movies
        '''
        params = self.__valid_language(language, {})
        params = self.__valid_page_number(page, params)      
        params = self.__valid_region(region , params)  
        return self.request("/movie/popular", params)

    def get_top_rated_movies(self, language = "", page = -1, region = ""):
        '''
        Get the top rated movies on TMDB.
        https://developers.themoviedb.org/3/movies/get-popular-movies
        '''
        params = self.__valid_language(language, {})
        params = self.__valid_page_number(page, params)      
        params = self.__valid_region(region , params)  
        return self.request("/movie/top_rated", params)

    def get_upcoming_movies(self, language = "", page = -1, region = ""):
        '''
        Get a list of upcoming movies in theatres. This is a release type query that looks for all movies that have a release type of 2 or 3 within the specified date range.
        https://developers.themoviedb.org/3/movies/get-upcoming
        '''
        params = self.__valid_language(language, {})
        params = self.__valid_page_number(page, params)      
        params = self.__valid_region(region , params)  
        return self.request("/movie/upcoming", params)

    # NETWORKS
    def get_network(self, network_id:int):
        '''
        Get the details of a network.
        https://developers.themoviedb.org/3/networks/get-network-details
        '''
        return self.request(f"/network/{network_id}")
    
    def get_network_alternative_names(self, network_id:int):
        '''
        Get the alternative names of a network.
        https://developers.themoviedb.org/3/networks/get-network-alternative-names
        '''
        return self.request(f"/network/{network_id}/alternative_names")

    def get_network_images(self, network_id:int):
        '''
        Get the TV network logos by id.
        https://developers.themoviedb.org/3/networks/get-network-images
        '''
        return self.request(f"/network/{network_id}/images")

    # TRENDING
    def get_trending(self, media_type:str, time_window:str):
        '''
        Get the daily or weekly trending items.
        The daily trending list tracks items over the period of a day while items have a 24 hour half life.
        The weekly list tracks items over a 7 day period, with a 7 day half life.
        https://developers.themoviedb.org/3/trending/get-trending
        '''
        valid_media_types = ["all", "movie", "tv", "person"]
        if media_type not in valid_media_types:
            raise ValueError(f"Media type {media_type} is not a valid type of: {', '.join(valid_media_types)}")
        
        valid_time_windows = ["day", "week"]
        if time_window not in valid_time_windows:
            raise ValueError(f"Time window {time_window} is not a valid type of: {', '.join(valid_time_windows)}")

        return self.request(f"/trending/{media_type}/{time_window}")

    # PEOPLE
    def get_person(self, person_id:int, language = "", append_to_response = ""):
        '''
        Get the primary person details by id.
        https://developers.themoviedb.org/3/people/get-person-details
        '''
        params = self.__valid_language(language, {})
        if append_to_response:
            params["append_to_response"] = append_to_response

        return self.request(f"/person/{person_id}", params)

    def get_person_changes(self, person_id:int, end_date = "", start_date = "", page = -1):
        '''
        Get the changes for a person. By default only the last 24 hours are returned.
        https://developers.themoviedb.org/3/people/get-person-changes
        '''
        params = self.__valid_page_number(page, {})
        params = self.__valid_date(end_date, params, "end_date")
        params = self.__valid_date(start_date, params, "start_date")

        return self.request(f"/person/{person_id}/changes", params)

    def get_person_movie_credits(self, person_id:int, language = ""):
        '''
        Get the movie credits for a person.
        https://developers.themoviedb.org/3/people/get-person-movie-credits
        '''
        return self.request(f"/person/{person_id}/movie_credits", self.__valid_language(language, {}))

    def get_person_tv_credits(self, person_id:int, language = ""):
        '''
        Get the TV show credits for a person.
        https://developers.themoviedb.org/3/people/get-person-tv-credits
        '''
        return self.request(f"/person/{person_id}/tv_credits", self.__valid_language(language, {}))

    def get_person_credits(self, person_id:int, language = ""):
        '''
        Get the movie and TV credits together in a single response.
        https://developers.themoviedb.org/3/people/get-person-combined-credits
        '''
        return self.request(f"/person/{person_id}/combined_credits", self.__valid_language(language, {}))

    def get_person_external_ids(self, person_id:int, language = ""):
        '''
        Get the external ids for a person.
        https://developers.themoviedb.org/3/people/get-person-external-ids
        '''
        return self.request(f"/person/{person_id}/external_ids", self.__valid_language(language, {}))
    
    def get_person_images(self, person_id:int):
        '''
        Get the images for a person.
        https://developers.themoviedb.org/3/people/get-person-images
        '''
        return self.request(f"/person/{person_id}/images")

    def get_person_tagged_images(self, person_id:int, language = "", page = -1):
        '''
        Get the images that this person has been tagged in.
        https://developers.themoviedb.org/3/people/get-tagged-images
        '''
        params = self.__valid_language(language, {})
        params = self.__valid_page_number(page, params)

        return self.request(f"/person/{person_id}/tagged_images", params)

    def get_person_tanslations(self, person_id:int, language = ""):
        '''
        Get a list of translations that have been created for a person.
        https://developers.themoviedb.org/3/people/get-person-translations
        '''
        return self.request(f"/person/{person_id}/translations", self.__valid_language(language, {}))

    def get_newest_person(self, language = ""):
        '''
        Get the most newly created person. This is a live response and will continuously change.
        https://developers.themoviedb.org/3/people/get-latest-person
        '''
        return self.request(f"/person/latest", self.__valid_language(language, {}))

    def get_popular_people(self, language = "", page = -1):
        '''
        Get the list of popular people on TMDB. This list updates daily.
        https://developers.themoviedb.org/3/people/get-popular-people
        '''
        params = self.__valid_language(language, {})
        params = self.__valid_page_number(page, params)

        return self.request("/person/popular", params)

    # REVIEWS
    def get_review(self, review_id:str):
        '''
        Retrieve the details of a movie or TV show review.
        https://developers.themoviedb.org/3/reviews/get-review-details
        '''
        return self.request(f"/review/{review_id}")

    # SEARCH
    def search_companies(self, query, page = -1):
        '''
        Search for companies.
        https://developers.themoviedb.org/3/search/search-companies
        '''
        params = { "query": query }

        return self.request("/search/company", params)

    def search_collection(self, query:str, language = "", page = -1):
        '''
        Search for collections.
        https://developers.themoviedb.org/3/search/search-companies
        '''
        params = { "query": query }

        params = self.__valid_language(language, params)
        params = self.__valid_page_number(page, params)

        return self.request("/search/company", params)

    def search_movies(self, query:str, include_adult = True, region = "", year = -1, primary_release_year = -1, language = "", page = -1):
        '''
        Search for movies.
        https://developers.themoviedb.org/3/search/search-movies
        '''
        params = { "query": query, "include_adult": include_adult }

        if region:
            params["region"] = region

        if year >= 0:
            params["year"] = year

        if primary_release_year >= 0:
            params["primary_release_year"] = primary_release_year

        params = self.__valid_language(language, params)
        params = self.__valid_page_number(page, params)

        return self.request("/search/movie", params)

    def search_multi(self, query:str, include_adult = True, region = "", language = "", page = -1, year = None):
        '''
        Search multiple models in a single request. Multi search currently supports searching for movies, tv shows and people in a single request.
        https://developers.themoviedb.org/3/search/multi-search
        '''
        params = { "query": query, "include_adult": include_adult }

        if region:
            params["region"] = region

        params = self.__valid_language(language, params)
        params = self.__valid_page_number(page, params)

        results = self.request("/search/multi", params)

        # For a general search results doesn't support the year. So loop through and remove anything from an incorrect year.
        if 'results' in results and results['results'] and year:
            temp_results = []
            for result in results['results']:
                result_datetime = None
                if 'first_air_date' in result:
                    result_datetime = datetime.strptime(result['first_air_date'], '%Y-%M-%d')
                if 'release_date' in result:
                    result_datetime = datetime.strptime(result['release_date'], '%Y-%M-%d')
                if result_datetime and result_datetime.year == year:
                    temp_results.append(result)
            
            results['results'] = temp_results[:] 

        return results

    def search_people(self, query:str, include_adult = True, reigon = "", language = "", page = -1):
        '''
        Search for people.
        https://developers.themoviedb.org/3/search/search-tv-shows
        '''
        url_directory = "/search/person"
        params = { "query": query, "include_adult": include_adult }

        params = self.__valid_language(language, params)
        params = self.__valid_page_number(page, params)

        return self.request(url_directory, params)

    def search_tv(self, query:str, first_air_date_year = -1, include_adult = True, language = "", page = -1):
        '''
        Search for TV shows.
        https://developers.themoviedb.org/3/search/search-tv-shows
        '''
        params = { "query": query, "include_adult": include_adult }

        if first_air_date_year >= 0:
            params["first_air_date_year"] = first_air_date_year

        params = self.__valid_language(language, params)
        params = self.__valid_page_number(page, params)

        return self.request("/search/tv", params)

    # TV
    def get_tv(self, id:int):
        '''
        Get the primary TV show details by id.
        https://developers.themoviedb.org/3/tv/get-tv-details
        '''
        return self.request(f"/tv/{id}")

    def get_tv_account_states(self, tv_id:int, language = "", guest_session_id= "", session_id = ""):
        '''
        Grab the following account states for a session:
            TV show rating
            If it belongs to your watchlist
            If it belongs to your favourite list
        https://developers.themoviedb.org/3/tv/get-tv-account-states
        '''
        params = self.__valid_language(language, {})
        if guest_session_id:
            params["guest_session_id"] = guest_session_id
        if session_id:
            params["session_id"] = session_id
        return self.request(f"/tv/{tv_id}/account_states", params)

    def get_tv_aggregate_credits(self, tv_id:int, language = ""):
        '''
        Get the aggregate credits (cast and crew) that have been added to a TV show.
        https://developers.themoviedb.org/3/tv/get-tv-aggregate-credits
        '''
        return self.request(f"/tv/{tv_id}/aggregate_credits", self.__valid_language(language, {}))

    def get_alternate_tv_titles(self, tv_id:int, language = ""):
        '''
        Returns all of the alternative titles for a TV show.
        https://developers.themoviedb.org/3/tv/get-tv-alternative-titles
        '''
        return self.request(f"/tv/{tv_id}/alternative_titles", self.__valid_language(language, {}))

    def get_tv_changes(self, tv_id:int, start_date = "", end_date = "", page = -1):
        '''
        Get the changes for a TV show. By default only the last 24 hours are returned.
        https://developers.themoviedb.org/3/tv/get-tv-changes
        '''
        params = self.__valid_date(start_date, {}, "start_date")
        params = self.__valid_date(end_date, params, "end_date")
        params = self.__valid_page_number(page, params)

        return self.request(f"/tv/{tv_id}/changes", params)

    def get_tv_content_rating(self, tv_id:int, language = ""):
        '''
        Get the list of content ratings (certifications) that have been added to a TV show.
        https://developers.themoviedb.org/3/tv/get-tv-content-ratings
        '''
        return self.request(f"/tv/{tv_id}/content_ratings", self.__valid_language(language, {}))

    def get_tv_credits(self, tv_id:int, language = ""):
        '''
        Get the credits (cast and crew) that have been added to a TV show.
        https://developers.themoviedb.org/3/tv/get-tv-credits
        '''
        return self.request(f"/tv/{tv_id}/credits", self.__valid_language(language, {}))

    def get_tv_episode_groups(self, tv_id:int, language = ""):
        '''
        Get all of the episode groups that have been created for a TV show. 
        https://developers.themoviedb.org/3/tv/get-tv-episode-groups
        '''
        return self.request(f"/tv/{tv_id}/episode_groups", self.__valid_language(language, {}))

    def get_tv_external_ids(self, tv_id:int, language = ""):
        '''
        Get the external ids for a TV show.
        https://developers.themoviedb.org/3/tv/get-tv-external-ids
        '''
        return self.request(f"/tv/{tv_id}/external_ids", self.__valid_language(language, {}))

    def get_tv_images(self, tv_id:int, language = ""):
        '''
        Get the images that belong to a TV show.
        https://developers.themoviedb.org/3/tv/get-tv-images
        '''
        return self.request(f"/tv/{tv_id}/images", self.__valid_language(language, {}))
    
    def get_tv_keywords(self, tv_id:int):
        '''
        Get the keywords that have been added to a TV show.
        https://developers.themoviedb.org/3/tv/get-tv-keywords
        '''
        return self.request(f"/tv/{tv_id}/keywords")

    def get_tv_recommendations(self, tv_id:int, language = "", page = -1):
        '''
        Get the list of TV show recommendations for this item.
        https://developers.themoviedb.org/3/tv/get-tv-recommendations
        '''
        params = self.__valid_language(language, {})
        params = self.__valid_page_number(page, params)
        return self.request(f"/tv/{tv_id}/recommendations", params)

    def get_tv_reviews(self, tv_id:int, language = "", page = -1):
        '''
        Get the reviews for a TV show.
        https://developers.themoviedb.org/3/tv/get-tv-reviews
        '''
        params = self.__valid_language(language, {})
        params = self.__valid_page_number(page, params)
        return self.request(f"/tv/{tv_id}/reviews", params)

    def get_tv_items_screened_theatrically(self, tv_id:int):
        '''
        Get a list of seasons or episodes that have been screened in a film festival or theatre.
        https://developers.themoviedb.org/3/tv/get-screened-theatrically
        '''
        return self.request(f"/tv/{tv_id}/screened_theatrically")
    
    def get_similar_tv_shows(self, tv_id:int, language = "", page = -1):
        '''
        Get a list of similar TV shows. These items are assembled by looking at keywords and genres.
        https://developers.themoviedb.org/3/tv/get-similar-tv-shows
        '''
        params = self.__valid_language(language, {})
        params = self.__valid_page_number(page, params)
        return self.request(f"/tv/{tv_id}/similar", params)

    def get_tv_translations(self, tv_id:int):
        '''
        Get a list of the translations that exist for a TV show.
        https://developers.themoviedb.org/3/tv/get-tv-translations
        '''
        return self.request(f"/tv/{tv_id}/translations")

    def get_tv_videos(self, tv_id:int, language = ""):
        '''
        Get the videos that have been added to a TV show.
        https://developers.themoviedb.org/3/tv/get-tv-videos
        '''
        return self.request(f"/tv/{tv_id}/videos", self.__valid_language(language, {}))

    def get_tv_watch_providers(self, tv_id:int):
        '''
        You can query this method to get a list of the availabilities per country by provider.
        https://developers.themoviedb.org/3/tv/get-tv-watch-providers
        '''
        return self.request(f"/tv/{tv_id}/watch/providers")

    def rate_tv_show(self, tv_id:int, rating:float, guest_session_id = "", session_id = "", content_type = "application/json;charset=utf-8"):
        '''
        Rate a TV show.
        https://developers.themoviedb.org/3/tv/rate-tv-show
        '''
        params = {}
        if guest_session_id:
            params["guest_session_id"] = guest_session_id
        if session_id:
            params["session_id"] = session_id
        
        headers = {
            "Content-Type":content_type
        }

        data = self.__valid_float(rating, {}, "value")
        
        return self.request(f"/tv/{tv_id}/rating", params, headers, data, action="POST")

    def remove_tv_show_rating(self, tv_id:int, guest_session_id = "", session_id = "", content_type = "application/json;charset=utf-8"):
        '''
        Rate a TV show.
        https://developers.themoviedb.org/3/tv/rate-tv-show
        '''
        params = {}
        if guest_session_id:
            params["guest_session_id"] = guest_session_id
        if session_id:
            params["session_id"] = session_id
        
        headers = {
            "Content-Type":content_type
        }
        
        return self.request(f"/tv/{tv_id}/rating", params, headers, action="DELETE")

    def get_latest_tv_show(self, language = ""):
        '''
        Get the most newly created TV show. This is a live response and will continuously change.
        https://developers.themoviedb.org/3/tv/get-latest-tv
        '''
        return self.request("/tv/latest", self.__valid_language(language, {}))

    def get_tv_airing_today(self, language = "", page = -1):
        '''
        Get a list of TV shows that are airing today.
        https://developers.themoviedb.org/3/tv/get-tv-airing-today
        '''
        params = self.__valid_language(language, {})
        params = self.__valid_page_number(page, params)
        return self.request("/tv/airing_today", params)

    def get_tv_on_air(self, language = "", page = -1):
        '''
        Get a list of shows that are currently on the air.
        https://developers.themoviedb.org/3/tv/get-tv-on-the-air
        '''
        params = self.__valid_language(language, {})
        params = self.__valid_page_number(page, params)
        return self.request("/tv/on_the_air", params)

    def get_popular_tv_shows(self, language = "", page = -1):
        '''
        Get a list of the current popular TV shows on TMDB.
        https://developers.themoviedb.org/3/tv/get-popular-tv-shows
        '''
        params = self.__valid_language(language, {})
        params = self.__valid_page_number(page, params)
        return self.request("/tv/popular", params)

    def get_top_rated_tv_shows(self, language = "", page = -1):
        '''
        Get a list of the top rated TV shows on TMDB.
        https://developers.themoviedb.org/3/tv/get-top-rated-tv
        '''
        params = self.__valid_language(language, {})
        params = self.__valid_page_number(page, params)
        return self.request("/tv/top_rated", params)

    # TV SEASONS
    def get_tv_season(self, id:int, season_number:int, language = "", append_to_result = ""):
        '''
        Get the TV season details by id.
        https://developers.themoviedb.org/3/tv-seasons/get-tv-season-details
        '''
        params = self.__valid_language(language, {})
        if append_to_result:
            params["append_to_result"] = append_to_result

        return self.request(f"/tv/{id}/season/{season_number}", params)

    # TV EPISODES

    # TV EPISODE GROUPS
    def get_tv_episode_group(self, id = "", language = ""):
        '''
        Get the details of a TV episode group. 
        https://developers.themoviedb.org/3/tv-episode-groups/get-tv-episode-group-details
        '''
        return self.request(f"/tv/episode_group/{id}", self.__valid_language(language, {}))

    # WATCH PROVIDERS
    def get_regions(self, language = ""):
        '''More intuative version of get_watch_providers_countries'''
        return self.get_watch_providers_countries(language)["results"]

    def get_watch_providers_countries(self, language = ""):
        '''
        Returns a list of all of the countries we have watch provider (OTT/streaming) data for.
        https://developers.themoviedb.org/3/watch-providers/get-available-regions
        '''
        return self.request("/watch/providers/regions", self.__valid_language(language, {}))

    def get_watch_providers_movies(self, language = "", watch_region = ""):
        '''
        Returns a list of the watch provider (OTT/streaming) data we have available for movies.
        https://developers.themoviedb.org/3/watch-providers/get-movie-providers
        '''
        params = self.__valid_language(language, {})
        params = self.__valid_region(watch_region, params)
        return self.request("/watch/providers/movie", params)

    def get_watch_providers_tv(self, language = "", watch_region = ""):
        '''
        Returns a list of the watch provider (OTT/streaming) data we have available for movies.
        https://developers.themoviedb.org/3/watch-providers/get-movie-providers
        '''
        params = self.__valid_language(language, {})
        params = self.__valid_region(watch_region, params)
        return self.request("/watch/providers/tv", params)

    # OTHER
    def request(self, resource:str, params = {}, headers = {}, data = {}, action = "GET"):
        '''
        Standardises the requests sent to tmdb.
        '''

        if not self.api_key:
            raise ValueError("Unable to request data. API key missing.")

        # DOMAIN / RESOURCE / PARAMS
        url = f"https://api.themoviedb.org/{self.api_version}{resource}?api_key={self.api_key}&{urllib.parse.urlencode(params)}"

        if self.debug:
            print(f"params:\n{params}\nurl:\n{url}\nheaders:\n{headers}\naction:\n{action}")
        
        kwargs = {}

        if headers:
            kwargs["headers"] = headers
        
        if data:
            kwargs["data"] = data

        if kwargs and self.debug:
            print(f"kwargs:\n{kwargs}")

        if action == "DELETE":
            # Delete a specified resource
            response = requests.delete(url, **kwargs)
        elif action == "GET":
            # Request data from a specified resource
            response = requests.get(url, **kwargs)
        elif action == "POST":
            # Create new for a specified resource
            response = requests.post(url, **kwargs)
        elif action == "PUT":
            # Inset, replace if already exists
            response = requests.put(url, **kwargs)
        else:
            raise ValueError(f"{action} is not a supported action.")

        if response.status_code == 200:
            return response.json()
        else:
            return { "status_code":response.status_code, "response":response.json() }

if __name__ == "__main__":
    # For quick testing purposes
    file_name = "key"
    if os.path.exists(file_name):
        with open(file_name, "r") as f:
            tmdb = TMDB(f.read().strip())
