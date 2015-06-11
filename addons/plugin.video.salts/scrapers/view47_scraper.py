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
import urllib
import urlparse
import re
import xbmcaddon
from salts_lib.constants import VIDEO_TYPES
from salts_lib.db_utils import DB_Connection

BASE_URL = 'http://view47.com'
EPID_URL = '/ip.temp/swf/plugins/ipplugins.php'
JSON_URL = '/ip.temp/swf/plugins/plugins_player.php'

class View47_Scraper(scraper.Scraper):
    base_url = BASE_URL

    def __init__(self, timeout=scraper.DEFAULT_TIMEOUT):
        self.timeout = timeout
        self.db_connection = DB_Connection()
        self.base_url = xbmcaddon.Addon().getSetting('%s-base_url' % (self.get_name()))
        if 'www' in self.base_url: self.base_url = BASE_URL  # hack base url to work

    @classmethod
    def provides(cls):
        return frozenset([VIDEO_TYPES.MOVIE])

    @classmethod
    def get_name(cls):
        return 'view47'

    def resolve_link(self, link):
        return link

    def format_source_label(self, item):
        return '[%s] %s' % (item['quality'], item['host'])

    def get_sources(self, video):
        source_url = self.get_url(video)
        hosters = []
        if source_url:
            url = urlparse.urljoin(self.base_url, source_url)
            html = self._http_get(url, cache_limit=.5)
            for match in re.finditer('file\s*:\s*"([^"]+).*?label\s*:\s*"([^p"]+)', html):
                stream_url, height = match.groups()
                hosters.append({'multi-part': False, 'url': stream_url, 'class': self, 'quality': self._height_get_quality(height), 'host': 'view47.com', 'rating': None, 'views': None, 'direct': True})

        return hosters

    def get_url(self, video):
        return super(View47_Scraper, self)._default_get_url(video)

    def search(self, video_type, title, year):
        search_url = urlparse.urljoin(self.base_url, '/search/%s.html' % (urllib.quote_plus(title)))
        html = self._http_get(search_url, cache_limit=.25)
        results = []
        pattern = 'class="year">(\d{4}).*?href="([^"]+)"\s+title="([^"]+)'
        for match in re.finditer(pattern, html):
            match_year, url, title = match.groups()
            if not year or not match_year or year == match_year:
                result = {'title': title, 'year': match_year, 'url': url.replace(self.base_url, '')}
                results.append(result)
        return results

    def _http_get(self, url, data=None, cache_limit=8):
        return super(View47_Scraper, self)._cached_http_get(url, self.base_url, self.timeout, data=data, cache_limit=cache_limit)
