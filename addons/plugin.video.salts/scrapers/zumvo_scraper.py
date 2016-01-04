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
import base64
import time
from salts_lib import kodi
from salts_lib import log_utils
from salts_lib.constants import VIDEO_TYPES
from salts_lib.constants import FORCE_NO_MATCH
from salts_lib.constants import QUALITIES

BASE_URL = 'http://zumvo.so'
QUALITY_MAP = {'HD': QUALITIES.HIGH, 'CAM': QUALITIES.LOW, 'BR-RIP': QUALITIES.HD720, 'UNKNOWN': QUALITIES.MEDIUM, 'SD': QUALITIES.HIGH}
AJAX_URL = '/ajax/?episode_id=%s&film_id=%s&episode-time=%s'

class Zumvo_Scraper(scraper.Scraper):
    base_url = BASE_URL

    def __init__(self, timeout=scraper.DEFAULT_TIMEOUT):
        self.timeout = timeout
        self.base_url = kodi.get_setting('%s-base_url' % (self.get_name()))
        self.ajax_url = urlparse.urljoin(self.base_url, AJAX_URL)

    @classmethod
    def provides(cls):
        return frozenset([VIDEO_TYPES.MOVIE])

    @classmethod
    def get_name(cls):
        return 'zumvo.com'

    def resolve_link(self, link):
        return link

    def format_source_label(self, item):
        label = '[%s] %s' % (item['quality'], item['host'])
        if item['views'] is not None:
            label += ' (%s views)' % (item['views'])
        return label

    def get_sources(self, video):
        source_url = self.get_url(video)
        hosters = []
        if source_url and source_url != FORCE_NO_MATCH:
            url = urlparse.urljoin(self.base_url, source_url)
            html = self._http_get(url, cache_limit=.5)
            match = re.search('href="([^"]+)"\s*class="player_btn_big"', html)
            if match:
                url = match.group(1)
                html = self._http_get(url, cache_limit=.5)
                            
                q_str = ''
                match = re.search('class="status">([^<]+)', html)
                if match:
                    q_str = match.group(1)
                
                views = None
                match = re.search('Views:</dt>\s*<dd>(\d+)', html, re.DOTALL)
                if match:
                    views = match.group(1)
                
                match = re.search('data-film-id\s*=\s*"([^"]+)', html)
                if match:
                    film_id = match.group(1)
                    for match in re.finditer('data-episode-id\s*=\s*"([^"]+)', html):
                        episode_id = match.group(1)
                        now = int(time.time() * 1000)
                        ajax_url = self.ajax_url % (episode_id, film_id, now)
                        ajax_html = self._http_get(ajax_url, cache_limit=.5)
                        ajax_html = ajax_html.replace('\\"', '"').replace('\/', '/')
                        match = re.search('<iframe[^>]+src="([^"]+)', ajax_html)
                        if match:
                            stream_url = match.group(1)
                            host = urlparse.urlparse(stream_url).hostname
                            direct = False
                            quality = QUALITY_MAP.get(q_str, QUALITIES.HIGH)
                        else:
                            match = re.search('proxy\.link":\s*"([^"&]+)', html)
                            if match:
                                proxy_link = match.group(1)
                                proxy_link = proxy_link.split('*', 1)[-1]
                                stream_url = self._gk_decrypt(base64.urlsafe_b64decode('NlFQU1NQSGJrbXJlNzlRampXdHk='), proxy_link)
                                if self._get_direct_hostname(stream_url) == 'gvideo':
                                    host = self._get_direct_hostname(stream_url)
                                    direct = True
                                    quality = self._gv_get_quality(stream_url)
                                else:
                                    continue
                            else:
                                continue
                                                
                        hoster = {'multi-part': False, 'url': stream_url, 'class': self, 'quality': quality, 'host': host, 'rating': None, 'views': views, 'direct': direct}
                        hosters.append(hoster)

        return hosters

    def get_url(self, video):
        return super(Zumvo_Scraper, self)._default_get_url(video)

    def search(self, video_type, title, year):
        search_url = urlparse.urljoin(self.base_url, '/search/')
        search_url += urllib.quote_plus(title)
        html = self._http_get(search_url, cache_limit=0)
        results = []
        match = re.search('ul class="list-film"(.*?)</ul>', html, re.DOTALL)
        if match:
            result_fragment = match.group(1)
            pattern = 'class="name">\s*<a\s+href="([^"]+)"\s+title="Watch\s+(.*?)\s+\((\d{4})\)'
            for match in re.finditer(pattern, result_fragment, re.DOTALL):
                url, title, match_year = match.groups('')
                if not year or not match_year or year == match_year:
                    result = {'url': self._pathify_url(url), 'title': title, 'year': match_year}
                    results.append(result)
        return results

    def _http_get(self, url, cache_limit=8):
        html = super(Zumvo_Scraper, self)._cached_http_get(url, self.base_url, self.timeout, cache_limit=cache_limit)
        cookie = self._get_sucuri_cookie(html)
        if cookie:
            log_utils.log('Setting Zumvo cookie: %s' % (cookie), log_utils.LOGDEBUG)
            html = super(Zumvo_Scraper, self)._cached_http_get(url, self.base_url, self.timeout, cookies=cookie, cache_limit=0)
        return html
