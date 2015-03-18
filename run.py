#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# license: AGPL, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.

from amivapi import bootstrap

if __name__ == '__main__':
    app = bootstrap.create_app()
    app.run()
