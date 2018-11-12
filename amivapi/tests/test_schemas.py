# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""General checks for all schemas."""
from amivapi.tests.utils import WebTest


class SchemaTest(WebTest):
    """Test for all resource schemas."""

    def test_required_xor_default(self):
        """Fields must be either required xor have a default value.

        Per default, this is not necessary, as fields can simply be
        'missing'. However, this can cause confusion and problems:
        Using PATCH, fields *cannot* be removed. As a result, missing
        fields can result in unreachable state as soon as item is created.

        To avoid headaches, we simply enforce that this undefined state is
        impossible. Either a field must be required (cannot be missing) or must
        have a sensible default value, to which it can be reset using PATCH.

        Furthermore, if a field has a default value, it is unnecessary to
        mark it as required and vice versa.
        """
        no_required_or_default = []
        required_and_default = []
        for resource, domain in self.app.config['DOMAIN'].items():
            for field, definition in domain['schema'].items():
                if definition.get('readonly'):
                    continue

                if (('required' not in definition) and
                        ('default' not in definition)):
                    no_required_or_default.append((resource, field))

                if ('required' in definition) and ('default' in definition):
                    required_and_default.append((resource, field))

        self.assertEqual(no_required_or_default, [])
        self.assertEqual(required_and_default, [])
