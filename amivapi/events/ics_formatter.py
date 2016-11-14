# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""Hooks to generate ICS data format for event resource"""

from json import loads as jloads
from icalendar import Calendar, Event
from eve.utils import str_to_date
from datetime import timedelta


def find_Language_match(acceptedLang):
    """This function finds out if the client prefers english or german.
    (default English)"""
    for l in acceptedLang:
        for m in ['en', 'de']:
            if (m in l[0]):
                return m
    # default is english
    return 'en'


def post_events_get_callback(request, payload):
    # test if Accept header is set to the .ics MIME type
    if ('Accept' in request.headers) and \
       (request.headers['Accept'] == 'text/calendar'):

        # figure out best language
        engflag = (find_Language_match(request.accept_languages) == 'en')

        # get back data from json format
        p = jloads(payload.get_data(as_text=True))

        # create calendar object and fill with general infos
        cal = Calendar()
        cal.add('prodid', 'created_by_AMIVAPI_by_AMIV_an_der_ETH')
        cal.add('version', '2.0')  # specify iCalendar format

        # create list of all events
        if ('_items' in p):
            jeventlst = p['_items']
        else:
            # special case for event/_id endpoint
            jeventlst = [p]

        # loop through all events
        for jevent in jeventlst:

            # add start / end times
            if ('time_start' in jevent):
                e = Event()
                e.add('dtstart', str_to_date(jevent['time_start']))
                if ('time_end' in jevent):
                    # good, we have an end time
                    e.add('dtend', str_to_date(jevent['time_end']))
                else:
                    # if no end time is given, we just assume it runs one hour
                    d = str_to_date(jevent['time_start'])
                    e.add('dtend', d+timedelta(minutes=60))
            else:
                # if there is no start time, we do not add this
                # event to the calendar
                continue

            # get english if german not available or desired
            if not('title_de' in jevent) or \
               (engflag and ('title_en' in jevent)):
                t = jevent['title_en']
                if 'catchphrase_en' in jevent:
                    t += ' [' + jevent['catchphrase_en'] + ']'
                e.add('summary', t)
                if 'description_en' in jevent:
                    e.add('description', jevent['description_en'])
            # get german
            else:
                t = jevent['title_de']
                if 'catchphrase_de' in jevent:
                        t += ' [' + jevent['catchphrase_de'] + ']'
                e.add('summary', t)
                if 'description_de' in jevent:
                    e.add('description', jevent['description_de'])

            # add location (language indep.)
            if ('location' in jevent):
                e.add('location', jevent['location'])

            # add unique id for versioning in desktop calendar tools
            e.add('uid', str(jevent['_etag']))

            # add final event to calendar
            cal.add_component(e)

        # get ics file string and put it as response data
        payload.set_data(cal.to_ical())
        payload.content_type = 'text/calendar'
