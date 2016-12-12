# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.

"""File System based mediastorage class.

Saves Uploaded media to a folder specified in config['STORAGE_FOLDER']


"""

from bson import tz_util
from os import path, remove, makedirs, urandom
import errno
from contextlib import contextmanager
from datetime import datetime as dt
from mimetypes import guess_type
from base64 import b64encode
from imghdr import what
from werkzeug import secure_filename

from amivapi.utils import register_validator


@contextmanager
def ignore_not_found():
    """Ignore errno.ENOENT (no such file), re-raise everything else.

    In case of a FileNotFound error, just do nothing.
    """
    try:
        yield
    except (OSError, IOError) as e:
        if e.errno != errno.ENOENT:
            raise e


class FileWrapper(object):
    """A little wrapper providing extra attributes to opened file."""

    DEFAULT_MIMETYPE = "application/octet-stream"

    def __init__(self, filepath, filename):
        """Init: Open file and add attributes.

        Args:
            filepath (str): The path to the file (i.e. how its stored)
            filename (str): The filename the client should receive,
                will also be used to guess mimetype
        """
        self._file = open(filepath, 'rb')
        self.length = path.getsize(filepath)
        self.upload_date = dt.fromtimestamp(path.getmtime(filepath),
                                            tz_util.utc)
        self.name = filename
        self.content_type = guess_type(self.name)[0]
        if self.content_type is None:
            self.content_type = self.DEFAULT_MIMETYPE

    def __iter__(self):
        """Return the file as iterator."""
        return self._file

    def __getattr__(self, attr):
        """Pass everything to the file."""
        return getattr(self._file, attr)


class FileSystemStorage(object):
    """Mediastorage class to save files on the server."""

    def _add_randomness(self, str_in):
        """Add random stuff to a string."""
        n_bytes = self.app.config['FILENAME_RANDOM_BYTES']
        randomstr = secure_filename(
            b64encode(urandom(n_bytes)).decode('utf_8'))
        return "%s.%s" % (str_in, randomstr)

    def _remove_randomness(self, str_in):
        """Remove random stuff from the end of a string."""
        # Split at dots, remove last part and join with dots again
        return ".".join(str_in.split(".")[:-1])

    def __init__(self, app=None):
        """Init storage."""
        self.app = app

    def fullpath(self, filename):
        """Add storage path specified in config to the filename.

        Args:
            filename (str): the name of the file to save
        """
        storage_path = self.app.config['STORAGE_DIR']
        return path.join(storage_path, filename)

    def get(self, filename, resource=None):
        """Open the file given by name."""
        with ignore_not_found():
            return FileWrapper(self.fullpath(filename),
                               self._remove_randomness(filename))

    def put(self, content, filename=None, content_type=None, resource=None):
        """Save file.

        Also add randomness to file name and create directories if needed.
        """
        if filename:
            input_filename = secure_filename(filename)  # Safety first!
        elif content.filename:
            input_filename = secure_filename(content.filename)
        else:
            input_filename = 'file'

        # If needed, add number
        filename = self._add_randomness(input_filename)
        while self.exists(filename):
            filename = self._add_randomness(input_filename)

        # Create dir if needed
        storage_path = self.app.config['STORAGE_DIR']
        if not path.isdir(storage_path):
            makedirs(storage_path)

        # Save file
        content.save(self.fullpath(filename))
        return filename

    def delete(self, filename, resource=None):
        """Delete the file referenced by name."""
        with ignore_not_found():
            remove(self.fullpath(filename))

    def exists(self, filename, resource=None):
        """Check if file exists."""
        return path.isfile(self.fullpath(filename))


class MediaValidator(object):
    """Validation for files."""

    def _validate_filetype(self, filetype, field, value):
        """Validate filetype. Can validate images and pdfs.

        pdf: Check if first 4 characters are '%PDF' because that marks
        a PDF
        Image: Use imghdr library function what()

        Cannot validate others formats.

        Important: what() returns 'jpeg', NOT 'jpg', so 'jpg' will never be
        recognized!

        Args:
            filetype (list): filetypes, e.g. ['pdf', 'png']
            field (string): field name.
            value: field value.
        """
        is_pdf = value.read(4) == br'%PDF'
        value.seek(0)  # Go back to beginning for what()
        t = 'pdf' if is_pdf else what(value)

        if not(t in filetype):
            self._error(field, "filetype '%s' not supported, has to be in: "
                        "%s" % (t, filetype))


def init_app(app):
    """Register resources and blueprints, add hooks and validation."""
    register_validator(app, MediaValidator)
