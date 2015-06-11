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
import sys
import xbmcgui
import time
import xbmc
import os
from trakt_api import Trakt_API
from addon.common.addon import Addon

_SALTS = Addon('plugin.video.salts', sys.argv)
ICON_PATH = os.path.join(_SALTS.get_path(), 'icon.png')
use_https = _SALTS.get_setting('use_https') == 'true'
trakt_timeout = int(_SALTS.get_setting('trakt_timeout'))

def get_pin():
    AUTH_BUTTON = 200
    LATER_BUTTON = 201
    NEVER_BUTTON = 202
    ACTION_PREVIOUS_MENU = 10
    ACTION_BACK = 92
    CENTER_Y = 6
    CENTER_X = 2
    
    class PinAuthDialog(xbmcgui.WindowXMLDialog):
        auth = False
        
        def onInit(self):
            self.pin_edit_control = self.__add_editcontrol(30, 240, 40, 450)
            self.setFocus(self.pin_edit_control)
            auth = self.getControl(AUTH_BUTTON)
            never = self.getControl(NEVER_BUTTON)
            self.pin_edit_control.controlUp(never)
            self.pin_edit_control.controlLeft(never)
            self.pin_edit_control.controlDown(auth)
            self.pin_edit_control.controlRight(auth)
            auth.controlUp(self.pin_edit_control)
            auth.controlLeft(self.pin_edit_control)
            never.controlDown(self.pin_edit_control)
            never.controlRight(self.pin_edit_control)
            
        def onAction(self, action):
            #print 'Action: %s' % (action.getId())
            if action == ACTION_PREVIOUS_MENU or action == ACTION_BACK:
                self.close()

        def onControl(self, control):
            #print 'onControl: %s' % (control)
            pass

        def onFocus(self, control):
            #print 'onFocus: %s' % (control)
            pass

        def onClick(self, control):
            #print 'onClick: %s' % (control)
            if control == AUTH_BUTTON:
                if not self.__get_token():
                    builtin = "XBMC.Notification(%s, Trakt.tv PIN Authorization Failed, 5000, %s)" % (_SALTS.get_name(), ICON_PATH)
                    xbmc.executebuiltin(builtin)
                    return
                self.auth = True

            if control == LATER_BUTTON:
                builtin = "XBMC.Notification(%s, You will be reminded in 24 hours, 5000, %s)" % (_SALTS.get_name(), ICON_PATH)
                xbmc.executebuiltin(builtin)
                _SALTS.set_setting('last_reminder', str(int(time.time())))

            if control == NEVER_BUTTON:
                builtin = "XBMC.Notification(%s, Use Addon Settings later if you change your mind, 5000, %s)" % (_SALTS.get_name(), ICON_PATH)
                xbmc.executebuiltin(builtin)
                _SALTS.set_setting('last_reminder', '-1')

            if control in [AUTH_BUTTON, LATER_BUTTON, NEVER_BUTTON]:
                self.close()
        
        def __get_token(self):
            pin = self.pin_edit_control.getText().strip()
            if pin:
                try:
                    trakt_api = Trakt_API(use_https=use_https, timeout=trakt_timeout)
                    result = trakt_api.get_token(pin=pin)
                    _SALTS.set_setting('trakt_oauth_token', result['access_token'])
                    _SALTS.set_setting('trakt_refresh_token', result['refresh_token'])
                    return True
                except:
                    return False
            return False
        
        # have to add edit controls programatically because getControl() (hard) crashes XBMC on them
        def __add_editcontrol(self, x, y, height, width):
            media_path = os.path.join(_SALTS.get_path(), 'resources', 'skins', 'Default', 'media')
            temp = xbmcgui.ControlEdit(0, 0, 0, 0, '', font='font12', textColor='0xFFFFFFFF', focusTexture=os.path.join(media_path, 'button-focus2.png'),
                                       noFocusTexture=os.path.join(media_path, 'button-nofocus.png'), _alignment=CENTER_Y | CENTER_X)
            temp.setPosition(x, y)
            temp.setHeight(height)
            temp.setWidth(width)
            self.addControl(temp)
            return temp
        
    dialog = PinAuthDialog('TraktPinAuthDialog.xml', _SALTS.get_path())
    dialog.doModal()
    if dialog.auth:
        builtin = "XBMC.Notification(%s, Trakt Authorization Complete, 3000, %s)" % (_SALTS.get_name(), ICON_PATH)
        xbmc.executebuiltin(builtin)
    del dialog
