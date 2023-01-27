from django import template

register = template.Library()


@register.filter
def timedelta_to_hours(td):
    days = td.days
    hours, remainder = divmod(td.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    return "%d:%02d" % (hours + days * 24, minutes)
