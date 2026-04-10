from django.utils import timezone


def school_year(request):
    now = timezone.now()
    year = now.year
    if now.month >= 8:
        current_year = f"{year}-{year + 1}"
    else:
        current_year = f"{year - 1}-{year}"
    
    return {
        'current_school_year': current_year,
    }
