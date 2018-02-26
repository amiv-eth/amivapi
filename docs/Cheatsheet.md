# AMIVAPI Cheatsheet

## Filtering

```
https://amivapi/events?where={"title_en":"Party"}

https://amivapi/events?where={"$gt":{"time_start":"20180606T100000Z"}}

https://amivapi/events?where={"$or":{"title_en":"Party","title_de":"Feier"}}
```

Supported operators include:
`$gt` (>), `$gte` (>=), `$lt` (<), `$lte` (<=), `$ne` (!=), `$and`, `$or`, `$in`

Time format: `YYYYMMDDThhmmssZ`

**Y**ear, **M**onth, **D**ay, **h**our, **m**inutes, **s**econds, `T` is a required separator
and `Z` indicates UTC (other timezones are not supported)

## Sorting

```
https://amivapi/events?sort=time_start,-time_end
```

The prefix ```-``` inverts the sorting order.

## Pagination

```
https://amivapi/events?max_results=20&page=2
```

There is a global maximum on the results per page, so getting all results in one request
may not be possible.

## Embedding

By default, other resources are only included by `_id`. with embedding, you can include complete objects.

```
https://amivapi/groupmemberships?embedded={"user":1,"group":1}
```

## Projections

Hide fields or show hidden fields. Passwords can't be shown.

```
https://amivapi/groupmemberships?projection={"group":0}
```
