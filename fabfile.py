from fabric.api import *

import getpass
import sys
import os.path
import time

# TODO:
# Full deploy that restarts everything too
# Pull puppet on kippax, then pull elsewhere in one command
# Run Django tests automatically - on local or on dev?
# Run Selenium tests - on local or on dev?

# Example use:
# fab dev webserver
# fab dev webserver:buildout=no
# fab dev webserver:buildout=no --hide=running,stdout
# fab dev firebox:restart=yes

###########################################################################
# Server configurations

env.server_lookup = {
    ('webserver', 'dev'): ['yelland.scraperwiki.com'], 
    ('webserver', 'live'): ['rush.scraperwiki.com:7822'],

    ('datastore', 'dev'): ['kippax.scraperwiki.com'], 
    ('datastore', 'live'): ['burbage.scraperwiki.com:7822'],

    ('firebox', 'dev'): ['kippax.scraperwiki.com'], 
    ('firebox', 'live'): ['matfen.scraperwiki.com:7822', 'horsell.scraperwiki.com:7822'],

    ('screenshooter', 'live'): ['kippax.scraperwiki.com'], # bit nasty that this is a dev server!
}
# This is slightly magic - we want to generate the host list from
# the pair of the service deployed (e.g. firebox) and the flock
# (e.g. live). This gets fabric to call the function
# do_server_lookup to do that work -
# do_server_lookup in turn uses the env.server_lookup dictionary
# above.
env.roledefs = {
    'webserver' : lambda: do_server_lookup('webserver'),
    'datastore' : lambda: do_server_lookup('datastore'),
    'firebox' : lambda: do_server_lookup('firebox'),
    'screenshooter' : lambda: do_server_lookup('screenshooter')
}

env.path = '/var/www/scraperwiki'
env.activate = env.path + '/bin/activate'
env.user = 'scraperdeploy'
env.name = getpass.getuser()

# Call one of these tasks first to set which flock of servers
# you're working on.
@task
def dev():
    '''Call first to deploy to development servers'''
    env.flock = 'dev'
    env.branch = 'default'
    env.email_deploy = False

@task
def live():
    '''Call first to deploy to live servers'''
    env.flock = 'live'
    env.branch = 'stable'
    env.email_deploy = "deploy@scraperwiki.com"

###########################################################################
# Helpers

def parse_bool(s):
    if s not in ['yes','no']:
        raise Exception("bool flag must be yes or no")
    return s == 'yes'

def do_server_lookup(task):
    if not 'flock' in env:
        raise Exception("specify which flock (e.g. dev/live) first")
    hosts = env.server_lookup[(task, env.flock)]
    print "server_lookup: deploying '%s' on flock '%s', hosts: %s" % (task, env.flock, hosts)
    env.task = task
    return hosts

def run_in_virtualenv(command):
    temp = 'cd %s; source ' % env.path
    return run(temp + env.activate + '&&' + command)

def run_buildout():
    with cd(env.path):
        run('[ -f "bin/activate" ] || virtualenv --no-site-packages .')
        run_in_virtualenv('[ -f "bin/buildout" ] || pip install zc.buildout')

    run_in_virtualenv('buildout -N -qq')

def run_with_retries(cmd, success_output='', attempts=5, delay=1):
    for attempt in range(attempts):
        ret = run(cmd, shell=True)
        if ret == success_output:
            return
        time.sleep(delay)
    raise Exception("failed to get expected output '%s' after %d retries: %s" % (success_output, attempts, cmd))

def django_db_migrate():
    run_in_virtualenv('cd web; python manage.py syncdb --verbosity=0')
    run_in_virtualenv('cd web; python manage.py migrate --verbosity=0')

def update_js_cache_revision():
    """Put the current HG revision in the file web/revision.txt
    so that Django can use it to avoid caching JS files.
    """
    run_in_virtualenv("hg identify | awk '{print $1}' > web/revision.txt")

def _update_cron_if_exists(local_file):
    run('[ -e %s ] && sudo cp %s /etc/cron.d/ || echo -n'  % (local_file, local_file), shell=True)

def update_crons():
    """Deploy cron files for all servers, just this task, or
    just this task and flock.
    """
    _update_cron_if_exists('%(path)s/cron/scraperwiki-all' % env)
    _update_cron_if_exists('%(path)s/cron/scraperwiki-%(task)s-%(flock)s' % env)
    _update_cron_if_exists('%(path)s/cron/scraperwiki-%(task)s' % env)

