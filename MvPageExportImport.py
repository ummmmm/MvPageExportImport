import sublime, sublime_plugin
import json
import os.path
import urllib.request
import re
import threading
from .FTP import FTP

#
# Pages / Items Quick Panel Load
#

class MvPageExportImportGetSitesCommand( sublime_plugin.WindowCommand ):
	def run( self ):
		self.settings 	= sublime.load_settings( 'MvPageExportImport.sublime-settings' )
		sites			= []

		for site in self.settings.get( 'sites', [] ):
			sites.append( site[ 'name' ] )

		if not sites:
			sublime.error_message( 'No sites configured' )
			return

		sublime.set_timeout( lambda: self.window.show_quick_panel( sites, lambda index: self.site_callback( sites, index ) ) )

	def site_callback( self, sites, index ):
		if index == -1:
			return

		self.window.run_command( 'mv_page_export_import_get_pages', { 'site': sites[ index ] } )

class MvPageExportImportGetPagesCommand( sublime_plugin.WindowCommand ):
	def run( self, site = None ):
		settings = sublime.load_settings( 'MvPageExportImport.sublime-settings' )

		if site is None:
			if settings.get( 'sites' ) is not None:
				return self.window.run_command( 'mv_page_export_import_get_sites' )

			self.settings = settings
		else:
			try:
				for site_settings in settings.get( 'sites', [] ):
					if site_settings[ 'name' ] == site:
						self.settings = site_settings
						break
			except KeyError:
				sublime.error_message( 'Site not found' )
				return
			except Exception:
				sublime.error_message( 'Invalid configuration file' )
				return

		thread = PageListLoadThread( self.settings, on_complete = self.pages_quick_panel )
		thread.start()
		ThreadProgress( thread, 'Loading pages', error_message = 'Failed loading pages' )

	def pages_quick_panel( self, pages ):
		entries = []

		for page in pages:
			entries.extend( [ '{0} - {1}' . format( page[ 'code' ], page[ 'name' ] ) ] )

		self.show_quick_panel( entries, lambda index: self.pages_callback( pages, index ) )

	def pages_callback( self, pages, index ):
		if index == -1:
			return

		page_code 	= pages[ index ][ 'code' ]
		thread 		= PageExportThread( page_code, self.settings, on_complete = self.download_page )
		thread.start()
		ThreadProgress( thread, 'Exporting {0}' . format( page_code ), '{0} exported' . format( page_code ), 'Export of {0} failed' . format( page_code ) )

	def download_page( self, page_code ):
		file_name 	= '{0}-page.htm' . format ( page_code )
		thread 		= FileDownloadThread( file_name, self.settings, on_complete = self.download_page_callback )
		thread.start()
		ThreadProgress( thread, 'Downloading {0}' . format( page_code ), '{0} downloaded' . format( page_code ), 'Download of {0} failed' . format( page_code ) )

	def download_page_callback( self, local_file_path ):
		self.window.open_file( local_file_path )

	def show_quick_panel( self, entries, on_select, on_highlight = None ):
		sublime.set_timeout( lambda: self.window.show_quick_panel( entries, on_select, on_highlight = on_highlight ), 10 )

class MvPageExportImportGetItemsCommand( sublime_plugin.WindowCommand ):
	def run( self ):
		view 		= self.window.active_view()
		file_path 	= view.file_name()

		if file_path is None or not file_path.endswith( '.htm' ):
			return

		dir_name 		= os.path.dirname( file_path )
		self.settings	= determine_settings( dir_name )

		if self.settings is None:
			return

		item_paths	= []
		item_regex	= '<mvt:item name="[^"].+?"\s*(?:param="[^"].*?"\s*)?file="([^"].+?\.htm)"\s*\/>'
		view.find_all( item_regex, fmt = '$1', extractions = item_paths )

		if not item_paths:
			return

		self.show_quick_panel( item_paths, lambda index: self.itemlist_load( item_paths, index ) )

	def itemlist_load( self, item_paths, index ):
		if index == -1:
			return

		file_name 	= item_paths[ index ]
		thread 		= FileDownloadThread( file_name, self.settings, on_complete = self.download_item_callback )
		thread.start()
		ThreadProgress( thread, 'Downloading {0}' . format( file_name ), '{0} downloaded' . format( file_name ), 'Download of {0} failed' . format( 'file_name' ) )

	def download_item_callback( self, local_file_path ):
		self.window.open_file( local_file_path )

	def show_quick_panel( self, entries, on_select, on_highlight = None ):
		unique = []

		for entry in entries:
			if entry not in unique:
				unique.append( entry )

		sublime.set_timeout( lambda: self.window.show_quick_panel( unique, on_select, on_highlight = on_highlight ), 10 )

