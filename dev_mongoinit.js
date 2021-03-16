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

db.getSiblingDB('test_amivapi').createUser(
    {
        user: "test_user",
        pwd: "test_pw",
        roles: [
            {
                role: "readWrite",
                db: "test_amivapi"
            }
        ]
    }
);