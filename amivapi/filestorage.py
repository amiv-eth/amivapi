#from flask import current_app as app
from flask import Blueprint, send_from_directory, abort, request
from werkzeug import secure_filename

from eve.methods.post import post_internal
#from eve.methods.patch import patch_internal
#from eve.methods.common import ratelimit
from eve.render import send_response
from eve.auth import requires_auth

import os
import errno

from pprint import pprint

UPLOAD_FOLDER = r'D:\Programmieren\amivapi\src\filedump'
STORAGE_URL = r'/storage'
ALLOWED_EXTENSIONS = ['.pdf', '.jpg', '.png']


""" Additional file functions """


def create(file):
    """Attempt to create the file on the drive
    First secures the filename
    Then, if necessary, changes it if a file with the same name exists
    Finally get size and type from file
    A dict will be returned that has all the information for the resource
    /files
    """
    filename = secure_filename(file.filename)

    # If needed, add number
    base, ext = os.path.splitext(filename)
    i = 1
    while exists(fullpath(filename)):
        filename = '%s_%s%s' % (base, str(i), ext)
        i += 1

    # Save file
    file.save(fullpath(filename))

    # Return new name
    return {
        'name': file.filename,
        'type': file.mimetype,
        'size': os.path.getsize(fullpath(filename)),
        'content_url': '%s/%s' % (STORAGE_URL, filename),
    }


def remove(filename):
    """Remove file from file system silently
    """
    try:
        os.remove(fullpath(filename))
    except OSError as e:
        if e.errno != errno.ENOENT:  # errno.ENOENT = no such file or directory
            raise  # re-raise exception if a different error occured


def exists(filename):
    """Check if file exists
    """
    return os.path.isfile(fullpath(filename))


def fullpath(filename):
    """Add specified path to file
    """
    return os.path.join(UPLOAD_FOLDER, filename)


def check_filename(filename):
    base, ext = os.path.splitext(filename)
    return ext in ALLOWED_EXTENSIONS


"""Here starts the routing"""


upload = Blueprint('upload ', __name__)


@requires_auth('files')
@upload.route('/files', methods=['POST'])
def upload_file():
    """ This will catch all POST requests to files
    If the request contains no files, it will abort
    Multiple files possible - parses all files and then posts them again
    inside the app as 'real' resources
    """
    if not request.files:
        abort(400, 'The request needs to contain a file.')

    payload = []
    for file in request.files:
        if not check_filename(request.files[file].filename):
            abort(400, 'Forbidden extension.')
        payload.append(create(request.files[file]))

    #app.test_client().post('file', response)
    response = post_internal('files', payload)

    return send_response('files', response)


# @upload.route('/files/<id>', methods=['PATCH'])
# def modify_file(id):
#     """ This will catch all PATCH and PUT requests to a file
#     If the request contains no file or more than one file, it will abort

#     """
#     if len(request.files) != 1:
#         abort(400, 'The request needs to contain a single file.')

#     for file in request.files:
#         if not check_filename(request.files[file].filename):
#             abort(400, 'Forbidden extension.')
#         payload = create(request.files[file])

#     response = patch_internal('files/%s' % str(id), payload)

#     return send_response('files/%s' % str(id), response)


@upload.route('%s/<filename>' % STORAGE_URL, methods=['GET'])
def download_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)


#hook for delete
def post_database_delete(item):
    """After the file item has been removed from the database, the file will
    be removed from the server
    """
    # Take the url (has actual filename) and remove path
    remove(os.path.basename(dict(item)['content_url']))


def post_studydoc_insert(item):
    """After a studydocument is inserted into the database, the relation is saved in a table
    """
    pprint((item))

    # if dict(item)['files'a]
    # db = app.data.driver.session
    #             db.add(thisconfirm)
    #             db.commit()
    return
