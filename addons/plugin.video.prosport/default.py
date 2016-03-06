#!/usr/bin/python
#encoding: utf-8

#/*
# *      Copyright (C) 2015-2016 gerikss, modded with permission by podgod
# *
# *  This Program is free software; you can redistribute it and/or modify
# *  it under the terms of the GNU General Public License as published by
# *  the Free Software Foundation; either version 2, or (at your option)
# *  any later version.
# *
# *  This Program is distributed in the hope that it will be useful,
# *  but WITHOUT ANY WARRANTY; without even the implied warranty of
# *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# *  GNU General Public License for more details.
# *
# *  You should have received a copy of the GNU General Public License
# *  along with this program; see the file COPYING.  If not, write to
# *  the Free Software Foundation, 675 Mass Ave, Cambridge, MA 02139, USA.
# *  http://www.gnu.org/copyleft/gpl.html
# *
# *  ===================
# *
# *  Sbnation API in this plugin belongs to sbnation.com and being used 
# *  only to find NBA/NHL/NFL/MLB games and scores (the same way as on sbnation.com/scoreboard website)
# *  
# *  All Reddit resources used in this plugin belong to their owners and reddit.com
# *  
# *  All logos used in this plugin belong to their owners
# *  
# *  All video streams used in this plugin belong to their owners
# *  
# *  
# */



import urllib, urllib2, sys, cookielib, base64, re
import xbmc, xbmcgui, xbmcplugin, xbmcaddon
from datetime import datetime, timedelta
import json
import calendar, time
import CommonFunctions
import praw
from threadWithReturn import threadWithReturn
import urlparse
common = CommonFunctions

__addon__ = xbmcaddon.Addon('plugin.video.prosport')
__addonname__ = __addon__.getAddonInfo('name')
path = __addon__.getAddonInfo('path')
display_score = __addon__.getSetting('score')
display_status = __addon__.getSetting('status')
display_start_time = __addon__.getSetting('start_time')
show_sd = __addon__.getSetting('showsd')
show_hehe = __addon__.getSetting('showhehe')
show_cast = __addon__.getSetting('showcast')
display_pattern = __addon__.getSetting('pattern')

logos ={'nba':'http://bethub.org/wp-content/uploads/2015/09/NBA_Logo_.png',
'nhl':'https://upload.wikimedia.org/wikipedia/de/thumb/1/19/Logo-NHL.svg/2000px-Logo-NHL.svg.png',
'nfl':'http://www.shermanreport.com/wp-content/uploads/2012/06/NFL-Logo1.gif',
'mlb':'http://content.sportslogos.net/logos/4/490/full/1986.gif',
'soccer':'http://images.clipartpanda.com/soccer-ball-clipart-soccer-ball-clip-art-4.png'}

def utc_to_local(utc_dt):
    timestamp = calendar.timegm(utc_dt.timetuple())
    local_dt = datetime.fromtimestamp(timestamp)
    assert utc_dt.resolution >= timedelta(microseconds=1)
    return local_dt.replace(microsecond=utc_dt.microsecond)

def GetURL(url, referer=None):
    url = url.replace('///','//')
    request = urllib2.Request(url)
    request.add_header('User-Agent', 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.9.0.3) Gecko/2008092417 Firefox/3.0.3')
    if referer:
    	request.add_header('Referer', referer)
    try:
    	response = urllib2.urlopen(request, timeout=3)
    	html = response.read()
    	return html
    except:
    	if 'reddit' in url:
    		xbmcgui.Dialog().ok(__addonname__, 'Looks like '+url+' is down... Please try later...')
    	return None

def GetJSON(url):
    request = urllib2.Request(url)
    request.add_header('User-Agent', 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.9.0.3) Gecko/2008092417 Firefox/3.0.3')
    try:
    	response = urllib2.urlopen(request, timeout=3)
    	f = response.read()
    	jsonDict = json.loads(f)
    	return jsonDict
    except:
    	xbmcgui.Dialog().ok(__addonname__, 'Looks like '+url+' is down... Please try later...')
    	return None

def GameStatus(status):
	statuses = {'pre-event':'Not started', 'mid-event':'[COLOR green]In progress[/COLOR]', 'post-event':'Completed', 'postponed':'Postponed'}
	if status in statuses:
		return statuses[status]
	else: return ''	

def Main():
	addDir("[COLOR=FF00FF00][ NBA GAMES ][/COLOR]", '', iconImg='http://bethub.org/wp-content/uploads/2015/09/NBA_Logo_.png', mode="nba")
	addDir("[COLOR=FF00FF00][ NHL GAMES ][/COLOR]", '', iconImg='https://upload.wikimedia.org/wikipedia/de/thumb/1/19/Logo-NHL.svg/2000px-Logo-NHL.svg.png', mode="nhl")
	addDir("[COLOR=FF00FF00][ NFL GAMES ][/COLOR]", '', iconImg='http://www.shermanreport.com/wp-content/uploads/2012/06/NFL-Logo1.gif', mode="nfl")
	addDir("[COLOR=FF00FF00][ MLB GAMES ][/COLOR]", '', iconImg='http://content.sportslogos.net/logos/4/490/full/1986.gif', mode="mlb")
	addDir("[COLOR=blue][ MY SUBREDDITS ][/COLOR]", '', iconImg='http://scitechconnect.elsevier.com/wp-content/uploads/2014/07/1reddit-logo2.png', mode="myreddit")
	addDir("[COLOR=FFFFFF00][ Archive ][/COLOR]", '', iconImg='special://home/addons/plugin.video.prosport/icon.png', mode="archive")
	xbmcplugin.endOfDirectory(h)

def Arch():
	addDir("[COLOR=FFFFFF00][ NBA Archive ][/COLOR]", '', iconImg='http://bethub.org/wp-content/uploads/2015/09/NBA_Logo_.png', mode="nbaarch")
	addDir("[COLOR=FFFFFF00][ NFL Archive ][/COLOR]", '', iconImg='http://www.shermanreport.com/wp-content/uploads/2012/06/NFL-Logo1.gif', mode="nflarch")
	addDir("[COLOR=FFFFFF00][ NHL Archive ][/COLOR]", '', iconImg='https://upload.wikimedia.org/wikipedia/de/thumb/1/19/Logo-NHL.svg/2000px-Logo-NHL.svg.png', mode="nhlarch")
	#addDir("[COLOR=FFFFFF00][ MLB Archive ][/COLOR]", '', iconImg='http://content.sportslogos.net/logos/4/490/full/1986.gif', mode="mlbarch")
	xbmcplugin.endOfDirectory(h)
	