#
# File Upload
#

class MvPageExportImportSavePage( sublime_plugin.EventListener ):
	def on_post_save( self, view ):
		file_path = view.file_name()

		if file_path is None or not file_path.endswith( '.htm' ):
			return

		dir_name 		= os.path.dirname( file_path )
		self.settings	= determine_settings( dir_name )

		if self.settings is None:
			return

		file_name		= os.path.basename( file_path )
		thread 			= FileUploadThread( file_name, self.settings, on_complete = self.upload_file_callback )
		thread.start()
		ThreadProgress( thread, 'Uploading {0}' . format( file_name ), '{0} uploaded' . format( file_name ), 'Upload of {0} failed' . format( file_name ) )

	def upload_file_callback( self, file_name ):
		if not file_name.endswith( '-page.htm' ):
			return

		page_code 	= file_name.replace( '-page.htm', '' )
		thread 		= PageImportThread( page_code, self.settings, on_complete = None )
		thread.start()
		ThreadProgress( thread, 'Importing {0}' . format( page_code ), '{0} imported' . format( page_code ), 'Import of {0} failed' . format( page_code ) )

#
# File Open (used for underlining items)
#

class MvPageExportImportOpenPage( sublime_plugin.EventListener ):
	def __init__( self ):
		self.regions	= []
		self.item_regex = '<mvt:item name="[^"].+?"\s*(param="[^"].*?")?\s*file="[^"].+?\.htm"\s*\/>'

	def on_load( self, view ):
		file_path	= view.file_name()

		if file_path is None or not file_path.endswith( '.htm' ):
			return

		dir_name = os.path.dirname( file_path )
		settings = determine_settings( dir_name )

		if settings is None:
			return

		items = view.find_all( self.item_regex )
		self.do_underline( view, items )

	def on_modified( self, view ):
		file_path	= view.file_name()

		if file_path is None:
			return

		dir_name = os.path.dirname( file_path )
		settings = determine_settings( dir_name )

		if settings is None:
			return

		items 		= view.find_all( self.item_regex )
		self.do_underline( view, items )

	def do_underline( self, view, items ):
		scope_map 	= {}
		regex		= re.compile( 'file="([^"].+?\.htm)"')

		for region in self.regions:
			view.erase_regions( 'mvpageexportimport_{0}' . format( region ) )

		for item in items:
			line 	= view.substr( sublime.Region( item.a, item.b ) )
			matches	= regex.search( line )

			if not matches:
				continue

			start, end 	= matches.span()
			start 		= item.a + start + 6
			end			= item.a + end - 1

			self.regions.append( item.a )
			view.add_regions( 'mvpageexportimport_{0}' . format( item.a ), [ sublime.Region( start, end ) ], 'dot', flags = sublime.DRAW_SOLID_UNDERLINE | sublime.DRAW_NO_FILL | sublime.DRAW_NO_OUTLINE )

#
# Used by the mouse bindings
#

class MvPageExportImportOpenItemCommand( sublime_plugin.TextCommand ):
	def run( self, edit ):
		file_path 		= self.view.file_name()

		if file_path is None or not file_path.endswith( '.htm' ):
			return

		item_file_attr	= self.view.substr( self.view.expand_by_class( self.view.sel()[ 0 ], sublime.CLASS_WORD_START | sublime.CLASS_WORD_END, '"' ) )

		if not item_file_attr.endswith( '.htm' ):
			return

		dir_name = os.path.dirname( file_path )
		settings = determine_settings( dir_name )

		if settings is None:
			return

		file_name 	= item_file_attr
		thread 		= FileDownloadThread( file_name, settings, on_complete = self.download_item_callback )
		thread.start()
		ThreadProgress( thread, 'Downloading {0}' . format( file_name ), '{0} downloaded' . format( file_name ), 'Download of {0} failed' . format( file_name ) )

	def download_item_callback( self, local_file_path ):
		self.view.window().open_file( local_file_path )

