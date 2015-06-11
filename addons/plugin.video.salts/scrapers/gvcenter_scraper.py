"""
    SALTS XBMC Addon
    Copyright (C) 2014 tknorris

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
import scraper
import xbmc
import urllib
import urlparse
import re
import xbmcaddon
import json
from salts_lib.db_utils import DB_Connection
from salts_lib import log_utils
from salts_lib.constants import VIDEO_TYPES

BASE_URL = 'http://www.gearscenter.com/'
SEARCH_URL = '/cartoon_control/gapi-202/?param_10=AIzaSyBsxsynyeeRczZJbxE8tZjnWl_3ALYmODs&param_7=2.0.2&param_8=com.appcenter.sharecartoon&os=android&versionCode=202&op_select=search_catalog&q='
SOURCE_URL = '/cartoon_control/gapi-202/?param_10=AIzaSyBsxsynyeeRczZJbxE8tZjnWl_3ALYmODs&param_7=2.0.2&param_8=com.appcenter.sharecartoon&os=android&versionCode=202&op_select=films&param_15=0&id_select='
RESULT_URL = '/video_type=%s&catalog_id=%s'
EPISODE_URL = RESULT_URL + '&season=%s&episode=%s'

class GVCenter_Scraper(scraper.Scraper):
    base_url = BASE_URL

    def __init__(self, timeout=scraper.DEFAULT_TIMEOUT):
        self.timeout = timeout
        self.db_connection = DB_Connection()
        self.base_url = xbmcaddon.Addon().getSetting('%s-base_url' % (self.get_name()))

    @classmethod
    def provides(cls):
        return frozenset([VIDEO_TYPES.TVSHOW, VIDEO_TYPES.SEASON, VIDEO_TYPES.EPISODE, VIDEO_TYPES.MOVIE])

    @classmethod
    def get_name(cls):
        return 'GVCenter'

    def resolve_link(self, link):
        return link

    def format_source_label(self, item):
        if 'resolution' in item:
            return '[%s] (%s) %s' % (item['quality'], item['resolution'], item['host'])
        else:
            return '[%s] %s' % (item['quality'], item['host'])

    def get_sources(self, video):
        source_url = self.get_url(video)
        sources = []
        if source_url:
            params = urlparse.parse_qs(source_url)
            show_url = SOURCE_URL + params['catalog_id'][0]
            url = urlparse.urljoin(self.base_url, show_url)
            html = self._http_get(url, cache_limit=.5)
            try:
                js_data = json.loads(html)
                if video.video_type == VIDEO_TYPES.EPISODE:
                    js_data = self.__get_episode_json(params, js_data)
            except ValueError:
                log_utils.log('Invalid JSON returned for: %s' % (url), xbmc.LOGWARNING)
            else:
                for film in js_data['films']:
                    for match in re.finditer('(http.*?(?:#(\d+)#)?)(?=http|$)', film['film_link']):
                        link, height = match.groups()
                        if height is None: height = 360  # Assumed medium quality if not found
                        source = {'multi-part': False, 'url': link, 'host': self.get_name(), 'class': self, 'quality': self._height_get_quality(height), 'views': None, 'rating': None, 'direct': True, 'resolution': '%sp' % (height)}
                        sources.append(source)

        return sources

    def __get_episode_json(self, params, js_data):
            new_data = {'films': []}
            for film in js_data['films']:
                if ' S%02dE%02d ' % (int(params['season'][0]), int(params['episode'][0])) in film['film_name']:
                    new_data['films'].append(film)
            return new_data

    def get_url(self, video):
        return super(GVCenter_Scraper, self)._default_get_url(video)

    def search(self, video_type, title, year):
        results = []
        search_url = urlparse.urljoin(self.base_url, SEARCH_URL)
        search_url += urllib.quote_plus(title)
        html = self._http_get(search_url, cache_limit=.25)
        if html:
            try:
                js_data = json.loads(html)
            except ValueError:
                log_utils.log('Invalid JSON returned for: %s' % (search_url), xbmc.LOGWARNING)
            else:
                for item in js_data['categories']:
                    match = re.search('(.*?)\s+\((\d{4}).?\d{0,4}\s*\)', item['catalog_name'])
                    if match:
                        match_title, match_year = match.groups()
                    else:
                        match_title = item['catalog_name']
                        match_year = ''
                    
                    if not year or not match_year or year == match_year:
                        result_url = RESULT_URL % (video_type, item['catalog_id'])
                        result = {'title': match_title, 'url': result_url, 'year': match_year}
                        results.append(result)
        return results

    def _get_episode_url(self, show_url, video):
        params = urlparse.parse_qs(show_url)
        source_url = SOURCE_URL + params['catalog_id'][0]
        url = urlparse.urljoin(self.base_url, source_url)
        html = self._http_get(url, cache_limit=.5)
        try:
            js_data = json.loads(html)
        except ValueError:
            log_utils.log('Invalid JSON returned for: %s' % (url), xbmc.LOGWARNING)
        else:
            force_title = self._force_title(video)
            if not force_title:
                for film in js_data['films']:
                    if ' S%02dE%02d ' % (int(video.season), int(video.episode)) in film['film_name']:
                        return EPISODE_URL % (video.video_type, params['catalog_id'][0], video.season, video.episode)
            
            if (force_title or xbmcaddon.Addon().getSetting('title-fallback') == 'true') and video.ep_title:
                norm_title = self._normalize_title(video.ep_title)
                for film in js_data['films']:
                    match = re.search('-\s*S(\d+)E(\d+)\s*-\s*(.*)', film['film_name'])
                    if match:
                        season, episode, title = match.groups()
                        if title and norm_title == self._normalize_title(title):
                            return EPISODE_URL % (video.video_type, params['catalog_id'][0], int(season), int(episode))

    def _http_get(self, url, data=None, cache_limit=8):
        return super(GVCenter_Scraper, self)._cached_http_get(url, self.base_url, self.timeout, data=data, cache_limit=cache_limit)