def Games(mode):
	today = datetime.utcnow() - timedelta(hours=8)
	today_from = str(today.strftime('%Y-%m-%d'))+'T00:00:00.000-05:00'
	today_to = str(today.strftime('%Y-%m-%d'))+'T23:59:00.000-05:00'
	js = GetJSON('http://www.sbnation.com/sbn_scoreboard/ajax_leagues_and_events?ranges['+mode+'][from]='+today_from+'&ranges['+mode+'][until]='+today_to)
	js = js['leagues'][mode]
	if js:	
		if mode == 'nfl':
			addDir('[COLOR=FF00FF00][B]NFL Redzone[/B][/COLOR]', GAMEURL, iconImg=logos[mode], home='redzone', away='redzone', mode="STREAMS")
		for game in js:
			home = game['away_team']['name']
			away = game['home_team']['name']
			if 'mlb' in mode:
				try:
					hs = str(game['score']['home'][game['score']['cols'].index('R')])
					if not hs:
						hs = '0'
				except:
					hs = '0'
				try:
					avs = str(game['score']['away'][game['score']['cols'].index('R')])
					if not avs:
						avs = '0'
				except:
					avs = '0'
			else:
				hs = str(game['score']['home'][game['score']['cols'].index('Total')])
				if not hs:
					hs = '0'
				avs = str(game['score']['away'][game['score']['cols'].index('Total')])
				if not avs:
					avs = '0'
			score = ' - '+avs+':'+hs
			start_time = game['start_time']
			try:
				plus = False
				st = start_time.replace('T', ' ')
				if '+' in st:
					plus = True
					str_new = st.split('+')[-1]
					st = st.replace('+'+str_new,'')
				else:
					str_new = st.split('-')[-1]
					st = st.replace('-'+str_new,'')
				str_new = str_new.split(':')[0]
				if plus:
					st_time_utc = datetime(*(time.strptime(st, '%Y-%m-%d %H:%M:%S')[0:6]))-timedelta(hours=int(str_new))
				else:
					st_time_utc = datetime(*(time.strptime(st, '%Y-%m-%d %H:%M:%S')[0:6]))+timedelta(hours=int(str_new))
				local_game_time = utc_to_local(st_time_utc)
				local_time_str = ' - '+local_game_time.strftime(xbmc.getRegion('dateshort')+' '+xbmc.getRegion('time').replace('%H%H','%H').replace(':%S',''))
			except:
				local_time_str = ''
			status = GameStatus(game['status'])
			status = ' - '+status
			title = '[COLOR=FF00FF00][B]'+game['title'].replace(game['title'].split()[-1],'')+'[/B][/COLOR]'
			if display_start_time=='true':
				title = title+'[COLOR=FFFFFF00]'+local_time_str+'[/COLOR]'
			if display_status=='true':
				title = title+'[COLOR=FFFF0000]'+status+'[/COLOR]'
			if display_score=='true':
				title = title+'[COLOR=FF00FFFF]'+score+'[/COLOR]'
			addDir(title, mode, iconImg=logos[mode], home=home, away=away, mode="PROSTREAMS")
	else:
		addDir("[COLOR=FFFF0000]Could not fetch today's "+mode.upper()+" games... Probably no games today?[/COLOR]", '', iconImg="", mode="")
	xbmcplugin.endOfDirectory(h, cacheToDisc=True)

def MyReddits():
	sys_url = sys.argv[0] + '?mode=addnew'
	item = xbmcgui.ListItem('[COLOR=FFFF0000][ Add new subreddit ][/COLOR]', iconImage='', thumbnailImage='')
	xbmcplugin.addDirectoryItem(handle=h, url=sys_url, listitem=item, isFolder=False)
	reddits = __addon__.getSetting('reddits').split(',')
	if len(reddits)>0:
		for reddit in reddits:
			popup = []
			uri = sys.argv[0] + "?url="+reddit+"&mode=edit"
			popup.append(('Edit subreddit', 'RunPlugin(%s)'%uri,))
			uri2 = sys.argv[0] + "?url="+reddit+"&mode=remove"
			popup.append(('Remove subreddit', 'RunPlugin(%s)'%uri2,))
			if ':' in reddit:
				title = reddit.split(":")[0]
				pattern = ''
				if display_pattern == 'true':
					pattern = " - "+reddit.split(":")[-1]
				if len(title)>0:
					addDir2("[COLOR=FF00FF00][ "+title.upper()+" ]"+pattern+"[/COLOR]", reddit, '', iconImg='', popup=popup, mode="topics")
			else:
				if len(reddit)>0:
					addDir2("[COLOR=FF00FF00][ "+reddit.upper()+" ][/COLOR]", reddit, '', iconImg='', popup=popup, mode="topics")
	xbmcplugin.endOfDirectory(h)

def Topics(url):
	r = praw.Reddit(user_agent='xbmc pro sport addon')
	r.config.api_request_delay = 0
	for submission in r.get_subreddit(url.split(':')[0]).get_hot(limit=30):
		if ":" in url:
			pattern = url.split(":")[-1]
			if pattern.lower() in submission.title.lower():
				addDir("[COLOR=FFFFFF00][ "+submission.title.encode('utf-8')+" ][/COLOR]", submission.id, iconImg='', home=submission.title.encode('utf-8'), away='', mode="MYSTREAMS")
		else:
			addDir("[COLOR=FFFFFF00][ "+submission.title.encode('utf-8')+" ][/COLOR]", submission.id, iconImg='', home=submission.title.encode('utf-8'), away='', mode="MYSTREAMS")
	xbmcplugin.endOfDirectory(h)

def Addnew():
	kbd = xbmc.Keyboard()
	kbd.setDefault('')
	kbd.setHeading("Add new subreddit")
	kbd.doModal()
	s = None
	if kbd.isConfirmed():
	    s = kbd.getText()
	words = []
	history = __addon__.getSetting('reddits')
	if history:
	    words = history.split(",")
	if s and s not in words:
	    words.append(s)
	    __addon__.setSetting('reddits', ','.join(words))
	xbmc.executebuiltin("Container.Refresh")

def Edit(url):
	kbd = xbmc.Keyboard()
	kbd.setDefault(url)
	kbd.setHeading("Edit subreddit")
	kbd.doModal()
	s = None
	if kbd.isConfirmed():
	    s = kbd.getText()
	words = []
	history = __addon__.getSetting('reddits')
	if history:
	    words = history.split(",")
	for el in words:
		if el==url and s:
			words[words.index(el)] = s
	__addon__.setSetting('reddits', ','.join(words))
	xbmc.executebuiltin("Container.Refresh")

def Remove(url):
	title = xbmc.getInfoLabel('ListItem.Title')
	title = title.replace('[COLOR=FFFFFF00][','').replace('][/COLOR]','').strip()
	reddits = __addon__.getSetting('reddits').split(',')
	reddits = [x.lower() for x in reddits]
	reddits.remove(url.lower())
	__addon__.setSetting('reddits', ','.join(reddits))
	xbmc.executebuiltin("Container.Refresh")

