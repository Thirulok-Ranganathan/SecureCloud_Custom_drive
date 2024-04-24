from flask import Flask, request, url_for, render_template, session, redirect, jsonify, flash, send_file
from flask_login import logout_user, login_required
from flask_bcrypt import Bcrypt
from flask_pymongo import PyMongo
from validate_email import validate_email
from werkzeug.utils import secure_filename
from cloud_utils import google_drive_upload, Google_list_files, google_drive_download, dropbox_upload, dropbox_list
import requests, io, json, dropbox
from crypto_process import encryption_process, decryption_process, key_creation
from stego_process import audio_encode, audio_decode

app = Flask(__name__)
bcrypt = Bcrypt(app)
app.config['MONGO_URI'] = 'mongodb://localhost:27017/flask_db'
mongo = PyMongo(app)
app.secret_key = 'holaholahoho'
app.config['UPLOAD_FOLDER'] = 'uploads/'




@app.route('/')
def index():
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        #retrieve data
        users = mongo.db.users
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        email = request.form['email']
        password = request.form['password']

        # Validate email
        if not validate_email(email):
            flash('Invalid email address', 'error')
            return render_template('register.html')
        
        private_key, public_key = key_creation()

        audio_encode(private_key)

        # Save user data to MongoDB
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        user_data = {
            'first_name': first_name,
            'last_name': last_name,
            'email': email,
            'password': hashed_password,
            'public_key': public_key
        }
        #insert and save data to mongodb
        users.insert_one(user_data)
        session['user'] = email
        session['username'] = first_name
        flash('Registration successful!', 'success')
        return render_template('index.html')

    return render_template('register.html')

@app.route('/login', methods=['POST'])
def login():
    if('user' in session):
        return render_template('index.html')
    if request.method == 'POST':
        users = mongo.db.users
        login_user = users.find_one({'email': request.form['email']})
        if login_user:
            if bcrypt.check_password_hash(login_user['password'], request.form['password']):
                session['user'] = login_user['email']
                session['username'] = login_user['first_name']
                return render_template('index.html')
        return 'Invalid email or password'
    return render_template('login.html')
    
@app.route('/logout')
def logout():
    session.pop('user', None) 
    return redirect('/')

@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        drive = request.form.get('folder')
        if drive:
            return render_template('upload.html', drive=drive)
        else:
            return "Please select a drive before uploading a file."

    return render_template('index.html')

@app.route('/upload/<drive>/', methods=['GET', 'POST'])
def process_upload(drive):
    if request.method == 'POST':
        email = session['user']
        if 'file' not in request.files:
            return 'No file part'

        uploaded_file = request.files['file']

        if uploaded_file.filename == '':
            return 'Invalid file type'
        usr_data = mongo.db.users.find_one({'email': email})
        public_key = usr_data.get('public_key')
        if drive == 'Google':
            folderid = usr_data.get('folder_id','')
            cred = usr_data.get('cred',{})
            cred_dict = json.loads(cred)
            read_file = uploaded_file.read()
            encrypt = encryption_process(read_file,public_key)
            
            msg = google_drive_upload(encrypt, uploaded_file.filename, folderid, cred_dict)
        elif drive == 'dropbox':
            read_file = uploaded_file.read()
            encrypt = encryption_process(read_file, public_key)
            access_token = usr_data.get('drop_access','')
            msg = dropbox_upload(encrypt, uploaded_file.filename, access_token)
        else:
            return 'Unknown Drive'

        if msg == 'File uploaded successfully':
            return render_template('index.html')

    return render_template('upload.html')

@app.route('/download', methods=['GET','POST'])
def show_files():
    drive = request.form.get('folder')
    email = session['user']
    usr_data = mongo.db.users.find_one({'email': email})    
    if drive == 'Google':
        folderid = usr_data.get('folder_id','')
        cred = usr_data.get('cred',{})
        cred_dict = json.loads(cred)
        # Retrieve list of files from Google Drive
        files = Google_list_files(folderid, cred_dict)
    elif drive == 'dropbox':
        access_token = usr_data.get('drop_access','')
        # Retrieve list of files from OneDrive or any other service
        files = dropbox_list(access_token)
    else:
        return 'Unknown Drive'

    return render_template('download.html', drive=drive, files=files)


@app.route('/download/<drive>/<file_name>/<file_id>', methods=['GET'])
def download_file(drive, file_name, file_id):
    email = session['user']
    usr_data = mongo.db.users.find_one({'email': email})
    private_key = audio_decode()
    if drive == 'Google':
        
        folderid = usr_data.get('folder_id','')
        cred = usr_data.get('cred',{})
        cred_dict = json.loads(cred)
        try:
            #file = []
            file = google_drive_download(file_id, folderid, cred_dict)
            name = file[0]
            data = file[1]
            """with open(name, 'wb') as fl:
               fl.write(data)
            fl.close()"""

            decrypted_data = decryption_process(data, private_key)

            decrypted_file_obj = io.BytesIO(decrypted_data)
            decrypted_file_obj.seek(0)
            return send_file(decrypted_file_obj, as_attachment = True, download_name = name)
        except Exception as e:
            return f'Error downloading file: {str(e)}', 500
    elif drive == 'dropbox':
        access_token = usr_data.get('drop_access', '')
        dbx = dropbox.Dropbox(access_token)
        try:

            metadata, response = dbx.files_download('/' + file_name)
            print(response.content)
            decrypted_data = decryption_process(response.content, private_key)

            decrypted_file_obj = io.BytesIO(decrypted_data)
            decrypted_file_obj.seek(0)
            return send_file(decrypted_file_obj, as_attachment=True, download_name = file_name)
        except dropbox.exceptions.ApiError as e:
            return f'Error downloading file from Dropbox: {str(e)}', 500
    else:
        abort(404, description='Invalid drive specified. Choose only "Google" drive.')

@app.route('/google_load', methods=['POST'])
def load_google_link():
    return render_template('google_link.html')

@app.route('/dropbox_load', methods=['POST'])
def load_dropbox_link():
    return render_template('dropbox_link.html')

@app.route('/google_link', methods=['GET', 'POST'])
def link_google():
    credentials_file = request.files['file']
    folder_id = request.form.get('folder_id')
    cred_file = credentials_file.read().decode('utf-8')
    email = session['user']
    # Check if data is already present in MongoDB
    existing_data = mongo.db.users.find_one({'email': email})


        # Add credentials and folder ID to MongoDB
    mongo.db.users.update_one({'email': existing_data['email']}, {'$set': {'cred': cred_file, 'folder_id': folder_id}})
    return 'Drive updated'

@app.route('/dropbox_link', methods=['GET', 'POST'])
def link_dropbox():
    app_key = request.form.get('app_key')
    access_token = request.form.get('access_token')

    email = session['user']
    # Check if data is already present in MongoDB
    existing_data = mongo.db.users.find_one({'email': email})


        # Add credentials and folder ID to MongoDB
    mongo.db.users.update_one({'email': existing_data['email']}, {'$set': {'drop_access': access_token}})
    return 'Drive updated'

if __name__ == '__main__':
    bcrypt.init_app(app)
    app.run(debug=True)



    