#
# Thread Functionality
#

class ThreadProgress():
	def __init__( self, thread, message, success_message = '', error_message = '' ):
		self.thread 			= thread
		self.message 			= message
		self.success_message 	= success_message
		self.error_message		= error_message
		self.addend 			= 1
		self.size 				= 8

		sublime.set_timeout( lambda: self.run( 0 ), 100 )

	def run( self, i ):
		if not self.thread.is_alive():
			if hasattr( self.thread, 'result' ) and not self.thread.result:
				return sublime.status_message('')

			if hasattr( self.thread, 'error' ) and self.thread.error:
				return sublime.status_message( self.error_message )

			return sublime.status_message( self.success_message )

		before 	= i % self.size
		after 	= ( self.size - 1 ) - before

		sublime.status_message( '{0} [{1}={2}]' . format( self.message, ' ' * before, ' ' * after ) )

		if not after:
			self.addend = -1

		if not before:
			self.addend = 1

		i += self.addend

		sublime.set_timeout( lambda: self.run( i ), 100 )

class PageListLoadThread( threading.Thread ):
	def __init__( self, settings, on_complete ):
		self.settings 		= settings
		self.on_complete	= on_complete
		self.error			= False
		threading.Thread.__init__( self )

	def run( self ):
		store_settings = self.settings.get( 'store' )

		print( 'Retrieving pages' )

		result, response, error = make_json_request( store_settings, 'PageList_Load_Query', '&Count=50000&Sort=code' )

		if not result:
			self.error = True
			return sublime.error_message( error )

		pages = response[ 'data' ][ 'data' ]

		print( 'Retrieved {0} pages' . format( len( pages ) ) )

		sublime.set_timeout( lambda: self.on_complete( pages ), 10 )

class PageExportThread( threading.Thread ):
	def __init__( self, page_code, settings, on_complete ):
		self.page_code		= page_code
		self.settings 		= settings
		self.on_complete	= on_complete
		self.error			= False
		threading.Thread.__init__( self )

	def run( self ):
		store_settings = self.settings.get( 'store' )

		print( "Exporting {0}" . format( self.page_code ) )

		result, response, error	= make_json_request( store_settings, 'Page_Export_Code', '&Page_Code={0}' . format( self.page_code ) )

		if not result:
			self.error = True
			return sublime.error_message( error )

		print( 'Page exported' )

		sublime.set_timeout( lambda: self.on_complete( self.page_code ), 10 )

class FileDownloadThread( threading.Thread ):
	def __init__( self, file_name, settings, on_complete ):
		self.file_name		= file_name
		self.settings		= settings
		self.on_complete	= on_complete
		self.error			= False
		threading.Thread.__init__( self )

	def run( self ):
		ftp_settings = self.settings.get( 'ftp', {} )

		ftp_settings.setdefault( 'host', '' )
		ftp_settings.setdefault( 'username', '' )
		ftp_settings.setdefault( 'password', '' )
		ftp_settings.setdefault( 'exported_templates', '' )
		ftp_settings.setdefault( 'timeout', 15 )

		server_directory	= ftp_settings[ 'exported_templates' ]
		local_directory		= self.settings.get( 'local_exported_templates', '' )

		server_file_path 	= os.path.join( server_directory, self.file_name )
		local_file_path		= os.path.join( local_directory, self.file_name )
		ftp 				= FTP( ftp_settings[ 'host' ], ftp_settings[ 'username' ], ftp_settings[ 'password' ], ftp_settings[ 'timeout' ] )

		print( 'Downloading file {0}' . format( server_file_path ) )

		if not ftp.download_file( server_file_path, local_file_path ):
			self.error = True
			return sublime.error_message( ftp.error )

		print( 'Downloaded complete' )

		sublime.set_timeout( lambda: self.on_complete( local_file_path ) )

