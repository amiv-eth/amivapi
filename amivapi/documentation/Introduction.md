
# REST Introduction

A [REST](https://en.wikipedia.org/wiki/Representational_state_transfer) API
is a certain type of web service, following a set of design principles for
the structure of, and interaction with data.


## Data structure

In the API, data is grouped by resources, such as *Users*, which consist of 
items, e.g. a *User*, which are identified by unique ids.
Every resource and item is reachable by an endpoint,
e.g. `/users` for *Users* and `/users/<id>` for a *User* with a given id.


## Interaction with data

Interacting with data follows the *Create, Read, Update, Delete*
([CRUD](https://en.wikipedia.org/wiki/Representational_state_transfer))
principle, where each operation corresponds to
[HTTP methods](https://en.wikipedia.org/wiki/Hypertext_Transfer_Protocol#Request_methods).

Concretely, this API supports the following methods:

| Operation  | Method          | Endpoint |Description |
|------------|-----------------|--|--|
| **Create** | `POST`          | Resource |Create a new item for a resource. |
| **Read**   | `GET`,`OPTIONS` | Resource, Item | Read all items of a resource, or a specific item. `OPTIONS` works like `GET`, but only returns headers. <blockquote>Additional filtering is supported, have a look at the [Cheatsheet](#section/Cheatsheet) for more info.</blockquote> |
| **Update** | `PATCH`         | Item | Modify an item.|
| **Delete** |  `DELETE`       | Item | Delete an item.|


## Security

Most resources are not public, but require authentication & authorization.
The API uses tokens for both, which need to be provided with the
`Authorization` header:

```
Authorization: <token>
```

How to aquire a token and how permissions work is explained in the
[Authentication and Authorization](#section/Authentication-and-Authorization)
section below.