def getProStreams(ur, home, away):
	orig_title = '[COLOR=FF00FF00][B]'+away+' at '+home+'[/B][/COLOR]'
	if 'redzone' in orig_title:
		orig_title = '[COLOR=FF00FF00][B]NFL Redzone[/B][/COLOR]'
	home_f = home.lower().split()[0]
	away_f = away.lower().split()[0]
	home_l = home.lower().split()[-1]
	away_l = away.lower().split()[-1]
	r = praw.Reddit(user_agent='xbmc pro sport addon')
	r.config.api_request_delay = 0
	links=[]
	is_101_hd = False
	for submission in r.get_subreddit(ur+'streams').get_hot(limit=30):
		if (home_l in submission.title.lower() and away_l in submission.title.lower()) or (home_f in submission.title.lower() and away_l in submission.title.lower()) or (home_l in submission.title.lower() and away_f in submission.title.lower()) or (home_f in submission.title.lower() and away_f in submission.title.lower()):
			submiss = submission
			break
		else:
			submiss = None
	if submiss:
		flat_comments = praw.helpers.flatten_tree(submiss.comments)
		for comment in flat_comments:
			if not isinstance(comment,praw.objects.Comment):
				flat_comments.remove(comment)
		flat_comments.sort(key=lambda comment: comment.score , reverse=True)
		for comment in flat_comments:
			if ('HD' in comment.body or 'hd' in comment.body) and '101live' in comment.body:
				is_101_hd = True
			regex = re.compile(r'([-a-zA-Z0-9@:%_\+.~#?&//=]{2,256}\.[a-z]{2,4}\b(\/[-a-zA-Z0-9@:%_\+.~#?&//=]*)?)',re.IGNORECASE)
			link = re.findall(regex, comment.body)
			links = links + link
	else:
		addDir("[COLOR=FFFF0000]Could not find game on reddit...[/COLOR]", '', iconImg="", mode="")
		xbmcplugin.endOfDirectory(h, cacheToDisc=True)		
	if links:
		ParseLinks(links, ur, is_101_hd, home_f, away_f, orig_title)
	else:
		addDir("[COLOR=FFFF0000]Could not find any streams...[/COLOR]", '', iconImg="", mode="")
		xbmcplugin.endOfDirectory(h, cacheToDisc=True)

def getMyStreams(url, home):
	r = praw.Reddit(user_agent='xbmc pro sport addon')
	r.config.api_request_delay = 0
	submission = r.get_submission(submission_id=url)
	links=[]
	is_101_hd = False
	flat_comments = praw.helpers.flatten_tree(submission.comments)
	for comment in flat_comments:
		if not isinstance(comment,praw.objects.Comment):
			flat_comments.remove(comment)
	flat_comments.sort(key=lambda comment: comment.score , reverse=True)
	for comment in flat_comments:
		if ('HD' in comment.body or 'hd' in comment.body) and '101live' in comment.body:
			is_101_hd = True
		regex = re.compile(r'([-a-zA-Z0-9@:%_\+.~#?&//=]{2,256}\.[a-z]{2,4}\b(\/[-a-zA-Z0-9@:%_\+.~#?&//=]*)?)',re.IGNORECASE)
		link = re.findall(regex, comment.body)
		links = links + link
	if links:
		ParseLinks(links, url, is_101_hd, '', '', home)
	else:
		addDir("[COLOR=FFFF0000]Could not find any streams...[/COLOR]", '', iconImg="", mode="")
		xbmcplugin.endOfDirectory(h, cacheToDisc=True)

	
