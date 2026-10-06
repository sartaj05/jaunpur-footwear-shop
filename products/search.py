from django.db.models import Q


SEARCH_SYNONYMS = {
    'shoe': ('shoes', 'footwear', 'जूता', 'जूते'),
    'shoes': ('shoe', 'footwear', 'जूता', 'जूते'),
    'footwear': ('shoe', 'shoes', 'जूता', 'जूते', 'चप्पल', 'सैंडल'),
    'जूता': ('shoe', 'shoes', 'footwear', 'जूते'),
    'जूते': ('shoe', 'shoes', 'footwear', 'जूता'),
    'slipper': ('slippers', 'चप्पल'),
    'slippers': ('slipper', 'चप्पल'),
    'चप्पल': ('slipper', 'slippers', 'footwear'),
    'sandal': ('sandals', 'सैंडल'),
    'sandals': ('sandal', 'सैंडल'),
    'सैंडल': ('sandal', 'sandals', 'footwear'),
    'sneaker': ('sneakers', 'sports shoes', 'स्पोर्ट्स शूज'),
    'sneakers': ('sneaker', 'sports shoes', 'स्पोर्ट्स शूज'),
    'sports shoes': ('sneaker', 'sneakers', 'स्पोर्ट्स शूज'),
    'स्पोर्ट्स शूज': ('sports shoes', 'sneaker', 'sneakers'),
}


def product_search_query(query):
    normalized = (query or '').strip().casefold()
    if not normalized:
        return Q()
    terms = {normalized, *SEARCH_SYNONYMS.get(normalized, ())}
    clause = Q()
    for term in terms:
        clause |= (
            Q(name__icontains=term)
            | Q(name_hi__icontains=term)
            | Q(description__icontains=term)
            | Q(description_hi__icontains=term)
            | Q(brand__name__icontains=term)
            | Q(category__name__icontains=term)
        )
    return clause
