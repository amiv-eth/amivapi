# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.

"""File System based mediastorage class.

Saves Uploaded media to a folder specified in config['STORAGE_FOLDER']


"""

from os import path, remove, makedirs
import errno
from imghdr import what
from itsdangerous import Signer, BadSignature
from werkzeug import secure_filename, FileStorage

from amivapi.utils import register_validator, register_domain


class FileWrapper(object):
    """Put a little wrapper around a file so we can set attributes."""

    def __init__(self, file_):
        """Init."""
        self._file = file_

    def __getattr__(self, attr):
        """Pass everything to the file."""
        return getattr(self._file, attr)

    def close(self):
        print("closed")
        return self._file.close()


class FileSystemStorage(object):
    """Mediastorage class to save files on the server."""

    def __init__(self, app=None):
        """Init storage."""
        self.app = app
        self.signer = Signer(self.app.config['TOKEN_SECRET'])

    def fullpath(self, filename, create=False):
        """Add storage path specified in config to the filename.

        Args:
            filename (str): the name of the file to save
            create (bool): If true, create all dirs along path.
        """
        path = self.app.config['STORAGE_DIR']
        if create:
            makedirs(path, exist_ok=True)
        return path.join(path, filename)

    def get(self, filename):
        """Open the file given by name.

        Args:
            filename (string): the file to open.

        Returns:
            ExtFile: file object with additional parameters
        """
        if not filename:
            return None  # Without filename, there will be no file

        try:
            f = FileWrapper(open(self.fullpath(filename), 'r'))
            f.filename = path.basename(self.name)
            f.size = path.getsize(filename)
            f.content_url = '%s/%s' % ('/storage', self.filename)

            return f
        except OSError as e:
            if e.errno != errno.ENOENT:  # errno.ENOENT = no such file
                raise  # re-raise exception if a different error occured
            return None

    def put(self, content, filename=None, content_type=None):
        """Save file.

         Saves a new file using the storage system, preferably with the name
        specified. If there already exists a file with this name name, the
        storage system may modify the filename as necessary to get a unique
        name. The actual name of the stored file will be returned.
        The content argument has to be of type FileStorage (see Werkzeug),
        the validator will ensure this.
        The content type argument is used to appropriately identify the file
        when it is retrieved.
        .. versionchanged:: 0.5
           Allow filename to be optional (#414).
        """
        if filename:
            filename = secure_filename(filename)  # Safety first!
        elif content.filename:
            filename = secure_filename(content.filename)
        else:
            filename = 'file'

        # If needed, add number
        base, ext = path.splitext(filename)
        i = 1
        while self.exists(self.fullpath(filename)):
            filename = '%s_%i%s' % (base, i, ext)
            i += 1

        # Save file
        content.save(self.fullpath(filename, create=True))
        return filename

    def delete(self, filename):
        """Delete the file referenced by name."""
        if not(filename):
            return  # Nothing to do here

        try:
            remove(self.fullpath(filename))
        except OSError as e:
            if e.errno != errno.ENOENT:  # errno.ENOENT = no such file
                raise  # re-raise exception if a different error occured

    def exists(self, filename):
        """Check if file exists.

        Return True if a file referenced by the given name
        already exists in the storage system, or False if the name is available
        for a new file.
        """
        return path.isfile(self.fullpath(filename))


class MediaValidator(object):
    """Validation for files."""

    def _validate_type_media(self, field, value):
        """Validate `media` data type.

        Args:
            field (string): field name.
            value: field value.
        """
        if not isinstance(value, FileStorage):
            self._error(field, "file was expected, got '%s' instead." % value)

    def _validate_filetype(self, filetype, field, value):
        """Validate filetype. Can validate images and pdfs.

        Pdf: Check if first 4 characters are '%PDF' because that marks
        a PDF
        Image: Use imghdr library function what()

        Cannot validate others formats.

        Args:
            filetype (list): filetypes, e.g. ['pdf', 'png']
            field (string): field name.
            value: field value.
        """
        if not((('pdf' in filetype) and (value.read(4) == r'%PDF')) or
               (what(value) in filetype)):
            self._error(field, "filetype not supported, has to be one of: " +
                        " %s" % str(filetype))


storagedomain = {
    'storage': {
        'resource_methods': ['GET'],
        'item_methods': ['GET'],
        'public_methods': [],
        'public_item_methods': [],
        'registered_methods': ['GET'],
        'description': {
            'general': 'Endpoint to download files, get the URLs via /files'
        }
    }
}


def init_app(app):
    """Register resources and blueprints, add hooks and validation."""
    register_validator(app, MediaValidator)
    register_domain(app, storagedomain)
