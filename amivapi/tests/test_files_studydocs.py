# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.

from io import BytesIO  # Simulate a file
from amivapi.tests import util
from os.path import dirname, extsep, exists, join
from amivapi import models


class FileTest(util.WebTestNoAuth):
    """This tests will check if the file system works correctly.
    """
    def test_upload(self):
        """Tries uploading a file and checks if its safed in the storage dir.
        """
        studydoc = self.new_studydocument()
        studyid = studydoc.id

        h = {'content-type': 'multipart/form-data'}

        filename_post = u"post.txt"
        content_post = b"random content"

        # POST
        data_post = {'study_doc_id': studyid,
                     'name': u'Randomfile',
                     'data': (BytesIO(content_post), filename_post)
                     }

        file_post = self.api.post('/files', data=data_post, headers=h,
                                  status_code=201).json
        self.assert_media_stored(filename_post, content_post)

        id = file_post['_id']

        # PATCH
        # Should return a 405 METHOD NOT ALLOWED since patching is not intended
        filename_patch = u"patch.txt"
        content_patch = b"more random content"

        data_patch = {'study_doc_id': studyid,
                      'name': u'Better Randomfile',
                      'data': (BytesIO(content_patch), filename_patch)
                      }

        h["If-Match"] = file_post['_etag']
        self.api.patch('/files/%i' % id, data=data_patch,
                       headers=h,
                       status_code=405).json

        # PUT
        filename_put = u"put.txt"
        content_put = b"even more random content"
        data_put = {'study_doc_id': studyid,
                    'name': u'Best Randomfile ever',
                    'data': (BytesIO(content_put), filename_put)
                    }

        # Todo: File patch/put:
        # Works with requests, problem with testcase
        h["If-Match"] = file_post['_etag']
        file_put = self.api.put('/files/%i' % id, data=data_put,
                                headers=h,
                                status_code=200).json

        self.assert_media_deleted(filename_patch)
        self.assert_media_stored(filename_put, content_put)

        # DELETE
        h["If-Match"] = file_put['_etag']
        self.api.delete('/files/%i' % id, headers=h,
                        status_code=204)
        self.assert_media_deleted(filename_put)

    def test_upload_existing(self):
        """Upload a second file with the same name

        Expected: Second file gets different filename so they can be stored
        separately and nothing should be overwritten in the first file
        """
        studydoc = self.new_studydocument()
        studyid = studydoc.id

        header = {'content-type': 'multipart/form-data'}

        data = {'study_doc_id': studyid,
                'name': u'Randomfile',
                'data': (BytesIO(b'Content'), u'samename.txt')
                }

        r1 = self.api.post('/files', data=data, headers=header).json

        data = {'study_doc_id': studyid,
                'name': u'Randomfile',
                'data': (BytesIO(b'Different content'), u'samename.txt')
                }

        r2 = self.api.post('/files', data=data, headers=header).json

        name1 = r1['data']['filename']
        name2 = r2['data']['filename']

        self.assertFalse(name1 == name2)
        self.assert_media_stored(name1, 'Content')
        self.assert_media_stored(name2, 'Different content')

    def test_upload_without_studydoc(self):
        """A file needs to belong to a study document. Upload without it should
        fail"""
        header = {'content-type': 'multipart/form-data'}

        # Without ID
        data = {'name': u'Randomfile',
                'data': (BytesIO(b'Content'), u'samename.txt')
                }

        self.api.post('/files', data=data, headers=header, status_code=422)

        # Wrong ID
        data = {'study_doc_id': 42,
                'name': 'Randomfile',
                'data': (BytesIO(b'Content'), u'samename.txt')
                }

        self.api.post('/files', data=data, headers=header, status_code=422)

    def test_delete_studydoc(self):
        """Deleting a studydoc should delete all associated files"""
        studydoc = self.new_studydocument()
        studyid = studydoc.id
        self.new_file(study_doc_id=studyid)

        len = self.db.query(models.File).count()
        self.assertTrue(len == 1)

        h = {"If-Match": studydoc._etag}
        self.api.delete("/studydocuments/%i" % studyid, headers=h,
                        status_code=204)

        len = self.db.query(models.File).count()
        self.assertTrue(len == 0)

    def test_filetype(self):
        """This test will check filetype whitelisting"""

        header = {'content-type': 'multipart/form-data'}

        data = {'pdf': 'Not a file at all.'}
        self.api.post('/joboffers', data=data, headers=header, status_code=422)

        data = {'pdf': (BytesIO(b'Not a pdf'), u'file.pdf')}
        self.api.post('/joboffers', data=data, headers=header, status_code=422)

        data = {'logo': (BytesIO(b'Not a jpeg'), u'file.jpg')}
        self.api.post('/joboffers', data=data, headers=header, status_code=422)

        data = {'logo': (BytesIO(b'Not a png'), u'file.png')}
        self.api.post('/joboffers', data=data, headers=header, status_code=422)

        # Upload something that at least wants to be a PDF
        data = {'pdf': (BytesIO(r'%PDF 1.5% maybe a pdf..'), u'file.pdf')}
        self.api.post('/joboffers', data=data, headers=header, status_code=201)

        # Create Images as jpeg and png which are allowed
        for ext in ("jpg", "png"):
            filename = "lena" + extsep + ext
            filepath = join(dirname(__file__), "fixtures", filename)
            with open(filepath, "rb") as image:
                data = {'logo': (image, filename)}
                self.api.post(
                    '/joboffers', data=data, headers=header, status_code=201
                )

    def assert_media_stored(self, filename, content):
        """Is the file there?"""
        path = join(self.app.config['STORAGE_DIR'], filename)
        self.assertTrue(exists(path))
        with open(path, 'r') as file:
            self.assertTrue(file.read() == content)

    def assert_media_deleted(self, filename):
        """Is the file gone?"""
        self.assertFalse(exists(join(self.app.config['STORAGE_DIR'],
                         filename)))
