"""
Context Processors for Incomplete Visits Notifications
Place this at: alpha/core/context_processors.py
(or wherever you keep your context processors)

Then add to settings.py TEMPLATES['OPTIONS']['context_processors']:
    'alpha.core.context_processors.incomplete_visits',
"""
from alpha.visits.models import Visit


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
    
    # Get recent visits (last 50) and check which are incomplete
    # We fetch more than we display to ensure we have enough incomplete ones
    recent_visits = Visit.objects.select_related(
        'appointment',
        'appointment__client',
        'appointment__service',
        'staff'
    ).order_by('-created_at')[:50]
    
    # Filter incomplete visits in Python using the is_complete property
    # This is acceptable since we're only checking recent visits
    incomplete_visit_list = [v for v in recent_visits if not v.is_complete]
    
    # Limit to 10 most recent incomplete visits for the dropdown
    incomplete_visit_list = incomplete_visit_list[:10]
    
    return {
        'incomplete_visits': incomplete_visit_list,
        'incomplete_visits_count': len(incomplete_visit_list),
    }