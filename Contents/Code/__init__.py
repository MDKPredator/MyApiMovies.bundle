# -*- coding: utf-8 -*-
import \
    re  # import time def Log(dbgline): Log("\n\n\n----------\n\n" + time.strftime("%H:%M:%S - ") + dbgline + "\n\n---------\n\n\n")

MAM_BASE_URL = 'https://www.myapimovies.com/api/v1'

MAM_SEARCH_URL = '/movie/search?title=%s&token=%s'
MAM_SEARCH_URL_PARAM_YEAR = '&year=%s'

MAM_IMDB_MOVIE = '/movie/%s?token=%s'
MAM_IMDB_MOVIE_GENRES = '/movie/%s/genres?token=%s'
MAM_IMDB_MOVIE_COUNTRIES = '/movie/%s/countries?token=%s'
MAM_IMDB_MOVIE_CREW = '/movie/%s/crew?token=%s'
MAM_IMDB_MOVIE_ACTORS = '/movie/%s/actors?token=%s&full=true'

MAM_IMDB_SERIE_SEASON = '/movie/%s/season/%s?token=%s'
MAM_IMDB_SERIE_SEASON_EPISODE = '/movie/%s/season/%s/episode/%s?token=%s'

RE_IMDB_ID = Regex('^tt\d{7}$')

def Start():
    HTTP.CacheTime = CACHE_1DAY
    HTTP.Headers['User-Agent'] = 'Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 6.2; ' \
                                 'Trident/4.0; SLCC2; .NET CLR 2.0.50727; .NET CLR 3.5.30729; ' \
                                 '.NET CLR 3.0.30729; Media Center PC 6.0)'

class MyApiMoviesAgent(Agent.Movies):
  name, primary_provider, fallback_agent, contributes_to, languages, \
  accepts_from = ('MyApiMovies', True, False, None, [Locale.Language.English, ], ['com.plexapp.agents.localmedia'])

  def search(self, results, media, lang, manual=False):
    search(media, results, lang)

  def update(self, metadata, media, lang):
    get_results(metadata, media, 'movie')


class MyApiMoviesAgent(Agent.TV_Shows):
    name, primary_provider, fallback_agent, contributes_to, languages, accepts_from = (
    'MyApiMovies', True, False, None, [Locale.Language.English, ],
    ['com.plexapp.agents.localmedia'])  # , 'com.plexapp.agents.opensubtitles'

    def search(self, results, media, lang, manual=False):
        search(media, results, lang)

    def update(self, metadata, media, lang):
        token = ''
        if Prefs['personal_api_key'] != '':
            token = Prefs['personal_api_key']

        get_results(metadata, media, 'serie')

        @parallelize
        def UpdateEpisodes():
            for num_season in media.seasons:
                for num_episode in media.seasons[num_season].episodes:
                    episode = metadata.seasons[num_season].episodes[num_episode]

                    episode_url = MAM_BASE_URL + MAM_IMDB_SERIE_SEASON_EPISODE % (metadata.id, num_season, num_episode, token)
                    # Log('DEBUG: Episode url: ' + episode_url)
                    episode_obj = JSON.ObjectFromURL(episode_url, headers={'Accept': 'application/json'})
                    imdb_id = episode_obj['data']['imdbId']

                    url = MAM_BASE_URL + MAM_IMDB_MOVIE % (imdb_id, token)
                    # Log('DEBUG: Episode info url: ' + url)
                    json_obj = JSON.ObjectFromURL(url, headers={'Accept': 'application/json'})
                    data = json_obj['data']

                    imdb_id = data['imdbId']
                    episode.title = data['title']

                    if 'rating' in data:
                        episode.rating = float(data['rating'])

                    if 'plot' in data:
                        episode.summary = data['plot']

                    try:
                        if 'releaseDate' in data:
                            release_date = data['releaseDate']
                            if len(data) == 8:
                                year = data['releaseDate'][0:4]
                                month = data['releaseDate'][4:2]
                                day = data['releaseDate'][6:2]

                                release_date = year + '-' + month + '-' + day
                            elif len(data) == 6:
                                year = data['releaseDate'][0:4]
                                month = data['releaseDate'][4:2]

                                release_date = year + '-' + month

                        episode.originally_available_at = Datetime.ParseDate(release_date).date()
                    except:
                        pass

                    # Crew
                    get_crew(episode, imdb_id)

                    # Log('DEBUG: Epsiode [' + num_episode + '] updated')


