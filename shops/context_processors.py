def language_context(request):
    language = request.session.get('site_language') or getattr(request, 'LANGUAGE_CODE', 'en')
    language = language.split('-', 1)[0]
    if language not in ('en', 'hi'):
        language = 'en'
    return {'site_language': language, 'is_hindi': language == 'hi'}
