# -*- coding: utf-8 -*-
# The root HTML has:
# 首页，综艺，少儿，电视，电影
# 首页分类：本周热门，最新添加，口碑榜，烂片榜，每一分类是一个category：
#          /home/categories/44, 46, 47, 48
# 综艺分类：/zongyi/categories/##，再进去是分页显示
# 少儿分类：/children/categories/##，再进去是分页显示
# 电视分类：/tv/categories/##，再进去是分页显示
# 电影分类，/movies/categories/##，再进去是分页显示

# dirLevel = 0: main menu - 综艺，少儿，电视，电影
# dirLevel = 1: category list for one main menu item
# dirLevel = 2: pages in one category if it's more than one page
# dirLevel = 3: items in one category
# dirLevel = 4: series for one item
# dirLevel = 5: single video

import xbmcplugin, xbmcgui, urllib, re, urllib2, string, urlparse

domainName = 'http://v.aibuka.com'

################################################################################
# This function showes an URL and an error message in xbmc when the URL cannot be opened
# Param: error message
################################################################################
def error(message):
    addon_id = urlparse.urlsplit(sys.argv[0])[1]
    err_msg = 'ERROR: %s [%s] ' % (message, addon_id)
    xbmcgui.Dialog().ok('错误', '不好意思，出错了！', err_msg)
    sys.exit(1)

################################################################################
# This function is to remove HTML comments from page data
# Param: page data with comments
# returns: page data without comments
################################################################################
def removeHTMLComments(rawData):
    htmlcomments = re.compile('\<![ \r\n\t]*(--([^\-]|[\r\n]|-[^\-])*--[ \r\n\t]*)\>')
    new_content = htmlcomments.sub('', rawData)
    #print "DEBUGGGGGING - removeHTMLComments" + new_content
    return new_content

################################################################################
# This function reads in data from an URL
# Param: url
#        level - this is just for debugging
# returns: data
################################################################################
def getPageData(url, level):
    user_agent = 'Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.1; Trident/5.0)'
    req = urllib2.Request(urllib.unquote(url))
    req.add_header('User-Agent', user_agent)
    try:
        response = urllib2.urlopen(req)
    except:
        error('<' + str(level) + '>' + ': URL不能打开' + url)
    data = response.read()
    response.close()
    items = re.compile('meta charset="(.+?)"').findall(data)
    doc = removeHTMLComments(data)
    return doc

################################################################################
# This function corresponds to dirLevel = 0
#*******************************************************************************
# Simply reads the main menu: 首页，电视，电影，综艺，少儿.
# This regex has been rewritten and quite robust now.
# We need to get the main menu and their ULStrings.
# Param: pageData - page data
# Return: contentList - includes main menu and URLString.
################################################################################
def getMainMenu(pageData):
    contentList = []

    ULStrRex = '<div class="(.+?)</div>'
    rex = ['<ul(.+?)</ul>', '<li(.+?)</li>', '<a href="(.+?)">(.+?)</a>']

    m0 = re.compile(ULStrRex, re.DOTALL).findall(pageData)
    for div in m0:
        m1 = re.compile(rex[0], re.DOTALL).findall(div)
        for ul in m1:
            # read contents inside all <ul>s
            m2 = re.compile(rex[1], re.DOTALL).findall(ul)
            for li in m2:
                # read contents inside all <li>s for each <ul>
                m3 = re.compile(rex[2], re.DOTALL).findall(li)
                if len(m3) > 0:
                    for href, category in m3:
                        # only append those URLs that has one "/" into the list
                        # so we get 首页，电影，电视，综艺
                        # 避免 “添加视频” 和 “登录”被选中，这里要求len(m2) > 2
                        if href.count('/') == 1 and len(m2) > 2:
                            contentList.append((category, href))
                            #print "DEBUGGGGGING = getMainMenu - contentList" + category + ', ' + href
    if len(contentList) == 0:
        print "DEBUGGGGGING - getMainMenu - empty list"
    return contentList

################################################################################
# This function corresponds to dirLevel = 1
#*******************************************************************************
# We need to get categories for each main menu item.
# Param: pageURL
# Return: categoryList
################################################################################
def getCategoryList(pageURL):
    pageData = getPageData(pageURL, 1)
    catList = []
    rex = ['<a href=(.+?)/a>', '\"/(.+?)/categories/(.+?)\">(.+?)<']
    m0 = re.compile(rex[0], re.DOTALL).findall(pageData)
    for anchorContent in m0:
        #print "DEBUGGGGGING - getCategoryList: " + anchorContent
        # We only need those items that does not include "more":
        if 'more' not in anchorContent:
            m1 = re.compile(rex[1], re.DOTALL).findall(anchorContent)
            for mainMenuItem, catNum, catName in m1:
                #print "DEBUGGGGGING - getCategoryList： " + ", " + mainMenuItem + ", " + catName + ", " + catNum
                catList.append("/" + mainMenuItem + "/categories/" + catNum + "@" + catName)
    return list(set(catList))

