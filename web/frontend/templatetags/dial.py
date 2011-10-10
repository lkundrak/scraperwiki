from django.template import Library

register = Library()

@register.inclusion_tag('frontend/templatetags/dial.html')
def dial(value, width, height):
    
    colour = '62B957'
    if value < 50:
        colour = 'C4161C'        
    elif value < 80:
        colour = 'F58220'
            
    return {'value': value, 'width': width, 'height': height, 'colour': colour}
