import os
import shutil
import uuid
from contextlib import contextmanager, suppress
from typing import Iterator, Optional

from litestar.datastructures import UploadFile

UPLOAD_COPY_CHUNK_SIZE = 1024 * 1024

class RESTAPIFileHandler:

    def __init__(self, root_folder: str):
        self.root_folder = root_folder
        self.uploads_folder = os.path.join(self.root_folder, "uploads")
        self.downloads_folder = os.path.join(self.root_folder, "downloads")

        if not os.path.exists(self.uploads_folder):
            os.makedirs(self.uploads_folder)

        if not os.path.exists(self.downloads_folder):
            os.makedirs(self.downloads_folder)

    def save_upload(self, uploaded_file: UploadFile) -> str:
        """Copy an upload to a new file in the uploads folder and return its path.

        The file gets a random name so concurrent uploads of the same filename
        can't overwrite each other, and a client-supplied name like
        ``../../x`` can't write outside the folder. Only the extension is
        kept: record processing builds the MinIO object key from it.
        """
        extension = os.path.splitext(os.path.basename(uploaded_file.filename or ""))[1]
        local_file_path = os.path.join(self.uploads_folder, f"{uuid.uuid4().hex}{extension}")
        uploaded_file.file.seek(0)
        with open(local_file_path, "wb") as f:
            shutil.copyfileobj(uploaded_file.file, f, UPLOAD_COPY_CHUNK_SIZE)
        return os.path.abspath(local_file_path)

    @contextmanager
    def saved_upload(self, uploaded_file: Optional[UploadFile]) -> Iterator[Optional[str]]:
        """Save ``uploaded_file`` for the duration of the block, then delete it.

        Yields None when there is no upload.
        """
        if uploaded_file is None:
            yield None
            return
        local_file_path = self.save_upload(uploaded_file)
        try:
            yield local_file_path
        finally:
            with suppress(FileNotFoundError):
                os.remove(local_file_path)

# Create a File Handler for uploads and downloads
home_dir = os.path.expanduser("~")
gemini_data_dir = os.path.join(home_dir, "gemini_data")
if not os.path.exists(gemini_data_dir):
    os.makedirs(gemini_data_dir)
api_file_handler = RESTAPIFileHandler(root_folder=gemini_data_dir)

