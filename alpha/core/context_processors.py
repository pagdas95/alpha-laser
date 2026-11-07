"""
Context Processors for Incomplete Visits Notifications
Place this at: alpha/core/context_processors.py
(or wherever you keep your context processors)

Then add to settings.py TEMPLATES['OPTIONS']['context_processors']:
    'alpha.core.context_processors.incomplete_visits',
"""
from alpha.visits.models import recent_incomplete_visits


def incomplete_visits(request):
    """
    Add incomplete visits count and list to all templates for notification bell
    Only for authenticated users
    """
    if not request.user.is_authenticated:
        return {
            'incomplete_visits': [],
            'incomplete_visits_count': 0,
        }
    
    # 10 newest unpaid visits among the last 50, in ONE query
    # (previously this ran ~50 extra queries on every page load)
    incomplete_visit_list = recent_incomplete_visits()

    return {
        'incomplete_visits': incomplete_visit_list,
        'incomplete_visits_count': len(incomplete_visit_list),
    }