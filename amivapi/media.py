# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.

"""File System based mediastorage class.

Saves Uploaded media to a folder specified in config['STORAGE_FOLDER']

Adds an endpoint to serve media files
"""

from os import path, remove
from io import FileIO
import errno
from imghdr import what

from werkzeug import secure_filename, FileStorage
from flask import abort, Blueprint, send_from_directory, current_app as app

from amivapi.auth.authorization import common_authorization
from amivapi.utils import register_validator, register_domain


class ExtFile(FileIO):
    """This Class extends the normal file object.

    Includes filename (basename of the file), size and content_url
    """

    def __init__(self, filename):
        """Init."""
        FileIO.__init__(self, filename)
        self.filename = path.basename(self.name)
        self.size = path.getsize(filename)
        self.content_url = '%s/%s' % ('/storage', self.filename)

    def close(self):
        """Close internal file object."""
        FileIO.close(self)


class FileSystemStorage(object):
    """Mediastorage class to save files on the server."""

    def __init__(self, app=None):
        """Init storage."""
        self.app = app

    def fullpath(self, filename):
        """Add storage path specified in config to the filename."""
        return path.join(self.app.config['STORAGE_DIR'], filename)

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
            f = ExtFile(self.fullpath(filename))
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
        while self.exists(filename):
            filename = '%s_%s%s' % (base, str(i), ext)
            i += 1

        # Save file
        content.save(self.fullpath(filename))
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


# Endpoint to download files

download = Blueprint('download', __name__)


@download.route('/storage/<filename>', methods=['GET'])
def download_file(filename):
    """Send a file.

    TODO (Alex): Maybe better use new eve method?
    """
    if not common_authorization('storage', 'GET'):
        abort(401)
    return send_from_directory(app.config['STORAGE_DIR'], filename)


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

    app.register_blueprint(download)
