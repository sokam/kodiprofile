# -*- coding: utf-8 -*-

'''
    Genesis Add-on
    Copyright (C) 2015 lambda

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
'''


import re
import urllib
import urlparse
from modules.libraries import cleantitle
from modules.libraries import cloudflare
from modules.libraries import client
from modules.resolvers import videomega


class source:
    def __init__(self):
        self.base_link = 'http://onlinemovies.pro'
        self.search_link = 'https://www.google.com/search?q=%s&sitesearch=onlinemovies.pro'
        self.videomega_link = 'http://videomega.tv/cdn.php?ref=%s'


    def get_movie(self, imdb, title, year):
        try:
            query = self.search_link % (urllib.quote_plus(title))

            result = client.source(query)

            title = cleantitle.movie(title)
            years = ['%s' % str(year), '%s' % str(int(year)+1), '%s' % str(int(year)-1)]

            result = client.parseDOM(result, "h3", attrs = { "class": ".+?" })
            result = [(client.parseDOM(i, "a", ret="href"), client.parseDOM(i, "a")) for i in result]
            result = [(i[0][0], i[1][-1]) for i in result if len(i[0]) > 0 and len(i[1]) > 0]
            result = [i for i in result if any(x in i[0] for x in years) or  any(x in i[1] for x in years)]
            result = [i[0] for i in result if title in cleantitle.movie(i[0]) or  title in cleantitle.movie(i[1])][0]

            result = result.replace('/tag/', '/')
            result = cloudflare.source(result)

            r = client.parseDOM(result, "title")[0]

            t = re.sub('(\.|\_|\(|\[|\s)(\d{4}|3D)(\.|\_|\)|\]|\s)(.+)', '', r)
            if not title == cleantitle.movie(t): raise Exception()

            y = re.compile('[\.|\_|\(|\[|\s](\d{4})[\.|\_|\)|\]|\s]').findall(r)[0]
            if not any(x == y for x in years): raise Exception()

            result = client.parseDOM(result, "link", ret="href", attrs = { "rel": "canonical" })[0]

            try: url = re.compile('//.+?(/.+)').findall(result)[0]
            except: url = result
            url = client.replaceHTMLCodes(url)
            url = url.encode('utf-8')
            return url
        except:
            return


    def get_sources(self, url, hosthdDict, hostDict, locDict):
        try:
            sources = []

            if url == None: return sources

            url = urlparse.urljoin(self.base_link, url)
            result = client.source(url)

            fmt = re.compile('<strong>Quality</strong>.+?<strong>(.+?)</strong>').findall(result)
            if len(fmt) > 0: fmt = (' '.join((fmt[0].decode("utf-8").lower().strip()).split())).split(' ')

            if any(x in ['dvdscr', 'r5', 'r6'] for x in fmt): quality = 'SCR'
            elif any(x in ['camrip', 'tsrip', 'hdcam', 'hdts', 'dvdcam', 'dvdts', 'cam', 'ts'] for x in fmt): quality = 'CAM'
            else: quality = 'HD'

            result = client.parseDOM(result, "div", attrs = { "class": "video-embed" })[0]
            url = re.compile('hashkey=(.+?)[\'|\"]').findall(result)
            url += re.compile('[?]ref=(.+?)[\'|\"]').findall(result)
            url = self.videomega_link % url[0]

            url = videomega.resolve(url)
            if url == None: raise Exception()

            sources.append({'source': 'Videomega', 'quality': quality, 'provider': 'Onlinemovies', 'url': url})

            return sources
        except:
            return sources


    def resolve(self, url):
        return url

