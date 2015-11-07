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
import base64
import string
import urlparse
import urllib
from salts_lib import kodi
from salts_lib import log_utils
from salts_lib import dom_parser
from salts_lib.constants import VIDEO_TYPES
from salts_lib.constants import USER_AGENT
from salts_lib.constants import QUALITIES

BASE_URL = 'http://shush.se'
KEY = base64.urlsafe_b64decode('Z2h3VTJiNk5RWFZpbkk3dnFFeW8=')
QUALITY_MAP = {'MOBILE': QUALITIES.LOW, 'LOWEST': QUALITIES.LOW, 'LOW': QUALITIES.MEDIUM, 'SD': QUALITIES.HIGH, 'HD': QUALITIES.HD720}
REFERER = 'http://player.shush.tv/player.swf'

class Shush_Scraper(scraper.Scraper):
    base_url = BASE_URL
    
    def __init__(self, timeout=scraper.DEFAULT_TIMEOUT):
        self.timeout = timeout
        self.base_url = kodi.get_setting('%s-base_url' % (self.get_name()))
   
    @classmethod
    def provides(cls):
        return frozenset([VIDEO_TYPES.TVSHOW, VIDEO_TYPES.SEASON, VIDEO_TYPES.EPISODE, VIDEO_TYPES.MOVIE])
    
    @classmethod
    def get_name(cls):
        return 'Shush.se'
    
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
            html = re.sub('\/\*.*?\*\/', '', html, flags=re.DOTALL)
            if detect(html):
                html = unpack(html)
                html = html.replace("\\'", "'")

            match = re.search("proxy\.link='\+([^+]+)", html)
            if match:
                match = re.search('var\s+%s\s*=\s*([^(]+)\(([^)]+)' % (match.group(1)), html)
                if match:
                    func, var = match.groups()
                    var_match = re.search('var\s+%s\s*=\s*"([^"]+)' % (var), html)
                    func_match = re.search('function\s+%s\(.*?\)\s*{var\s+[^=]+="([^="]+)' % (func), html)
                    if var_match and func_match:
                        proxy_link = self.__decode(var_match.group(1), func_match.group(1))
                        proxy_link = proxy_link.split('*', 1)[-1]
                        stream_url = self._gk_decrypt(KEY, proxy_link)
                        sources = {}
                        for php_host in ['http://srv.player.shush.tv', 'http://player.shush.tv/ce9boreB59']:
                            for php_url in ['/d/plugins_player.php', '/o/plugins_player.php', '/f/plugins_player.php', '/d/HunDheKLsMcKjI.php']:
                                data = {'url': stream_url, 'isslverify': 'true', 'ihttpheader': 'true', 'iheader': 'true', 'iagent': USER_AGENT}
                                php_url = php_host + php_url
                                html = self._http_get(php_url, data=data, cache_limit=0)
                                if 'google' in stream_url or 'picasa' in stream_url:
                                        if 'fmt_stream_map' in html:
                                            sources = self.__parse_fmt(html)
                                        else:
                                            sources = self.__parse_fmt2(html)
                                        direct = True
                                        if sources: break
                                elif 'ok.ru' in stream_url:
                                    if html:
                                        sources = self.__parse_fmt3(html)
                                    direct = True
                                    if sources: break
                                else:
                                    sources = {stream_url: QUALITIES.HIGH}
                                    direct = False
                                    host = urlparse.urlparse(stream_url).hostname
                                    break
                            
                            if sources: break
                
                        if sources:
                            for source in sources:
                                stream_url = source + '|User-Agent=%s&Referer=%s' % (USER_AGENT, urllib.quote(REFERER))
                                host = self._get_direct_hostname(stream_url)
                                hoster = {'multi-part': False, 'url': stream_url, 'class': self, 'quality': sources[source], 'host': host, 'rating': None, 'views': None, 'direct': direct}
                                hosters.append(hoster)
         
        return hosters

    def __decode(self, data, custom):
        standard = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/'
        return base64.b64decode(data.translate(string.maketrans(custom, standard)))
            
    def __parse_fmt(self, html):
        html = re.sub('\s', '', html)
        html = html.replace('\\u0026', '&')
        html = html.replace('\\u003d', '=')
        sources = {}
        formats = {}
        for match in re.finditer('\["(.*?)","(.*?)"\]', html):
            key, value = match.groups()
            if key == 'fmt_stream_map':
                items = value.split(',')
                for item in items:
                    source_fmt, source_url = item.split('|')
                    sources[source_url] = source_fmt
            elif key == 'fmt_list':
                items = value.split(',')
                for item in items:
                    format_key, q_str, _ = item.split('/', 2)
                    w, _ = q_str.split('x')
                    formats[format_key] = self._width_get_quality(w)
        
        for source in sources:
            sources[source] = formats[sources[source]]
        return sources
    
    def __parse_fmt2(self, html):
        pattern = '"url"\s*:\s*"([^"]+)"\s*,\s*"height"\s*:\s*\d+\s*,\s*"width"\s*:\s*(\d+)\s*,\s*"type"\s*:\s*"video/'
        sources = {}
        for match in re.finditer(pattern, html):
            url, width = match.groups()
            url = url.replace('%3D', '=')
            sources[url] = self._width_get_quality(width)
        return sources

    def __parse_fmt3(self, html):
        sources = {}
        html = html.replace('\\&quot;', '"')
        html = html.replace('&quot;', '"')
        html = html.replace('\\\\', '\\')
        html = html.decode('unicode_escape')
        match = re.search('"videos"\s*:\s*\[(.*?)\]', html)
        if match:
            for match in re.finditer('"name"\s*:\s*"([^"]+)"\s*,\s*"url"\s*:\s*"([^"]+)', match.group(1)):
                name, url = match.groups()
                quality = QUALITY_MAP.get(name.upper(), QUALITIES.HIGH)
                sources[url] = quality
        return sources
            
    def get_url(self, video):
        return super(Shush_Scraper, self)._default_get_url(video)
    
    def search(self, video_type, title, year):
        search_url = urlparse.urljoin(self.base_url, '/index.php')
        if video_type == VIDEO_TYPES.MOVIE:
            search_url += '?movies'
        else:
            search_url += '?shows'
        html = self._http_get(search_url, cache_limit=.25)
        match = re.search('\.([^:]+):hover\s*{\s*border', html, re.DOTALL)
        if match:
            klass = match.group(1)
        else:
            klass = 'klass'
        
        results = []
        norm_title = self._normalize_title(title)
        for element in dom_parser.parse_dom(html, 'div', {'class': klass}):
            url = dom_parser.parse_dom(element, 'a', ret='href')
            if video_type == VIDEO_TYPES.MOVIE:
                match_title_year = dom_parser.parse_dom(element, 'img', ret='title')
            else:
                match_title_year = dom_parser.parse_dom(element, 'span', {'class': 'caption'})
    
            if match_title_year and url:
                url = url[0]
                match_title_year = match_title_year[0]
                match = re.search('(.*)(?:\s+\((\d{4})\))', match_title_year)
                if match:
                    match_title, match_year = match.groups()
                else:
                    match_title = match_title_year
                    match_year = ''
                
                if norm_title in self._normalize_title(match_title) and (not year or not match_year or year == match_year):
                    if not url.startswith('/'): url = '/' + url
                    result = {'url': url, 'title': match_title, 'year': match_year}
                    results.append(result)

        return results
    
    def _get_episode_url(self, show_url, video):
        episode_pattern = '<a\s+href="([^"]+)"[^<]+Season\s+%s\s+Episode:\s+%s' % (video.season, video.episode)
        title_pattern = '<a\s+href="([^"]+)"[^<]+Season\s+\d+\s+Episode:\s+\d+\s+-\s+([^<]+)'
        url = super(Shush_Scraper, self)._default_get_episode_url(show_url, video, episode_pattern, title_pattern)
        if url and not url.startswith('/'): url = '/' + url
        return url
        
    def _http_get(self, url, data=None, cache_limit=8):
        return super(Shush_Scraper, self)._cached_http_get(url, self.base_url, self.timeout, data=data, cache_limit=cache_limit)

