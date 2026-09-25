"""Uploaded record files never write outside the uploads folder."""
import asyncio
import os
from unittest.mock import AsyncMock, MagicMock

import pytest

from gemini.rest_api.file_handler import RESTAPIFileHandler


def _upload(name: str, data: bytes = b"x"):
    f = MagicMock()
    f.filename = name
    f.read = AsyncMock(return_value=data)
    return f


@pytest.mark.parametrize(
    "name, ext",
    [
        ("../../escape.py", ".py"),
        ("/etc/passwd", ""),
        ("..\\..\\win.txt", ".txt"),
        ("plot_7.tif", ".tif"),
        ("no-extension", ""),
    ],
)
def test_saved_inside_uploads_with_a_fresh_name(tmp_path, name, ext):
    handler = RESTAPIFileHandler(root_folder=str(tmp_path))
    path = asyncio.run(handler.create_file(_upload(name)))
    assert os.path.dirname(path) == os.path.abspath(handler.uploads_folder)
    assert os.path.splitext(path)[1] == ext


def test_same_name_uploads_do_not_overwrite(tmp_path):
    handler = RESTAPIFileHandler(root_folder=str(tmp_path))
    a = asyncio.run(handler.create_file(_upload("r.csv", b"a")))
    b = asyncio.run(handler.create_file(_upload("r.csv", b"b")))
    assert a != b
    assert open(a, "rb").read() == b"a"