def get_results(metadata, media, type):
  try:
    token = ''
    if Prefs['personal_api_key'] != '':
      token = Prefs['personal_api_key']

    url = MAM_BASE_URL + MAM_IMDB_MOVIE % (metadata.id, token)
    # Log('DEBUG: Result url: ' + url)

    json_obj = JSON.ObjectFromURL(
      url,
      headers={'Accept': 'application/json'}
    )

    data = json_obj['data']

    # Title
    metadata.title = data['title']

    # Poster
    if 'posterUrl' in data:
        poster_url = data['posterUrl']
        if poster_url not in metadata.posters:
            metadata.posters[poster_url] = Proxy.Preview(HTTP.Request(poster_url, sleep=0.5).content, sort_order=1)

    # Runtime
    if 'runtime' in data:
        runtime = data['runtime'].replace('min', '').strip()
        metadata.duration = int(runtime)

    # Genre(s)
    get_genres(metadata)

    # Country
    get_countries(metadata)

    # Release date
    if 'releaseDate' in data:
        release_date = data['releaseDate']

        if len(data) == 8:
            year = data['releaseDate'][0:4]
            month = data['releaseDate'][4:2]
            day = data['releaseDate'][6:2]

            release_date = year + '-' + month + '-' + day
        elif len(data) == 6:
            year = data['releaseDate'][0:4]
            month = data['releaseDate'][4:2]

            release_date = year + '-' + month

        metadata.originally_available_at = Datetime.ParseDate(release_date).date()

    # Rating
    metadata.rating = None
    if 'rating' in data:
        metadata.rating = float(data['rating'])

    # Rated
    if 'rated' in data:
        metadata.content_rating = data['rated']

    # Summary
    metadata.summary = ''
    if 'plot' in data:
        metadata.summary = data['plot']

    # Year
    if type == 'movie' and 'year' in data:
        metadata.year = int(data['year'])

    if type == 'movie':
        # Crew
        get_crew(metadata, metadata.id)

    # Cast
    get_cast(metadata, type)

    # Log('Data updated successfully')
  except Exception as e:
    #print e
    return


def get_genres(metadata):
    token = ''
    if Prefs['personal_api_key'] != '':
        token = Prefs['personal_api_key']

    # Peticion para recuperar los generos de la pelicula
    genres_url = MAM_BASE_URL + MAM_IMDB_MOVIE_GENRES % (metadata.id, token)
    # Log('DEBUG: Genres url: ' + genres_url)
    json_obj = JSON.ObjectFromURL(genres_url, headers={'Accept': 'application/json'})

    genres_data = json_obj['data']

    # Genres
    metadata.genres.clear()

    for idx, genre in enumerate(genres_data):
        metadata.genres.add(genre['genre'])


def get_countries(metadata):
    token = ''
    if Prefs['personal_api_key'] != '':
        token = Prefs['personal_api_key']

    # Peticion para recuperar los paises de la pelicula
    genres_url = MAM_BASE_URL + MAM_IMDB_MOVIE_COUNTRIES % (metadata.id, token)
    # Log('DEBUG: Countries url: ' + genres_url)
    json_obj = JSON.ObjectFromURL(genres_url, headers={'Accept': 'application/json'})

    countries_data = json_obj['data']

    # Countries
    metadata.countries.clear()

    for country in countries_data:
        metadata.countries.add(country['country'])


