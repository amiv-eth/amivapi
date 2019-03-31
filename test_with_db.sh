#!/bin/bash -i

# Use alternate port for less interaction with existing mongo servers.
MONGO_PORT=27099

# Create a mongodb server.
mkdir /tmp/test_db
mongod --dbpath /tmp/test_db --port $MONGO_PORT >/tmp/mongo.log &

# Now is a good time to run flake8, so it can run during the mongo startup.
flake8 /api/amivapi || { echo 'Please fix the flake8 errors :)' >&2; exit 1; }

echo "Waiting for mongodb to start..."
grep -q "waiting for connections on port" <(tail -f /tmp/mongo.log)

# Create DB user.
mongo test_amivapi --port=$MONGO_PORT --eval \
    'db.createUser({user:"test_user",pwd:"test_pw",roles:["readWrite"]})'

# Create amivapi config.
echo > /tmp/amivconfig.py 'MONGO_HOST = "localhost"'
echo >>/tmp/amivconfig.py "MONGO_PORT = $MONGO_PORT"

# Start tests. Use amivapi/tests as default argument
if [ $# -eq 0 ]; then
    args="amivapi/tests"
else
    args=$@
fi
AMIVAPI_CONFIG=/tmp/amivconfig.py pytest $args &
PYTEST_PID=$!

# When running in docker, Ctrl-C will send a SIGINT to the shell running this
# script (PID 1), not the pytest subprocess. Bash does not handle signals while
# a process is running in the foreground, so we have to run the tests in the
# background, handle SIGINT here and forward it to the pytest process to make
# Ctrl-C work.
trap 'kill -INT $PYTEST_PID' INT
wait $PYTEST_PID

# This is needed to give enough time for output to be sent to the terminal.
# Without it the docker container is killed before the test results are
# flushed.
sleep 3
