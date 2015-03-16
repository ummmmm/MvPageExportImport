import ftplib

class FTP():
	def __init__( self, host, username, password, timeout = 15 ):
		self.host		= host
		self.username	= username
		self.password	= password
		self.timeout	= timeout
		self.ftp		= None
		self.error		= ''

	def __del__( self ):
		if self.ftp:
			self.ftp.quit()

	def download_file( self, server_file_path, local_file_path ):
		if not self.login():
			return False

		try:
			self.ftp.retrbinary( 'RETR {0}' . format( server_file_path ), open( local_file_path, 'wb+' ).write )
		except Exception as e:
			print( 'Failed downloading file: {0}' . format( str( e ) ) )
			return self.log_error( 'Failed to download file' )

		return True

	def upload_file( self, local_file_path, server_file_path ):
		if not self.login():
			return False

		try:
			self.ftp.storbinary( 'STOR {0}' . format( server_file_path ), open( local_file_path, 'rb' ) )
		except Exception as e:
			print( 'Failed uploading file: {0}' . format( str( e ) ) )
			return self.log_error( 'Failed to upload file' )

		return True

	def login( self ):
		try:
			self.ftp = ftplib.FTP( self.host, self.username, self.password, self.timeout )
		except Exception as e:
			print( 'Failed connecting / logging in: {0}' . format( str( e ) ) )
			return self.log_error( 'Failed to login' )

		return True

	def log_error( self, error ):
		self.error = error
		return False
