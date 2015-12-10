# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.

from itertools import count

from amivapi.tests import util

from jsonschema import Draft4Validator


class GroupPermissionTest(util.WebTest):
    def test_validator_schema(self):
        """
        Test to verify that the validator correctly aborts
        if the jsonschema is not valid
        """

        # Will raise an exception if the schema is broken
        Draft4Validator.check_schema(
            self.app.config['GROUP_PERMISSIONS_JSONSCHEMA']
        )

    def test_validator_input(self):
        """
        Test to verify that inputs are validated correctly
        """
        token = self.new_session(user_id=0).token  # root login

        gen = count()

        # Helper function to post group
        def p_post(permissions, status):
            self.api.post("/groups", data={
                "name": "Testgroup%i" % gen.next(),
                "permissions": permissions,
                "moderator_id": 0,
                "allow_self_enrollment": False,
                "has_zoidberg_share": False
            }, token=token, status_code=status)

        # Empty is ok
        p_post({}, 201)
        # None is ok
        p_post(None, 201)
        # resources with no methods ok
        p_post({"users": {}}, 201)
        # More resources
        p_post({
            "users": {
                "POST": True,
                "DELETE": False},
            "events": {
                "GET": True}
        }, 201)

        # Wrong resource
        p_post({
            "users": {},
            "Idontexist": {}
        }, 422)

        # Wrong method
        p_post({
            "users": {
               "POST": True,
               "SUPERWRONG": False}
        }, 422)

        # All possible eve endpoints
        all = {}
        methods = ["GET", "PATCH", "PUT", "POST", "DELETE"]

        for endpoint in self.app.config["DOMAIN"]:
            all[endpoint] = {
                method: True for method in methods
            }

        p_post(all, 201)

    def test_permissions(self):
        # Create 3 groups
        g1 = self.new_group(permissions={"events": {"POST": True}}).id
        g2 = self.new_group(
            permissions={"groups": {"PATCH": True, "DELETE": False}}).id
        g3 = self.new_group()

        # And a user
        u = self.new_user().id
        # Get a session for the user
        token = self.new_session(user_id=u).token

        # Try to create an event and patch a user
        # No authorization
        h = {"If-Match": g3._etag}
        self.api.post("/events", data={"spots": -1,
                                       "allow_email_signup": False},
                      token=token, status_code=403)
        self.api.patch("/groups/%i" % g3.id, data={"name": "newname"},
                       headers=h, token=token, status_code=403)

        # User is member of g1 and g2 -> no owner permissions for g3
        self.new_group_member(user_id=u, group_id=g1)
        self.new_group_member(user_id=u, group_id=g2)

        # Try again
        # Authorized this time
        self.api.post("/events", data={
                      "spots": -1,
                      "allow_email_signup": False
                      }, token=token, status_code=201)
        self.api.patch("/groups/%i" % g3.id, data={
                       "name": "newname"
                       }, headers=h,
                       token=token, status_code=200)
