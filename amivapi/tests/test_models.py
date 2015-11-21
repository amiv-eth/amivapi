# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.


from sqlalchemy.ext.declarative import DeclarativeMeta

from amivapi.tests import util
from amivapi import models


class ModelValidationTest(util.WebTestNoAuth):
    """ Check whether the data model is correct and has valid meta fields """

    def test_owners(self):
        """ Test whether all owner fields exist and are ForeignKeys to
        user ids """

        # Loop over all models
        for model in models.Base._decl_class_registry.values():
            # Skip Base class
            if not isinstance(model, DeclarativeMeta):
                continue

            for owner in model.__owner__:
                print("Testing owner field %s of %s" % (owner, str(model)))

                # Start with model and resolve next class for every part of
                # owner field
                cls = model
                path = owner.split('.')  # emoticons everywhere
                for field in path[:-1]:
                    try:
                        # Find target class of the relationship and use next
                        cls = getattr(cls, field).property.mapper.class_
                    except AttributeError:
                        raise AttributeError("Field %s in __owner__ attribute "
                                             "%s of class %s does not exist!"
                                             % (field, owner, str(model)))

                # If we are at User and the field is id we are done
                if cls == models.User and path[-1] == 'id':
                    continue

                # The field can also be a foreign key to User.id, so check that
                # now

                # Search for foreign key to User.id of field named path[-1]
                try:
                    fks = cls.__table__.columns[path[-1]].foreign_keys
                except KeyError:
                    raise AttributeError("Field %s in __owner__ attribute "
                                         "%s of class %s does not exist!"
                                         % (path[-1], owner, str(model)))
                print("Has foreign keys: %s" % str(fks))

                foundUserIdFk = False
                for foreign_key in fks:
                    if foreign_key.target_fullname == 'users.id':
                        foundUserIdFk = True
                        break

                self.assertTrue(foundUserIdFk,
                                "Owner field %s of %s is not a foreign key of "
                                "User.id" % (owner, str(model)))
