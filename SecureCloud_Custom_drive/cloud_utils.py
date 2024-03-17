import io
from googleapiclient.discovery import build
from google.oauth2 import service_account
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload, MediaIoBaseUpload
import dropbox
from dropbox.exceptions import AuthError


def google_drive_upload(encrypted_data, filename, folder_id, CREDENTIALS_FILE_PATH):  

    scopes = ['https://www.googleapis.com/auth/drive']
    credentials = service_account.Credentials.from_service_account_info(CREDENTIALS_FILE_PATH, scopes=scopes)
    service = build('drive', 'v3', credentials=credentials)

    try:
         

        file_metadata = {
            'name': filename,  
            'parents': [folder_id]
        }

        # Convert encrypted_data to BytesIO object
        encrypted_file = io.BytesIO(encrypted_data)

        media_body = MediaIoBaseUpload(encrypted_file, mimetype='application/octet-stream', resumable=True)
        
        file = service.files().create(
            body=file_metadata,
            media_body=media_body
        ).execute()

        return 'File uploaded successfully'
    except Exception as e:
        return f'Error uploading file: {str(e)}'





def Google_list_files(folder_id, CREDENTIALS_FILE_PATH):
    scopes = ['https://www.googleapis.com/auth/drive']
    credentials = service_account.Credentials.from_service_account_info(CREDENTIALS_FILE_PATH, scopes=scopes)
    service = build('drive', 'v3', credentials=credentials)

    try:
        query = f"'{folder_id}' in parents and trashed = false"  
        results = service.files().list(q=query, pageSize=10, fields="files(id, name)").execute()
        items = results.get('files', [])
        
        files_list = []
        for item in items:
            files_list.append({'id': item['id'], 'name': item['name']})
        
        return files_list
    except Exception as e:
        return f'Error listing files: {str(e)}'

def google_drive_download(file_id, folder_id, CREDENTIALS_FILE_PATH):
    scopes = ['https://www.googleapis.com/auth/drive']
    credentials = service_account.Credentials.from_service_account_info(CREDENTIALS_FILE_PATH, scopes=scopes)
    service = build('drive', 'v3', credentials=credentials)

    try:
        file_metadata = service.files().get(fileId=file_id).execute()
        file_name = file_metadata['name']

        request = service.files().get_media(fileId=file_id)
        file = io.BytesIO()
        downloader = MediaIoBaseDownload(file, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
            print(f"Download {int(status.progress() * 100)}.")
        file.seek(0)
        file_data = file.getvalue()  
        response_data = [file_name, file_data]
        return response_data
    except Exception as e:
        return f'Error downloading file: {str(e)}'



def dropbox_upload(encrypted_data, file_name, access_token):
    try:
        dbx = dropbox.Dropbox(access_token)

        # Create a new file with the given name and encrypted data
        dbx.files_upload(encrypted_data, '/'+file_name)
        
        return 'File uploaded successfully'
    except Exception as e:
        print(f'Error uploading file: {str(e)}')
        return f'Error uploading file: {str(e)}'

def dropbox_list(access_token):
    dbx = dropbox.Dropbox(access_token)
    try:
        files_list = []
        for entry in dbx.files_list_folder('').entries:
            files_list.append({'id': entry.id, 'name': entry.name})
        
        return files_list
    except AuthError as e:
        return f'Error authenticating with Dropbox: {str(e)}'
    except dropbox.exceptions.ApiError as e:
        return f'Error listing files: {str(e)}'