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

Eve is still in early development and changing a lot. That means it might be possible that we can improve our codebase as more features move into Eve's core. We are currently using a patched version of Eve, which is forked on github here: [Eve fork by Leonidaz0r](https://github.com/Leonidaz0r/eve)

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

    pip install -r requirements.py
    pip install -r test-requirements.py

## Configuration

Create a configuration:

    python2 manage.py create_config
    python2 manage.py -c <environment> create_database

In the first step you are prompted which environment you want to setup. Normally you will want to separate a development database and a testing database.

## Running the tests

After setting up a testing database you can run the tests using:

    nosetests

## Debugging server

To play around with the API start a debug server:

    python2 run.py

When the debug server is running it will be available at http://localhost:5000 and show all messages printed using the logger functions, print functions or exceptions thrown.

# Architecture

TODO(Alle): Describe what files we have and where to start

# Authentification

TODO(Conrad): Write details why stuff is like that and how it works

# Files

TODO(Alex): Describe stuff here
