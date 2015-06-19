# General

## Used Frameworks

AMIV API uses the [python-eve](http://python-eve.org/) Framework which is a collection of libraries around [Flask](http://flask.pocoo.org/) and [SQLAlchemy](http://www.sqlalchemy.org/).
The best source for information during development is the EVE Source Code at [Eve Github Repository SQL Alchemy Branch](https://github.com/nicolaiarocci/eve/tree/sqlalchemy).

The main links for research about the used technologies are:

 * [Flask](http://flask.pocoo.org/docs/0.10/api/)
 * [SQL Alchemy](http://docs.sqlalchemy.org/en/rel_0_9/)
 * [Flask-SQL Alchemy](https://pythonhosted.org/Flask-SQLAlchemy/)
 * [Werkzeug](http://werkzeug.pocoo.org/)
 * [Eve](http://python-eve.org/)

## Development status

Eve is still in early development and changing a lot. That means it might be possible that we can improve our codebase as more features move into Eve's core. We are currently using a patched version of eve-sqlalchemy and eve-docs, which are forked on github here:

* [eve-sqlalchemy fork by Leonidaz0r](https://github.com/Leonidaz0r/eve-sqlalchemy)
* [eve-docs fork by hermannsblum](https://github.com/hermannsblum/eve-docs)

## Installation

To setup a development environment of the API we recommend using a virtual environment with the pip python package manager. Furthermore you need git.

The following command works on Archlinux based systems, other distributions should provide a similar package:

    sudo pacman -S python2-pip git

After installing pip create a working environment. First create a folder:

    mkdir amivapi
    cd amivapi

Now create a virtualenv which will have the python package inside and activate it:

    virtualenv venv
    . venv/bin/activate

Now get the source:

    git clone https://github.com/amiv-eth/amivapi.git
    cd amivapi

Install requirements:

    pip install --allow-external mysql-connector-python -r requirements.txt

## Configuration

Create a configuration:

    python2 manage.py create_config

The tests will create their own database. If you configure a MySQL Server you will be asked whether the tests should also be run there. If you don't activate that
they will create temporary databases on the fly in temporary files. Note that even if they run on a MySQL server they will create their own database, so you need
to have the permissions for CREATE DATABASE.

## Running the tests

To run the tests you need to install tox:

    pip install tox

Create a config(see above). To run all tests enter

    tox

To test just one environment use -e with py27, py34, pypi or flake8

    tox -e py27

To run only some tests specify them in the following way(substitute your test class):

    tox -- amivapi.tests.forwards


## Debugging server

To play around with the API start a debug server:

    python2 run.py

When the debug server is running it will be available at http://localhost:5000 and show all messages printed using the logger functions, print functions or exceptions thrown.

# Architecture

The main-directory lists following files:

* authentification.py: Everything about who somebody is. Tokens are mapped to sessions and logins are handled. Also author fields are set.
* authorization.py: Everything about what somebody can do. Permissions are implemented here.
* bootstrap.py: The Eve-App gets created here. All blueprints and event-hooks are registered in the bootstrap.
* confirm.py: Blueprint and event-hooks regarding the confirmation of unregistered users.
* cron.py: Jobs run on a regular basis (sending mail about expiring permissions, cleanup)
* documentation.py: Loads additional documentation for the blueptrints.
* forwards.py: Hooks to implement the email-functionality of forwards and assignments to forwards.
* localization.py: Localization of content-fields.
* media.py: File Storage. Handles uploaded files and serves them to the user.
* models.py: The Data-Model. As a basis of the API, in the Data-Model the different Data-Classes and their relations get defined.
* schemas.py: Creates the basic validation-schema out of the data-model and applies custom changes.
* settings.py: Constants which should not be changed by the admin, but can be changed by some developer
* utils.py: General helping functions.
* validation.py: Every validation that extends the basic Cerberus-schema-definition and Hooks for special semantic checks, e.g. whether an end-time comes after a start-time.

For understanding the structure of the api, the data-model in models.py is the Point to start.

# Security

Checking whether a request should be allowed consists of two steps,
authentification and authorization. Authentification is the process of
determining the user which is performing the action. Authorization is the
process of determining which actions should be allowed for the authentificated
user.

Authentification will provide the ID of the authentificated user in
g.logged_in_user

Authorization will provide whether the user has an admin role in
g.resource_admin

Requests which are handled by eve will automatically perform authentification
and authorization. If you implement a custom endpoint you have to call them
yourself. However authorization really depends on what is about to happen,
so you might have to do it yourself. To get an idea of what to do look at
the authorization hooks(pre_xxx_permission_filter()). You can quite certainly
reuse that code somehow.

Perform authentification(will abort the request for anonymous users):

    if app.auth and not app.auth.authorized([], <resource>, request.method):
        return app.auth.authenticate()

Replace <resource> with the respective resource name.


## Authentification

File: authentification.py

The process of authentification is straight forward. A user is identified by
his username and his password. He can sent those to the /sessions resource and
obtain a token which can prove authenticity of subsequent requests.
This login process is done by the process_login function. Sessions do not time
out, but can be deleted.

When a user sends a request with a token eve will create a TokenAuth object
and call its check_auth function. That function will check the token against
the database and set the global variable g.logged_in_user(g is the Flask g
object) to the ID of the owner of the token.

## Authorization

File: authorization.py

A request might be authorized based on different things. These are defined by
the following properties of the model:

    __public_methods__ = [<methods>]
    __registered_methods__ = [<methods>]
    __owner_methods__ = [<methods>]
    __owner__ = [<fields>]

The __xx_methods__ properties define methods which can be accessed. Also a list
of fields can be set, which make somebody an owner of that object if he has the
user ID corresponding to the fields content. For example a ForwardUser object
has the list

    __owner__ = ['user_id', 'forward.owner_id']

This defines the user referenced by the field user_id as well as the user
referenced by owner_id of the corresponding Forward as the owner of this
ForwardUser object.

I recommend to look over the common_authorization() function. The rules created
by it are the following, in that order:

1. If the user has ID 0 allow the request.
2. If the user has a role which allows admin access to the endpoint allow the
    request
3. If the endpoint is public allow the request.
4. If the endpoint is open to registered users allow the request.
5. If the endpoint is open to object owners, perform owner checks(see below)
6. Abort(403)

The function will also set the variable g.resource_admin depending on whether
the user has an admin role(or is root).

One thing to note is that users which are not logged in are already aborted by
eve when authentification fails for resources which are not public, therefore
this is not checked anymore in step 4.

### Roles

Roles can be defined in permission_matrix.py. A role can give a user the right
to perform any action on an endpoint. If permission is granted based on a role
no further filters are applied, hence it is refered to as admin access and
g.resource_admin is set.

### Owner checks

If the authorization check arrives at step 5 and the requested resource has
owner fields, then those will be used to determine the results. This is the
case for example when a registered user without an admin role performs a GET
request on the ForwardUser resource. He can perform that query, however he is
supposed to only see entries which forward to him or where he is the
listowner.

This is solved by two functions. When extracting data we need to create
additional lookup filters. Those are inserted by the
apply_lookup_filters() function which is called by the hooks below it.
When inserting new data or changing data it gets more complicated. First we
need to make sure that the object which is manipulated belongs to the user,
that is achieved using the previously described function. In addition we need
to make sure that the object afterwards still belongs to him. We do not want
people moving EventSignups or ForwardUsers to other users. All this is done in
the will_be_owner() function which is used by the hooks as needed.
However to achieve this the function needs to figure out what would happen if
the request was executed. This is currently done by the resolve_future_field()
function, which tries to resolve relationships using SQLAlchemy meta
attributes for the data which is not yet inserted.
If this checks out ok, the hooks return, if not the request is aborted.

To check ownership inside your own function for an existing object, you can use get_owner(resource, _id) from utils. It will return a list of user-ids who are owners of the item. A common owner check looks like this:

    if g.logged_in_user is in utils.get_owner(<resource>, <_id>):

## API Keys

Instead of a token an API key can be sent. These are generated by manage.py
and are stored in the config file. If an API key is sent, the user ID will be
-1(the anonymous user) and all actions will be authorized based on the
settings for that key in the config.

For implementation see common_authorization() and TokenAuth.check_auth()

# Localization

The api includes support for several languages in four fields which contain
language_dependant content, these are:

- joboffers.title
- joboffers.description
- events.title
- events.desription


The general idea is: for every instance of each field we want an unique ID that
can be used to provide translated content.

This is solved using two new resources:

1. translationmappings
This resource is internal (see schemas.py), which means that it can only
be accessed by eve internally.
To ensure that this works with eve and our modifications (like _author
fields) we are not using SQLAlchemy relationship configurations to create
this field.
Instead the hook "insert_localization_ids" is called whenever events and
joboffers are created. It posts internally to languagemappings to create
the ids which are then added to the data of post.
The relationship in models.py ensures that all entries in the mapping
table are deleted with the event/joboffer

2. translations
This resource contains the actual translated data and works pretty
straightforward:
Given a localization id entries can be added

How is the content added when fetching the resource?

The insert_localized_fields hook check the language relevant fields and
has to query the database to retrieve the language content for the given
localization id.

Then it uses flasks request.accept_languages.best_match() function to get
the best fitting option. (it compares the Accept Language header to the
given languages)

When none is matching it tries to return content in default language as
specified in settings.py (Idea behind this: There will nearly always be
german content). If this it not available, it uses an empty string)

The field (title or description) is then added to the response


## Note: Testing

Both events and joboffers have the exact language fields, but job_offers have
less other required fields.
Therefore testing is done with job_offers - if there are any problems with
language fields in events, ensure that the tests work AND that all language
fields in events are configured EXACLY like in joboffers

## Note: Automatization

Since there are only four language fields (with title and description for both
events and joboffers, which is convenient) all hooks and schema updates are
done manually. Should a update of the api be intended which includes several
more language fields automating this should be considered.

For every language field the following is necessary:

- Internal post to languagemappings to create the id (locatization.py, hook)
- Retrieving the content when fetching the resource (locatization.py, hook)
- Adding a  id (foreignkey) and relationship to translationmappings (models.py)
- Removing id from the schema to prohibit manually setting it (schemas.py)


# Files

For files we wrote our own MediaStorage class as used by Eve by [extending the
template](https://github.com/nicolaiarocci/eve/blob/develop/eve/io/media.py) .
The files need a folder which is created in the process of "create_config".

Maybe in future releases of Eve there will be an official implementation of
file system storage. Maybe it would be useful to use this instead of our
implementation instead in this case.

How Eve uses the MediaStorage Class can be found [here](http://python-eve.org/features.html#file-storage)

To serve the information specified in EXTENDED_MEDIA_INFO the file "media.py"
contains the class "ExtFile" which contains the file as well as the additional
information Eve needs.

As EXTENDED_MEDIA_INFO we use file name, size and a URL to the file.
The URL can be accessed over a custom endpoint specified in "file_endpoint.py",
using flask methods.


# Validation

Luckily the cerberus validator is easily extensible, so we could implement many
custom rules. Those are found in validator.py and are not very complex.

More information on cerberus and its merits can be found in the [Cerberus Documentation](https://cerberus.readthedocs.org/en/latest/)

# Cron

There are some tasks which are done on a regular basis. This includes removing
expired permissions and unused sessions. Users who's permissions expire should
be warned prior to this by mail. This is all done by a cronjob. The cronjob runs
cron.py.
