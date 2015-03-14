import sublime, sublime_plugin
import json
import os.path
import urllib.request
from .FTP import FTP

class MvPageExportImportOpenItemCommand( sublime_plugin.TextCommand ):
	def run( self, edit ):
		file_path 		= self.view.file_name()
		item_file_attr	= self.view.substr( self.view.expand_by_class( self.view.sel()[ 0 ], sublime.CLASS_WORD_START | sublime.CLASS_WORD_END, '"' ) )

		if file_path is None or not file_path.endswith( '-page.htm' ) or not item_file_attr.endswith( '.htm' ):
			return
	
		settings 					= sublime.load_settings( 'MvPageExportImport.sublime-settings' )
		local_exported_templates	= settings.get( 'local_exported_templates', '' )

		if os.path.dirname( file_path ) != local_exported_templates:
			return

		ftp = FTP( settings )

		if not ftp.download_file( item_file_attr ):
			return sublime.error_message( ftp.error )

		self.view.window().open_file( os.path.join( local_exported_templates, item_file_attr ) )

class MvPageExportImportGetPageCommand( sublime_plugin.WindowCommand ):
	def run( self ):
		self.settings					= sublime.load_settings( 'MvPageExportImport.sublime-settings' )
		self.ftp						= FTP( self.settings )
		self.store_settings 			= self.settings.get( 'store' )
		self.local_exported_templates	= self.settings.get( 'local_exported_templates', '' )

		self.pages_quick_panel()

	def pages_quick_panel( self ):
		print( 'Retrieving store pages through JSON...' )

		entries					= []
		result, response, error = make_json_request( self.store_settings, 'PageList_Load_Query', '&Count=50000&Sort=code' )

		if not result:
			return sublime.error_message( error )

		pages = response[ 'data' ][ 'data' ]

		print( 'Retrieved {0} pages' . format( len( pages ) ) )

		for page in pages:
			entries.extend( [ '{0} - {1}' . format( page[ 'code' ], page[ 'name' ] ) ] )

		self.show_quick_panel( entries, lambda index: self.pages_callback( pages, index ) )

	def pages_callback( self, pages, index ):
		if index == -1:
			return

		page_code				= pages[ index ][ 'code' ]

		print( "Triggering page export for page code '{0}' through JSON" . format( page_code ) )

		result, response, error	= make_json_request( self.store_settings, 'Page_Export_Code', '&Page_Code={0}' . format( page_code ) )

		if not result:
			return sublime.error_message( error )

		print( 'Page exported' )

		export_name = '{0}-page.htm' . format( page_code )

		if not self.ftp.download_file( export_name ):
			return sublime.error_message( self.ftp.error )
		
		self.window.open_file( os.path.join( self.local_exported_templates, export_name ) )

	def show_quick_panel( self, entries, on_select, on_highlight = None ):
		sublime.set_timeout( lambda: self.window.show_quick_panel( entries, on_select, on_highlight = on_highlight ), 10 )

class MvPageExportImportSavePage( sublime_plugin.EventListener ):
	def on_post_save( self, view ):
		file_path = view.file_name()

		if file_path is None or not file_path.endswith( '.htm' ):
			return

		settings 					= sublime.load_settings( 'MvPageExportImport.sublime-settings' )
		store_settings 				= settings.get( 'store', dict() )
		ftp_settings				= settings.get( 'ftp', dict() )
		local_exported_templates	= settings.get( 'local_exported_templates', '' )

		if os.path.dirname( file_path ) != local_exported_templates:
			return

		ftp 		= FTP( settings )
		file_name 	= os.path.basename( file_path )
		page_code 	= os.path.splitext( file_name )[ 0 ].replace( '-page', '' )

		if not ftp.upload_file( file_name ):
			return sublime.error_message( ftp.error )

		if not file_name.endswith( '-page.htm' ):
			return

		print( "Triggering page import for page code '{0}' through JSON" . format( page_code ) )

		result, response, error = make_json_request( store_settings, 'Page_Import_Code', '&Page_Code={0}' . format( page_code ) )

		if not result:
			sublime.error_message( error )

		print( 'Page imported' )

def make_json_request( store_settings, function, other_data = '' ):		
		store_code	= store_settings[ 'store_code' ]
		username	= store_settings[ 'username' ]
		password	= store_settings[ 'password' ]
		json_url 	= store_settings[ 'json_url' ]

		if not json_url.endswith( '?' ):
			json_url += '?'

		url = json_url + 'Store_Code={store_code}&Function={function}&Session_Type=admin&Username={username}&Password={password}{other_data}' \
			  . format( store_code = store_code,  function = function, username = username, password = password, other_data = other_data )

		try:
			request = urllib.request.urlopen( url )
		except Exception as e:
			print( "The following error occurred when requesting URL '{0}': {1}" . format( url, str( e ) ) )
			return False, None, 'Failed to load store pages'

		try:
			content 		= request.read().decode()
			json_response 	= json.loads( content )
		except Exception as e:
			print( "The following error occurred when decoding content '{0}': {1}" . format( content, str( e ) ) )
			return False, None, 'Failed to parse JSON response'

		if 'success' not in json_response or json_response[ 'success' ] != 1:
			print( "The JSON response was not a success: '{0}'" . format( json_response ) )
			return False, None, json_response[ 'error_message' ]

		return True, json_response, None
