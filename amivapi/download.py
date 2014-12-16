"""
    amivapi.download
    ~~~~~~~~~~~~~~~~~~~~~~~
    Custom endpoint to access file via url
"""

from flask import Blueprint, send_from_directory, current_app as app

download = Blueprint('download', __name__)


@download.route('/<filename>', methods=['GET'])
def download_file(filename):
    return send_from_directory(app.config['STORAGE_FOLDER'], filename)