def get_crew(metadata, imdb_id):
    token = ''
    if Prefs['personal_api_key'] != '':
        token = Prefs['personal_api_key']

    # Peticion para recuperar la crew de la pelicula
    crew_url = MAM_BASE_URL + MAM_IMDB_MOVIE_CREW % (imdb_id, token)
    # Log('DEBUG: Crew url: ' + crew_url)
    json_obj = JSON.ObjectFromURL(crew_url, headers={'Accept': 'application/json'})

    crew_data = json_obj['data']

    # Crew
    metadata.directors.clear()
    metadata.writers.clear()
    metadata.producers.clear()

    for crew in crew_data:
        crew_name = crew['name']['name']
        if crew['type'] == 'DIRECTOR':
            meta_director = metadata.directors.new()
            try:
                meta_director.name = crew_name
            except:
                try:
                    metadata.directors.add(crew_name)
                except:
                    pass
        elif crew['type'] == 'WRITER':
            meta_writer = metadata.writers.new()
            try:
                meta_writer.name = crew_name
            except:
                try:
                    metadata.writers.add(crew_name)
                except:
                    pass


def get_cast(metadata, type):
    token = ''
    if Prefs['personal_api_key'] != '':
        token = Prefs['personal_api_key']

    # Peticion para recuperar los actores de la pelicula
    actors_url = MAM_BASE_URL + MAM_IMDB_MOVIE_ACTORS % (metadata.id, token)
    # Log('DEBUG: Actors url: ' + actors_url)
    json_obj = JSON.ObjectFromURL(actors_url, headers={'Accept': 'application/json'})

    actors_data = json_obj['data']

    if type == 'movie':
        # Actors
        metadata.roles.clear()

        for actor in actors_data:
            role = metadata.roles.new()
            role.role = actor['character']
            role.name = actor['name']['name']
            if 'photoUrl' in actor['name'] and actor['name']['photoUrl'] is not None:
                role.photo = actor['name']['photoUrl']

#            metadata.roles.add(role)
    else:
        metadata.roles.clear()

        for actor in actors_data:
            role = metadata.roles.new()
            role.role = actor['character']
            role.name = actor['name']['name']
            if 'photoUrl' in actor['name'] and actor['name']['photoUrl'] is not None:
                role.photo = actor['name']['photoUrl']


def search(media, results, lang):
    show = ''

    # print "Haciendo peticion http con titulo [" + str(media.title) + "] nombre [" + str(media.name) + "] show [" + str(show) + "] anio [" + str(media.year) + "]"
    title = media.name
    if title is None and media.show is not None:
        title = media.show

    title = String.StripDiacritics(title)
    title = String.Quote(title)

    try:
        if media.primary_metadata is not None and RE_IMDB_ID.search(media.primary_metadata.id):
            AppendSearchResult(results=results, id=media.primary_metadata.id, score=100)
        else:
            token = ''
            if Prefs['personal_api_key'] != '':
                token = Prefs['personal_api_key']

            url = MAM_BASE_URL + MAM_SEARCH_URL % (title, token)
            # Si viene informado el año se añade a la peticion
            if media.year:
                url = url + MAM_SEARCH_URL_PARAM_YEAR % media.year
            # LOG('DEBUG: Search URL: ' + url)

            # cacheTime=CACHE_1WEEK
            json_obj = JSON.ObjectFromURL(url, headers={'Accept': 'application/json'})

            data = json_obj['data']
            for movie in data:
                year = movie['year']
                if '-' in movie['year']:
                    year = movie['year'][:4]

                AppendSearchResult(results=results,
                           id=movie['imdbId'],
                           name=movie['title'],
                           year=int(year),
                           score=100,
                           lang=lang)
    except Exception as e:
        print e


def AppendSearchResult(results, id, name=None, year=-1, score=0, lang=None):
    new_result = dict(id=str(id), name=name, year=int(year), score=score, lang=lang)
    if isinstance(results, list):
        results.append(new_result)
    else:
        results.Append(MetadataSearchResult(**new_result))
