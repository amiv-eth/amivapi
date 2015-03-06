from flask import request, abort, current_app as app
from eve.methods.post import post_internal
from amivapi.models import Translation


def insert_localized_fields(response):
    """Insert title and description field into event and joboffer with correct
    language
    This is done like this and not more abstract since there are only four
    localized fields in total
    """
    for field in ['title', 'description']:
        id = response['%s_id' % field]

        session = app.data.driver.session

        query = session.query(Translation.language, Translation.content). \
            filter_by(localization_id=id)

        locales = {}

        for language, content in query:
            locales[language] = content

        match = request.accept_languages.best_match(locales.keys())

        if match:
            response[field] = locales[match]
        else:
            default = app.config['DEFAULT_LANGUAGE']
            if default in locales.keys():  # Try to fall back to default
                response[field] = locales[default]
            else:
                response[field] = u''  # Last resort: Just empty field


def create_localization_ids(items):
    """Whenever a event or joboffer is created, add translation fields"""
    for item in items:
        mapping = post_internal("translationmappings", payl={})
        item['title_id'] = mapping[0]['id']
        mapping = post_internal("translationmappings", payl={})
        item['description_id'] = mapping[0]['id']


def unique_language_per_locale_id(items):
    """Ensure that for every locale_id each language only exists once, e.g. not
    two english translations at the same time
    """
    for item in items:
        id = item['localization_id']

        """Now database query is needed to check if this language exists for
        the given id
        """
        session = app.data.driver.session

        query = session.query(Translation.language). \
            filter_by(localization_id=id)

        if str(item['language']) in str(list(query)):
            error = "Language '%s' already exists for localization_id '%i', \
                     post not allowed. Try to patch instead." \
                     % (item['language'], id)
            abort(405, description=error)
