#!/bin/bash
if [ -d "/storage/.xbmc" ]; then
  mcversion=".xbmc"
  echo "xbmc installed"
elif [ -d "/storage/.kodi" ]; then
  mcversion=".kodi"
  echo "kodi installed"
else
  mcversion=".kodi"
  echo "none...assuming kodi"
fi

echo $mcversion

if [ $mcversion = '.kodi' ]; then
    export LD_LIBRARY_PATH=/storage/$mcversion/userdata/addon_data/plugin.video.p2p-streams/acestream/lib
fi

/storage/$mcversion/userdata/addon_data/plugin.video.p2p-streams/acestream/acestreamengine --lib-path /storage/$mcversion/userdata/addon_data/plugin.video.p2p-streams/acestream --client-console $1 $2
