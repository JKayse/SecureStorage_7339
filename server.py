import os
import sys
from cloud_storage_app_database import CredentialsWrapper
from flask import Flask, Response, flash, request, redirect, url_for, session, render_template
from werkzeug.utils import secure_filename
import dropbox_functions
import box_functions
import google_drive_functions
import encrypt
import json


app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = './uploads'
global_stuff = {}

@app.route('/', methods=['GET', 'POST'])
def index():
    if global_stuff.has_key('current_user'):
        #3 methods below are used to add the APIs
        if request.method == 'POST' and request.form['type'] == "google":
            global_stuff['google_drive_wrapper'] = google_drive_functions.GoogleDriveWrapper()
            return redirect(url_for('index'))

        elif request.method == 'POST' and request.form['type'] == "dropbox":
            global_stuff['drop_box_wrapper'] = dropbox_functions.DropBoxWrapper()
            return redirect(url_for('index'))

        elif request.method == 'POST' and request.form['type'] == "box":
            global_stuff['box_wrapper'] = box_functions.BoxWrapper()
            return redirect(url_for('index'))

        #If the user wants to upload a file figure out where and encrypt the file
        elif request.method == 'POST' and request.form['type'] == "upload":
            if 'file' not in request.files:
                return redirect(request.url)
            file = request.files['file']
            if file.filename == '':
                return redirect(request.url)
            if file:
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                filepath = app.config['UPLOAD_FOLDER']+"/"+filename

                #Encrypt the file
                encryption_wrapper = encrypt.EncryptWrapper()
                password = global_stuff['current_user'].get_password()
                key = encryption_wrapper.generateKey(password)
                encryption_wrapper.encryptFile(filepath, key)
                encryption_wrapper.saveKey(filepath, key)
                encryption_wrapper.encryptKey(filepath + '.key', password)

                if request.form['api'] == '0':
                    #Upload to the google api. Connect to the api if you haven't yet.
                    if not global_stuff.has_key('google_drive_wrapper'):
                        global_stuff['google_drive_wrapper'] = google_drive_functions.GoogleDriveWrapper()
                    global_stuff['google_drive_wrapper'].upload_file(filepath)

                if request.form['api'] == '1':
                    #Upload to the dropbox api. Connect to the api if you haven't yet.
                    if not global_stuff.has_key('drop_box_wrapper'):
                        global_stuff['drop_box_wrapper'] = dropbox_functions.DropBoxWrapper()
                    global_stuff['drop_box_wrapper'].upload_file(filepath)

                if request.form['api'] =='2':
                    #Upload to the box api. Connect to the api if you haven't yet.
                    if not global_stuff.has_key('box_wrapper'):
                        global_stuff['box_wrapper'] = box_functions.BoxWrapper()
                    global_stuff['box_wrapper'].upload_file(filepath)

                if request.form['api'] == '3':
                    #Upload to the database
                    with open(filepath, 'rb') as file:
                        tfile = file.read()
                    with open(filepath+".key", 'rb') as file:
                        kfile = file.read()
                    global_stuff['current_user'].add_local_file_and_key(filename, tfile, kfile)
    
                return redirect(url_for('index', filename=filename))
        elif request.method == 'POST' and request.form['type'] == "download":
            #Get the filename and location of the file (api or local)
            value = request.form['files'].split('/', 1 )
            filename = value[1]
            if value[0] == 'google':
                #Download to the google api. Connect to the api if you haven't yet.
                if not global_stuff.has_key('google_drive_wrapper'):
                    global_stuff['google_drive_wrapper'] = google_drive_functions.GoogleDriveWrapper()
                global_stuff['google_drive_wrapper'].download_file(filename)

            elif value[0] == 'dropbox':
                #Download to the dropbox api. Connect to the api if you haven't yet.
                if not global_stuff.has_key('drop_box_wrapper'):
                    global_stuff['drop_box_wrapper'] = dropbox_functions.DropBoxWrapper()
                global_stuff['drop_box_wrapper'].download_file(filename)

            elif value[0] == 'box':
                #Download to the box api. Connect to the api if you haven't yet.
                if not global_stuff.has_key('box_wrapper'):
                    global_stuff['box_wrapper'] = box_functions.BoxWrapper()
                global_stuff['box_wrapper'].download_file(filename)

            elif value[0] == 'local':
                #Get the file strings then write the file locally.
                tfile, kfile = global_stuff['current_user'].get_local_file_and_key(filename)
                with open(filename, 'wb') as file_out:
                    file_out.write(tfile)
                with open(filename + ".key", 'wb') as file_out:
                    file_out.write(kfile)
                
            #Decrypt the file
            encryption_wrapper = encrypt.EncryptWrapper()
            password = global_stuff['current_user'].get_password()
            key = encryption_wrapper.decryptKey(filename, password)
            encryption_wrapper.decryptFile(filename, key)

            return redirect(url_for('index'))

        #Get the file lists for the search. Only use the APIs that have been added
        file_list = []     
        local_file_names = global_stuff['current_user'].get_local_file_names()
        for val in local_file_names:
            data = {}
            data['api'] = 'local'
            data['name'] = str(val)
            file_list.append(data)
        if global_stuff.has_key('google_drive_wrapper'):
            google_file_names = global_stuff['google_drive_wrapper'].list_files()
            for val in google_file_names:
                data = {}
                data['api'] = 'google'
                data['name'] = val
                file_list.append(data)
        if global_stuff.has_key('drop_box_wrapper'):
            dropbox_file_names = global_stuff['drop_box_wrapper'].list_files()
            for val in dropbox_file_names:
                data = {}
                data['api'] = 'dropbox'
                data['name'] = val
                file_list.append(data)
        if global_stuff.has_key('box_wrapper'):
            box_file_names = global_stuff['box_wrapper'].list_files()
            for val in box_file_names:
                data = {}
                data['api'] = 'box'
                data['name'] = val
                file_list.append(data)

        return render_template('function.html', file_list=file_list)
    else:
        return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if not global_stuff.has_key('current_user'):
        #Create an account
        if request.method == 'POST' and request.form['type'] == "signUp":
            global_stuff['current_user'] = CredentialsWrapper(request.form['username'],request.form['password'])
            global_stuff['current_user'].add_user()
            return redirect(url_for('index'))
        #Try logging in
        elif request.method == 'POST' and request.form['type'] == "signIn":
            global_stuff['current_user'] = CredentialsWrapper(request.form['username'],request.form['password'])
            value = global_stuff['current_user'].user_credentials_correct()
            if value:
                return redirect(url_for('index'))
            else:
                global_stuff.pop('current_user', None)
                return redirect(url_for('login'))

        return render_template('initial.html')
    else:
        return redirect(url_for('index'))

@app.route('/logout', methods=['GET'])
def logout():
    if global_stuff.has_key('current_user'):
        global_stuff.pop('current_user', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.config['SECRET_KEY'] = "ITSASECRET"
    app.run(port=5000, debug=True)
