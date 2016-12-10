# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""Tests for auth rules for studydocuments."""

from io import BytesIO

from amivapi.tests.utils import WebTest


# this is the smallest possible zip file
test_file_content = b"\x50\x4b\x05\x06" + b"\x00" * 18


class StudydocsAuthTest(WebTest):
    """Studycos Test class."""

    def test_uploader_added(self):
        """Test that the uploader is correctly added to a document."""
        user = self.new_object('users')
        token = self.get_user_token(user['_id'])

        doc = self.api.post('/studydocuments', token=token,
                            headers={'content-type': 'multipart/form-data'},
                            data={
                                'files': [
                                    (BytesIO(test_file_content), 'test.zip')
                                ]
                            }, status_code=201).json

        self.assertEqual(doc['uploader'], str(user['_id']))

    def test_can_edit_own_doc(self):
        """Test that a user can edit the studydocs he uploaded."""
        user = self.new_object('users')
        token = self.get_user_token(user['_id'])

        doc = self.api.post('/studydocuments', token=token,
                            headers={'content-type': 'multipart/form-data'},
                            data={
                                'files': [
                                    (BytesIO(test_file_content), 'test.zip')
                                ]
                            }, status_code=201).json

        doc = self.api.patch('/studydocuments/%s' % doc['_id'], token=token,
                             headers={'If-Match': doc['_etag']},
                             data={'title': 'new name'}, status_code=200).json

        self.api.delete('/studydocuments/%s' % doc['_id'], token=token,
                        headers={'If-Match': doc['_etag']},
                        status_code=204)

    def test_can_not_edit_others_docs(self):
        """Test that a user can't edit the studydocs other people uploaded."""
        user = self.new_object('users')
        user2 = self.new_object('users')
        token = self.get_user_token(user['_id'])
        token2 = self.get_user_token(user2['_id'])

        doc = self.api.post('/studydocuments', token=token,
                            headers={'content-type': 'multipart/form-data'},
                            data={
                                'files': [
                                    (BytesIO(test_file_content), 'test.zip')
                                ]
                            }, status_code=201).json

        self.api.patch('/studydocuments/%s' % doc['_id'], token=token2,
                       headers={'If-Match': doc['_etag']},
                       data={'title': 'new name'}, status_code=403)

        self.api.delete('/studydocuments/%s' % doc['_id'], token=token2,
                        headers={'If-Match': doc['_etag']},
                        status_code=403)

    def test_can_see_all_docs(self):
        """Test that a user can see all docs."""
        self.load_fixture({
            'studydocuments': [{} for _ in range(5)]
        })
        user = self.new_object('users')
        token = self.get_user_token(user['_id'])

        docs = self.api.get('/studydocuments', token=token, status_code=200)
        self.assertEqual(len(docs.json['_items']), 5)
