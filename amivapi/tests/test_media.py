# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.

"""Test Media handling."""

from io import BytesIO
from os.path import dirname, join
from werkzeug.datastructures import FileStorage

from amivapi.tests.utils import WebTestNoAuth

lenaname = "lena.png"
lenapath = join(dirname(__file__), "fixtures", lenaname)
with open(lenapath, 'rb') as f:
    lenadata = f.read()

test_resource = {
    'resource_methods': ['POST', 'GET'],
    'item_methods': ['GET', 'DELETE'],
    'schema': {
        'test_file': {
            'type': 'media'
        }
    }
}


class MediaTest(WebTestNoAuth):
    """Test upload of file and if a link is returned."""

    def setUp(self):
        """Add test resource."""
        super().setUp()
        self.app.register_resource('test', {
            'resource_methods': ['POST', 'GET'],
            'item_methods': ['GET', 'DELETE'],
            'schema': {
                'test_file': {
                    'type': 'media'
                }
            }
        })

    def _post_file(self, data=lenadata, name=lenaname):
        """Post file. Use BytesIO to be able to set the filename."""
        headers = {'content-type': 'multipart/form-data'}
        _data = {'test_file': (BytesIO(data), name)}
        r = self.api.post("/test", data=_data, headers=headers,
                          status_code=201).json

        # Access file to ensure it's stored correctly
        stored = self.api.get(r['test_file']['file'], status_code=200).data
        self.assertEqual(data, stored)

        return r

    def test_upload(self):
        """Test if uploading works and stores data correctly."""
        self._post_file()

    def test_delete(self):
        """Test removing works."""
        r = self._post_file()
        self.api.delete('/test/' + r['_id'],
                        headers={'If-Match': r['_etag']},
                        status_code=204)
        self.api.get(r['test_file']['file'], status_code=404)

    def test_extended_fields_exist(self):
        """Check attributes."""
        file_info = self._post_file()['test_file']
        for field in ['name', 'content_type', 'length', 'upload_date']:
            self.assertTrue(field in file_info)

    def test_content_type(self):
        """See if content_type is set."""
        content_type = self._post_file()['test_file']['content_type']
        self.assertEqual(content_type, 'image/png')

    def test_name(self):
        """See if name is correct."""
        filename = self._post_file()['test_file']['name']
        self.assertEqual(filename, lenaname)

    def test_random_filename(self):
        """Assert that the url does not equal the filename."""
        url = self._post_file()['test_file']['file']
        # Get file -> last part of url
        file_url = url.split('/')[-1]
        self.assertNotEqual(file_url, lenaname)

    def test_default_content_type(self):
        """See if default content type is application/octet-stream."""
        r = self._post_file(data=b'some_content',
                            name="no_extension_to_guess")
        content_type = r['test_file']['content_type']
        self.assertEqual(content_type, 'application/octet-stream')

    def test_validator(self):
        """Test that the validator correctly accepts formats.

        Ensure that the files is saved correctly in any situation.
        """
        headers = {'content-type': 'multipart/form-data'}
        # Add validator
        schema = self.app.config['DOMAIN']['test']['schema']
        schema['test_file']['filetype'] = ['pdf', 'png', 'jpeg']

        # PNG with default lena
        self._post_file()
        # PDF
        self._post_file(data=br'%PDF magic', name='some.pdf')

        # JPG
        lenapath = join(dirname(__file__), "fixtures", 'lena.jpg')
        with open(lenapath, 'rb') as f:
            jpg_data = f.read()
        self._post_file(data=jpg_data, name='lena.jpg')

        # Something else will be rejected
        data = {'test_file': (BytesIO(b'trololo'), "something")}
        self.api.post("/test", data=data, headers=headers, status_code=422)

    def test_aspect_ratio_validation(self):
        """Test aspect ratio validation."""
        schema = self.app.config['DOMAIN']['test']['schema']
        schema['test_file']['aspect_ratio'] = (1, 1)

        self._post_file()  # Succeeds if lena.png can be posted

        headers = {'content-type': 'multipart/form-data'}
        lionpath = join(dirname(__file__), "fixtures", 'lion.jpg')
        with open(lionpath, 'rb') as f:
            liondata = f.read()

        data = {'test_file': (BytesIO(liondata), "file")}
        self.api.post("/test", data=data, headers=headers, status_code=422)

        # If we change the accepted aspect ratio in the schema, everything works
        # (even if its a non-integer ratio)
        schema['test_file']['aspect_ratio'] = (1.33, 1)

        self._post_file(data=liondata)

    def test_timezone_error(self):
        """Test that #150 is fixed."""
        obj = self.new_object('test',
                              test_file=FileStorage(BytesIO(lenadata),
                                                    lenaname))

        self.api.get(obj['test_file']['file'], headers={
            'If-Modified-Since': 'Mon, 12 Dec 2016 12:23:46 GMT'},
            status_code=200)
