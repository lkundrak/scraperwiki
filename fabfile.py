from fabric.api import *

import getpass
import sys
import os.path

# TODO:
# Restart things for firebox, webstore if specified (and indeed twister for webserver)
# Full deploy that restarts everything too
# Pull puppet on kippax, then pull elsewhere in one command
# Run Django tests automatically - on local or on dev?
# Run Selenium tests - on local or on dev?
# Merge code from default into stable for you (on dev)

# Example use:
# fab dev webserver
# fab dev webserver:buildout=no
# fab dev webserver:buildout=no --hide=running,stdout

###########################################################################
# Server configurations

env.server_lookup = {
    ('webserver', 'dev'): ['yelland.scraperwiki.com'], 
    ('webserver', 'live'): ['rush.scraperwiki.com:7822'],

    ('webstore', 'dev'): ['ewloe.scraperwiki.com'], 
    ('webstore', 'live'): ['burbage.scraperwiki.com:7822'],

    ('firebox', 'dev'): ['kippax.scraperwiki.com'], 
    ('firebox', 'live'): ['horsell.scraperwiki.com:7822'],
}
# This is slightly magic - we want to generate the host list from the pair of
# the service deployed (e.g. firebox) and the flock (e.g. live). This gets
# fabric to call the function do_server_lookup to do that work -
# do_server_lookup in turn uses the env.server_lookup dictionary above
env.roledefs = {
    'webserver' : lambda: do_server_lookup('webserver'),
    'webstore' : lambda: do_server_lookup('webstore'),
    'firebox' : lambda: do_server_lookup('firebox')
}

env.path = '/var/www/scraperwiki'
env.activate = env.path + '/bin/activate'
env.user = 'scraperdeploy'
env.name = getpass.getuser()

# Call one of these tasks first to set which flock of servers you're working on
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
        run_in_virtualenv('[ -f "bin/buildout" || pip install zc.buildout')

    run_in_virtualenv('buildout -N -qq')

def django_db_migrate():
    run_in_virtualenv('cd web; python manage.py syncdb --verbosity=0')
    run_in_virtualenv('cd web; python manage.py migrate --verbosity=0')

def update_js_cache_revision():
    # Put the current HG revision in a file so that Django can use it to avoid caching JS files
    run_in_virtualenv("hg identify | awk '{print $1}' > web/revision.txt")

def _update_cron_if_exists(local_file):
    run('[ -e %s ] && sudo cp %s /etc/cron.d/ || echo -n'  % (local_file, local_file), shell=True)

def update_crons():
    # deploy cron files for all servers, just this task, or just this task and flock
    _update_cron_if_exists('%(path)s/cron/scraperwiki-all' % env)
    _update_cron_if_exists('%(path)s/cron/scraperwiki-%(task)s-%(flock)s' % env)
    _update_cron_if_exists('%(path)s/cron/scraperwiki-%(task)s' % env)

def restart_webserver():
    sudo('apache2ctl graceful')

def deploy_done():
    if not env.email_deploy:
        return

    message = """From: ScraperWiki <developers@scraperwiki.com>
Subject: New Scraperwiki Deployment of '%(task)s' to flock '%(flock)s' (deployed by %(name)s)

%(name)s deployed

Old revision: %(old_revision)s
New revision: %(new_revision)s

""" % env
    sudo("""echo "%s" | sendmail deploy@scraperwiki.com """ % message)

def code_pull():
    with cd(env.path):
        env.old_revision = run("hg identify")
        run("hg pull --quiet; hg update --quiet -C %(branch)s" % env)
        env.new_revision = run("hg identify")
        if env.old_revision == env.new_revision:
            print "WARNING: code hasn't changed since last update"

###########################################################################
# Tasks

@task
@roles('webserver')
def webserver(buildout='yes'):
    '''Deploys Django web application, runs schema migrations, clears caches,
kicks webserver so it starts using new code. 

buildout=no, stops it updating buildout which can be slow'''

    if buildout not in ['yes','no']:
        raise Exception("buildout must be yes or no")

    code_pull()

    if buildout == 'yes':
        run_buildout()
    django_db_migrate()
    update_js_cache_revision()
    restart_webserver()   

    update_crons()
    deploy_done()


@task
@roles('webstore')
def webstore(buildout='no'): # default to no until ready
    '''Deploys webstore SQL database. XXX currently doesn't restart any daemons.

buildout=no, stops it updating buildout which can be slow'''

    if buildout not in ['yes','no']:
        raise Exception("buildout must be yes or no")

    code_pull()

    if buildout == 'yes':
        run_buildout()

    update_crons()
    deploy_done()


@task
@roles('firebox')
def firebox():
    '''Deploys LXC script sandbox executor. XXX currently doesn't restart any daemons'''
    code_pull()

    update_crons()
    deploy_done()


@task
def merge_to_stable():
    '''In your local copy, merges changes from default branch to stable in Mercurial,
in preparation for a deploy. Pushes to server. Make sure you commit everything first.'''

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
def setup():
    # this really ought to make sure it checks out default vs. stable
    raise Exception("not implemented, really old broken code")

    sudo('hg clone file:///home/scraperwiki/scraperwiki %(path)s' % env)        
    sudo('chown -R %(fab_user)s %(path)s' % env)
    sudo('cd %(path)s; easy_install virtualenv' % env)
    run('hg clone %(web_path)s %(path)s' % env, fail='ignore')
'''

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
