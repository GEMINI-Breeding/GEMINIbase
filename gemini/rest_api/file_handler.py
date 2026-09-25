import os
import re
import uuid
from litestar.datastructures import UploadFile

class RESTAPIFileHandler:

    def __init__(self, root_folder: str):
        self.root_folder = root_folder
        self.uploads_folder = os.path.join(self.root_folder, "uploads")
        self.downloads_folder = os.path.join(self.root_folder, "downloads")

        if not os.path.exists(self.uploads_folder):
            os.makedirs(self.uploads_folder)

        if not os.path.exists(self.downloads_folder):
            os.makedirs(self.downloads_folder)

    async def create_file(self, uploaded_file: UploadFile) -> str:
        """Save an upload under a fresh name in the uploads folder.

        The client's filename is never part of the path: it used to be
        joined in as-is, so ``../../app/x.py`` or an absolute path wrote
        anywhere the API could, and two uploads with the same name
        overwrote each other. Only its extension is kept — the record
        code derives the storage key's extension from it.
        """
        ext = os.path.splitext(os.path.basename(uploaded_file.filename or ""))[1]
        if not re.fullmatch(r"\.[A-Za-z0-9]{1,16}", ext):
            ext = ""
        file_content = await uploaded_file.read()
        local_file_path = os.path.join(self.uploads_folder, f"{uuid.uuid4().hex}{ext}")
        with open(local_file_path, "wb") as f:
            f.write(file_content)
        return os.path.abspath(local_file_path)

# Create a File Handler for uploads and downloads
home_dir = os.path.expanduser("~")
gemini_data_dir = os.path.join(home_dir, "gemini_data")
if not os.path.exists(gemini_data_dir):
    os.makedirs(gemini_data_dir)
api_file_handler = RESTAPIFileHandler(root_folder=gemini_data_dir)

