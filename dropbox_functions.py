#Author: Jordan Kayse
#Class: CSE 7339
#Filename: dropbox_functions.py

# Include the Dropbox SDK and any other libraries.
import dropbox
import bottle
import os
from threading import Thread, Event
import webbrowser
from wsgiref.simple_server import WSGIServer, WSGIRequestHandler, make_server

class DropBox():
	#Authorize the client to use the API and get the credentials.
	def add_api(self):
		#App key and secret
		app_key = ''
		app_secret = ''

		#Start a temporary server to catch the GET request when the URL redirects to the localhost.
		web_session={}
		class StoppableWSGIServer(bottle.ServerAdapter):
			def __init__(self, *args, **kwargs):
				super(StoppableWSGIServer, self).__init__(*args, **kwargs)
				self._server = None
			def run(self, app):
				server_cls = self.options.get('server_class', WSGIServer)
				handler_cls = self.options.get('handler_class', WSGIRequestHandler)
				self._server = make_server(self.host, self.port, app, server_cls, handler_cls)
				self._server.serve_forever()
			def stop(self):
				self._server.shutdown()
		auth_code_is_available = Event()
		local_oauth_redirect = bottle.Bottle()
		auth_code = {}
		@local_oauth_redirect.get('/')
		def get_token():
			auth_code['code'] = bottle.request.query.code
			auth_code['state'] = bottle.request.query.state
			auth_code_is_available.set()
		local_server = StoppableWSGIServer(host='localhost', port=8080)
		server_thread = Thread(target=lambda: local_oauth_redirect.run(server=local_server))
		server_thread.start()
		flow = dropbox.client.DropboxOAuth2Flow(app_key, app_secret, 'http://localhost:8080', web_session, "dropbox-auth-csrf-token")
		authorize_url = flow.start()
		webbrowser.open(authorize_url)
		auth_code_is_available.wait()
		local_server.stop()

		#If the CSRF matches, finish the authorization and save the access_token.
		assert auth_code['state'] == web_session["dropbox-auth-csrf-token"]
		access_token, user_id, url_state = flow.finish({'state':auth_code['state'],'code':auth_code['code']})

		#Return the client to use in the future.
		return dropbox.client.DropboxClient(access_token)

	#Upload a file and the key file given a file path.
	def upload_file(self, client, filePath):
		#First uploads the file then uploads the key file in its own folder by appending .key in the name.
		fileName = os.path.basename(filePath)
		f = open(filePath, 'rb')
		response = client.put_file("/{}".format(fileName), f)
		f = open("{}.key".format(filePath), 'rb')
		response = client.put_file("/Keys/{}.key".format(fileName), f)

	#Return a list of the files on the api.
	def list_files(self, client):
		#Get all the metadata in the root folder
		folder_metadata = client.metadata('/')
		file_names = []
		for content in folder_metadata['contents']:
			#Add the file if it is not a folder.
			if not content['is_dir']:
				file_names.append(content['path'][1:])
		return file_names

	#Download a file and the key file onto the client's computer given a file name.
	def download_file(self, client, fileName):
		f, metadata = client.get_file_and_metadata("/{}".format(fileName))
		out = open(fileName, 'wb')
		out.write(f.read())
		out.close()
		#Adds .key to get the key file.
		f, metadata = client.get_file_and_metadata("/Keys/{}.key".format(fileName))
		out = open("{}.key".format(fileName), 'wb')
		out.write(f.read())
		out.close()

#Wrapper class for the drop box api.
class DropBoxWrapper():
	def __init__(self):
		self.drop_box = DropBox()
		self.__client = self.drop_box.add_api()

	def upload_file(self, filePath):
		return self.drop_box.upload_file(self.__client, filePath)

	def list_files(self):
		return self.drop_box.list_files(self.__client)

	def download_file(self, fileName):
		return self.drop_box.download_file(self.__client, fileName)
