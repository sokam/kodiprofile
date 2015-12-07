"""
    Kodi urlresolver plugin
    Copyright (C) 2014  The Highway

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

from t0mm0.common.net import Net
from urlresolver.plugnplay.interfaces import UrlResolver
from urlresolver.plugnplay.interfaces import PluginSettings
from urlresolver.plugnplay import Plugin
from urlresolver import common
import urllib,urllib2,re


class Play44Resolver(Plugin, UrlResolver, PluginSettings):
    implements = [UrlResolver, PluginSettings]
    name = "play44.net"
    domains = ["play44.net", "byzoo.org", "playpanda.net", "playbb.me", "videozoo.me", "videowing.me"]

    def __init__(self):
        p = self.get_setting('priority') or 99
        self.priority = int(p)
        self.net = Net()
        self.pattern = 'http://((?:www\.)*(?:play44\.net|byzoo\.org|playpanda\.net|playbb\.me|videozoo\.me|videowing\.me)/(?:embed[/0-9a-zA-Z]*?|gplus)(?:\.php)*)\?.*?((?:vid|video|id)=[%0-9a-zA-Z_\-\./]+|.*)[\?&]*.*'

    def get_url(self, host, media_id):
        if media_id: return 'http://%s?%s' % (host, media_id)
        else: return 'http://%s' % host

    def get_host_and_id(self, url):
        r = re.search(self.pattern, url)
        if r: return r.groups()
        else: return False

    def valid_url(self, url, host):
        if self.get_setting('enabled') == 'false': return False
        for a in self.domains:
          if a.lower()==host.lower().replace('www.','').replace('http://','').replace('https://',''):
            return True
        return re.match(self.pattern, url) or self.name in host

    def get_media_url(self, host, media_id):
        web_url = self.get_url(host, media_id)
        stream_host = ''
        new_host = re.search('([0-9a-zA-Z\.]+)/', host)
        if new_host: host = new_host.group(1)
        try:
            resp = self.net.http_GET(web_url)
            html = resp.content
            resp = None
        except urllib2.URLError, e:
            common.addon.log_error(self.name + ': got HTTP Error %d %s while fetching %s' % (e.code, e.reason, web_url))
            return self.unresolvable(code=3, msg=e)
        r = re.search('(?:playlist:|timer\s*=\s*null;).+?url\s*[:=]+\s*[\'"]+(.+?)[\'"]+', html, re.DOTALL)
        if r:
            stream_url = urllib.unquote_plus(r.group(1))
            if 'http' not in stream_url: #add
                if ('/gplus.php' in stream_url) or ('/picasa.php' in stream_url): stream_url = 'http://' + host + stream_url #indent
                elif ('gplus.php' in stream_url) or ('picasa.php' in stream_url): stream_url = 'http://' + host + '/' + stream_url #indent
            new_host = re.search('http(?:s)*://([0-9a-zA-Z\.]+)/', stream_url)
            if new_host: stream_host = new_host.group(1)
            opener = urllib2.build_opener()
            opener.addheaders = [('User-agent', 'Mozilla/5.0')]
            opener.addheaders = [('Host', stream_host)]
            try:
                """ Quick test for redirected stream_url """
                resp = opener.open(stream_url)
                if stream_url != resp.geturl(): stream_url = resp.geturl()
            except urllib2.URLError, e:
                if e.code == 403:
                    if stream_url != e.geturl(): stream_url = e.geturl()
                    else: stream_url = ''
                else:
                    common.addon.log_error(self.name + ': got HTTP Error %d %s while fetching %s' % (e.code, e.reason, stream_url))
                    return self.unresolvable(code=3, msg=e)
            """ Rebuild stream_url with only st= and e= flags """
            s = re.search('(http://.+/)(.+?)\?.*(st=[0-9a-zA-Z_\-]+).*?(e=[0-9]+).*', stream_url)
            if s:
                stream_url = s.group(1) + s.group(2) + '?' + s.group(3) + '&' + s.group(4)
        else:
            common.addon.log_error(self.name + ': stream url not found')
            return self.unresolvable(code=0, msg='File not found or removed')
        return stream_url