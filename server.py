# [bjoern](https://github.com/jonashaag/bjoern) uwsgi server to server app
# Used to serve amivapi in Docker container.

from amivapi import create_app
import bjoern

print('Starting bjoern...')
bjoern.run(create_app(), '0.0.0.0', 8080)
