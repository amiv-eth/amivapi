from amivapi import bootstrap

if __name__ == '__main__':
    app = bootstrap.create_app()
    app.run()
