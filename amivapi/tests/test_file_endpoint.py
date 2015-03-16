# -*- coding: utf-8 -*-
#
# AMIVAPI test_file_endpoint.py
# Copyright (C) 2015 AMIV an der ETH, see AUTHORS for more details
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

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
