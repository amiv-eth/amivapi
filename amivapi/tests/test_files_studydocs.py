from StringIO import StringIO  # Used to create file on the go
from amivapi.tests import util
from os.path import exists, join
from amivapi import models
from PIL import Image


class FileTest(util.WebTestNoAuth):
    """This tests will check if the file system works correctly.
    """
    def test_upload(self):
        """Tries uploading a file and checks if its safed in the storage dir.
        """
        studydoc = self.new_studydocument()
        studyid = studydoc.id

        h = {'content-type': 'multipart/form-data'}

        filename_post = "post.txt"
        content_post = "random content"

        # POST
        data_post = {'study_doc_id': studyid,
                     'name': 'Randomfile',
                     'data': (StringIO(content_post), filename_post)
                     }

        file_post = self.api.post('/files', data=data_post, headers=h,
                                  status_code=201).json
        self.assert_media_stored(filename_post, content_post)

        id = file_post['_id']

        # PATCH
        # Should return a 405 METHOD NOT ALLOWED since patching is not intended
        filename_patch = "patch.txt"
        content_patch = "more random content"

        data_patch = {'study_doc_id': studyid,
                      'name': 'Better Randomfile',
                      'data': (StringIO(content_patch), filename_patch)
                      }

        h["If-Match"] = file_post['_etag']
        self.api.patch('/files/%i' % id, data=data_patch,
                       headers=h,
                       status_code=405).json

        # PUT
        filename_put = "put.txt"
        content_put = "even more random content"
        data_put = {'study_doc_id': studyid,
                    'name': 'Best Randomfile ever',
                    'data': (StringIO(content_put), filename_put)
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
                'name': 'Randomfile',
                'data': (StringIO('Content'), 'samename.txt')
                }

        r1 = self.api.post('/files', data=data, headers=header).json

        data = {'study_doc_id': studyid,
                'name': 'Randomfile',
                'data': (StringIO('Different content'), 'samename.txt')
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
        data = {'name': 'Randomfile',
                'data': (StringIO('Content'), 'samename.txt')
                }

        self.api.post('/files', data=data, headers=header, status_code=422)

        # Wrong ID
        data = {'study_doc_id': 42,
                'name': 'Randomfile',
                'data': (StringIO('Content'), 'samename.txt')
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

        data = {'pdf': (StringIO('Not a pdf'), 'file.pdf')}
        self.api.post('/joboffers', data=data, headers=header, status_code=422)

        data = {'logo': (StringIO('Not a jpeg'), 'file.jpg')}
        self.api.post('/joboffers', data=data, headers=header, status_code=422)

        data = {'logo': (StringIO('Not a png'), 'file.png')}
        self.api.post('/joboffers', data=data, headers=header, status_code=422)

        # Upload something that at least wants to be a PDF
        data = {'pdf': (StringIO(r'%PDF 1.5% maybe a pdf..'), 'file.pdf')}
        self.api.post('/joboffers', data=data, headers=header, status_code=201)

        # Create Images as jpeg and png which are allowed
        image = Image.new('RGBA', size=(50, 50), color=(256, 0, 0))
        image_file = StringIO()
        image.save(image_file, 'jpeg')
        image_file.seek(0)

        data = {'logo': (image_file, 'file.jpeg')}
        self.api.post('/joboffers', data=data, headers=header, status_code=201)

        image_file = StringIO()
        image.save(image_file, 'png')
        image_file.seek(0)

        data = {'logo': (image_file, 'file.png')}
        self.api.post('/joboffers', data=data, headers=header, status_code=201)

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
