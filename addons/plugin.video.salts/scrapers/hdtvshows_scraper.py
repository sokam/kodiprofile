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
import re
import urlparse
import xbmcaddon
import xbmc
import urllib
from salts_lib.db_utils import DB_Connection
from salts_lib import log_utils
from salts_lib.constants import VIDEO_TYPES
from salts_lib.constants import QUALITIES

BASE_URL = 'http://hdtvshows.net'

class HDTVShows_Scraper(scraper.Scraper):
    base_url = BASE_URL

    def __init__(self, timeout=scraper.DEFAULT_TIMEOUT):
        self.timeout = timeout
        self.db_connection = DB_Connection()
        self.base_url = xbmcaddon.Addon().getSetting('%s-base_url' % (self.get_name()))
        self.username = xbmcaddon.Addon().getSetting('%s-username' % (self.get_name()))
        self.password = xbmcaddon.Addon().getSetting('%s-password' % (self.get_name()))

    @classmethod
    def provides(cls):
        return frozenset([VIDEO_TYPES.TVSHOW, VIDEO_TYPES.SEASON, VIDEO_TYPES.EPISODE])

    @classmethod
    def get_name(cls):
        return 'hdtvshows.net'

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
            match = re.search('url\s*:\s*"(http[^"]+)', html)
            if match:
                stream_url = match.group(1)
                match = re.search('key=(.*)', stream_url)
                if match:
                    key = match.group(1)
                    stream_url = stream_url.replace(key, urllib.quote(key))
                hoster = {'multi-part': False, 'host': 'hdtvshows.net', 'class': self, 'url': stream_url, 'quality': QUALITIES.HIGH, 'views': None, 'rating': None, 'direct': True}
                hosters.append(hoster)
        return hosters

    def get_url(self, video):
        return super(HDTVShows_Scraper, self)._default_get_url(video)

    def _get_episode_url(self, show_url, video):
        episode_pattern = 'href="([^"]+)"\s*(?:[^>]+>){2}S%d,\s*Ep%d' % (int(video.season), int(video.episode))
        title_pattern = 'class="main-tt"[^>]+href="([^"]+)(?:[^>]*>){3}\s*(?:&nbsp;)*(.*?)</a>'
        return super(HDTVShows_Scraper, self)._default_get_episode_url(show_url, video, episode_pattern, title_pattern)

    def search(self, video_type, title, year):
        url = urlparse.urljoin(self.base_url, '/find.php?q=%s' % (urllib.quote_plus(title)))
        data = {'q': title}
        html = self._http_get(url, data=data, cache_limit=.25)
        results = []
        for match in re.finditer('b>\s*<a\s+title="\s*Watch\s+(.*?)\s+Free\s*"\s+href="([^"]+)', html, re.DOTALL):
            match_title, url = match.groups()
            result = {'url': url.replace(self.base_url, ''), 'title': match_title, 'year': ''}
            results.append(result)

        return results

    @classmethod
    def get_settings(cls):
        name = cls.get_name()
        return ['         <setting id="%s-enable" type="bool" label="%s Enabled" default="true" visible="true"/>' % (name, name),
                    '         <setting id="%s-base_url" type="text" label="     Base Url" default="%s" visible="eq(-1,true)"/>' % (name, cls.base_url),
                    '         <setting id="%s-username" type="text" label="     Username" default="" visible="eq(-2,true)"/>' % (name),
                    '         <setting id="%s-password" type="text" label="     Password" option="hidden" default="" visible="eq(-3,true)"/>' % (name)]

    def _http_get(self, url, data=None, cache_limit=8):
        # return all uncached blank pages if no user or pass
        if not self.username or not self.password:
            return ''

        if not self.__logged_in():
            log_utils.log('Logging in for url (%s)' % (url), xbmc.LOGDEBUG)
            self.__login()
        html = super(HDTVShows_Scraper, self)._cached_http_get(url, self.base_url, self.timeout, data=data, cache_limit=cache_limit)

        return html

    def __login(self):
        url = urlparse.urljoin(self.base_url, '/login.php')
        html = super(HDTVShows_Scraper, self)._cached_http_get(url, self.base_url, self.timeout, cache_limit=0)
        data = {}
        for match in re.finditer(r'type="hidden" name="(.+?)" value="(.+?)"', html):
            data[match.group(1)] = match.group(2)
        data.update({'UserUsername': self.username, 'subscriptionsPass': self.password})
        url = urlparse.urljoin(self.base_url, '/reg.php')
        html = super(HDTVShows_Scraper, self)._cached_http_get(url, self.base_url, self.timeout, data=data, cache_limit=0)
        if not self.__logged_in():
            raise Exception('hdtvshows.net login failed')

    def __logged_in(self):
        url = urlparse.urljoin(self.base_url, '/post.php')
        data = {'type': 'checklogin'}
        html = super(HDTVShows_Scraper, self)._cached_http_get(url, self.base_url, self.timeout, data=data, cache_limit=0)
        return html.startswith(self.username)