def restart_daemon(name, process_check=None):
    """*process_check* is a string to search in output of ps to
    check if process has not died.
    """
    run('sudo -i /etc/init.d/%s stop' % name)
    if process_check:
        with settings(warn_only=True):
            run_with_retries('ps auxww | egrep -- "%s" | egrep -v "/bin/bash|grep"; true' % process_check)

    # This needs a login shell with "sudo -i" to start scriptmgr,
    # for unknown reasons.
    run('sudo -i /etc/init.d/%s start' % name)

def deploy_done():
    if not env.email_deploy:
        return

    env.changelog = local('hg log -r %(old_revision)s:%(new_revision)s' % env, capture=True)

    message = """From: ScraperWiki <developers@scraperwiki.com>
Subject: New Scraperwiki Deployment of '%(task)s' to flock '%(flock)s' (deployed by %(name)s)

%(name)s deployed

Old revision: %(old_revision)s
New revision: %(new_revision)s

%(changelog)s
""" % env

    sudo("""echo "%s" | sendmail deploy@scraperwiki.com """ % message)

def code_pull():
    with cd(env.path):
        env.old_revision = run("hg identify -i")
        run("hg pull --quiet; hg update --quiet -C %(branch)s" % env)
        env.new_revision = run("hg identify -i")
        if env.old_revision == env.new_revision:
            print "WARNING: code hasn't changed since last update"

###########################################################################
# Tasks

@task
@roles('webserver')
def webserver(buildout='yes', restart='no'):
    '''Deploys Django web application, runs schema migrations,
    clears caches, kicks webserver so it starts using new code. 

    restart=yes, also restarts twisted (uwgsi will gracefully restart
    automatically because revision.txt is touched);
    buildout=no, stops it running buildout which can be slow.
    '''
    restart = parse_bool(restart)
    buildout = parse_bool(buildout)

    code_pull()

    if buildout:
        run_buildout()
    django_db_migrate()
    update_js_cache_revision()

    if restart:
        restart_daemon('twister', 'twister.py')

    if 'CI' not in os.environ:
        update_crons()
    deploy_done()

# Currently this is just for the live site, to make the screenshots run
# on a separate server, as they would often break and spin and take down
# the live site.
@task
@roles('screenshooter')
def screenshooter():
    with cd("/home/screenshooter/scraperwiki"):
        run("sudo -u screenshooter hg pull --quiet")
        run("sudo -u screenshooter hg update --quiet -C %(branch)s" % env)
        run("sudo -u screenshooter -s -- 'source bin/activate; buildout -N -qq'")


@task
@roles('datastore')
def datastore(buildout='no', restart='no'):
    '''Deploys datastore SQL database.

    restart=yes, restarts daemons;
    buildout=no, stops it running buildout which can be slow:
    '''
    restart = parse_bool(restart)
    buildout = parse_bool(buildout)

    code_pull()

    if buildout:
        run_buildout()
    if restart:
        restart_daemon('dataproxy', 'dataproxy.py')
        #restart_daemon('datastore', 'datastore') # XXX doesn't work yet, needs right hand part checking/changing

    update_crons()
    deploy_done()


@task
@roles('firebox')
def firebox(restart='no'):
    '''Deploys LXC script sandbox executor.
    :todo: currently doesn't restart any daemons.

    restart=yes, restarts daemons.
    '''
    restart = parse_bool(restart)

    code_pull()

    if restart:
        restart_daemon('httpproxy', '--mode=H')
        restart_daemon('httpsproxy', '--mode=S')
        restart_daemon('ftpproxy', 'ftpproxy.py')
        restart_daemon('scriptmgr', 'scriptmgr.js')

    update_crons()
    deploy_done()


@task
def merge_to_stable():
    '''In your local copy, merges changes from default branch to stable
    in Mercurial, in preparation for a deploy.  Pushes to server.
    It can get upset if you have uncommitted changes, so
    make sure you commit everything first.
    '''

    # grab anything remote
    local('hg --quiet update default')
    local('hg --quiet pull --rebase') # configure the rebase extension in your ~/.hgrc
    local('hg --quiet push')

    # just in case someone committed stuff to stable, merge that to dev
    local('hg --quiet merge stable || echo "merge failed"')
    local('hg --quiet commit -m "Merge from stable to dev via fab" || echo "no commit needed"')

    # merge everything to stable
    local('hg --quiet update stable')
    local('hg --quiet merge default || echo "merge failed"')
    local('hg --quiet commit -m "Merge to stable via fab" || echo "no commit needed"')
    local('hg --quiet push')

    # done, working in default again
    local('hg --quiet update default')

'''
@task
def run_puppet():
    sudo("puppetd --no-daemonize --onetime --debug")        
    
@task
def test():
    if env.host != "dev.scraperwiki.com":
        print "Testing can only be done on the dev machine"
    else:
        run_in_virtualenv('cd web; python manage.py test')
'''
