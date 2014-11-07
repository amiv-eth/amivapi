import requests
import subprocess
from signal import SIGTERM
from os import remove, killpg, setsid
from os.path import abspath, join, dirname


apiurl = 'http://localhost:5000'

ROOT_PATH = abspath(join(dirname(__file__), ".."))
LOGFILE_PATH = ROOT_PATH + '/tests_server.log'


class ServerError(Exception):
    def __init(self, value):
        self.value = value

    def __repr__(self):
        return str(self.value)


class TestServer:

    def __enter__(self):

        # Check for running server
        try:
            requests.get(apiurl + '/')
            raise ServerError(
                'A server is already running. Are you debugging?')

        except requests.ConnectionError:
            pass

        # If there is a database, delete it

        try:
            remove(ROOT_PATH + '/data.db')
        except OSError:
            pass

        # Start the server

        self.logfile = open(LOGFILE_PATH, 'a')
        # prexec_fn=setsid makes the process and all its children part of
        # a group so we can kill them all as one later
        self.serverProcess = subprocess.Popen(
            ['python', ROOT_PATH + '/amivapi/run.py'],
            cwd=ROOT_PATH + '/amivapi',
            stdout=self.logfile,
            stderr=subprocess.STDOUT,
            preexec_fn=setsid
            )

        # Wait for the server to finish booting up

        # If the server process finishes, the loop is left
        while(self.serverProcess.poll() is None):
            try:
                if(requests.get(apiurl + '/').status_code == 200):
                    # Connection successful, server is up
                    return self
            except requests.ConnectionError:
                pass

        raise ServerError(
            'Could not start development server! Exit code: ' +
            str(self.serverProcess.returncode) +
            '\nTry checking the logfile in ' + LOGFILE_PATH)

    def __exit__(self, type, value, traceback):

        # Kill the development server process group
        killpg(self.serverProcess.pid, SIGTERM)
