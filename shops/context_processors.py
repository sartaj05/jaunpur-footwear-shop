def language_context(request):
    language = request.session.get('site_language', 'en')
    if language not in ('en', 'hi'):
        language = 'en'
    return {'site_language': language, 'is_hindi': language == 'hi'}
