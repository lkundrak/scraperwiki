import optparse
import logging, logging.config
import time
import ConfigParser

try:
    import cloghandler
except:
    pass


def jstime(dt):
    return str(1000*int(time.mktime(dt.timetuple()))+dt.microsecond/1000)


parser = optparse.OptionParser()
parser.add_option("--pidfile")
parser.add_option("--config")
parser.add_option("--logfile")
parser.add_option("--setuid", action="store_true")
poptions, pargs = parser.parse_args()

config = ConfigParser.ConfigParser()
config.readfp(open(poptions.config))

djangokey = config.get("twister", "djangokey")
djangourl = config.get("twister", "djangourl")

stdoutlog = poptions.logfile and open(poptions.logfile+"-stdout", 'a', 0)  
logger = logging.getLogger('twister')

# List of machine IPs that are allowed to connect to this machine
allowed_ips = []

try:
    allowed_ips = [ x.replace("'", "").strip() for x in config.get('security', 'allowed_ips').split(',')]
except:
    logger.warning("Only allowing local connections, bad settings")        
    allowed_ips = ['127.0.0.1']


# Rather than only allowing a single server we'll start sending 
# requests to a random server from a list, that list decided based on 
# whether it is a live in-editor run or a scheduled one.  At some point
# it might be useful to have it check on error and possibly redirect so
# that the LXC boxes can be taken down individually.
node_config = {
    "scheduled": [],
    "live": []
}

try:
    node_names = (config.get("twister", "node_names") or '').split(',')
    for node in node_names:
        d = {
            "name": node,
            "host": config.get(node, 'host'),
            "port": config.getint(node, 'port')
        }
        for k in ['live','scheduled']:
            if config.getint(node,k) == 1:            
                node_config[k].append( d )
except:
    # Either a configuration error or we are running locally with a dodgy 
    # uml.cfg file.
    logger.warning('Unable to load node_names and settings from config, assuming local')
    localhost = {"name": "local", "host": "localhost", "port": 9001 }
    node_config['scheduled'].append( localhost )
    node_config['live'].append( localhost )    
    

def choose_controller(deliver_to='scheduled'):
    """
    Choose a controller to send the request to based on the type of execution 
    we want, scheduled or live and randomly chosen from the list.
    """
    from random import choice
    c = choice( node_config[deliver_to] )
    if not c:
        return None, None, None
    return c['name'], c['host'], c['port']