################################################################################
# This function reads youtube videoid from string in HTML
# the videoid is of length 11 and the string in HTML is in
# format of [["video_name_1", "video_id_1", num1, num2, "list_name"],
# ["video_name_2", "video_id_2", num1, num2, "list_name"]...]
# Param: the URL for a TV play
# return: the video list that holds the video_ids
################################################################################
def getVideoURL(preUrl):
    videoEleList = []
    videoData = getPageData(preUrl, -1)
    videoData = videoData.replace("\\\"", "'");
    #print "DEBUGGGGGING - preUrl: " + preUrl + ", videoData: " + videoData
    rex = ['\[\[(.+?)\]\]', '\[(.+?)\]', '\"[-_\w]{11}\"', '\["(.+?)\"']
    m0 = re.compile(rex[0], re.DOTALL).findall(videoData)

    for videoList in m0:
        m1 = videoList.split('],')
        for videoPiece in m1:
            m2 = videoPiece.split('"')
            #print "DEBUGGGGGING - getVideoURL"
            # Here we made a shortcut which is not flexible
            # TODO: Will make it more general later.
            #print "DEBUGGGGGING - m2[3]: " + m2[3] + ", m2[1]: " + m2[1]
            videoEleList.append(('"' + m2[3] + '"', m2[1]))

    return videoEleList

################################################################################
# This function get total page number for the current page in a list
# If there is some contents about paging in the HTML, then returns total page number
# If there is no, then returns 1 as total page number
# Param: page data
# return: total page number
################################################################################
def getTotalPageNumber(pageData):
    rex1 = '<span class="last">(.+?)</span>'
    rex2 = '<a href="(.+?)page=(.+?)">'
    m1 = re.compile(rex1, re.DOTALL).findall(pageData)
    if len(m1) > 0:
        m2 = re.compile(rex2, re.DOTALL).findall(m1[0])
        if len(m2) ==1:
            for info1, totalPageNumber in m2:
                return totalPageNumber
    else:
        return 1

################################################################################
# This function corresponds to dirLevel = 3
#*******************************************************************************
# It reads list of video programs with info
# Param: pageData - page data
################################################################################
def getVideoInfoFromUL(pageData):
    contentList = []
    pageDataWithoutNewLine = " ".join(pageData.split())
    # print "DEBUGGGGGING - getVideoInfoFromUL - pageDataWithoutNewLine: " + pageDataWithoutNewLine

    programREX = ['<ul class=(.+?)</ul>', '<li(.+?)</li>',
        ' src="(.+?)"', 'data-href="' + domainName + ':80(.+?)"', 'title="(.+?)"']

    # This is video extracting, we need new RegEx for the new HTML
    m4 = re.compile(programREX[0], re.DOTALL).findall(pageDataWithoutNewLine)
    if len(m4) > 0:
        for ul in m4:
            # print "DEBUGGGGGING - getVideoInfoFromUL - ul: " + ul
            m5 = re.compile(programREX[1], re.DOTALL).findall(ul)
            if len(m5) > 0:
                for li in m5:
                    # print "DEBUGGGGGING - getVideoInfoFromUL - li: " + li
                    m6 = re.compile(programREX[2], re.DOTALL).findall(li)
                    if len(m6) > 0:
                        programThumb = m6[0]
                    else:
                        programThumb = ""
                    m7 = re.compile(programREX[3], re.DOTALL).findall(li)
                    if len(m7) > 0:
                        programHref = m7[0]
                    else:
                        programHref = ""
                    m8 = re.compile(programREX[4], re.DOTALL).findall(li)
                    if len(m8) > 0:
                        programName = m8[0]
                    else:
                        programName = ""
                    if len(m6) > 0 and len(m7) > 0:
                        contentList.append((programName.strip(), programHref, programThumb))
                #if len(contentList) == 0:
                    # We use more general regular expressions format now, so it is normal
                    # that this situation is met.
                    #print "DEBUGGGGGING - getVideoInfoFromUL - empty contentList"
            else:
                print "empty hit in dirLevel = 3 at m5 in getVideoInfoFromUL"
    return contentList


