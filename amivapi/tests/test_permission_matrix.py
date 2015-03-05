from amivapi.tests import util


class PermissionMatrixTest(util.WebTest):

    def test_vorstand_role(self):
        user = self.new_user()
        self.new_permission(user_id=user.id, role="vorstand")
        token = self.new_session(user_id=user.id).token

        self.api.get("/joboffers", token=token, status_code=200)

        data = {
            "company": "Conrad AG"
        }
        of = self.api.post("/joboffers", token=token, data=data,
                           status_code=201).json

        of = self.api.patch("/joboffers/%i" % of['id'],
                            headers={"If-Match": of['_etag']},
                            token=token,
                            data=data,
                            status_code=200).json

        of = self.api.put("/joboffers/%i" % of['id'],
                          headers={"If-Match": of['_etag']},
                          token=token,
                          data=data,
                          status_code=200).json

        self.api.delete("/joboffers/%i" % of['id'],
                        headers={"If-Match": of['_etag']},
                        token=token,
                        status_code=204)

    def test_event_admin_role(self):
        user = self.new_user()
        self.new_permission(user_id=user.id, role="event_admin")
        token = self.new_session(user_id=user.id).token

        self.api.get("/joboffers", token=token, status_code=200)

        data = {
            "title": "no"
        }
        self.api.post("/joboffers", token=token, data=data,
                      status_code=403)

        of = self.new_joboffer()

        self.api.patch("/joboffers/%i" % of.id,
                       token=token,
                       headers={"If-Match": of._etag},
                       data=data,
                       status_code=403)

        self.api.put("/joboffers/%i" % of.id,
                     token=token,
                     headers={"If-Match": of._etag},
                     data=data,
                     status_code=403)

        self.api.delete("/joboffers/%i" % of.id,
                        token=token,
                        headers={"If-Match": of._etag},
                        status_code=403)
