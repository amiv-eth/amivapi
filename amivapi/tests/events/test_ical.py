# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""Test event GET text/calendar MIME support"""

from icalendar import Calendar
from json import loads as jloads
from datetime import datetime, timedelta
import sys

from amivapi.tests.utils import WebTestNoAuth


class EventiCalendarTest(WebTestNoAuth):
    def test_events_json_ical_3_multilang(self):
        ev0 = {
            'title_en': 'party',
            'description_en': 'fun',
            'catchphrase_en': 'disco, disco, party, party',
            'spots': None,
            'show_website': False,
            'show_infoscreen': True,
            'show_announce': False,
            'time_start': '2016-10-17T18:11:14Z',
            'time_end': '2016-10-17T22:33:37Z',
            'location': 'AMIV Office'
        }
        ev1 = {
            'title_en': 'party2',
            'description_en': 'fun2',
            'catchphrase_en': 'disco, disco, party, party2',
            'spots': None,
            'show_website': False,
            'show_infoscreen': False,
            'show_announce': True,
            'time_start': '2016-10-18T18:11:14Z',
            'time_end': '2016-10-18T22:33:37Z'
        }
        ev2 = {
            'title_de': 'party 3',
            'description_de': 'fun de 3',
            'catchphrase_de': 'disco, disco, party, party de 3',
            'spots': None,
            'show_website': True,
            'show_infoscreen': False,
            'show_announce': False,
            'time_start': '2016-10-19T18:11:14Z',
            'time_end': '2016-10-19T22:33:37Z'
        }
        """Fill database with dummy data"""
        self.api.post("/events", data=ev0, status_code=201)
        self.api.post("/events", data=ev1, status_code=201)
        self.api.post("/events", data=ev2, status_code=201)

        # get JSON data and do some simple checks
        r = jloads(self.api.get("/events", status_code=200)
                   .get_data(as_text=True))
        d = r['_items']
        self.assertEqual(len(d), 3)
        # this checks if d[X+1] is a superset of evX (python! yay!)
        if sys.version_info < (3, 0):
            self.assertTrue(ev0.viewitems() <= d[0].viewitems())
            self.assertTrue(ev1.viewitems() <= d[1].viewitems())
            self.assertTrue(ev2.viewitems() <= d[2].viewitems())
        else:
            self.assertTrue(ev0.items() <= d[0].items())
            self.assertTrue(ev1.items() <= d[1].items())
            self.assertTrue(ev2.items() <= d[2].items())
        # save uids for comparison with iCal
        etaglist = [x['_etag'] for x in d]

        # get iCalendar data and check if etag matches uid

        # no specified language case
        r = self.api.get("/events", headers={'Accept': 'text/calendar'},
                         status_code=200).get_data(as_text=True)
        g = Calendar.from_ical(r)
        self.assertEqual(g['version'], '2.0')
        count = 0
        for c in g.walk():
            if c.name == "VEVENT":
                self.assertTrue(str(c.get('uid')) in etaglist)
                count += 1
        self.assertEqual(count, len(etaglist))

        # swiss german desired
        r = self.api.get("/events", headers={'Accept': 'text/calendar',
                         'Accept-Language': 'de-CH'},
                         status_code=200).get_data(as_text=True)
        g = Calendar.from_ical(r)
        self.assertEqual(g['version'], '2.0')
        count = 0
        for c in g.walk():
            if c.name == "VEVENT":
                self.assertTrue(str(c.get('uid')) in etaglist)
                count += 1
        self.assertEqual(count, len(etaglist))

        # us-english desired
        r = self.api.get("/events", headers={'Accept': 'text/calendar',
                         'Accept-Language': 'en-US'},
                         status_code=200).get_data(as_text=True)
        g = Calendar.from_ical(r)
        self.assertEqual(g['version'], '2.0')
        count = 0
        for c in g.walk():
            if c.name == "VEVENT":
                self.assertTrue(str(c.get('uid')) in etaglist)
                count += 1
        self.assertEqual(count, len(etaglist))

    def test_events_json_ical_1(self):
        ev0 = {
            'title_en': 'party',
            'description_en': 'fun',
            'catchphrase_en': 'disco, disco, party, party',
            'spots': None,
            'show_website': False,
            'show_infoscreen': True,
            'show_announce': False,
            'time_start': '2016-10-17T18:11:14Z',
            'time_end': '2016-10-17T22:33:37Z'
        }
        """Fill database with dummy data"""
        self.api.post("/events", data=ev0, status_code=201)

        # get JSON data and do some simple checks
        r = jloads(self.api.get("/events", status_code=200)
                   .get_data(as_text=True))
        d = r['_items']
        self.assertEqual(len(d), 1)
        # check if data matches
        if sys.version_info < (3, 0):
            self.assertTrue(ev0.viewitems() <= d[0].viewitems())
        else:
            self.assertTrue(ev0.items() <= d[0].items())

        # get iCalendar data and check if etag matches uid
        r = self.api.get("/events", headers={'Accept': 'text/calendar'},
                         status_code=200).get_data(as_text=True)
        g = Calendar.from_ical(r)
        self.assertEqual(g['version'], '2.0')
        count = 0
        for c in g.walk():
            if c.name == "VEVENT":
                self.assertEqual(str(c.get('uid')), d[0]['_etag'])
                count += 1
        self.assertEqual(count, 1)

    def test_events_json_ical_1_notime(self):
        ev0 = {
            'title_en': 'party',
            'description_en': 'fun',
            'catchphrase_en': 'disco, disco, party, party',
            'spots': None,
            'show_website': False,
            'show_infoscreen': True,
            'show_announce': False
        }
        """Fill database with dummy data"""
        self.api.post("/events", data=ev0, status_code=201)

        # get JSON data and do some simple checks
        r = jloads(self.api.get("/events", status_code=200)
                   .get_data(as_text=True))
        d = r['_items']
        self.assertEqual(len(d), 1)
        # check if data matches
        if sys.version_info < (3, 0):
            self.assertTrue(ev0.viewitems() <= d[0].viewitems())
        else:
            self.assertTrue(ev0.items() <= d[0].items())

        # get iCalendar data and check if is empty as expected
        r = self.api.get("/events", headers={'Accept': 'text/calendar'},
                         status_code=200).get_data(as_text=True)
        g = Calendar.from_ical(r)
        self.assertEqual(g['version'], '2.0')
        count = 0
        for c in g.walk():
            if c.name == "VEVENT":
                count += 1
        self.assertEqual(count, 0)

    def test_events_json_ical_1_noendtime(self):
        testtime = datetime.now().replace(microsecond=0)
        ev0 = {
            'title_en': 'party',
            'description_en': 'fun',
            'catchphrase_en': 'disco, disco, party, party',
            'spots': None,
            'show_website': False,
            'show_infoscreen': True,
            'show_announce': False,
            'time_start': datetime.strftime(testtime, '%Y-%m-%dT%H:%M:%SZ')
        }
        """Fill database with dummy data"""
        self.api.post("/events", data=ev0, status_code=201)

        # get JSON data and do some simple checks
        r = jloads(self.api.get("/events", status_code=200)
                   .get_data(as_text=True))
        d = r['_items']
        self.assertEqual(len(d), 1)
        # check if data matches
        if sys.version_info < (3, 0):
            self.assertTrue(ev0.viewitems() <= d[0].viewitems())
        else:
            self.assertTrue(ev0.items() <= d[0].items())

        # get iCalendar data and check if is empty as expected
        r = self.api.get("/events", headers={'Accept': 'text/calendar'},
                         status_code=200).get_data(as_text=True)
        g = Calendar.from_ical(r)
        self.assertEqual(g['version'], '2.0')
        count = 0
        for c in g.walk():
            if c.name == "VEVENT":
                self.assertEqual(c.get('dtstart').dt, testtime)
                self.assertEqual(c.get('dtend').dt, testtime
                                 + timedelta(minutes=60))
                count += 1
        self.assertEqual(count, 1)

    def test_events_json_ical_1_idendpoint(self):
        ev0 = {
            'title_de': 'party de',
            'description_de': 'fun de',
            'catchphrase_de': 'disco, disco, party, party de',
            'spots': None,
            'show_website': True,
            'show_infoscreen': True,
            'show_announce': True,
            'time_start': '2016-10-17T18:11:14Z',
            'time_end': '2016-10-17T22:33:37Z'
        }
        """Fill database with dummy data"""
        self.api.post("/events", data=ev0, status_code=201)

        # get JSON data and do some simple checks
        r = jloads(self.api.get("/events", status_code=200)
                   .get_data(as_text=True))
        d = r['_items']
        self.assertEqual(len(d), 1)
        # check if data matches
        if sys.version_info < (3, 0):
            self.assertTrue(ev0.viewitems() <= d[0].viewitems())
        else:
            self.assertTrue(ev0.items() <= d[0].items())
        ev_id = d[0]['_id']
        ev_etag = d[0]['_etag']

        # get iCalendar data and check if etag matches uid
        r = self.api.get('/events/'+str(ev_id),
                         headers={'Accept': 'text/calendar'},
                         status_code=200).get_data(as_text=True)
        g = Calendar.from_ical(r)
        self.assertEqual(g['version'], '2.0')
        count = 0
        for c in g.walk():
            if c.name == "VEVENT":
                self.assertEqual(str(c.get('uid')), ev_etag)
                count += 1
        self.assertEqual(count, 1)
