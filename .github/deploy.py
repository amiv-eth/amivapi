#!/usr/bin/env python3
"""Cluster Service Update Helper

This script handles everything needed to trigger a forced update of a service,
(which also causes nodes to pull new images, e.g. newer 'latest' images) and
can be configured with environment variables:

- `CI_DEPLOY_URL`: The URL of the [Service-Update-Helper-Service](https://gitlab.ethz.ch/amiv/service-update-helper-service)
- `CI_DEPLOY_TOKEN`: authorization token
- `CI_DEPLOY_SERVICE`: name of the service to update

Exit Codes:

0: Update triggered with success.
1: Missing environment variables
2: Service-Update-Helper-Service is not reachable (maybe URL is invalid?)
3: Invalid authorization token
4: No permission to update the given service
5: Service not found
6: Update failed
"""

from sys import exit
from os import getenv
import requests


def main():
    """Update a service using the Service-Update-Helper-Service."""
    session = requests.Session()

    # 0. Get configuration from environment
    # -------------------------------------

    url = getenv('CI_DEPLOY_URL')
    token = getenv('CI_DEPLOY_TOKEN')
    service = getenv('CI_DEPLOY_SERVICE')

    error = False
    if not url:
        print("Please specify the Service-Update-Helper-Service url with the environment "
              "variable 'CI_DEPLOY_URL'!")
        error = True
    else:
        url = url[:-1] if url.endswith('/') else url
    if not token:
        print("Please specify valid authorization token with the environment variable "
              "'CI_DEPLOY_TOKEN'!")
        error = True
    if not service:
        print("Please specify the service name with the environment variable "
              "'CI_DEPLOY_SERVICE'!")
        error = True
    if error:
        exit(1)

    session.headers['Authorization'] = token

    # 1. Update the service
    # ---------------------

    service_url = '%s/service/%s/update' % (url, service)

    print('Triggering forced service update...')
    try:
        update = session.get(service_url)
    except (requests.exceptions.RequestException, RuntimeError):
        print('Failed: The Service-Update-Helper-Service URL is invalid!')
        exit(2)

    if update.status_code == 401:
        print('Failed: The authorization token is invalid!')
        exit(3)
    elif update.status_code == 403:
        print("Failed: Updating the service '%s' is not allowed!" % service)
        exit(4)
    elif update.status_code == 404:
        print("Failed: The service '%s' could not be found!" % service)
        exit(5)
    elif update.status_code != 200:
        print("Failed: Could not update the service '%s'! (Error %i)" % (service, update.status_code))
        exit(6)

    print('Success!')


if __name__ == '__main__':
    main()
