

from flask import (
    abort,
    request,
    current_app,
    Blueprint
)

from eve.auth import BasicAuth

subscriberlist_blueprint = Blueprint('subscriberlist', __name__)

@subscriberlist_blueprint.route('/subscriberlist', methods=['GET'])
def subscriberlist():
    '''Returns a string with email, firstname and lastname of every subscribed user.'''
    if check_token_authorization(request.authorization):
        db = current_app.data.driver.db['users']
        query = db.find({ 'send_newsletter': True })
        sub_list_string = ''
        for u in query:
            sub_list_string += '%s\t%s %s\n' % (u['email'], u['firstname'], u['lastname'])
        return sub_list_string
    else:
        abort(401, 'Not authorized. Please contact an administrator.')

def check_token_authorization(token):
    '''Checks the provided authorization token against the config file.'''
    if token and token.username and token.password:
        user = current_app.config['SUBSCRIBER_LIST_USERNAME']
        password = current_app.config['SUBSCRIBER_LIST_PASSWORD']
        return token.username == user and token.password == password]
    else:
        return False


def init_subscriberlist(app):
    app.register_blueprint(subscriberlist_blueprint)
