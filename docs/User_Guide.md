# General

[TOC]

## About this document

This document should help somebody who wants to develop a client for the AMIV API. It focuses on manipulating data via the public interface. For in depth information see Developer Guide, for reference visit the [API Reference](https://api.amiv.ethz.ch/docs).

## Encryption

The API is only accessible via SSL and will never be made public via an unencrypted channel, as should all your apps.

## Date format, string format

Date and time is always UTC in ISO format with time and without microseconds. Any different time format will result in 400 Bad Request.

    %Y-%m-%DT%H:%M:%SZ
    
All strings are UTF-8.

## About REST

AMIV API is a [REST API](https://de.wikipedia.org/wiki/Representational_State_Transfer). REST is a stateless protocoll modelled after HTTP. The API consists of resources, which have objects. For example the resource /users provides access to the member database. Every resource has the methods GET, POST, PUT, PATCH, DELETE. These are the known regular HTTP methods, GET and POST being the most well known. The API is based on the [python-eve](http://python-eve.org/index.html) framework, so you can refer to eve for detailed information as well.

There are many clients available to use REST and there are libraries for all kind of programming languages. Many HTTP libraries will also be able to communicate with a REST API.

The methods meanings:

Resource methods(use i.e. on /users)
 * GET - Retriving data, query information may be passed in the query string
 * POST - Creating a new entry, the new entry must be provided in the data section

Item methods(use i.e. on /users/4)
 * PATCH - Changing an entry
 * DELETE - Removing an entry
 * PUT - Replacing an entry, this is like DELETE immediately followed by POST. PUT ensures no one else can perform a transaction in between those two queries

## Response format

The status code returned by the API are the standard [HTTP status codes](https://de.wikipedia.org/wiki/HTTP-Statuscode). Codes starting with 2 mean the operation was successfull, starting with 3 are authentification related, 4 are client errors, 5 are server errors, 6 are global errors. Most important codes are:

 * 200 - OK (Generic success)
 * 201 - Created (successful POST)
 * 204 - Deleted (successful DELETE)

 * 400 - Bad request(This means your request has created an exception in the server and the previous state was restored, if you are sure it is not your fault file a bug report)
 * 401 - Please log in
 * 403 - Logged in but not allowed(This is not for you)
 * 404 - No content(This can also mean you could retrive something here, but no object is visible to you because your account is that of a peasant)
 * 422 - Semantic error(Your data does not make sense, e.g. dates in the past which should not be)

 * 500 - Generic server error
 * 501 - Not implemented (Should work after alpha)

All responses by the API are in the [json format](https://de.wikipedia.org/wiki/JavaScript_Object_Notation) by default. Using the Accept header output can be switched to XML, but we encourage to use json as near to no testing has been done for XML output. If you want XML support consider reading the Developer Guide and providing unit tests for XML output.

## HATEOAS

The API is supposed to be human readable, meaning a human can read the responses and only knowing REST standard can perform any action available. That means it is possible to get any information about the structure of the data via the API. Starting at the root node / URL links will be provided to any object.

See: https://en.wikipedia.org/wiki/HATEOAS

## Examples

The examples will provide code in python using the [requests](http://docs.python-requests.org/en/latest/) library. If you are developing a client in the python language requests might be a possible choice to query the API.

### Example: Retriving resources

Request:

    GET /

Code:

    response = requests.get("https://api.amiv.ethz.ch/")

Response:

    status: 200

    {
     "_links": {
      "child": [
       {
        "href": "/files",
        "title": "files"
       },
       {
        "href": "/studydocuments",
        "title": "studydocuments"
       },
       {
        "href": "/forwardusers",
        "title": "forwardusers"
       },
       {
        "href": "/forwards",
        "title": "forwards"
       },
       {
        "href": "/sessions",
        "title": "sessions"
       },
       {
        "href": "/joboffers",
        "title": "joboffers"
       },
       {
        "href": "/eventsignups",
        "title": "eventsignups"
       },
       {
        "href": "/forwardaddresses",
        "title": "forwardaddresses"
       },
       {
        "href": "/users",
        "title": "users"
       },
       {
        "href": "/events",
        "title": "events"
       },
       {
        "href": "/permissions",
        "title": "permissions"
       }
      ]
     }
    }


# Authentification

Most access to the API is restricted. To perform queries you have to log in and acquire a login token. The login token is a unique string identifying you during a session. Sessions are a part of the data model as any other object and can be created in the normal way. Just send a POST request to the /sessions resource:

## Example: Login

Request:

    POST /sessions?username=myuser&password=mypassword

Code:

    response = requests.post("https://api.amiv.ethz.ch/sessions", data={"username": "myuser", "password": "mypassword"})

Response:

    status = 201

    {
        u'_author': -1,
        u'_created': u'2014-12-20T11:50:06Z',
        u'_etag': u'088401622fc10cbf0d549e9282072c37829a1b81',
        u'_id': 4,
        u'_links': {u'self': {u'href': u'/sessions/4', u'title': u'Session'}},
        u'_status': u'OK',
        u'_updated': u'2014-12-20T11:50:06Z',
        u'id': 4,
        u'token': u'eyJzaWduYXR1cmUiOiAiSFlKVGhIeUVvSHNSL203M0I1RlBTckdUQlFyOUJ4QzlUMHhsZmNZY1dWQlBpQnZ6T2dvM1NXY2RSU3NiVTJhRFRpQzQ4N2VlcVFxcjN4d094YStZM1o2Zi85cnV6d1RKVHVDL1pqcnlKaXZ4cDc4RzlaejdGb1BvZ0VhTXk5Zy9DdW9LL25vb3BNYVRnd2hmUW1RZDRPV1dMV1ZDZVZkM0dYb0VKQWJZR3NEZ2F3V0Q5dlRhanVIcEhUQUYwS1FOSlp0V3prcU9ldW5nb1pseHdqUXhxdXJhK2hjaEdTNmFsWC9NT3NiWVh1d2R3TXFXaVFaMys0dTdVdHBrSmZiY04vcmJ6MS9ldWF6NFJlRCtMandoWDBMTTAvOXdLamlFNW9BbFlrajkxQW9LYnJtY0R2Q0gxcGlJaWtlRHVxL2NiZHhTT1Uvck5jOC9GR29JejRPMG13PT0iLCAidXNlcl9pZCI6IDAsICJsb2dpbl90aW1lIjogIjIwMTQtMTItMjBUMTI6NTA6MDZaIn0=',
        u'user_id': 4
    }

We will look at the details of this response later. First we only notice the token field and use that token to issue an authenticated query to find out something about our user account. A token can be passed as the HTTP Basic Auth username with an empty password. The python requests library provides this functionality as does command line curl. If you can not pass such a field you can create the Authorization header which would be generated by that parameter yourself. For that you need to base64 encode the token followed by a colon. We will see examples for both methods.


## Example: Retriving user

It is possible to retrive a user using its username. Normally we would use an ID to retrive an item, but in this case it is easier this way.

Request:

    POST /sessions "username=myuser&password=mypassword"
    GET /users/myuser (+Authorization header)

Code with good REST library:

    login = requests.post("http://api.amiv.ethz.ch/sessions", data={"username": "myuser", "password": "mypassword"})
    token = login.json()['token']
    response = requests.get("https://api.amiv.ethz.ch/users/myuser", auth=requests.auth.HTTPBasicAuth(token, ""))

Code with bad REST library:

    login = requests.post("/sessions", data={"username": "myuser", "password": "mypassword"})
    token = login.json()['token']
    auth_header = b64encode(token + ":")
    response = requests.get("/users/myuser", headers={"Authorization": auth_header})

Response:

    {
        '_author': 0,
        '_created': '2014-12-18T23:29:07Z',
        '_etag': '290234023482903482034982039482034',
        '_links': {
            'parent': {
                'href': '/', 'title': 'home'
            },
            'self': {
                'href': '/users',
                'title': 'users'
            }
        },
        '_updated': '2014-12-18T23:29:07Z',
        'birthday': None,
        'department': None,
        'email': 'kimjong@whitehouse.gov',
        'firstname': 'Edward',
        'gender': 'male',
        'groups': None,
        'id': 4,
        'lastname': 'Nigma',
        'ldapAddress': None,
        'legi': None,
        'membership': 'none',
        'nethz': None,
        'phone': None,
        'rfid': None,
        'username': 'myuser'
    }


# Using GET

GET queries can be customized in many ways. There is the possibility for where, projection, embedding and pagination clauses.

## where clauses

Using a where clause one can specify details about the object looked for. Queries can be stated in either the python syntax or as a Mongo DB Query document(Both are some kind of experimential at the moment, feel free to experiment and improve. If you want to help, have a look at the sqlalchemy branch of the python-eve project).

TODO: Test these, if they work remove this notice, maybe add more examples or links to external documentation

An example for the python syntax(url-encoded) is:

    GET /events?where=title=="Testevent"+and+spots>5

An example for Mongo DB Query Documents is:

    GET /events?where={"title":"Testevent","spots":{"$gt":5}}

A more complex query would be

    GET /studydocuments?where={"$or":[{"name":"Zsfg","lecture":"Regelsysteme"},{"title":"Regelsysteme_Zsfg"}]}

Available Mongo DB Query Document operators are: $or, $and, $gt, $gte, $lt, $lte
Embedding works only for equal and no recursion at the moment(to improve, again commit to the python-eve project), for example:

    GET /studydocuments?where={"files.name": "Regelsysteme_Zsfg.pdf"}

## Projections

Using the projection parameter it is possible to decide which fields should be returned. For example:

    GET /events?projection={"location":0,"signups":1}

This will turn of the location field, but return a list of signups. The behaviour of data relations when their projection is enabled can be configured using embedding.

## Embedding

Turning embedding on and off will determine how relations are returned by the API. With embedding turned on the whole object will be returned, with embedding turned off only the ID will be returned.

    GET /users?projection={"permissions":1}&embedding={"permissions":1}

This will return all the permission objects embedded in the response

## Sorting

Results can be sorted using the *sort* query parameter. Prepending the name with a - will sort in descending order.

    GET /events?sort=-start_time

This will return the events sorted by descending start_time.

## Pagination

The number of returned results for queries to resource endpoints can be controlled using the max_results and the page parameter.

    GET /events?max_results=10&page=3

This will return the third page of 10 items.


# PUT, PATCH, DELETE queries

## If-Match

To manipulate an existing object you have to supply the If-Match header to prevent race conditions.
When you use GET on an element you will be provided with an _etag field. The etag is a string which changes whenever the object is manipulated somehow. When issuing a PUT, PATCH or DELETE query you must supply the etag in the If-Match header to ensure that no one else changed the object in between.

### Example: Use PATCH to change a password

    GET /users/myuser (+Authorization header)
    PATCH /users/myuser data: "password=newpw" headers: "If-Match: a23...12b"

Code:

    me = requests.get("/users/myuser", auth=myauth)
    etag = me.json()['_etag']
    result = requests.patch("/users/myuser", data={"password":"newpw"}, headers={"If-Match":etag})

The response will be the changed user object. 


# Working with files

TODO(Alex)
