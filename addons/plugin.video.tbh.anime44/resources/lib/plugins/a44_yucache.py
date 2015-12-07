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
import urllib
import urllib2
import re


class A44YucacheResolver(Plugin, UrlResolver, PluginSettings):
    implements = [UrlResolver, PluginSettings]
    name = "a44_yucache.net"
    domains = ["yucache.net"]

    def __init__(self):
        p = self.get_setting('priority') or 99
        self.priority = int(p)
        self.net = Net()
        self.pattern = 'http://((?:www|embed)*\.*(?:yucache\.net))/((?:embed(?:_ext)*/)*[0-9a-zA-Z/\?_\-=]+)[&]*.*'

    def get_url(self, host, media_id):
        return 'http://%s/%s' % (host, media_id)

    def get_host_and_id(self, url):
        r = re.search(self.pattern, url)
        if r: return r.groups()
        else: return False

    def valid_url(self, url, host):
        if self.get_setting('enabled') == 'false': return False
        return re.match(self.pattern, url) or self.name in host

    def get_media_url(self, host, media_id):
        web_url = self.get_url(host, media_id)
        try:
            resp = self.net.http_GET(web_url)
            html = resp.content
            resp = None
        except urllib2.URLError, e:
            common.addon.log_error(self.name + ': got HTTP Error %d %s while fetching %s' % (e.code, e.reason, web_url))
            return self.unresolvable(code=3, msg=e)
        r = re.search('(?:playlist:|timer\s*=\s*null;).+?url\s*[:=]+\s*[\'"]+(http://stream\..+?)[\'"]+', html, re.DOTALL)
        if r:
            stream_url = urllib.unquote_plus(r.group(1))
            opener = urllib2.build_opener()
            opener.addheaders = [('User-agent', 'Mozilla/5.0')]
            opener.addheaders = [('Host', host)]
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
        else:
            common.addon.log_error(self.name + ': stream url not found')
            return self.unresolvable(code=0, msg='File not found or removed')
        return stream_url