def ParseLinks(links, ur, is_101_hd, home_f, away_f, orig_title):	
	if 'nba' in ur and show_hehe=='true':
		twrb = threadWithReturn(target=Hehestreams, args=(home_f, away_f,))
		twrb.start()
	if 'nhl' in ur and show_cast=='true':
		twrh = threadWithReturn(target=Caststreams, args=(home_f, away_f,))
		twrh.start()
	urls = []
	for el in links:
		el = el[0]
		if 'http://' not in el and 'https://' not in el:
			el = 'http://www.'+el
		if show_sd=='true':
			if 'streamendous.com' in el:
				url = Streamendous(el)
				if url and url not in urls:
					addLink('Streamendous (SD)', orig_title, url, mode="PLAY")
					urls.append(url)
			elif 'ciscoweb.ml' in el:
				url = Ciscoweb(el)
				if url and url not in urls:
					addLink('Ciscoweb (SD)', orig_title, url, mode="PLAY")
					urls.append(url)
			elif 'zona4vip.com' in el:
				url = Zona4vip(el)
				if url and url not in urls:
					addLink('Zona4vip (SD)', orig_title, url, mode="PLAY")
					urls.append(url)
			elif 'serbiaplus.club/wlive' in el:
				url = Serbiaplus(el)
				if url and url not in urls:
					addLink('Serbiaplus (SD)', orig_title, url, mode="PLAY")
					urls.append(url)
			elif 'jugandoes.com' in el or 'bosscast.net' in el or 'watchsportstv.boards.net' in el or 'tv-link.in' in el or 'giostreams.eu' in el or 'klivetv.co' in el:
				url = Universal(el)
				if url and url not in urls:
					addLink('SD Stream', orig_title, url, mode="PLAY")
					urls.append(url)	
		if 'blabseal.com' in el:
			url = Blabseal(el)
			if url and url not in urls:
				addLink('Blabseal.com', orig_title, url, mode="PLAY")
				urls.append(url)
		elif '1apps.com' in el:
			url = Oneapp(el)
			if url and url not in urls:
				addLink('Oneapp', orig_title, url, mode="PLAY")
				urls.append(url)
		elif 'youtu' in el and 'list' not in el:
			url = GetYoutube(el)
			if url and url not in urls:
				addLink('Youtube.com', orig_title, url, mode="PLAY")
				urls.append(url)
		elif 'freecast.in' in el:
			url = Freecastin(el)
			if url and url not in urls:
				addLink('Freecast.in', orig_title, url, mode="PLAY")
				urls.append(url)
		elif 'streamsus.com' in el:
			url = Streamsus(el)
			if url and url not in urls:
				addLink('Streamsus.com', orig_title, url, mode="PLAY")
				urls.append(url)
		elif 'streamboat.tv' in el:
			url = Streambot(el)
			if url and url not in urls:
				addLink('Streamboat.tv', orig_title, url, mode="PLAY")
				urls.append(url)
		elif 'nbastream.net' in el:
			url = Nbanhlstreams(el)
			if url and url not in urls:
				addLink('Nbastream.net', orig_title, url, mode="PLAY")
				urls.append(url)
		elif 'nhlstream.net' in el:
			url = Nbanhlstreams(el)
			if url and url not in urls:
				addLink('Nhlstream.net', orig_title, url, mode="PLAY")
				urls.append(url)
		elif 'livenflstream.net' in el:
			url = Nbanhlstreams(el)
			if url and url not in urls:
				addLink('Livenflstream.net', orig_title, url, mode="PLAY")
				urls.append(url)
		elif 'fs.anvato.net' in el:
			url = Getanvato(el)
			if url and url not in urls:
				addLink('Fox ToGo (US IP Only)', orig_title, url, mode="PLAY")
				urls.append(url)
		elif 'mlblive-akc' in el:
			url = Getmlb(el)
			if url and url not in urls:
				addLink('MLB app', orig_title, url, mode="PLAY")
				urls.append(url)
		elif 'streamsarena.eu' in el:
			url = Streamarena(el)
			if url and url not in urls:
				addLink('Streamsarena.eu', orig_title, url, mode="PLAY")
				urls.append(url)
		elif 'streamup.com' in el and 'm3u8' not in el:
			url = GetStreamup(el.split('/')[3])
			if url and url not in urls:
				addLink('Streamup.com', orig_title, url, mode="PLAY")
				urls.append(url)
		elif 'torula' in el:
			url = Torula(el)
			if url and url not in urls:
				addLink('Torula.us', orig_title, url, mode="PLAY")
				urls.append(url)
		elif 'gstreams.tv' in el:
			url = Gstreams(el)
			if url and url not in urls:
				addLink('Gstreams.tv', orig_title, url, mode="PLAY")
				urls.append(url)
		elif 'nfl-watch.com/live/watch' in el or 'nfl-watch.com/live/-watch' in el or 'nfl-watch.com/live/nfl-network' in el:
			url = Nflwatch(el)
			if url and url not in urls:
				addLink('Nfl-watch.com', orig_title, url, mode="PLAY")
				urls.append(url)
		elif 'ducking.xyz' in el:
			url = Ducking(el)
			if url and url not in urls:
				addLink('Ducking.xyz', orig_title, url, mode="PLAY")
				urls.append(url)
		elif 'streamandme' in el:
			url = Streamandme(el)
			if url and url not in urls:
				addLink('Streamandme', orig_title, url, mode="PLAY")
				urls.append(url)
		elif 'stream2hd.net' in el:
			url = Stream2hd(el)
			if url and url not in urls:
				addLink('Stream2hd', orig_title, url, mode="PLAY")
				urls.append(url)
		elif 'serbiaplus.club/cbcsport.html' in el:
			url = CbcSportAz(el)
			if url and url not in urls:
				addLink('CbcSportAz', orig_title, url, mode="PLAY")
				urls.append(url)
		elif 'mursol.moonfruit.com' in el:
			url = Moonfruit(el)
			if url and url not in urls:
				addLink('Moonfruit', orig_title, url, mode="PLAY")
				urls.append(url)
		elif 'castalba.tv' in el:
			url = Castalba(el)
			if url and url not in urls:
				addLink('Castalba', orig_title, url, mode="PLAY")
				urls.append(url)
		elif 'room' in el and 'm3u8' in el:
			url = Getroom(el)
			if url and url not in urls:
				addLink('Room HD (US IP Only)', orig_title, url, mode="PLAY")
				urls.append(url)
		elif '101livesportsvideos.com' in el and 'SD' not in el and 'ace' not in el and is_101_hd:
			url = Livesports101(el)
			if url and url not in urls:
				addLink('101livesportsvideos.com', orig_title, url, mode="PLAY")
				urls.append(url)
		elif '.m3u8' in el and 'room' not in el and 'anvato' not in el and 'mlblive-akc' not in el:
			url = el
			if url and url not in urls:
				addLink('M3U8 stream', orig_title, url, mode="PLAY")
				urls.append(url)
		
	if 'nba' in ur and show_hehe=='true':
		links = twrb.join()
		if links:
			for lnk in links:
				if 'turner' in lnk:
					try:
						timest = lnk.split("exp=")[-1].split("~acl")[0]
						time_exp = datetime.fromtimestamp(int(timest)).strftime(xbmc.getRegion('time').replace('%H%H','%H').replace(':%S',''))
					except:
						time_exp = ''
					addDirectLink('Turner - (external player) link expires '+time_exp, {'Title': orig_title}, lnk)
				elif 'neulion' in lnk:
					lnk = lnk.replace('amp;','')
					try:
						timest = lnk.split("expires%3D")[-1].split("%7E")[0]
						time_exp = datetime.fromtimestamp(int(timest)).strftime(xbmc.getRegion('time').replace('%H%H','%H').replace(':%S',''))
					except:
						time_exp = ''
					addDirectLink('Neulion link expires '+time_exp, {'Title': orig_title}, lnk)
		
	if 'nhl' in ur and show_cast=='true':
		link = twrh.join()
		addDirectLink('CastStreams', {'Title': orig_title}, link)
	xbmcplugin.endOfDirectory(h, cacheToDisc=True)

def strip_non_ascii(string):
    stripped = (c for c in string if 0 < ord(c) < 127)
    return ''.join(stripped)

def Archive(page, mode):
	if mode == 'mlbarch':
		url = 'http://www.life2sport.com/category/basketbol/nba/page/'+str(page)
	if mode == 'nbaarch':
		url = 'http://www.life2sport.com/category/basketbol/nba/page/'+str(page)
	elif mode == 'nflarch':
		url = 'http://www.life2sport.com/category/american-football/page/'+str(page)
	html = GetURL(url)
	links = common.parseDOM(html, "a", attrs={"rel": "bookmark"}, ret="href")
	titles = common.parseDOM(html, "a", attrs={"rel": "bookmark"}, ret="title")
	del links[1::2]
	for i, el in enumerate(links):
		if '-nba-' in el or '-nfl-' in el:
			title = common.parseDOM(html, "a", attrs={"href": el}, ret="title")[0]
			title = title.split('/')[-1]+' - '+title.split('/')[len(title.split('/'))-2]
			title = strip_non_ascii(title)
			title = title.replace('&#8211;','').strip()
			addDir(title, el, iconImg="", mode="playarchive")
	uri = sys.argv[0] + '?mode=%s&page=%s' % (mode, str(int(page)+1))
	item = xbmcgui.ListItem("next page...", iconImage='', thumbnailImage='')
	xbmcplugin.addDirectoryItem(h, uri, item, True)
	xbmcplugin.endOfDirectory(h, cacheToDisc=True)
	
def Nhlarchive(page, mode):
	url = 'http://rutube.ru/api/video/person/979571/?page='+str(page)+'&format=json'
	json = GetJSON(url)
	json = json['results']
	for el in json:
		title = el['title']
		id = el['id']
		img = el['thumbnail_url']
		addLink(title, title, id, iconImg=img, mode="playnhlarchive")
	uri = sys.argv[0] + '?mode=%s&page=%s' % (mode, str(int(page)+1))
	item = xbmcgui.ListItem("next page...", iconImage='', thumbnailImage='')
	xbmcplugin.addDirectoryItem(h, uri, item, True)
	xbmcplugin.endOfDirectory(h, cacheToDisc=True)