################################################################################
# Program Entrance Point:
################################################################################
rootURL = domainName + '/'
youtubeURL = 'plugin://plugin.video.youtube/?action=play_video&autoplay=1&videoid=%s'
handle = int(sys.argv[1])
dirLevel = 0
isFolder = True
# Get parameters
# sys.argv[0]: plugin://plugin.video.txbb/
# sys.argv[1]: 2 or 3 or 4 or -1
# sys.argv[2]: ?%2ftv&1
#              or ?3&http%3a%2f%2fv.aibuka.com%2f%2ftv_1_1
#              or ?%2fwatch%2f6413&4
#              or ?5&plugin://plugin.video.youtube/?action=play_video&autoplay=1&videoid=-Cyv83ujec0

if sys.argv[2] != '':
    #print "DEBUGGGGGING sys.argv[0] = " + sys.argv[0] + ",    sys.argv[1] = " + sys.argv[1] + ",    sys.argv[2] = " + sys.argv[2]
    paraList = sys.argv[2][1:].replace('%2f', '/').split('&', 1)
    # /tv, 1
    # 3, http%3a//v.aibuka.com//tv_1_1
    # /watch/6413, 4
    # 5, plugin://plugin.video.youtube/?action=play_video&autoplay=1, videoid=-Cyv83ujec0
    #
    # Rule 1: Single digit number is the dirLevel.
    # Rule 2: for dirLevel = 1 or 4, we need add rootURL, otherwise no need to do so.
    #
    # Right now there are only two kinds of parameters:
    # 1. dirLevel (single digit number)
    # 2. the URL

    # dirLevel:1, pageURL: http://v.aibuka.com//tv
    # dirLevel:3, pageURL: http%3a//v.aibuka.com//tv_1_1
    # dirLevel:4, pageURL: http://v.aibuka.com//watch/6413
    # dirLevel:5, pageURL: plugin://plugin.video.youtube/?action=play_video&autoplay=1&videoid=ItrvV2WbDBg

    for item in paraList:
        if len(item) == 1 and item != '/':
            dirLevel = int(item);
        else:
            pageURL = item

    if dirLevel < 3:
        pageURL = rootURL + pageURL
    elif dirLevel == 4:
        pageURL = rootURL + pageURL

    #print "DEBUGGGGGING dirLevel: " + str(dirLevel) + ", pageURL: " + pageURL

menu = []

#*******************************************************************************
# dirLevel = 0, 主菜单
#*******************************************************************************
if dirLevel == 0:
    menu = getMainMenu(getPageData(rootURL, 0))
    for menuItem in menu:
        listitem = xbmcgui.ListItem( menuItem[0] )
        xbmcplugin.addDirectoryItem(handle, sys.argv[0] + '?1&' + menuItem[1], listitem, True)
        #print "DEBUGGGGGING dirLevel: " + str(dirLevel) + ", menuItem: " + str(menuItem[0])

#*******************************************************************************
# dirLevel = 1, 一个主菜单选项的category list
#*******************************************************************************
# pageURL: http://v.aibuka.com//tv
# So this should be cover page for one main menu item.
# We cannot get total page number here, since it would always be one page.
# We need get categories on this page, and make them the list.
elif dirLevel == 1:
    catList = getCategoryList(pageURL)
    for catItem in catList:
        catItemArray = catItem.split('@')
        nextURL = sys.argv[0] + '?2&' + catItemArray[0]
        #print "BEGUGGGGGING - dirLevel=1 - nextURL: " + nextURL + ", " + catItemArray[1]
        listitem = xbmcgui.ListItem( catItemArray[1] )
        xbmcplugin.addDirectoryItem(handle, nextURL, listitem, True)

#*******************************************************************************
# dirLevel = 2, 一个category的分页
#*******************************************************************************
elif dirLevel == 2:
    # We suppose this would always be the list page of sub-categories
    pageData = getPageData(pageURL, 2)
    totalPageNumber  = int(getTotalPageNumber(pageData))
    #print "DEBUGGGGGING - dirLevel=2 - main stream - " + pageURL + " - totalPageNumber: " + str(totalPageNumber)
    # We combine every 4 pages into one page
    if totalPageNumber <= 4:
        # For one page, we read out the program list directly
        menu = getVideoInfoFromUL(getPageData(pageURL, 3))
        if totalPageNumber >= 2:
            menu.extend(getVideoInfoFromUL(getPageData(pageURL + '?page=2', 3)))
        if totalPageNumber >= 3:
            menu.extend(getVideoInfoFromUL(getPageData(pageURL + '?page=3', 3)))
        if totalPageNumber == 4:
            menu.extend(getVideoInfoFromUL(getPageData(pageURL + '?page=4', 3)))
        for menuItem in menu:
            listitem = xbmcgui.ListItem( menuItem[0], thumbnailImage=menuItem[2])
            xbmcplugin.addDirectoryItem(handle, sys.argv[0] + '?4&' + menuItem[1], listitem, True)
            #print "DEBUGGGGGING dirLevel: " + str(dirLevel) + ", menuItem: " + str(menuItem[0])
    else:
        for num in range(1, totalPageNumber + 1):
            # We make an paging design here. We combine 4 pages into 1.
            if num % 4 == 1:
                listitem = xbmcgui.ListItem( '第' + str(num / 4 + 1) + '页' )
                nextURL = sys.argv[0] + '?3&' + pageURL + '_' + str(num) + '_' + str(totalPageNumber)
                xbmcplugin.addDirectoryItem(handle, nextURL, listitem, True)
            #
            #listitem = xbmcgui.ListItem( '第' + str(num) + '页' )
            #if num == 1:
                # print "DEBUGGGGGING: " + sys.argv[0] + '?3&' + pageURL
            #    xbmcplugin.addDirectoryItem(handle, sys.argv[0] + '?3&' + pageURL, listitem, True)
            #else:
                # print "DEBUGGGGGING: " + sys.argv[0] + '?3&' + pageURL + '?page=' + str(num)
            #    xbmcplugin.addDirectoryItem(handle, sys.argv[0] + '?3&' + pageURL + '?page=' + str(num+10), listitem, True)

