# Using the central login

To use the central login, you must follow the OAuth 2.0 implicit grant flow. This basically means the following:

1. To get a user token you redirect the client's browser to the central login page, ```/oauth/authorize``` of the AMIV API. You need to provide the following query parameters:

* ```response_type```: Must be ```token```.
* ```client_id```: Name of your application (displayed to the user)
* ```redirect_uri```: URL to return the user to after successful login.
* ```state```: A random token you generated. Used to prevent CSRF attacks.

2. After successful login, the client will be redirected to the URL you provided in the ```redirect_uri``` parameter with the following additional query parameters:

* ```access_token```: Your new login token. Provide it in the Authorization header of requests to the AMIV API.
* ```token_type```: Will always be ```bearer```. You can ignore it.
* ```scope```: Will always be ```amiv```. You can ignore it.
* ```state```: The CSRF token you sent in the authorization request. You must check that it is still equal to your provided value to prevent CSRF attacks.


As OAuth is an open standard, it is very likely that there are libraries to automate this workflow in your preferred programming language. These libraries might expect more parameters, which we don't use. If you need to enter a token refresh URL or a ```client_secret```, make sure you are using the implicit grant authorization type. By the standard an authorization request can also supply a requested ```scope```. AMIVAPI will ignore this parameter, if you supply it.

# Whitelisting of OAuth clients

To prevent phishing attacks we use a whitelist of ```client_id``` and ```redirect_uri```. To register a client with the API, a request to the ```oauthclients``` endpoint can be issued, e.g. with the following command:

```curl -X POST -d "client_id=<your client ID>&redirect_uri=<your redirect URI>" -H "Authorization: <admin token>" https://<API URL>/oauthclients
```