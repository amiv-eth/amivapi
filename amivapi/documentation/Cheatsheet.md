# Cheatsheet

This cheatsheet show you how you can control the data fetched from the API
using `GET` requests with filtering, sorting, etc. and how to send different
kinds of data to the API, e.g. arrays, objects and files.

## Fetching Data

The API is based on the framework [Eve](http://docs.python-eve.org/en/latest/),
which supports a wide range of filtering, sorting, embedding and pagination
using the request [query string](https://en.wikipedia.org/wiki/Query_string).
Below is a short overview over the most important operations. Check out
the [Eve documentation](http://docs.python-eve.org/en/latest/features.html) for
further details.

In any case, data is returned in [JSON](https://www.json.org) format,
which is automatically parsed by JavaScript and supported by virtually all
other programming languages.

### Filtering

```
/events?where={"title_en":"Party"}

/events?where={"$time_start":{"$gt":"2018-06-06T10:00:00Z"}}

/events?where={"$or":{"title_en":"Party","title_de":"Feier"}}

/events?where={"img_infoscreen":{"$exists":true}}
```

Supported operators include:
`$gt` (>), `$gte` (>=), `$lt` (<), `$lte` (<=), `$ne` (!=), `$and`, `$or`,
`$in`, `$exists`

> **The time format is `YYYY-MM-DDThh:mm:ssZ`**
>
> **Y**ear, **M**onth, **D**ay, **h**our, **m**inutes, **s**econds, `T` is a
> required separator and `Z` indicates UTC (other timezones are not supported)


### Sorting

```
/events?sort=time_start,-time_end
```

The prefix `-` inverts the sorting order.


### Pagination

There is a global maximum on the results per request, so getting all results in
one request may not be possible. Each portion of results is called a *page*,
and you can specify the number of results per page and page number:

```
/events?max_results=20&page=2
```


### Embedding

By default, other resources are only included by `_id`. With *embedding*, you
can include complete objects.

```
/groupmemberships?embedded={"user":1,"group":1}
```

### Projections

Hide fields or show hidden fields. Some fields like passwords can't be shown.

```
/groupmemberships?projection={"group":0}
```

## Sending Data

Data can be sent in JSON format or using
[multipart/form-data](https://tools.ietf.org/html/rfc2388).

### JSON

Primarily, data is sent to the API in JSON format. This allows sending
arrays and objects in fields without problems.

Concretely, a request is sent with the header
`Content-Type: application/json` and a JSON string as body.

In most languages, sending JSON is very easy, e.g. in Javascript the
[axios library](https://github.com/axios/axios) sends JSON by default and
in python, the [requests package](http://docs.python-requests.org) can
send dictionaries as JSON directly, too.
Other languages may have similar libraries available.

However, there is one caveat: With JSON, it is not possible to send files.
For this reason, the API also accepts forms, in particular the
*multipart/form-data format*, wich can be used for sending files.


### multipart/form-data

Using multipart/form-data, sending arrays and objects is also possible.
When files are not required, sending JSON data might be preferrable though,
as it is a bit simpler.

- **File** sending is implemented a bit differently by each library, so it's
  best to google quickly how to do it.

  - [Javascript Example](https://stackoverflow.com/a/9397172)
  - [Python Example](http://docs.python-requests.org/en/master/user/quickstart/#post-a-multipart-encoded-file)

- **Arrays** can be sent by simply including the same field multiple times in
  the request form, e.g. the API transforms the request form

  ```
  field1: value1
  field1: value2
  ```

  into the array

  ```
  field1: [value1, value2]
  ```


- **Objects** can be sent using *dot notation*, e.g. the API transforms the 
  request form

  ```
  field1.subfield1: value1
  field1.subfield2: value2
  ```

  into the object

  ```
  field1: {
   subfield1: value1,
   subfield2: value2
  }
  ```
