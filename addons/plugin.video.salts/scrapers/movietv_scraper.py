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
import json
import random
import time
import urllib
from salts_lib import kodi
from salts_lib import dom_parser
from salts_lib import log_utils
from salts_lib.constants import VIDEO_TYPES
from salts_lib.constants import FORCE_NO_MATCH
from salts_lib.constants import QUALITIES
from salts_lib.constants import XHR


BASE_URL = 'http://movietv.to'
SEASON_URL = '/series/season?id=%s&s=%s&_=%s'
LINK_URL = '/series/getLink?id=%s&s=%s&e=%s'

BR_VERS = [
    ['%s.0' % i for i in xrange(18, 42)],
    ['41.0.2228.0', '41.0.2227.1', '41.0.2227.0', '41.0.2226.0', '40.0.2214.93', '37.0.2062.124']]
WIN_VERS = ['Windows NT 6.3', 'Windows NT 6.1', 'Windows NT 6.0', 'Windows NT 5.0', 'Windows 3.1']
MV_UAS = ['Mozilla/5.0 ({win_ver}; WOW64; rv:{br_ver}) Gecko/20100101 Firefox/{br_ver}',
          'Mozilla/5.0 ({win_ver}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{br_ver} Safari/537.36']

class MovieTV_Scraper(scraper.Scraper):
    base_url = BASE_URL

    def __init__(self, timeout=scraper.DEFAULT_TIMEOUT):
        self.timeout = timeout
        self.base_url = kodi.get_setting('%s-base_url' % (self.get_name()))

    @classmethod
    def provides(cls):
        return frozenset([VIDEO_TYPES.TVSHOW, VIDEO_TYPES.EPISODE, VIDEO_TYPES.MOVIE])

    @classmethod
    def get_name(cls):
        return 'movietv.to'

    def resolve_link(self, link):
        return link

    def format_source_label(self, item):
        label = '[%s] %s ' % (item['quality'], item['host'])
        return label

    def get_sources(self, video):
        source_url = self.get_url(video)
        hosters = []
        if source_url and source_url != FORCE_NO_MATCH:
            if video.video_type == VIDEO_TYPES.EPISODE:
                source_url += '&_=%s' % (str(int(time.time()) * 1000))
            url = urlparse.urljoin(self.base_url, source_url)
            headers = {'Referer': self.base_url + '/'}
            html = self._http_get(url, headers=headers, cache_limit=1)
            sources = {}
            if video.video_type == VIDEO_TYPES.MOVIE:
                for match in re.finditer('var\s+(videolink[^\s]*)\s*=\s*"([^"]+)', html):
                    var_name, stream_url = match.groups()
                    if 'hd' in var_name:
                        quality = QUALITIES.HD1080
                    else:
                        quality = QUALITIES.HD720
                    sources[stream_url] = quality
            else:
                try:
                    js_data = json.loads(html)
                except ValueError:
                    log_utils.log('Invalid JSON returned: %s: %s' % (url, html), log_utils.LOGWARNING)
                else:
                    sources[js_data['url']] = QUALITIES.HD720
                
            for match in re.finditer('<source[^>]+src=["\']([^\'"]+)[^>]+type=[\'"]video', html):
                sources[match.group(1)] = QUALITIES.HD720
                
            for source in sources:
                stream_url = source + '|Referer=%s&Cookie=%s' % (urllib.quote(url), self.__get_stream_cookies())
                hoster = {'multi-part': False, 'host': self._get_direct_hostname(stream_url), 'class': self, 'url': stream_url, 'quality': sources[source], 'views': None, 'rating': None, 'direct': True}
                hosters.append(hoster)

        return hosters

    def __get_stream_cookies(self):
        cj = self._set_cookies(self.base_url, {})
        cookies = []
        for cookie in cj:
            cookies.append('%s=%s' % (cookie.name, cookie.value))
        return urllib.quote(';'.join(cookies))

    def get_url(self, video):
        return super(MovieTV_Scraper, self)._default_get_url(video)

    def _get_episode_url(self, show_url, video):
        url = urlparse.urljoin(self.base_url, show_url)
        html = self._http_get(url, cache_limit=1)
        match = re.search("var\s+id\s*=\s*'?(\d+)'?", html)
        if match:
            show_id = match.group(1)
            season_url = SEASON_URL % (show_id, video.season, str(int(time.time()) * 1000))
            season_url = urlparse.urljoin(self.base_url, season_url)
            html = self._http_get(season_url, cache_limit=1)
            try:
                js_data = json.loads(html)
            except ValueError:
                log_utils.log('Invalid JSON returned: %s: %s' % (url, html), log_utils.LOGWARNING)
            else:
                force_title = self._force_title(video)
                if not force_title:
                    for episode in js_data:
                            if int(episode['episode_number']) == int(video.episode):
                                return LINK_URL % (show_id, video.season, episode['episode_number'])
                
                if (force_title or kodi.get_setting('title-fallback') == 'true') and video.ep_title:
                    norm_title = self._normalize_title(video.ep_title)
                    for episode in js_data:
                        if norm_title == self._normalize_title(episode['title']):
                            return LINK_URL % (show_id, video.season, episode['episode_number'])
        
    def search(self, video_type, title, year):
        results = []
        url = urlparse.urljoin(self.base_url, '/index/loadmovies')
        if video_type == VIDEO_TYPES.MOVIE:
            query_type = 'movie'
        else:
            query_type = 'tv'
        data = {'loadmovies': 'showData', 'page': 1, 'abc': 'All', 'genres': '', 'sortby': 'Popularity', 'quality': 'All', 'type': query_type, 'q': title}
        html = self._http_get(url, data=data, headers=XHR, cache_limit=2)

        for item in dom_parser.parse_dom(html, 'div', {'class': 'item'}):
            match = re.search('href="([^"]+).*?class="movie-title">\s*([^<]+).*?movie-date">(\d+)', item, re.DOTALL)
            if match:
                link, match_title, match_year = match.groups()
                if not year or not match_year or int(year) == int(match_year):
                    result = {'url': self._pathify_url(link), 'title': match_title, 'year': match_year}
                    results.append(result)

        return results

    def _http_get(self, url, data=None, headers=None, allow_redirect=True, cache_limit=8):
        if headers is None: headers = {}
        index = random.randrange(len(MV_UAS))
        headers['User-Agent'] = MV_UAS[index].format(win_ver=random.choice(WIN_VERS), br_ver=random.choice(BR_VERS[index]))
        return super(MovieTV_Scraper, self)._cached_http_get(url, self.base_url, self.timeout, data=data, headers=headers, allow_redirect=allow_redirect, cache_limit=cache_limit)
