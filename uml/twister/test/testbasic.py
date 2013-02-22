import mock
import unittest

def load_twister():
    # Because twister has a config file, we need to pretend that we
    # have passed --config as command line option.
    import sys
    sys.argv=['twister', '--config=/var/www/scraperwiki/uml/uml.cfg']
    import twister
    return twister

def ensure_can_load_twister():
    """Ensure that we can load twister as a module."""

    twister = load_twister()

def ensure_can_instantiate_RunnerProtocol():
    """Ensure that we can create a RunnerProtocol instance."""

    twister = load_twister()
    runner = twister.RunnerProtocol()
    assert runner

def ensure_can_make_connection():
    """Ensure we can call the connectionMade() method."""

    twister = load_twister()
    runner = twister.RunnerProtocol()
    runner.factory = mock.Mock()
    runner.factory.clientcount = 7
    runner.transport = mock.Mock(
      getHandle=lambda:mock.Mock(getpeername=lambda:["127.0.0.1"]))
    runner.connectionMade()


