# Authentication and Authorization

Most resources are not public and require you to *authenticate* yourself
using an `Authorization` header. If the header is provided, the API will
verify that you are *authorized* to execute the requested operation.

## Authentication

First of all, you must aquire a token which is used by the API to identify
which [user](#tag/User) you are.
Providing the token is possible in two ways:

1. The API supports a high-level interface based on
   [OAuth 2 Implicit Grants](https://oauth.net/2/grant-types/implicit/),
   intended for web applications authorizing over the API.

   > Take a look at the API [OAuth Guide below](#section/OAuth) to learn how
   > to use it.

2. Aside from that, the `/sessions` resource provides a low-level interface
   to all active user sessions for scripting and management.

   > Take a look at the [Sessions resource below](#tag/Session) for more info.


After you have acquired a token, you must send it with all your requests
in the `Authorization` header. The API supports multiple ways of
providing a token:

```
Authorization: <token>

Authorization: <keyword> <token>
```

Where `<keyword>` can be anything, e.g. `Token`, `Bearer`, etc.

Furthermore, you can also use
[HTTP basic auth](https://en.wikipedia.org/wiki/Basic_access_authentication)
with the token as username and an empty password.

## Authorization

The API handles permissions on a *per resource* basis.
There are two fundamental permissions:

| Permission  | Allowed Methods                             |
|-------------|---------------------------------------------|
| `read`      | `GET`, `OPTIONS`                            |
| `readwrite` | `GET`, `OPTIONS`, `POST`, `PATCH`, `DELETE` |

> **Not all resources support every method**
> 
> Have a look at the respective resource sections for detailed information

### Permissions are granted by groups

Groups can grant permissions to all their members. Concretely,
groups contain a `permissions` field, which maps resources to
the permissions the group grants (if any).

> Have a look at the [group section](#tag/Group) for more information. 

After you have been authenticated, the API checks the permissions
of all the groups you are a member of, to determine whether you are
*authorized*.

### Admins and Users

If one of your groups grants you permissions for a resource and method, you
are considered an **admin** for this resource and method.

If you are athenticated, but not an admin, you are considered a **user**.

### Item and field level permissions

While the API in general handles permissions per resource, some resources
implement further restrictions on a *per item* or *per field* basis, e.g. you
can change only your own password, not that of other users; or you can
change the details of an event signup, but you may not replace your user with
someone else.

> Have a look at the respective resource sections for detailed information
