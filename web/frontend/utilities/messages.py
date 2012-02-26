from django.contrib import messages
from django.utils.safestring import mark_safe
from django.template.loader import render_to_string

# An example of sending an alert message
#
# from frontend.utilities.messages import send_message
# send_message ( request, {
#        "message": "Your data has been deleted",
#        "level"  : "info",
#        "actions": 
#            [ 
#                ("Undo?", "https://.....", True,) # Boolean denotes secondary action
#            ]
#    } )        

def send_message( request, message_dict ):
    """
    Loads a template as a string and provides the information in the message_dict as 
    context.
    """
    if not 'level' in message_dict:
        message_dict['level'] = 'info'
        
    try:
        lvl = getattr(messages, message_dict['level'].upper())
    except:
        lvl = messages.INFO

    result = render_to_string('frontend/messages.html', message_dict)
    messages.add_message(request, lvl, mark_safe(result) )