def Playnhlarchive(url):
	orig_title = xbmc.getInfoLabel('ListItem.Title')
	url = 'http://rutube.ru/api/play/options/'+url+'?format=json'
	json = GetJSON(url)
	link = json['video_balancer']['m3u8']
	Play(link, orig_title)
	
def PlayArchive(url):
	orig_title = xbmc.getInfoLabel('ListItem.Title')
	html = GetURL(url)
	html = html.split('>english<')[-1]
	link = common.parseDOM(html, "iframe", ret="src")[0]
	link = link.replace('https://videoapi.my.mail.ru/videos/embed/mail/','http://videoapi.my.mail.ru/videos/mail/')
	link = link.replace('html','json')
	cookieJar = cookielib.CookieJar()
	opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookieJar), urllib2.HTTPHandler())
	conn = urllib2.Request(link)
	connection = opener.open(conn)
	f = connection.read()
	connection.close()
	js = json.loads(f)
	for cookie in cookieJar:
		token = cookie.value
	js = js['videos']
	for el in js:
		addLink(el['key'], orig_title, el['url']+'|Cookie=video_key='+token, mode="PLAY")
	xbmcplugin.endOfDirectory(h, cacheToDisc=True)

def GetStreamup(channel):
	try:
		chan = GetJSON('https://api.streamup.com/v1/channels/'+channel)
		if chan['channel']['live']:
			videoId = chan['channel']['capitalized_slug'].lower()
			domain = GetURL('https://lancer.streamup.com/api/redirect/'+videoId)
			return 'https://'+domain+'/app/'+videoId+'_aac/playlist.m3u8'
	except:
		return None	

def GetYoutube(url):
	try:
		if 'channel' in url and 'live' in url:
			html = GetURL(url)
			videoId = html.split("https://www.youtube.com/watch?v=")[-1].split('">')[0]
			link = 'plugin://plugin.video.youtube/?action=play_video&videoid=' + videoId
			return link
		regex = (r'(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})')
		youtube_regex_match = re.match(regex, url)
		videoId = youtube_regex_match.group(6)
		link = 'plugin://plugin.video.youtube/?action=play_video&videoid=' + videoId
		return link
	except:
		return None
		
def Getmlb(url):
	try:
		if 'master' in url:
			return url
		else:	 
			lst = url.split('/')
			link = url.replace(lst[len(lst)-2],'3000K').replace(lst[len(lst)-1],'3000_slide.m3u8')
			return link
	except:
		return None

def Getanvato(url):
	try:
		if 'master' in url:
			return url
		else:	 
			lst = url.split('/')
			link = url.replace(lst[len(lst)-2],'4028k')
			return link
	except:
		return None
		
def Getroom(url):
	try:
		if 'master' in url:
			return url
		else:	 
			lst = url.split('/')
			link = url.replace(lst[len(lst)-2],'4028k')
			return link
	except:
		return url
		
def Blabseal(url):
	try:
		html = GetURL(url)
		block_content = common.parseDOM(html, "iframe", ret="src")[0]
		link = GetYoutube(block_content)
		return link
	except:
		return None
		
def Hehestreams(home, away):
	try:
		html = GetURL("http://hehestreams.xyz/")
		titles = common.parseDOM(html, "a", attrs={"class": "results-link"})
		links = common.parseDOM(html, "a", attrs={"class": "results-link"}, ret="href")
		for title in titles:
			if home.lower() in title.lower() and away.lower() in title.lower():
				link = links[titles.index(title)]
				link = "http://hehestreams.xyz"+link
				html = GetURL(link)
				lnks = common.parseDOM(html, "option", ret="value")
				return lnks
			else:
				continue
	except:
		return None	


def Caststreams(home, away):
	try:
		url = 'https://caststreams.com:2053/login'
		data = urllib.urlencode({"email":"prosport@testmail.com","password":"prosport","ipaddress":"desktop","androidId":"","deviceId":"","isGoogleLogin":0})
		request = urllib2.Request(url, data)
		response = urllib2.urlopen(request, timeout=3)
		resp = response.read()
		jsonDict = json.loads(resp)
		token = jsonDict['token']
		url = 'https://caststreams.com:2053/feeds'
		request = urllib2.Request(url)
		request.add_header('Authorization', token)
		response = urllib2.urlopen(request, timeout=3)
		resp = response.read()
		jsonDict = json.loads(resp)
		feeds = jsonDict['feeds']
		for feed in feeds:
			title = feed['nam'].lower().replace('ny', 'new')
			print title
			print home
			print away
			if home.lower() in title.lower() and away.lower() in title.lower() and 'testing' not in title.lower():
				channel = feed['url'][0]
				print channel
				link = 'https://caststreams.com:2053/getGame?rUrl='+channel
				return link	
			else:
				continue
	except:
		return None		
		
def Oneapp(url):
	try:
		html = GetURL(url)
		block_content = common.parseDOM(html, "iframe", ret="src")[0]
		link = GetYoutube(block_content)
		return link
	except:
		return None
		
def Torula(url):
	try:
		html = GetURL(url)
		block_content = common.parseDOM(html, "input", attrs={"id": "vlc"}, ret="value")[0]
		link = block_content
		return link
	except:
		return None

def Freecastin(url):
	try:
		html = GetURL(url)
		block_content = common.parseDOM(html, "iframe", attrs={"width": "100%"}, ret="src")[0]
		link = GetYoutube(block_content)
		return link
	except:
		return None
		
def Streamsus(url):
	try:
		html = GetURL(url)
		block_content = common.parseDOM(html, "iframe", ret="src")[0]
		link = GetYoutube(block_content)
		return link
	except:
		return None

def CbcSportAz(url):
	try:
		html = GetURL('http://serbiaplus.club/embedhls/cbcsport.html')
		regex = re.compile(r'([-a-zA-Z0-9@:%_\+.~#?&//=]{2,256}\.[a-z]{2,4}\b(\/[-a-zA-Z0-9@:%_\+.~#?&//=]*)?)',re.IGNORECASE)
		links = re.findall(regex, html)
		for link in links:
			if 'http' in link[0] and 'm3u8' in link[0]:
				return link[0]
	except:
		return None
			
