from amivapi import bootstrap

if __name__ == '__main__':
    app = bootstrap.create_app("development")
    app.run()
