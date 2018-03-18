"""Utility functions to check function arguments."""

from flask import abort, current_app


def check_true(s, user_errmsg):
    """Check that the argument is a nonempty string."""
    if not s:
        current_app.logger.info("Check failed: %s is not True!" % s)
        abort(400, user_errmsg)


def check_str_nonempty(s, user_errmsg):
    """Check that the argument is a nonempty string."""
    if not isinstance(s, str):
        current_app.logger.info("Check failed: %s is not a str!" % s)
        abort(400, user_errmsg)
    check_true(s, user_errmsg)