def Streambot(url):
	try:
		cookieJar = cookielib.CookieJar()
		opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookieJar), urllib2.HTTPHandler())
		conn = urllib2.Request('https://streamboat.tv/signin')
		connection = opener.open(conn, timeout=3)
		for cookie in cookieJar:
			token = cookie.value
		headers = {
            "User-Agent": "Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.9.0.3) Gecko/2008092417 Firefox/3.0.3",
            "Content-Type" : "application/x-www-form-urlencoded",
            "Cookie":"_gat=1; csrftoken="+token+"; _ga=GA1.2.943051497.1450922237",
            "Origin":"https://streamboat.tv",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.8,bg;q=0.6,it;q=0.4,ru;q=0.2,uk;q=0.2",
            "Accept-Encoding" : "windows-1251,utf-8;q=0.7,*;q=0.7",
            "Referer": "https://streamboat.tv/signin"
		}
		reqData = {'csrfmiddlewaretoken':token,'username' : 'test_user', 'password' : 'password'}
		conn = urllib2.Request('https://streamboat.tv/signin', urllib.urlencode(reqData), headers)
		connection = opener.open(conn, timeout=3)
		conn = urllib2.Request(url)
		connection = opener.open(conn, timeout=3)
		html = connection.read()
		connection.close()
		link1 = 'http://' + html.split("cdn_host: '")[-1].split("',")[0]
		link2 = html.split("playlist_url: '")[-1].split("',")[0]
		link = link1+link2
		return link
	except:
		return None

def Nbanhlstreams(url):
	try:
		if 'nba' in url:
			URL = 'http://www.nbastream.net/'
		elif 'nhl' in url:
			URL = 'http://www.nhlstream.net/'
		elif 'nfl' in url:
			URL = 'http://www.livenflstream.net/'
		html = GetURL(url)
		link = common.parseDOM(html, "iframe",  ret="src")[0]
		html  = GetURL(URL+link)
		link = common.parseDOM(html, "iframe",  ret="src")[0]
		if 'streamup' in link:
			channel = link.split('/')[3]
			link = GetStreamup(channel)
			return link
	except:
		return None
		
def Streamandme(url):
	try:
		html = GetURL(url)
		link = common.parseDOM(html, "iframe",  ret="src")[0]
		channel = link.split('/')[3]
		link = GetStreamup(channel)
		return link
	except:
		return None
		
def Stream2hd(url):
	try:
		html = GetURL(url)
		link = common.parseDOM(html, "iframe",  ret="src")[0]
		if 'streamup' in link:
			channel = link.split('/')[3]
			link = GetStreamup(channel)
			return link
	except:
		return None

def Gstreams(url):
	try:
		html = GetURL(url)
		link = common.parseDOM(html, "iframe",  ret="src")[0]
		if 'gstreams.tv' in link:
			html  = GetURL(link)
			link = html.split('https://')[1]
			link = link.split('",')[0]
			link = 'https://' + link 
			return link
		elif 'streamup.com' in link and 'm3u8' not in link:
			channel = link.split('/')[3]
			link = GetStreamup(channel)
			return link
		elif 'youtu' in link:
			link = GetYoutube(link)
			return link
		elif 'm3u8' in link:
			return link
	except:
		return None
		
def Moonfruit(url):
	try:
		cookieJar = cookielib.CookieJar()
		opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookieJar), urllib2.HTTPHandler())
		conn = urllib2.Request(url+'/htown3')
		connection = opener.open(conn, timeout=3)
		for cookie in cookieJar:
			token = cookie.value
		headers = {
            "User-Agent": "Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.9.0.3) Gecko/2008092417 Firefox/3.0.3",
            "Content-Type" : "application/x-www-form-urlencoded",
            "Cookie":"markc="+token,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.8,bg;q=0.6,it;q=0.4,ru;q=0.2,uk;q=0.2",
		}
		html = connection.read()
		link = common.parseDOM(html, "iframe",  ret="src")
		link = url+link[-1]
		conn = urllib2.Request(link, headers=headers)
		connection = opener.open(conn, timeout=3)
		html = connection.read()
		link = common.parseDOM(html, "iframe",  ret="src")[0]
		if 'streamup.com' in link:
			channel = link.split('/')[4]
			link = GetStreamup(channel)
			return link
	except:
		return None

def Nflwatch(url):
	try:
		html = GetURL(url)
		links = common.parseDOM(html, "iframe",  ret="src")
		for link in links:
			if 'streamup' in link:
				channel = link.split('/')[3]
				link = GetStreamup(channel)
				return link
			else:
				continue
		if 'p2pcast.tv' in html:
			agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/47.0.2526.106 Safari/537.36'
			id = html.split("'text/javascript'>id='")[-1]
			id = id.split("';")[0]
			url = 'http://p2pcast.tv/stream.php?id='+id+'&live=0&p2p=0&stretching=uniform'
			request = urllib2.Request(url)
			request.add_header('User-Agent', agent)
			request.add_header('Referer', url)
			response = urllib2.urlopen(request, timeout=3)
			html = response.read()
			token = html.split('murl = "')[1].split('";')[0]
			link = base64.b64decode(token)
			request = urllib2.Request('http://p2pcast.tv/getTok.php')
			request.add_header('User-Agent', agent)
			request.add_header('Referer', url)
			request.add_header('X-Requested-With', 'XMLHttpRequest')
			response = urllib2.urlopen(request, timeout=3)
			html = response.read()
			js = json.loads(html)
			tkn = js['token']
			link = link+tkn
			link = link + '|User-Agent='+agent+'&Referer='+url
			return link
	except:
		return None
		
def Zona4vip(url):
	try:
		html = GetURL(url)
		link = common.parseDOM(html, "iframe",  ret="src")[0].replace('/live','')
		html = GetURL('http://www.zona4vip.com/'+link)
		link = common.parseDOM(html, "iframe",  ret="src")[0]
		html = GetURL(link)
		if 'p2pcast' in html:
			agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/47.0.2526.106 Safari/537.36'
			id = html.split("'text/javascript'>id='")[-1]
			id = id.split("';")[0]
			url = 'http://p2pcast.tech/stream.php?id='+id+'&live=0&p2p=0&stretching=uniform'
			request = urllib2.Request(url)
			request.add_header('User-Agent', agent)
			request.add_header('Referer', url)
			response = urllib2.urlopen(request, timeout=3)
			html = response.read()
			token = html.split('murl = "')[1].split('";')[0]
			link = base64.b64decode(token)
			request = urllib2.Request('http://p2pcast.tech/getTok.php')
			request.add_header('User-Agent', agent)
			request.add_header('Referer', url)
			request.add_header('X-Requested-With', 'XMLHttpRequest')
			response = urllib2.urlopen(request, timeout=3)
			html = response.read()
			js = json.loads(html)
			tkn = js['token']
			link = link+tkn
			link = link + '|User-Agent='+agent+'&Referer='+url
			return link
	except:
		return None
		
