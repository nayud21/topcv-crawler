"""
Google Drive Uploader using Service Account
Upload files to Google Drive folder
"""

import os
import json
from pathlib import Path
from typing import Optional, List
from datetime import datetime

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload


class GDriveUploader:
    """Upload files to Google Drive using Service Account"""
    
    SCOPES = ['https://www.googleapis.com/auth/drive.file']
    
    def __init__(self, credentials_json: str = None, credentials_file: str = None):
        """
        Initialize GDrive uploader
        
        Args:
            credentials_json: JSON string of service account credentials
            credentials_file: Path to service account JSON file
        """
        if credentials_json:
            # Parse from JSON string (for GitHub Actions secrets)
            creds_dict = json.loads(credentials_json)
            self.credentials = service_account.Credentials.from_service_account_info(
                creds_dict, scopes=self.SCOPES
            )
        elif credentials_file:
            # Load from file
            self.credentials = service_account.Credentials.from_service_account_file(
                credentials_file, scopes=self.SCOPES
            )
        else:
            raise ValueError("Either credentials_json or credentials_file must be provided")
        
        self.service = build('drive', 'v3', credentials=self.credentials)
    
    def upload_file(
        self, 
        file_path: str, 
        folder_id: str, 
        file_name: Optional[str] = None,
        mime_type: Optional[str] = None
    ) -> dict:
        """
        Upload a file to Google Drive
        
        Args:
            file_path: Local path to file
            folder_id: Google Drive folder ID
            file_name: Name for file in Drive (default: original name)
            mime_type: MIME type of file
            
        Returns:
            Dict with file info including id and webViewLink
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        if file_name is None:
            file_name = file_path.name
        
        # Auto-detect MIME type
        if mime_type is None:
            ext = file_path.suffix.lower()
            mime_types = {
                '.csv': 'text/csv',
                '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                '.xls': 'application/vnd.ms-excel',
                '.json': 'application/json',
                '.txt': 'text/plain',
                '.pdf': 'application/pdf',
            }
            mime_type = mime_types.get(ext, 'application/octet-stream')
        
        file_metadata = {
            'name': file_name,
            'parents': [folder_id]
        }
        
        media = MediaFileUpload(
            str(file_path),
            mimetype=mime_type,
            resumable=True
        )
        
        file = self.service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, name, webViewLink, size'
        ).execute()
        
        print(f"[INFO] ✅ Uploaded: {file_name}")
        print(f"[INFO]    File ID: {file.get('id')}")
        print(f"[INFO]    Link: {file.get('webViewLink')}")
        
        return file
    
    def upload_folder(
        self, 
        local_folder: str, 
        drive_folder_id: str,
        pattern: str = "*"
    ) -> List[dict]:
        """
        Upload all files matching pattern from local folder to Drive
        
        Args:
            local_folder: Local folder path
            drive_folder_id: Google Drive folder ID
            pattern: Glob pattern for files (default: all files)
            
        Returns:
            List of uploaded file info dicts
        """
        local_folder = Path(local_folder)
        if not local_folder.exists():
            raise FileNotFoundError(f"Folder not found: {local_folder}")
        
        uploaded = []
        for file_path in local_folder.glob(pattern):
            if file_path.is_file():
                try:
                    result = self.upload_file(str(file_path), drive_folder_id)
                    uploaded.append(result)
                except Exception as e:
                    print(f"[ERROR] Failed to upload {file_path}: {e}")
        
        return uploaded
    
    def create_folder(self, folder_name: str, parent_id: Optional[str] = None) -> str:
        """
        Create a folder in Google Drive
        
        Args:
            folder_name: Name of the folder
            parent_id: Parent folder ID (optional)
            
        Returns:
            Created folder ID
        """
        file_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        
        if parent_id:
            file_metadata['parents'] = [parent_id]
        
        folder = self.service.files().create(
            body=file_metadata,
            fields='id, name, webViewLink'
        ).execute()
        
        print(f"[INFO] ✅ Created folder: {folder_name}")
        print(f"[INFO]    Folder ID: {folder.get('id')}")
        
        return folder.get('id')
    
    def list_files(self, folder_id: str, page_size: int = 100) -> List[dict]:
        """
        List files in a Google Drive folder
        
        Args:
            folder_id: Google Drive folder ID
            page_size: Number of files to return
            
        Returns:
            List of file info dicts
        """
        results = self.service.files().list(
            q=f"'{folder_id}' in parents and trashed=false",
            pageSize=page_size,
            fields="files(id, name, mimeType, size, createdTime, modifiedTime)"
        ).execute()
        
        return results.get('files', [])


def upload_to_gdrive(
    file_path: str,
    folder_id: str,
    credentials_json: str = None,
    credentials_file: str = None
) -> dict:
    """
    Convenience function to upload a single file
    
    Args:
        file_path: Path to local file
        folder_id: Google Drive folder ID
        credentials_json: JSON string of service account credentials
        credentials_file: Path to service account JSON file
        
    Returns:
        Uploaded file info dict
    """
    # Try environment variable if not provided
    if not credentials_json and not credentials_file:
        credentials_json = os.environ.get('GDRIVE_CREDENTIALS')
    
    if not credentials_json and not credentials_file:
        raise ValueError(
            "No credentials provided. Set GDRIVE_CREDENTIALS env var "
            "or pass credentials_json/credentials_file"
        )
    
    uploader = GDriveUploader(
        credentials_json=credentials_json,
        credentials_file=credentials_file
    )
    
    return uploader.upload_file(file_path, folder_id)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Upload files to Google Drive")
    parser.add_argument("--file", "-f", required=True, help="File to upload")
    parser.add_argument("--folder-id", "-d", required=True, help="Google Drive folder ID")
    parser.add_argument("--credentials", "-c", help="Path to service account JSON file")
    
    args = parser.parse_args()
    
    credentials_json = os.environ.get('GDRIVE_CREDENTIALS')
    
    result = upload_to_gdrive(
        file_path=args.file,
        folder_id=args.folder_id,
        credentials_json=credentials_json,
        credentials_file=args.credentials
    )
    
    print(f"\n✅ Upload complete!")
    print(f"File ID: {result.get('id')}")
    print(f"Link: {result.get('webViewLink')}")
