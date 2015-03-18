# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.

import util


class FileEndpointTest(util.WebTest):
    """This will try to access a file with and without authorization
    using the url path

    Registered users should have access to all files,
    not registered users should have no access at all
    """
    def test_registered(self):
        """Test as registered user, should be ok (200)"""
        u = self.new_user()
        s = self.new_studydocument()
        f = self.new_file(study_doc_id=s.id)
        url = self.app.media.get(f.data).content_url

        session = self.new_session(user_id=u.id)  # fake login

        self.api.get(url, token=session.token, status_code=200)

    def test_not_registered(self):
        """Test as unregistered user, credentials are missing, 401 expected"""
        s = self.new_studydocument()
        f = self.new_file(study_doc_id=s.id)
        url = self.app.media.get(f.data).content_url
        self.api.get(url, status_code=401)
