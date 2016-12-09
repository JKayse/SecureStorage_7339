# SecureStorage_7339
Creates a Python server to manage cloud-based file storage by encrypting files before uploading them to either: a local server, Google Drive, DropBox, or Box.

## Installation instructions
  1. Install VirtualEnv for Flask by running `pip install virtualenv`
  2. Install Flask on your system by running `pip install Flask`
  3. Install pycrypto 2.6.1 on your system by running `python -m easy_install http://www.voidspace.org.uk/python/pycrypto-2.6.1/pycrypto-2.6.1.win32-py2.7.exe`
  4. Install the Google Drive API by running `pip install --upgrade google-api-python-client`
  5. Install the Drop Box API by running `pip install dropbox`
  6. Install the Box API by running `pip install boxsdk`

## Running the application
  Run the application by navigating to the application directory and running `python server.py` 