def Serbiaplus(url):
	try:
		html = GetURL('http://serbiaplus.club/whd/'+url.split('/w')[-1])
		link = common.parseDOM(html, "iframe",  ret="src")[0]
		if 'nullref' in link:
			link = link.split('?')[-1]
		html = GetURL(link)
		if 'p2pcast' in html:
			agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/47.0.2526.106 Safari/537.36'
			id = html.split("'text/javascript'>id='")[-1]
			id = id.split("';")[0]
			url = 'http://p2pcast.tech/stream.php?id='+id+'&live=0&p2p=0&stretching=uniform'
			request = urllib2.Request(url)
			request.add_header('User-Agent', agent)
			request.add_header('Referer', url)
			response = urllib2.urlopen(request, timeout=3)
			html = response.read()
			token = html.split('murl = "')[1].split('";')[0]
			link = base64.b64decode(token)
			request = urllib2.Request('http://p2pcast.tech/getTok.php')
			request.add_header('User-Agent', agent)
			request.add_header('Referer', url)
			request.add_header('X-Requested-With', 'XMLHttpRequest')
			response = urllib2.urlopen(request, timeout=3)
			html = response.read()
			js = json.loads(html)
			tkn = js['token']
			link = link+tkn
			link = link + '|User-Agent='+agent+'&Referer='+url
			return link
	except:
		return None

def Ducking(url):
	try:
		request = urllib2.Request('http://www.ducking.xyz/kvaak/stream/basu.php')
		request.add_header('Referer', 'www.ducking.xyz/kvaak/')
		request.add_header('User-Agent','Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/47.0.2526.106 Safari/537.36')
		response = urllib2.urlopen(request, timeout=3)
		html = response.read()
		link = common.parseDOM(html, "iframe", ret="src")[0]
		channel = link.split('/')[3]
		link = GetStreamup(channel)
		return link
	except:
		return None
		
def Streamarena(url):
	try:
		html = GetURL(url)
		link = common.parseDOM(html, "iframe",  ret="src")[0]
		link = link.replace('..','http://www.streamsarena.eu/')
		html  = GetURL(link)
		link = common.parseDOM(html, "iframe",  ret="src")[0]
		channel = link.split('/')[3]
		link = GetStreamup(channel)
		return link
	except:
		return None
		
def Livesports101(url):
	try:
		html = GetURL(url)
		try:
			block_content = common.parseDOM(html, "meta", attrs={"property": "og:description"}, ret="content")
			for el in block_content:
				if 'youtube.com' in el:
					link = GetYoutube(block_content)
					return link
				elif 'streamboat.tv' in el:
					link = el
					link = link.split('http://')[1]
					link = link.split("'")[0]
					link = 'http://' + link 
					return link
				elif 'streamup' in el:
					link = el
					link = link.split('https://')[1]
					link = link.split("'")[0]
					link = 'https://' + link 
					return link
		except:
			pass
		try:	
			block_content = common.parseDOM(html, "embed", attrs={"id": "vlcp"}, ret="target")[0]
			if 'streamboat' in block_content or 'streamup' in block_content:
				link = block_content
				return link
		except:
			pass
		try:
			block_content = common.parseDOM(html, "iframe", ret="src")[0]
			if 'streamup' in block_content:
				channel = block_content.split('/')[3]
				link = GetStreamup(channel)
				return link
		except:
			pass
	except:
		return None

def Streamendous(url):
	try:
		html = GetURL(url)
		req = common.parseDOM(html, 'iframe', attrs={'id': 'player'},ret='src')
		url = url.split('/ch')[0]+req[0]
		html = GetURL(url)
		req = common.parseDOM(html, 'iframe', attrs={'id': 'player'},ret='src')[0]
		html = GetURL(req, referer=req)
		link = re.compile('src="(.+?)"').findall(str(html))
		for item in link:
			if ('sawlive') in item:
				url = sawresolve(item)
				return url
			else:pass
		return None
	except:
		return None
		
def Ciscoweb(url):
	try:
		html = GetURL(url)
		req = common.parseDOM(html, 'iframe', attrs={'id': 'player'},ret='src')[0]
		html = GetURL(req)
		req = common.parseDOM(html, 'iframe', attrs={'id': 'player'},ret='src')[0]
		html = GetURL(req, referer=req)
		link = re.compile('src="(.+?)"').findall(str(html))
		for item in link:
			if ('sawlive') in item:
				url = sawresolve(item)
				return url
			else:pass
		return None
	except:
		return None


def Castalba(url):
	try:
		try:
			cid  = urlparse.parse_qs(urlparse.urlparse(url).query)['cid'][0] 
		except:
			cid = re.compile('channel/(.+?)(?:/|$)').findall(url)[0]
		try:
			referer = urlparse.parse_qs(urlparse.urlparse(url).query)['referer'][0]
		except:
			referer='http://castalba.tv'        
		url = 'http://castalba.tv/embed.php?cid=%s&wh=600&ht=380&r=%s'%(cid,urlparse.urlparse(referer).netloc)
		pageUrl=url
		request = urllib2.Request(url)
		request.add_header('User-Agent', 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.9.0.3) Gecko/2008092417 Firefox/3.0.3')
		request.add_header('Referer', referer)
		response = urllib2.urlopen(request, timeout=3)
		result = response.read()
		result=urllib.unquote(result)
		if 'm3u8' in result:
			link = re.compile('filez\s*=\s*(?:unescape\()\'(.+?)\'').findall(result)[0]
			link = 'http://' + url + '.m3u8'
			link += '|%s' % urllib.urlencode({'User-Agent': client.agent(), 'Referer': referer})          
		else:
			try:
				filePath = re.compile("'file'\s*:\s*(?:unescape\()?'(.+?)'").findall(result)[0]  
			except:
				file = re.findall('var file\s*=\s*(?:unescape\()?(?:\'|\")(.+?)(?:\'|\")',result)[0]
				try:
					file2 = re.findall("'file':\s*unescape\(file\)\s*\+\s*unescape\('(.+?)'\)",result)[0]
					filePath = file+file2
				except:
					filePath = file         
			swf = re.compile("'flashplayer'\s*:\s*\"(.+?)\"").findall(result)[0]
			try:
				streamer=re.findall('streamer\(\)\s*\{\s*return \'(.+?)\';\s*\}',result)[0]
				if 'rtmp' not in streamer:
					streamer = 'rtmp://' + streamer
			except:
				try:
					streamer = re.compile("var sts\s*=\s*'(.+?)'").findall(result)[0]
				except:
					streamer=re.findall('streamer\(\)\s*\{\s*return \'(.+?)\';\s*\}',result)[0]    
			link = streamer.replace('///','//') + ' playpath=' + filePath +' swfUrl=' + swf + ' flashver=WIN\\2020,0,0,228 live=true timeout=15 swfVfy=true pageUrl=' + pageUrl
		return link
	except:
		return None

def Universal(url):
	try:
		for i in range (5):
			domain = urlparse.urlparse(url).netloc
			req = GetURL(url)
			url = common.parseDOM(req, 'iframe', ret='src')[0]
			if 'http://' not in url:
				 url = 'http://'+domain+url
			if 'wiz1' in url or 'live9.net' in url:
				break
			else:
				continue 
		this = GetURL(url, referer=url)
		link = re.compile('src="(.+?)"').findall(str(this))[0]
		if ('sawlive') in link:
			link = sawresolve(link)
			return link
		else:pass
		return None
	except:
		return None


