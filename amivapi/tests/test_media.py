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

    def _post_file(self):
        """Post file. Use BytesIO to be able to set the filename."""
        headers = {'content-type': 'multipart/form-data'}
        data = {'test_file': (BytesIO(lenadata), lenaname)}
        r = self.api.post("/test", data=data, headers=headers,
                          status_code=201).json
        return r

    def test_upload(self):
        """Test if uploading works."""
        self._post_file()

    def test_delete(self):
        """Test removing works."""
        r = self._post_file()
        self.api.delete('/test/' + r['_id'],
                        headers={'If-Match': r['_etag']},
                        status_code=204)
        self.api.get(r['test_file']['file'], status_code=404)

    def test_download(self):
        """Test downloading."""
        r = self._post_file()
        data = self.api.get(r['test_file']['file'], status_code=200).data
        self.assertEqual(data, lenadata)

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
        data = {
            'test_file': (BytesIO(b'some_content'), "no_extension_to_guess")
        }
        headers = {'content-type': 'multipart/form-data'}
        r = self.api.post("/test", data=data, headers=headers,
                          status_code=201).json
        content_type = r['test_file']['content_type']
        self.assertEqual(content_type, 'application/octet-stream')

    def test_validator(self):
        """Test that the validator correctly accepts formats."""
        headers = {'content-type': 'multipart/form-data'}
        # Add validator
        schema = self.app.config['DOMAIN']['test']['schema']
        schema['test_file']['filetype'] = ['pdf', 'png', 'jpeg']

        # PNG
        self._post_file()
        # PDF
        data = {'test_file': (BytesIO(br'%PDF magic'), "some.pdf")}
        self.api.post("/test", data=data, headers=headers,
                      status_code=201)
        # JPG
        lenapath = join(dirname(__file__), "fixtures", 'lena.jpg')
        with open(lenapath, 'rb') as f:
            data = {'test_file': f}
            self.api.post("/test", data=data, headers=headers, status_code=201)

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

        data = {'test_file': (BytesIO(liondata), "file")}  # re-create 'file'
        self.api.post("/test", data=data, headers=headers, status_code=201)

    def test_timezone_error(self):
        """Test that #150 is fixed."""
        obj = self.new_object('test',
                              test_file=FileStorage(BytesIO(lenadata),
                                                    lenaname))

        self.api.get(obj['test_file']['file'], headers={
            'If-Modified-Since': 'Mon, 12 Dec 2016 12:23:46 GMT'},
            status_code=200)
