import os.path
import ftplib

class FTP():
	def __init__( self, settings ):
		self.ftp_settings				= settings.get( 'ftp', None )
		self.local_exported_templates	= settings.get( 'local_exported_templates', '' )
		self.ftp 						= ftplib.FTP( self.ftp_settings[ 'host' ] )
		self.error						= ''
		self.logged_in					= False
		self.current_directory			= None

	def download_file( self, template_name ):
		if not self.login():
			return False

		if not self.cwd( self.ftp_settings[ 'exported_templates' ] ):
			return False

		command 		= 'RETR {0}' . format( template_name )
		download_path 	= os.path.join( self.local_exported_templates, template_name )

		try:
			print( command )

			self.ftp.retrbinary( command, open( download_path, 'wb+' ).write )
		except Exception as e:
			print( "FTP: Failed to download file '{0}': {1}" . format( template_name, str( e ) ) )
			return self.log_error( 'Failed to download file' )

		return True

	def upload_file( self, template_name ):
		if not self.login():
			return False

		if not self.cwd( self.ftp_settings[ 'exported_templates' ] ):
			return False

		command 		= 'STOR {0}' . format( template_name )
		download_path 	= os.path.join( self.local_exported_templates, template_name )

		try:
			print( command )

			self.ftp.storbinary( command, open( download_path, 'rb' ) )
		except Exception as e:
			print( "FTP: Failed to upload file '{0}': {1}" . format( template_name, str( e ) ) )
			return self.log_error( 'Failed to upload file' )

		return True

	def login( self ):
		if self.logged_in:
			return True

		try:
			self.ftp.login( self.ftp_settings[ 'username' ], self.ftp_settings[ 'password' ] )
		except Exception as e:
			print( "FTP: Failed to login to server '{0}': {1}" . format( self.ftp_settings[ 'host' ], str( e ) ) )
			return self.log_error( 'Failed to login to server' )

		self.logged_in = True

		return True

	def cwd( self, path ):
		if self.current_directory == path:
			return

		try:
			self.ftp.cwd( path )
		except Exception as e:
			print( "FTP: Failed to change to directory '{0}': {1}" . format( path, str( e ) ) )
			return self.log_error( "Failed to changed to directory '{1}'" . format( path ) )

		self.current_directory = path

		return True

	def log_error( self, error ):
		self.error = error
		return False
