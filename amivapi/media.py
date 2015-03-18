# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.

"""
    amivapi.media
    ~~~~~~~~~~~~
    File System based mediastorage class.

    Saves Uploaded media to a folder specified in config['STORAGE_FOLDER']

    Adds an endpoint to serve media files
"""

from os import path, remove
from io import FileIO
import errno

from werkzeug import secure_filename
from flask import abort, Blueprint, send_from_directory, current_app as app

from amivapi.authorization import common_authorization


class ExtFile(FileIO):
    """This Class extends the normal file object

    Includes filename (basename of the file), size and content_url
    """
    def __init__(self, filename, app):
        FileIO.__init__(self, filename)
        self.filename = path.basename(self.name)
        self.size = path.getsize(filename)
        self.content_url = '%s/%s' % ('/storage', self.filename)

    def close(self):
        FileIO.close(self)


class FileSystemStorage(object):
    """ Mediastorage class to save files on the server
    """

    def __init__(self, app=None):
        """
        :param app: the flask application (eve itself). This can be used by
        the class to access, amongst other things, the app.config object to
        retrieve class-specific settings.
        """
        self.app = app

    def fullpath(self, filename):
        """Add storage path specified in config to the filename
        """
        return path.join(self.app.config['STORAGE_DIR'], filename)

    def get(self, filename):
        """ Opens the file given by name. Returns and extended file object
            with additional parameters. (See above)
            Returns None if no file was found.
        """
        if not filename:
            return None  # Without filename, there will be no file

        try:
            f = ExtFile(self.fullpath(filename), self.app)
            return f
        except OSError as e:
            if e.errno != errno.ENOENT:  # errno.ENOENT = no such file
                raise  # re-raise exception if a different error occured
            return None

    def put(self, content, filename=None, content_type=None):
        """ Saves a new file using the storage system, preferably with the name
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
        """ Deletes the file referenced by name.
        """
        if not(filename):
            return  # Nothing to do here

        try:
            remove(self.fullpath(filename))
        except OSError as e:
            if e.errno != errno.ENOENT:  # errno.ENOENT = no such file
                raise  # re-raise exception if a different error occured

    def exists(self, filename):
        """ Returns True if a file referenced by the given name
        already exists in the storage system, or False if the name is available
        for a new file.
        """
        return path.isfile(self.fullpath(filename))


#
#
# Endpoint to download files
#
#


download = Blueprint('download', __name__)


@download.route('/storage/<filename>', methods=['GET'])
def download_file(filename):
    if not common_authorization('storage', 'GET'):
        abort(401)
    return send_from_directory(app.config['STORAGE_DIR'], filename)
