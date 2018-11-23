# OAuth

The API implements the
[OAuth 2.0 Implicit Grant Flow](https://oauth.net/2/grant-types/implicit/)
to allow web-services to use the API for authorization.

This means that the API provides a central login page that other services
can use instead of implementing their own.

The process works like this:

1. Redirect the user from your web service to the `/oauth` endpoint
2. (The user logs in with the API)
3. The user is redirected back to your web-service with an API token

```
                  1. REDIRECT to API
+-------------+                            +-----------+
|             +---------------------------->           |
| web-service |                            | API OAuth | 2. Login
|             <----------------------------+           |
+-------------+                            +-----------+
                  3. REDIRECT to service
```

For increased security, web-services must be whitelisted to use OAuth.


## Using OAuth

To use the central login, you must follow the OAuth 2.0 implicit grant flow. This basically means the following:

1. To get a user token you redirect the client's browser to the central login page, `/oauth` of the AMIV API. You need to provide the following query parameters with the redirect:

   - ```response_type```: Must be set to ```token```.
   - ```client_id```: Name of your application (displayed to the user)
   - ```redirect_uri```: URL to return the user to after successful login.
   - ```state```: A random token you generated. Used to prevent CSRF attacks.

2. On the OAuth page, the user will be prompted to log in.

3. After successful login, the client will be redirected to the URL you provided in the ```redirect_uri``` parameter with the following additional query parameters:

   - ```access_token```: Your new login token. Provide it in the Authorization header of requests to the AMIV API.
   - ```token_type```: Will always be ```bearer```. You can ignore it.
   - ```scope```: Will always be ```amiv```. You can ignore it.
   - ```state```: The CSRF token you sent in the authorization request. You must check that it is still equal to your provided value to prevent CSRF attacks.

As OAuth is an open standard, it is very likely that there are libraries to automate this workflow in your preferred programming language. These libraries might expect more parameters, which we don't use. If you need to enter a token refresh URL or a ```client_secret```, make sure you are using the *implicit grant* authorization type. By the standard, an authorization request can also supply a requested ```scope```. AMIVAPI will ignore this parameter if you supply it.

The ```redirect_uri``` must be an **HTTPS** URL and must not contain a fragment
(nothing after ```#```).

## Whitelisting of OAuth clients

To prevent phishing attacks we use a whitelist of ```client_id``` and
```redirect_uri```. To register a client with the API, a request to the
```/oauthclients``` endpoint can be issued. Check out the
[resource documentation below](#tag/Oauthclient) for more info.
