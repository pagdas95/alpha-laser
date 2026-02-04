"""
Context Processor for Staff Profile
Add this to: alpha/staff/context_processors.py (create this file)

This makes staff profile available in all templates
"""

def staff_profile(request):
    """
    Add staff profile to template context for all templates
    """
    if request.user.is_authenticated:
        try:
            # Try to get staff profile
            staff_profile = request.user.staffprofile
        except AttributeError:
            # User doesn't have a staff profile
            staff_profile = None
        
        return {
            'user_staff_profile': staff_profile
        }
    
    return {
        'user_staff_profile': None
    }