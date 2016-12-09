#Author: Jordan Kayse
#Class: CSE 7339
#Filename: google_drive_functions.py

# Include the Google Drive SDK and any other libraries
from __future__ import print_function
import httplib2
import os
import urllib
import io
from apiclient import discovery
from oauth2client import client
from oauth2client import tools
from oauth2client.file import Storage
from apiclient.http import MediaFileUpload
from apiclient.http import MediaIoBaseDownload

try:
	import argparse
	flags = argparse.ArgumentParser(parents=[tools.argparser]).parse_args()
except ImportError:
	flags = None

class GoogleDrive():
	#Authorize the client to use the API and get the credentials.
	def add_api(self):
		#API Static variables
		SCOPES = 'https://www.googleapis.com/auth/drive.file'
		CLIENT_SECRET_FILE = 'client_secret.json'
		APPLICATION_NAME = 'SecureStorage_7339'

		#Get the Google Drive credentials
		home_dir = os.path.expanduser('~')
		credential_dir = os.path.join(home_dir, '.credentials')
		if not os.path.exists(credential_dir):
			os.makedirs(credential_dir)
		credential_path = os.path.join(credential_dir,
		   'drive-python-quickstart.json')

		store = Storage(credential_path)
		credentials = store.get()
		if not credentials or credentials.invalid:
			flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
			flow.user_agent = APPLICATION_NAME
			if flags:
				credentials = tools.run_flow(flow, store, flags)
			else: # Needed only for compatibility with Python 2.6
				credentials = tools.run(flow, store)
			print('Storing credentials to ' + credential_path)

		#Authorize the credentials then return the client to use in the future.
		http = credentials.authorize(httplib2.Http())
		return discovery.build('drive', 'v3', http=http)

	#Create the necessary folders if they don't exist
	def create_folders(self, client):
		response = client.files().list(q="mimeType='application/vnd.google-apps.folder'",fields='nextPageToken, files(id, name)').execute()
		items = response.get('files', [])
		found = 0
		app_folder_id = 0
		#Search to see if the SecureStorage file exists. If it doesn't create it.
		for item in items:
			if item['name'] == "SecureStorage_7339":
				found = 1
				app_folder_id = item['id']
		if found == 0:
			file_metadata = {
			  'name' : 'SecureStorage_7339',
			  'mimeType' : 'application/vnd.google-apps.folder'
			}
			file = client.files().create(body=file_metadata,fields='id').execute()
			app_folder_id = file.get('id')

		response = client.files().list(q="mimeType='application/vnd.google-apps.folder'",fields='nextPageToken, files(id, name)').execute()
		items = response.get('files', [])
		found = 0
		key_folder_id = 0
		#Search to see if the SecureStorage file exists. If it doesn't create it.
		for item in items:
			if item['name'] == "Keys":
				found = 1
				key_folder_id = item['id']
		if found == 0:
			file_metadata = {
			  'name' : 'Keys',
			  'mimeType' : 'application/vnd.google-apps.folder',
			  'parents': [app_folder_id]
			}
			file = client.files().create(body=file_metadata,fields='id').execute()
			key_folder_id = file.get('id')

		return app_folder_id, key_folder_id

	#Upload a file and the key file given a file path.
	def upload_file(self, client, filePath):
		#Create the folders if needed
		app_folder_id, key_folder_id = self.create_folders(client)

		#First uploads the file then uploads the key file in its own folder by appending .key in the name.
		fileName = os.path.basename(filePath)
		file_metadata = {
		  'name' : fileName,
		  'parents': [app_folder_id]
		}
		media = MediaFileUpload(filePath, resumable=True)
		file = client.files().create(body=file_metadata,media_body=media,fields='id').execute()
		file_metadata = {
		  'name' : "{}.key".format(fileName),
		  'parents': [key_folder_id]
		}
		media = MediaFileUpload("{}.key".format(filePath), resumable=True)
		file = client.files().create(body=file_metadata,media_body=media,fields='id').execute()

	#Return a list of the files on the api.
	def list_files(self, client):
		#Create the folders if needed
		app_folder_id, key_folder_id = self.create_folders(client)
		#Get all items in the SecureStorage folder
		response = client.files().list(q="'{0}' in parents and mimeType!='application/vnd.google-apps.folder'".format(app_folder_id), spaces='drive',pageSize=1000,fields="nextPageToken, files(id, name)").execute()
		items = response.get('files', [])
		file_names = []
		for item in items:
			file_names.append(item['name'])
		return file_names

	#Download a file and the key file onto the client's computer given a file name.
	def download_file(self, client, fileName):
		#Create the folders if needed
		app_folder_id, key_folder_id = self.create_folders(client)

		file_id = 0
		response = client.files().list(q="'{0}' in parents and mimeType!='application/vnd.google-apps.folder'".format(app_folder_id), spaces='drive',pageSize=1000,fields="nextPageToken, files(id, name)").execute()
		items = response.get('files', [])
		for item in items:
			if item['name'] == fileName:
				file_id = item['id']
		request = client.files().get_media(fileId=file_id)
		fh = io.FileIO(fileName, mode='wb')
		downloader = MediaIoBaseDownload(fh, request)
		done = False
		while done is False:
			status, done = downloader.next_chunk()
			print("Download %d%%." % int(status.progress() * 100))

		#Download the key file
		file_id = 0
		response = client.files().list(q="'{0}' in parents and mimeType!='application/vnd.google-apps.folder'".format(key_folder_id), spaces='drive',pageSize=1000,fields="nextPageToken, files(id, name)").execute()
		items = response.get('files', [])
		for item in items:
			if item['name'] == "{}.key".format(fileName):
				file_id = item['id']
		request = client.files().get_media(fileId=file_id)
		fh = io.FileIO("{}.key".format(fileName), mode='wb')
		downloader = MediaIoBaseDownload(fh, request)
		done = False
		while done is False:
			status, done = downloader.next_chunk()
			print("Download %d%%." % int(status.progress() * 100))

#Wrapper class for the google drive api.
class GoogleDriveWrapper():
	def __init__(self):
		self.google_drive = GoogleDrive()
		self.__client = self.google_drive.add_api()

	def upload_file(self, filePath):
		return self.google_drive.upload_file(self.__client, filePath)

	def list_files(self):
		return self.google_drive.list_files(self.__client)

	def download_file(self, fileName):
		return self.google_drive.download_file(self.__client, fileName)
