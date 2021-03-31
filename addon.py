#!/usr/bin/python3
# -*- coding: utf-8 -*-
#XBMC 
import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs
#EXTERNAL
import datetime
import json
import os
import requests
import sqlite3
from urllib import parse as urlparse
import FlixGui
import youtube_registration
#INTERNAL
import uservar



class WindowLoad(xbmcgui.WindowXML):

	FANART    = 1000
	ICON      = 1001
	BANNER    = 1002
	LABEL1    = 2003
	PROGRESS1 = 2004
	GROUP2    = 2005
	LABEL2    = 2006
	PROGRESS2 = 2007

	ACTION_PREVIOUS_MENU = 10
	ACTION_NAV_BACK      = 92

	addon         = xbmcaddon.Addon()
	setting       = addon.getSetting
	setting_true  = lambda self,x: bool(True if WindowLoad.setting(str(x)) == "true" else False)
	addoninfo     = addon.getAddonInfo
	addon_id      = addoninfo('id')
	addon_version = addoninfo('version')
	addon_name    = addoninfo('name')
	addon_fanart  = addoninfo('fanart')
	addon_icon    = addoninfo('icon')
	addon_path    = xbmcvfs.translatePath(addoninfo('path'))
	dbpath        = os.path.join(xbmcvfs.translatePath('special://database'),'{}.db'.format(addon_id))
	


	xmlFilename = 'Load_Window.xml'
	scriptPath  = addon_path
	defaultSkin = 'Default'
	defaultRes  = '720p'

	dbconn = None

	def __new__(cls,*args,**kwargs):
		return super(WindowLoad, cls).__new__(cls,WindowLoad.xmlFilename, WindowLoad.scriptPath, WindowLoad.defaultSkin, WindowLoad.defaultRes)
		

	def __init__(self,*args,**kwargs):
		super(WindowLoad,self).__init__()
		self.filmUrl = urlparse.urlunparse((uservar.url.scheme,uservar.url.netloc,uservar.url.filmpath,None,None,None))
		self.tvUrl   = urlparse.urlunparse((uservar.url.scheme,uservar.url.netloc,uservar.url.tvpath,None,None,None))
		self.dbconn  = FlixGui.DatabaseConnection(db=self.dbpath)
		self.meta_cache = FlixGui.MetaCache(self.dbconn,uservar.tmdbapi.key,self.addon_id)
		self.setProperty('COLOR1',uservar.colors.backcolor)
		self.setProperty('COLOR2',uservar.colors.progressbg)
		self.setProperty('THEMECOLOR',uservar.colors.colortheme)
		self.complete = False



	def onInit(self):
		self.winId = xbmcgui.getCurrentWindowId()
		self.setControlImage(self.FANART,self.addon_fanart)
		self.setControlImage(self.ICON,self.addon_icon)
		self.Squence()

	def onAction(self,action):
		self.Log('onAction: {}'.format(action.getId()))
		if action.getId() in [self.ACTION_NAV_BACK,self.ACTION_PREVIOUS_MENU]:
			self.Close()


	def Close(self):
		self.dbconn.Close()
		xbmc.executebuiltin('ActivateWindow(Home)')

	def setControlImage(self, controlId,image):
		if not controlId:
			return
		control = self.getControl(controlId)
		if control:
			control.setImage(image)

	def setControlLabel(self, controlId, label):
		if not controlId:
			return
		control = self.getControl(controlId)
		if control:
			control.setLabel(label)

	def setControlProgress(self,controlId,percent):
		if not controlId:
			return
		control = self.getControl(controlId)
		if control:
			control.setPercent(percent)


	def setControlVisible(self, controlId, visible):
		if not controlId:
			return
		control = self.getControl(controlId)
		if control:
			control.setVisible(visible)


	def Squence(self):
		while xbmc.getCondVisibility('Window.IsVisible({})'.format(self.winId)) and not self.complete:
			count = 0
			funtions = [(self.dbconn.Create,'Creating Cache DB',False),(self.registerkeys,'Registering Keys',False),(self.cachemovies,'Caching Movie List',True),(self.cachetv,'Caching TvShow List',True),(self.CacheTmdbMovie,'Getting TMDB Movie information',True),(self.CacheTmdbTv,'Getting TMDB Tv information',True),(self.SetDbData,'Setting DB Tables',False)]
			total = len(funtions)
			for func in funtions:
				count += 1
				self.setControlLabel(self.LABEL1,func[1])
				self.setControlProgress(self.PROGRESS1,(100.00/total)*count)
				func[0]()
				if func[2]:
					self.setControlVisible(self.GROUP2,True)
				else:
					self.setControlVisible(self.GROUP2,False)

			self.setControlVisible(self.GROUP2,False)		
			self.setControlLabel(self.LABEL1,'Complete')
			self.complete = True
		if self.complete:
			d=FlixGui.WindowHome(self.dbconn)
			d.doModal()
			del d 


	
	def SetDbData(self):
		with self.dbconn.conn:
			c=self.dbconn.conn.cursor()
			c.execute("INSERT OR IGNORE INTO user_watched_movie(tmdb_id) SELECT tmdb_id FROM movie_list")
			c.execute("INSERT OR IGNORE INTO user_list(tmdb_id,media_type) SELECT tmdb_id,media_type FROM movie_list")
			c.execute("INSERT OR IGNORE INTO user_watched_tv(tmdb_id,season,episode) SELECT tmdb_id,season,episode FROM tv_episode_list")
			c.execute("INSERT OR IGNORE INTO user_list(tmdb_id,media_type) SELECT tmdb_id,media_type FROM tv_list")
			c.execute("INSERT OR IGNORE INTO temp.caller(addon_id,tmdb_key,tmdb_user,tmdb_password,youtubeapi_key,youtubeapi_clientid,youtubeapi_clientsecret) VALUES(?,?,?,?,?,?,?)",(self.addon_id,uservar.tmdbapi.key,uservar.tmdbapi.username,uservar.tmdbapi.password,uservar.youtubeapi.apiKey,uservar.youtubeapi.clientId,uservar.youtubeapi.clientSecret))
			self.dbconn.conn.commit()


	def CacheTmdbTv(self):
		count = 0
		with self.dbconn.conn:
			c = self.dbconn.conn.cursor()
			c.execute("SELECT tmdb_id FROM tv_list EXCEPT SELECT tmdb_id FROM master.tmdb_tv_details")
			tmdbids=  [x[0] for x in c.fetchall()]
			total = len(tmdbids)
			if total >0:
				for tmdbid in tmdbids:
					count +=1
					self.setControlProgress(self.PROGRESS2,(100.00/total)*count)
					self.setControlLabel(self.LABEL2,'Collecting {} of {}'.format(count,total))
					self.meta_cache.TvMeta(tmdbid)
			c.close()

	def CacheTmdbMovie(self):
		count = 0
		with self.dbconn.conn:
			c = self.dbconn.conn.cursor()
			c.execute("SELECT tmdb_id FROM movie_list EXCEPT SELECT tmdb_id FROM master.tmdb_movie_details")
			tmdbids=  [x[0] for x in c.fetchall()]
			total = len(tmdbids)
			if total >0:
				for tmdbid in tmdbids:
					count +=1
					self.setControlProgress(self.PROGRESS2,(100.00/total)*count)
					self.setControlLabel(self.LABEL2,'Collecting {} of {}'.format(count,total))
					self.meta_cache.MovieMeta(tmdbid)
			c.close()


	def cachemovies(self):
		movies = []
		a=[]
		count = 0
		r = requests.get(self.filmUrl)
		if r.ok:
			movies = json.loads(r.content).get('movies')
			total = len(movies)
			with self.dbconn.conn:
				c = self.dbconn.conn.cursor()
				for movie in movies:
					count +=1
					self.setControlProgress(self.PROGRESS2,(100.00/total)*count)
					self.setControlLabel(self.LABEL2,'Collecting {} of {}'.format(count,total))
					tmdb_id = movie.get('tmdbid')
					a.append(tmdb_id)
					c.execute("INSERT OR IGNORE INTO movie_list(title,tmdb_id,genre, overview, poster_path,backdrop_path,release_date,stream,date_added) VALUES(?,?,?,?,?,?,?,?,?)",(movie.get('title'),tmdb_id,str(movie.get('genre')),movie.get('overview'),movie.get('poster'),movie.get('backdrop'),movie.get('releasedate'),str(movie.get('stream')),datetime.datetime.now()))
				c.execute("SELECT tmdb_id FROM movie_list")
				b = [i[0] for i in c.fetchall() if i[0] not in a]
				for d in b:
					c.execute("DELETE FROM movie_list WHERE tmdb_id=?",(d,))
			self.dbconn.conn.commit()
		c.close()

	def cachetv(self):
		count = 0
		tvshows= []
		r = requests.get(self.tvUrl)
		if r.ok:
			tvshows = json.loads(r.content).get('tvshows')
			total = len(tvshows)
			a=[]
			with self.dbconn.conn:
				c = self.dbconn.conn.cursor()
				for tvs in tvshows:
					count +=1
					self.setControlProgress(self.PROGRESS2,(100.00/total)*count)
					self.setControlLabel(self.LABEL2,'Collecting {} of {}'.format(count,total))
					tmdbid = tvs.get('tmdbid')
					episodes = tvs.get('episodes')
					a.append(tmdbid)
					c.execute("DELETE FROM tv_list WHERE tmdb_id =? AND episodes !=? ",(tmdbid,str(episodes)))
					c.execute("INSERT OR IGNORE INTO tv_list(title ,tmdb_id ,genre , overview,poster_path,backdrop_path,release_date,episodes,date_added) VALUES(?,?,?,?,?,?,?,?,?)",(tvs.get('title'),tmdbid,str(tvs.get('genre')),tvs.get('overview'),tvs.get('poster'),tvs.get('backdrop'),tvs.get('releasedate'),str(episodes),datetime.datetime.now()))
					for episode in episodes:
						c.execute("INSERT OR IGNORE INTO tv_episode_list(tmdb_id,season,episode,stream) VALUES(?,?,?,?)",(tmdbid,episode.get('season'),episode.get('episode'),str(episode.get('stream'))))
						c.execute("INSERT OR IGNORE INTO user_watched_tv(tmdb_id,season,episode) VALUES(?,?,?)",(tmdbid,episode.get('season'),episode.get('episode')))
				c.execute("SELECT tmdb_id FROM tv_list")
				b = [i[0] for i in c.fetchall() if i[0] not in a]
				for d in b:
					c.execute("DELETE FROM tv_list WHERE tmdb_id=?",(d,))
					c.execute("DELETE FROM user_viewed_tv WHERE tmdb_id=?",(d,))
				self.dbconn.conn.commit()
		c.close()

	def registerkeys(self):
		youtube_registration.register_api_keys(addon_id=self.addon_id,api_key=uservar.youtubeapi.apiKey,client_id=uservar.youtubeapi.clientId,client_secret=uservar.youtubeapi.clientSecret)


	def Log(self,msg):
		if self.setting_true('general.debug'):
			from inspect import getframeinfo, stack
			fileinfo = getframeinfo(stack()[1][0])
			xbmc.log('*__{}__{}*{} Python file name = {} Line Number = {}'.format(self.addon_name,self.addon_version,msg,fileinfo.filename,fileinfo.lineno), level=xbmc.LOGINFO)
		else:pass


if __name__ == '__main__':
	if float(xbmc.getInfoLabel("System.BuildVersion")[:4]) >= 18:
		xbmc.executebuiltin('Dialog.Close(busydialog)')
	d=WindowLoad()
	d.doModal()
	del d
	