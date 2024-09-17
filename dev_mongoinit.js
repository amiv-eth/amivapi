db.createUser(
    {
        user: "amivapi",
        pwd: "amivapi",
        roles: [
            {
                role: "readWrite",
                db: "amivapi"
            }
        ]
    }
);

db = db.getSiblingDB('amivapi');

// Create admin user with password admin
let userId = db.users.insertOne({
    nethz: 'admin',
    password: '$pbkdf2-sha256$5$OqfUmtNaq5UyRohxDuGckw$9H/UL5N5dA7JmUq7ohRPfmJ84OUnpRKjTgsMeuFilXM',
    email: "admin@example.com",
    membership: "regular",
    gender: "female",
    firstname: "ad",
    lastname: "min",
    _etag: "27f987fd9dd45d491e5aea3e27730israndom",
}).insertedId;

// Create admin group with permissions on all resources
let groupId = db.groups.insertOne({
    name: 'admin',
    permissions: {
        apikeys: "readwrite",
        users: "readwrite",
        sessions: "readwrite",
        events: "readwrite",
        eventsignups: "readwrite",
        groups: "readwrite",
        groupmemberships: "readwrite",
        joboffers: "readwrite",
        beverages: "read",
        studydocuments: "readwrite",
        oauthclients: "readwrite",
    },
    _etag: "27f987fd9dd45d491e5aea3e27730israndom",
}).insertedId;

// Add admin to admin group
db.groupmemberships.insertOne({
    user: userId,
    group: groupId,
    _etag: "27f987fd9dd45d491e5aea3e27730israndom",
})

// Add Local Tool client for admin tool
db.oauthclients.insertOne({
    client_id: "Local Tool",
    redirect_uri: "http://localhost",
    _etag: "27f987fd9dd45d491e5aea3e27730israndom",
});