def sawresolve(url):
	try:
		page = re.compile('//(.+?)/(?:embed|v)/([0-9a-zA-Z-_]+)').findall(url)[0]
		page = 'http://%s/embed/%s' % (page[0], page[1])
		try: 
			referer = urlparse.parse_qs(urlparse.urlparse(url).query)['referer'][0]
		except: 
			referer = page
		ch = url.split("/")[-1]
		request = urllib2.Request(url)
		request.add_header('Referer', referer)
		request.add_header('User-Agent','Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/47.0.2526.106 Safari/537.36')
		response = urllib2.urlopen(request, timeout=3)
		result = response.read()
		unpacked = ''
		packed = result.split('\n')
		for i in packed: 
			try: 
				unpacked += unpack(i)
			except: 
				pass
		result += unpacked
		result = urllib.unquote_plus(result)
		result = re.sub('\s\s+', ' ', result)
		url = common.parseDOM(result, 'iframe', ret='src')[-1]
		url = url.replace(' ', '').split("'")[0]
		#ch = re.compile('ch=""(.+?)""').findall(str(result))
		#ch = ch[0].replace(' ','')
		sw = re.compile(" sw='(.+?)'").findall(str(result))
		url = url+'/'+ch+'/'+sw[0]
		try:
			url = url.replace('watch//', 'watch/')
		except:
			pass
		request = urllib2.Request(url)
		request.add_header('Referer', referer)
		request.add_header('User-Agent','Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/47.0.2526.106 Safari/537.36')
		response = urllib2.urlopen(request, timeout=3)
		result = response.read()
		file = re.compile("'file'.+?'(.+?)'").findall(result)[0]
		try:
			if not file.startswith('http'): 
				raise Exception()
			request = urllib2.Request(file)
			response = urllib2.urlopen(request, timeout=3)
			url = response.geturl()
			if not '.m3u8' in url: 
				raise Exception()
			url += '|%s' % urllib.urlencode({'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/47.0.2526.106 Safari/537.36', 'Referer': file})
			return url            
		except:
			pass
		strm = re.compile("'streamer'.+?'(.+?)'").findall(result)[0]
		swf = re.compile("SWFObject\('(.+?)'").findall(result)[0]
		url = '%s playpath=%s swfUrl=%s pageUrl=%s live=1 timeout=40' % (strm, file, swf, url)
		return url
	except:
		return None


def unpack(source):
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
    source = source.replace("\\'", "'")
    return _replacestrings(source)
    
def Play(url, orig_title):
    item = xbmcgui.ListItem(path=url)
    item.setInfo('video', { 'Title': orig_title })
    xbmcplugin.setResolvedUrl(h, True, item)

    	
def addDir(title, url, iconImg="DefaultVideo.png", home="", away="", mode=""):
    sys_url = sys.argv[0] + '?url=' + urllib.quote_plus(url) + '&home=' + urllib.quote_plus(str(home)) +'&away=' + urllib.quote_plus(str(away)) +'&mode=' + urllib.quote_plus(str(mode))
    item = xbmcgui.ListItem(title, iconImage=iconImg, thumbnailImage=iconImg)
    item.setInfo(type='Video', infoLabels={'Title': title})
    xbmcplugin.addDirectoryItem(handle=h, url=sys_url, listitem=item, isFolder=True)

def addDir2(title, url, next_url, iconImg="DefaultVideo.png", popup=None, mode=""):
    sys_url = sys.argv[0] + '?url=' + urllib.quote_plus(url)+'&next_url=' + urllib.quote_plus(next_url) +'&mode=' + urllib.quote_plus(str(mode))
    item = xbmcgui.ListItem(title, iconImage=iconImg, thumbnailImage=iconImg)
    item.setInfo(type='Video', infoLabels={'Title': title})
    if popup:
    	item.addContextMenuItems(popup, True)
    xbmcplugin.addDirectoryItem(handle=h, url=sys_url, listitem=item, isFolder=True)

def addLink(title, orig_title, url, iconImg="DefaultVideo.png", mode=""):
    sys_url = sys.argv[0] + '?url=' + urllib.quote_plus(url) + '&mode=' + urllib.quote_plus(str(mode))+ '&orig=' + urllib.quote_plus(str(orig_title))
    item = xbmcgui.ListItem(title, iconImage=iconImg, thumbnailImage=iconImg)
    item.setLabel(title)
    item.setInfo(type='Video', infoLabels={'Title': title})
    item.setProperty('IsPlayable', 'true')
    xbmcplugin.addDirectoryItem(handle=h, url=sys_url, listitem=item)
    
def addDirectLink(title, infoLabels, url, iconImg="DefaultVideo.png"):
    item = xbmcgui.ListItem(title, iconImage=iconImg, thumbnailImage=iconImg)
    item.setInfo(type='Video', infoLabels=infoLabels)
    xbmcplugin.addDirectoryItem(handle=h, url=url, listitem=item)
       
def get_params():
    param=[]
    paramstring=sys.argv[2]
    if len(paramstring)>=2:
        params=sys.argv[2]
        cleanedparams=params.replace('?','')
        if (params[len(params)-1]=='/'):
            params=params[0:len(params)-2]
        pairsofparams=cleanedparams.split('&')
        param={}
        for i in range(len(pairsofparams)):
            splitparams={}
            splitparams=pairsofparams[i].split('=')
            if (len(splitparams))==2:
                param[splitparams[0]]=splitparams[1]

    return param

h = int(sys.argv[1])
params = get_params()

mode = None
url = None

try: mode = urllib.unquote_plus(params['mode'])
except: pass

try: url = urllib.unquote_plus(params['url'])
except: pass

try: home = urllib.unquote_plus(params['home'])
except: pass

try: away = urllib.unquote_plus(params['away'])
except: pass

try: orig_title = urllib.unquote_plus(params['orig'])
except: pass

try: page = params['page'] if 'page' in params else 1
except: pass

if mode == None: Main()
elif mode == 'nfl': Games(mode)
elif mode == 'nba': Games(mode)
elif mode == 'nhl': Games(mode)
elif mode == 'mlb': Games(mode)
elif mode == 'soccer': Games(mode)
elif mode == 'myreddit': MyReddits()
elif mode == 'nbaarch': Archive(page, mode)
elif mode == 'nflarch': Archive(page, mode)
elif mode == 'nhlarch': Nhlarchive(page, mode)
elif mode == 'archive': Arch()
elif mode == 'playarchive': PlayArchive(url)
elif mode == 'playnhlarchive': Playnhlarchive(url)
elif mode == 'PROSTREAMS': getProStreams(url, home, away)
elif mode == 'MYSTREAMS': getMyStreams(url, home)
elif mode == 'PLAY': Play(url, orig_title)
elif mode == 'topics': Topics(url)
elif mode == 'addnew': Addnew()
elif mode == 'remove': Remove(url)
elif mode == 'edit': Edit(url)

xbmcplugin.endOfDirectory(h)