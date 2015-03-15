# General

[TOC]

## About this document

This document should help somebody who wants to develop a client for the AMIV API. It focuses on manipulating data via the public interface. For in depth information see Developer Guide, for reference visit the [API Reference](https://<base_url>/docs).

## Portability

The API is designed and all clients should be designed to be useable outside of AMIV. Although we will use api.amiv.ethz.ch as the base URL in this document this is not necessary and a client should provide a config entry for that.

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

 * 400 - Bad request (This means your request has created an exception in the server and the previous state was restored, if you are sure it is not your fault file a bug report)
 * 401 - Please log in
 * 403 - Logged in but not allowed (This is not for you)
 * 404 - No content (This can also mean you could retrive something here, but no object is visible to you because your account is that of a peasant)
 * 422 - Semantic error (Your data does not make sense, e.g. dates in the past which should not be)

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

# API keys

If access is not done by a user but rather by a service(cron, vending machine, info screen), user based authorization does not work. Instead an API key can be used. The API administrator can generate keys using the manage.py script and configure which endpoints can be accessed. Endpoint access via API key will give admin priviledges. The API key can be sent in the same way as a token. You can think of it as a permanent admin session for specific endpoints.

# Using GET

GET queries can be customized in many ways. There is the possibility for where, projection, embedding and pagination clauses.

## where clauses

Using a where clause one can specify details about the object looked for. Queries can be stated in the python syntax(as if you would write an if clause). This is some kind of experimental, if any issues occur please contact api@amiv.ethz.ch or write a report in the issue tracker on github.

An example (url-encoded) is:

    GET /events?where=title=="Testevent"+and+spots>5

A more complex query would be

    GET /events?where=(title=="Testevent"+and+spots>5)+or+title=="Testevent2"

Embedding works only for equality comparison and no recursion at the moment(to improve, commit to the eve-sqlalchemy project), for example:

    GET /events?where=signups.user_id==5

This would return all events which the user with the id 5 is signed up for.

## Projections

Using the projection parameter it is possible to decide which fields should be returned. For example:

    GET /events?projection={"location":0,"signups":1}

This will turn of the location field, but return a list of signups. The behaviour of data relations when their projection is enabled can be configured using embedding.

## Embedding

Turning embedding on and off will determine how relations are returned by the API. With embedding turned on the whole object will be returned, with embedding turned off only the ID will be returned.

    GET /users?projection={"permissions":1}&embedded={"permissions":1}

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

# Localization: Content in different languages

The api supports descriptions and titles for events and job offers in different
languages.

If you post to one of those ressources, the response will contain a title_id
and description_id. Those are the unique identifiers.

To add content in various languages you can now use this id to post to the
/translations resource

Example: Create an event with the requests library

Code:

    import json  # To properly encode event data

    """Usual login"""
    auth = {'username': user, 'password': pw}
    r = requests.post('http://localhost:5000/sessions', data=auth)
    token = r.json().get('token')
    session = requests.Session()
    session.auth = (token, '')

    """Some data without language relevant content"""
    data = {'time_start': '2045-01-12T12:00:00Z',
            'time_end': '2045-01-12T13:00:00Z',
            'time_register_start': '2045-01-11T12:00:00Z',
            'time_register_end': '2045-01-11T13:00:00Z',
            'location': 'AMIV Aufenthaltsraum',
            'spots': 20,
            'is_public': True}

    payload = json.dumps(data)

    self.session.headers['Content-Type'] = 'application/json'
    response = self.session.post('http://localhost:5000/events',
                                 data=payload).json()
    del(self.session.headers['Content-Type']) # Header not needed anymore

Response:

    {u'_author': 0,
     u'_created': u'2015-03-05T14:12:19Z',
     u'_etag': u'8a20c7c3e035eb5a03906ce8f0f7717a4300e9de',
     u'_id': 1,
     u'_links': {u'self': {u'href': u'/events/1', u'title': u'Event'}},
     u'_status': u'OK',
     u'_updated': u'2015-03-05T14:12:19Z',
     u'description_id': 2,
     u'id': 1,
     u'is_public': True,
     u'location': u'AMIV Aufenthaltsraum',
     u'spots': 20,
     u'time_end': u'2045-01-12T13:00:00Z',
     u'time_register_end': u'2045-01-11T13:00:00Z',
     u'time_register_start': u'2045-01-11T12:00:00Z',
     u'time_start': u'2045-01-12T12:00:00Z',
     u'title_id': 1}

Now extract ids to post translations

Code:

    """Now add some titles"""
    self.session.post('http://localhost:5000/translations',
                      data={'localization_id': r['title_id'],
                            'language': 'de',
                            'content': 'Irgendein Event'})
    self.session.post('http://localhost:5000/translations',
                      data={'localization_id': r['title_id'],
                            'language': 'en',
                            'content': 'A random Event'})

    """And description"""
    self.session.post('http://localhost:5000/translations',
                      data={'localization_id': r['description_id'],
                            'language': 'de',
                            'content': 'Hier passiert was. Komm vorbei!'})
    self.session.post('http://localhost:5000/translations',
                      data={'localization_id': r['description_id'],
                            'language': 'en',
                            'content': 'Something is happening. Join us!'})

If we now specify the 'Accept-Language' Header, we get the correct content!

Code:

    self.session.headers['Accept-Language'] = 'en'

    self.session.get('http://localhost:5000/events/%i' % response['id']).json()

Response:

    {u'_author': 0,
     u'_created': u'2015-03-05T14:12:19Z',
     u'_etag': u'8a20c7c3e035eb5a03906ce8f0f7717a4300e9de',
     u'_links': {u'collection': {u'href': u'/events', u'title': u'events'},
                 u'parent': {u'href': u'/', u'title': u'home'},
                 u'self': {u'href': u'/events/1', u'title': u'Event'}},
     u'_updated': u'2015-03-05T14:12:19Z',
     u'additional_fields': None,
     u'description': u'Something is happening. Join us!',
     u'description_id': 2,
     u'id': 1,
     u'img_1920_1080': None,
     u'img_thumbnail': None,
     u'img_web': None,
     u'is_public': True,
     u'location': u'AMIV Aufenthaltsraum',
     u'price': None,
     u'signups': [],
     u'spots': 20,
     u'time_end': u'2045-01-12T13:00:00Z',
     u'time_register_end': u'2045-01-11T13:00:00Z',
     u'time_register_start': u'2045-01-11T12:00:00Z',
     u'time_start': u'2045-01-12T12:00:00Z',
     u'title': u'A random Event',
     u'title_id': 1}

Yay! The title and description are added in english as requested.

# Working with files

Working with files is not much different from other resources. Most resources
contain the file, only study documents, which will be explained below.

##Files in Events, Joboffers, etc.

Files can be uploaded using the "multipart/form-data" type. This is supported
by most REST clients. Example using python library "requests" and a job offer:
(More info on requests here: http://docs.python-requests.org/en/latest/)

Code:

    """Usual login"""
    auth = {'username': user, 'password': pw}
    r = requests.post('http://localhost:5000/sessions', data=auth)
    token = r.json().get('token')
    session = requests.Session()
    session.auth = (token, '')

    """Now uploading the file"""
    with open('somefile.pdf', 'rb') as file:
        data = {'title': 'Some Offer'}
        files = {'pdf': file}
        session.post('http://localhost:5000/joboffers',
                     data=data, files=files)

Response:

    {'_author': 0,
     '_created': '2015-02-19T14:46:14Z',
     '_etag': '9cd7fdf37507d2001f5902330ff38db1236bdb84',
     '_id': 1,
     '_links': {'self': {'href': '/joboffers/1', 'title': 'Joboffer'}},
     '_status': 'OK',
     '_updated': '2015-02-19T14:46:14Z',
     'id': 1,
     'pdf': {'content_url': '/storage/somefile.jpg',
             'file': None,
             'filename': 'somefile.jpg',
             'size': 55069},
     'title': 'Some Offer'}

Note that 'file' in the response is None since returning as Base64 string is
deactivated.

##Working with study documents

Study documents are a collection of files. Using them is simple:

1. Create a study document (POST to /studydocuments)
2. Save ID of the newly created document
3. Upload files to the '/files' resource as described above, using the ID

#Unregistered users

Next to GET operations on public data, AMIV API currently allows unregistered users in exactly two cases: Signing up for a public event or managing email-subscribtions for public email lists. In Both cases, 'is_public' of the event or forward must be True.

Basically, an unregistered user can perform any GET, POST, PATCH or DELETE action on the supported resource within the usual rights. However, as the HTTP request comes without login, you need to confirm yourself and your email-address with a special token.  
After the creation of a new item with POST, the User will get an email with the Token. Your Admin might provide links in this mail to a user-friendly tool. However, here is the Workflow that always works:  
Just POST the token send to you to '/confirmations' in the following way:

    POST /confirmations?token=dagrfvcihk34t8xa2dasfd

After this, the server knows that the given email-address is valid.  
Every further Action kann be performed as usually, but with a special Header:

    {
        'Token': dagrfvcihk34t8xa2dasfd
    }

##Public Events
To subscribe to a public event with an email-address you simply post to "/eventsignups":

Data:

    {
        'event_id': 17,
        'user_id': -1,
        'email': "mymail@myprovider.ch",
    }

You will receive a 202 Acepted. This means that the signup is not valid yet, but the server has received valid data and the user can confirm the signup by clicking on a link in an email.
The User-ID '-1' stands for the anonymous user.

##Email Forwards
For email-lists, we know 3 resources: '/forwards', '/forwardusers', '/forwardaddresses'. '/forwards' is used to manage lists. '/forwardusers' is used to manage entries which forward to a registered user. '/forwardaddresses' is used for anonymous entries. To create a new subscription or change an existing one for an unregistered user, you need to use '/forwardaddresses'. The procedure of confirmation is exactly the same as for events.

# Common Problems

## PATCH, PUT or DELETE returns 403

It is only possible to issue these methods on objects, not on resources.
This will not work:

    DELETE /users?where=id==3

Use this instead:

    DELETE /users/3

Make sure you provided the required If-Match header. If that does not help
make sure you can use GET on the item. If you are unable to request a GET
then your account can not access the object.
If you are able to GET the object, then your provided data is invalid. If
you do not have admin priviledges for the endpoint(method on that resource)
make sure your request will conserve your ownership of the object.

## How can I send boolean etc to the server using python requests?

To properly encode Integer, Boolean and such you need to properly format the
data to json before sending, like this:

Code:

    import json

    data_raw = {'spots': 42,
                'is_public:' True}

    payload = json.dumps(data_raw)

The payload is now ready for sending! (Be sure to set the 'Content-Type' header to 'application/json')
