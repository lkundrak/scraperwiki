import re

def is_gb_postcode(postcode):

    result = False

    #postcode parts
    ini  = 'ABDEFGHJLNPQRSTUWXYZ'
    fst = 'ABCDEFGHIJKLMNOPRSTUWYZ'
    sec = 'ABCDEFGHJKLMNOPQRSTUVWXY'
    thd = 'ABCDEFGHJKSTUW'
    fth = 'ABEHMNPRVWXY'
    num = '0123456789'
    nom = '0123456789'
    gap = '\s\.'

    #build up the various possible matches and engecases
    patterns = []
    patterns.append("^[%s][%s][%s]*[%s][%s][%s]$/i" %  (fst, num, gap, nom, ini, ini))    
    patterns.append("^[%s][%s][%s][%s]*[%s][%s][%s]$" %  (fst, num, num, gap, nom, ini, ini))
    patterns.append("^[%s][%s][%s][%s]*[%s][%s][%s]$" %  (fst, sec, num, gap, nom, ini, ini))
    patterns.append("^[%s][%s][%s][%s][%s]*[%s][%s][%s]$" %  (fst, sec, num, num, gap, nom, ini, ini))
    patterns.append("^[%s][%s][%s][%s]*[%s][%s][%s]$" %  (fst, num, thd, gap, nom, ini, ini))
    patterns.append("^[%s][%s][%s][%s][%s]*[%s][%s][%s]$" %  (fst, sec, num, fth, gap, nom, ini, ini))

    # see if any patterns match the postcode
    for pattern in patterns:
        regex = re.compile(pattern, re.IGNORECASE)
        if regex.match(postcode):
            result = True
            
    return result
    
    
