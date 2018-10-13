"""Custom Validator Class.

Custom validation rules defined here are used in multiple resources.
Validation rules used for single resources only can be found in the respective
resource directory.

Note the following phrase at the end of every validaton function docstring:
`The rule's arguments are validated against this schema:`

Cerberus expects this string followed by a schema in the docstring to
validate the schema itself.
[Read more](http://docs.python-cerberus.org/en/stable/customize.html)
"""

from datetime import datetime
from flask import g, request


class UserValidator(object):
    """Validator subclass adding more validation for usuers."""

    def _validate_session_younger_than(self, threshold_timedelta, field, _):
        """Validate that the session is fresh enough to change this field.

        E.g. the password may only be changed with a recent session.

        Only applies to updates.

        Args:
            threshold_timedelta (timedelta): threshold to compare with
            field (string): field name

        The rule's arguments are validated against this schema:
        {'type': 'timedelta', 'min': 0}
        """
        # When not updating or if there is no session, this validator has
        # nothing to do
        if request.method != 'PATCH' or not g.current_session:
            return

        # timezone is always utc, so we can remove tzinfo safely
        time_created = g.current_session['_created'].replace(tzinfo=None)
        time_now = datetime.utcnow()

        if time_now - time_created > threshold_timedelta:
            self._error(field, "Your session is too old. Using this field "
                        "is not allowed if your session is older than %s."
                        % threshold_timedelta)
