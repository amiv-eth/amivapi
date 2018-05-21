# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""Tests for purchases module"""

from datetime import datetime, timedelta
from io import BytesIO
from os.path import dirname, join

from amivapi.settings import DATE_FORMAT
from amivapi.tests import utils

pdfpath = join(dirname(__file__), "../fixtures", 'test.pdf')
lenapath = join(dirname(__file__), "../fixtures", 'lena.png')


class JobOffersTest(utils.WebTestNoAuth):
    """Test basic functionality of joboffers"""

    def test_add_joboffer_nomedia(self):
        """ Usecase: A firm wants to post a joboffer on the website without any media
        """
        time_start = (datetime.utcnow() + timedelta(days=1)).strftime(DATE_FORMAT);
        time_advertising_end = (datetime.utcnow() + timedelta(days=2)).strftime(DATE_FORMAT)
        post_data = {
            'company': 'ACME Inc.',
            'location': 'Zürich',
            'description_de': """Firmenbeschreibung auf Deutsch der
            weltberühmten ACME Inc. Von Herr Rädö im Jahr 1893 gegründet und
            seither nur am Wachsen, ACME Inc. zeichnete sich mit
            aussergewöhnlichst kreative Lösungen zum spontan Sachen zum
            explodieren bringen und irgendein depressives Coyote langsam
            aber sicher zum Selbstmord zu führen""",
            'description_en': """Firmdescription in English of the world renown
            ACME Inc. Founded by Mr. Rädö in 1893 and in proving constant
            growth since, ACME Inc. stands out thanks to it borderline
            creative solutions for spontaneous destruction by explosion and
            driving some random Coyote slowly but steadily to suicide""",
            'time_start':time_start,
            'time_advertising_end': time_advertising_end,
            'title_de': 'ACME Inc jetzt auf der Suche nach Explosionsexperte',
            'title_en': 'ACME Inc now hiring explosions experts',
            'pdf': (BytesIO(br'%PDF magic'), 'test.pdf'),
            'logo': (open(lenapath, 'rb'), 'logo.png'),
        }

        # Check if posting the joboffer is successful
        self.api.post("/joboffers",
                      headers={'content-type': 'multipart/form-data'},
                      data=post_data, status_code=201)

    def test_add_joboffer_nomedia_nostart(self):
        """ Usecase: A firm wants to post a joboffer on the website without any media, and without specifying a starting time.
        """
        time_start = None;
        time_advertising_end = (datetime.utcnow() + timedelta(days=2)).strftime(DATE_FORMAT)
        post_data = {
            'company': 'Dahle and partners',
            'location': 'Tübingen',
            'description_de': """Ä""",
            'description_en': """É""",
            'time_start':time_start,
            'time_advertising_end': time_advertising_end,
            'title_de': 'ü',
            'title_en': 'À',
            'pdf': (BytesIO(br'%PDF magic'), 'test.pdf'),
            'logo': (open(lenapath, 'rb'), 'logo.png'),
        }

        # Check if posting the joboffer is successful
        self.api.post("/joboffers",
                      headers={'content-type': 'multipart/form-data'},
                      data=post_data, status_code=201)

    def test_get_joboffer(self):
        """Usecase: User wants to see a job offer listing
        """

        # Now we test with a random job offer that has expired
        # Should return no joboffers since the only one has expired
        expired_time = datetime.utcnow() - timedelta(days=1)

        self.new_object(
            'joboffers',
            company='ACME Inc.',
            title_en="ACME Wants engineers",
            description_en="ACME needs your life",
            time_advertising_end=expired_time
        )

        p = self.api.get(
            '/joboffers?where={"time_advertising_end": {"$gte": "%s"}}'
            % datetime.utcnow().strftime(DATE_FORMAT),
            status_code=200).json['_items']
        self.assertEqual(len(p), 0)

        # Next we test fetching a valid job offer
        # Should return the fresh job offer which is still valid
        valid_time = (datetime.utcnow() + timedelta(days=1))

        self.new_object(
            'joboffers',
            company='AMIV Inc.',
            title_en="ACME wants more engineers",
            description_en="ACME need you life",
            time_advertising_end=valid_time
        )

        p = self.api.get(
            '/joboffers?where={"time_advertising_end" : {"$gte": "%s"}}'
            % datetime.utcnow().strftime(DATE_FORMAT),
            status_code=200).json['_items']
        self.assertTrue(len(p) > 0)