def detect(source):
    """Detects whether `source` is P.A.C.K.E.R. coded."""
    source = source.replace(' ', '')
    if re.search('eval\(function\(p,a,c,k,e,(?:r|d)', source): return True
    else: return False

def unpack(source):
    """Unpacks P.A.C.K.E.R. packed js code."""
    payload, symtab, radix, count = _filterargs(source)

    if count != len(symtab):
        raise UnpackingError('Malformed p.a.c.k.e.r. symtab.')

    try:
        unbase = Unbaser(radix)
    except TypeError:
        raise UnpackingError('Unknown p.a.c.k.e.r. encoding.')

    def lookup(match):
        """Look up symbols in the synthetic symtab."""
        word = match.group(0)
        return symtab[unbase(word)] or word

    source = re.sub(r'\b\w+\b', lookup, payload)
    return _replacestrings(source)

def _filterargs(source):
    """Juice from a source file the four args needed by decoder."""
    argsregex = (r"}\('(.*)', *(\d+), *(\d+), *'(.*?)'\.split\('\|'\)")
    args = re.search(argsregex, source, re.DOTALL).groups()

    try:
        return args[0], args[3].split('|'), int(args[1]), int(args[2])
    except ValueError:
        raise UnpackingError('Corrupted p.a.c.k.e.r. data.')

def _replacestrings(source):
    """Strip string lookup table (list) and replace values in source."""
    match = re.search(r'var *(_\w+)\=\["(.*?)"\];', source, re.DOTALL)

    if match:
        varname, strings = match.groups()
        startpoint = len(match.group(0))
        lookup = strings.split('","')
        variable = '%s[%%d]' % varname
        for index, value in enumerate(lookup):
            source = source.replace(variable % index, '"%s"' % value)
        return source[startpoint:]
    return source


class Unbaser(object):
    """Functor for a given base. Will efficiently convert
    strings to natural numbers."""
    ALPHABET = {
        62: '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ',
        95: (' !"#$%&\'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ'
             '[\]^_`abcdefghijklmnopqrstuvwxyz{|}~')
    }
    
    def __init__(self, base):
        self.base = base

        # If base can be handled by int() builtin, let it do it for us
        if 2 <= base <= 36:
            self.unbase = lambda string: int(string, base)
        else:
            if base < 62:
                self.ALPHABET[base] = self.ALPHABET[62][0:base]
            elif 62 < base < 95:
                self.ALPHABET[base] = self.ALPHABET[95][0:base]
            # Build conversion dictionary cache
            try:
                self.dictionary = dict((cipher, index) for index, cipher in enumerate(self.ALPHABET[base]))
            except KeyError:
                raise TypeError('Unsupported base encoding.')

            self.unbase = self._dictunbaser

    def __call__(self, string):
        return self.unbase(string)

    def _dictunbaser(self, string):
        """Decodes a  value to an integer."""
        ret = 0
        for index, cipher in enumerate(string[::-1]):
            ret += (self.base ** index) * self.dictionary[cipher]
        return ret

class UnpackingError(Exception):
    """Badly packed source or general error. Argument is a
    meaningful description."""
    pass