class FileUploadThread( threading.Thread ):
	def __init__( self, file_name, settings, on_complete ):
		self.file_name 		= file_name
		self.settings		= settings
		self.on_complete	= on_complete
		self.error			= False
		threading.Thread.__init__( self )

	def run( self ):
		ftp_settings = self.settings.get( 'ftp', {} )

		ftp_settings.setdefault( 'host', '' )
		ftp_settings.setdefault( 'username', '' )
		ftp_settings.setdefault( 'password', '' )
		ftp_settings.setdefault( 'exported_templates', '' )
		ftp_settings.setdefault( 'timeout', 15 )

		server_directory	= ftp_settings[ 'exported_templates' ]
		local_directory		= self.settings.get( 'local_exported_templates', '' )

		server_file_path 	= os.path.join( server_directory, self.file_name )
		local_file_path		= os.path.join( local_directory, self.file_name )
		ftp 				= FTP( ftp_settings[ 'host' ], ftp_settings[ 'username' ], ftp_settings[ 'password' ], ftp_settings[ 'timeout' ] )

		print( 'Uploading file {0}' . format( local_file_path ) )

		if not ftp.upload_file( local_file_path, server_file_path ):
			self.error = True
			return sublime.error_message( ftp.error )

		print( 'Upload complete' )

		sublime.set_timeout( lambda: self.on_complete( self.file_name ), 10 )

class PageImportThread( threading.Thread ):
	def __init__( self, page_code, settings, on_complete ):
		self.page_code		= page_code
		self.settings		= settings
		self.on_complete	= on_complete
		self.error			= False
		threading.Thread.__init__( self )

	def run( self ):
		store_settings = self.settings.get( 'store' )

		print( "Importing {0}" . format( self.page_code ) )

		result, response, error	= make_json_request( store_settings, 'Page_Import_Code', '&Page_Code={0}' . format( self.page_code ) )

		if not result:
			self.error = True
			return sublime.error_message( error )

		print( 'Page imported' )

#
# Helper Functions
#

def determine_settings( dir_name ):
	settings 	= sublime.load_settings( 'MvPageExportImport.sublime-settings' )
	sites		= settings.get( 'sites' )

	if sites is None:
		return settings

	try:
		for site in sites:
			if site[ 'local_exported_templates' ] == dir_name:
				return site
	except:
		pass

	return None

def make_json_request( store_settings, function, other_data = '' ):
		store_settings.setdefault( 'store_code', '' )
		store_settings.setdefault( 'json_url', '' )
		store_settings.setdefault( 'username', '' )
		store_settings.setdefault( 'password', '' )
		store_settings.setdefault( 'timeout', 15 )

		store_code	= store_settings[ 'store_code' ]
		json_url 	= store_settings[ 'json_url' ]
		username	= store_settings[ 'username' ]
		password	= store_settings[ 'password' ]
		timeout		= store_settings[ 'timeout' ]

		if not json_url.endswith( '?' ):
			json_url += '?'

		url = json_url + 'Store_Code={store_code}&Function={function}&Session_Type=admin&Username={username}&Password={password}{other_data}' \
			  . format( store_code = store_code,  function = function, username = username, password = password, other_data = other_data )

		try:
			request = urllib.request.urlopen( url, timeout = timeout )
		except Exception as e:
			print( 'Failed opening URL: {0}' . format( str( e ) ) )
			return False, None, 'Failed to open URL'

		try:
			content = request.read().decode()
		except Exception as e:
			print( 'Failed decoding response: {0}' . format( str( e ) ) )
			return False, None, 'Failed to decode response'

		try:
			json_response 	= json.loads( content )
		except Exception as e:
			print( 'Failed to parse JSON: {0}' . format( str( e ) ) )
			return False, None, 'Failed to parse JSON response'

		if 'success' not in json_response or json_response[ 'success' ] != 1:
			print( 'JSON response was not a success {0}' . format( json_response ) )
			return False, None, json_response[ 'error_message' ]

		return True, json_response, None
