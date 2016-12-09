#Author: Jordan Kayse
#Class: CSE 7339
#Filename: box_functions.py

# Include the Box SDK and any other libraries
import boxsdk
from boxsdk import OAuth2
from boxsdk import Client
import bottle
import os
from threading import Thread, Event
import webbrowser
from wsgiref.simple_server import WSGIServer, WSGIRequestHandler, make_server

class Box():
	#Authorize the client to use the API and get the credentials.
	def add_api(self):
		#App key and secret
		CLIENT_ID = ''
		CLIENT_SECRET = ''

		#Start a temporary server to catch the GET request when the URL redirects to the localhost.
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
		auth_code = {}
		auth_code_is_available = Event()
		local_oauth_redirect = bottle.Bottle()
		@local_oauth_redirect.get('/')
		def get_token():
			auth_code['auth_code'] = bottle.request.query.code
			auth_code['state'] = bottle.request.query.state
			auth_code_is_available.set()
		local_server = StoppableWSGIServer(host='localhost', port=8080)
		server_thread = Thread(target=lambda: local_oauth_redirect.run(server=local_server))
		server_thread.start()
		oauth = OAuth2(
			client_id=CLIENT_ID,
			client_secret=CLIENT_SECRET,
		)
		auth_url, csrf_token = oauth.get_authorization_url('http://localhost:8080')
		webbrowser.open(auth_url)
		auth_code_is_available.wait()
		local_server.stop()

		#If the CSRF matches, finish the authorization and save the access_token.
		assert auth_code['state'] == csrf_token
		access_token, refresh_token = oauth.authenticate(auth_code['auth_code'])

		#Return the client to use in the future.
		return Client(oauth)

	#Create the necessary folders if they don't exist
	def create_folders(self, client):
		root_folder = client.folder(folder_id='0')
		items = root_folder.get_items(limit=100, offset=0)
		found = 0
		folder_id = 0
		#Search to see if the SecureStorage file exists. If it doesn't create it.
		for item in items:
			if item.get()['name'] == "SecureStorage_7339" and item.get()['type'] == "folder":
				found = 1
				folder_id = item.get()['id']
		if found == 0:
			app_folder = root_folder.create_subfolder("SecureStorage_7339")
		else:
			app_folder = client.folder(folder_id=folder_id)

		items = app_folder.get_items(limit=100, offset=0)
		found = 0
		folder_id = 0
		#Search to see if the Keys file exists. If it doesn't create it.
		for item in items:
			if item.get()['name'] == "Keys" and item.get()['type'] == "folder":
				found = 1
				folder_id = item.get()['id']
		if found == 0:
			key_folder = app_folder.create_subfolder("Keys")
		else:
			key_folder = client.folder(folder_id=folder_id)
		return app_folder, key_folder

	#Upload a file and the key file given a file path.
	def upload_file(self, client, filePath):
		#Create the folders if needed
		app_folder, key_folder = self.create_folders(client)

		#First uploads the file then uploads the key file in its own folder by appending .key in the name.
		fileName = os.path.basename(filePath)
		f = open(filePath, 'rb')
		a_file = app_folder.upload_stream(f, fileName)
		f = open("{}.key".format(filePath), 'rb')
		fileName = os.path.basename("{}.key".format(filePath))
		a_file = key_folder.upload_stream(f, fileName)


	#Return a list of the files on the api.
	def list_files(self, client):
		#Create the folders if needed
		app_folder, key_folder = self.create_folders(client)
		#Get all items in the SecureStorage folder
		items = app_folder.get_items(limit=100, offset=0)
		file_names = []
		for item in items:
			#Add the file if it is not a folder.
			if item.get()['type'] == "file":
				file_names.append(item.get()['name'])
		return file_names

	#Download a file and the key file onto the client's computer given a file name.
	def download_file(self, client, fileName):
		#Create the folders if needed
		app_folder, key_folder = self.create_folders(client)

		items = app_folder.get_items(limit=100, offset=0)
		file_id = 0
		for item in items:
			if item.get()['name'] == fileName and item.get()['type'] == "file":
				file_id = item.get()['id']
		out = open(fileName, 'wb')
		client.file(file_id=file_id).download_to(out)
		out.close()

		#Download the key file
		items = key_folder.get_items(limit=100, offset=0)
		file_id = 0
		for item in items:
			if item.get()['name'] == "{}.key".format(fileName) and item.get()['type'] == "file":
				file_id = item.get()['id']
		out = open("{}.key".format(fileName), 'wb')
		client.file(file_id=file_id).download_to(out)
		out.close()

#Wrapper class for the box api.
class BoxWrapper():
	def __init__(self):
		self.box = Box()
		self.__client = self.box.add_api()

	def upload_file(self, filePath):
		return self.box.upload_file(self.__client, filePath)

	def list_files(self):
		return self.box.list_files(self.__client)

	def download_file(self, fileName):
		return self.box.download_file(self.__client, fileName)