#*******************************************************************************
# dirLevel = 3, 一个category的清单，或者一个category指定页面的清单
#*******************************************************************************
# pageURL: http%3a//v.aibuka.com//tv_1_1
# sys.argv[0]: plugin://plugin.video.txbb/?4
# menuItem[0]: 后宫·甄嬛传
# menuItem[1]: /watch/4
# menuItem[2]: http://d3u20pllglzex1.cloudfront.net/channel-v/covers/4-1374801233.jpg
elif dirLevel == 3:
    # This is supposed to be a selected program page that may get a list of videos
    # menuItem contains programName, programHref and programThumb
    # We had a customization that combine 4 pages into 1
    #print "DEBUGGGGGING - dirLevel = 3, " + pageURL
    pageURList = pageURL.split('_')
    pageStartNum = int(pageURList[1])
    pageTotalNum = int(pageURList[2])
    if pageStartNum == 1:
        menu = getVideoInfoFromUL(getPageData(pageURList[0], 3))
    else:
        menu = getVideoInfoFromUL(getPageData(pageURList[0] + '?page=' + str(pageStartNum), 3))
    if pageStartNum + 1 < pageTotalNum:
        menu.extend(getVideoInfoFromUL(getPageData(pageURList[0] + '?page=' + str(pageStartNum + 1), 3)))
    if pageStartNum + 2 < pageTotalNum:
        menu.extend(getVideoInfoFromUL(getPageData(pageURList[0] + '?page=' + str(pageStartNum + 2), 3)))
    if pageStartNum + 3 < pageTotalNum:
        menu.extend(getVideoInfoFromUL(getPageData(pageURList[0] + '?page=' + str(pageStartNum + 3), 3)))

    for menuItem in menu:
        #print "checking listURL3: " + str(dirLevel) + ", " + sys.argv[0] + '?' + str(dirLevel + 1) + '&' + menuItem[0] + ' $$ ' + menuItem[1] + ' $$ ' + menuItem[2]
        listitem = xbmcgui.ListItem( menuItem[0], thumbnailImage=menuItem[2])
        xbmcplugin.addDirectoryItem(handle, sys.argv[0] + '?4&' + menuItem[1], listitem, True)

#*******************************************************************************
# dirLevel = 4, 一个系列剧
#*******************************************************************************
# series for one item in a category
# pageURL: http://v.aibuka.com//watch/6413
# menuItemURL: "3ehiztRWYEM"
# lisrURL4: "plugin://plugin.video.txbb/?5&3ehiztRWYEM"
elif dirLevel == 4:
    #print "DEBUGGGGGING - dirLevel = 4, " + pageURL
    menu = getVideoURL(pageURL)
    for menuItemURL, menuItemTitle in menu:
        #print "DEBUGGGGGING - menuItemURL: " + menuItemURL
        listitem = xbmcgui.ListItem( menuItemTitle )
        #print "checking listURL4: " + str(dirLevel) + ", " + sys.argv[0] + '?' + str(dirLevel + 1) + '&' + menuItemURL[1:12]
        xbmcplugin.addDirectoryItem(handle, sys.argv[0] + '?5&' + youtubeURL % menuItemURL[1:12], listitem, False)

#*******************************************************************************
# dirLevel = 5, 一个视频
#*******************************************************************************
# Single video in a series
elif dirLevel == 5:
    print "DEBUGGGGG: dirLevel=5 - " + pageURL
    xbmc.Player(xbmc.PLAYER_CORE_MPLAYER).play(pageURL)

xbmc.executebuiltin("Container.SetViewMode(500)")
xbmcplugin.endOfDirectory(handle)
