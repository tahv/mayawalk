import pytest

from maya import cmds


def pytest_sessionstart(session):
    """Initialize a Maya standalone session, if we are running on mayapy.

    Called after the Session object has been created and before performing
    collection and entering the run test loop.
    """
    import maya.standalone
    try:
        maya.standalone.initialize()
    except RuntimeError:  # Can be used from an external Python interpreter
        pass


def pytest_sessionfinish(session, exitstatus):
    """Uninitialize a Maya standalone session, if we are running on mayapy.

    Called after whole test run finished, right before returning the exit status
    to the system.
    """
    import maya.standalone
    try:
        maya.standalone.uninitialize()
    except AttributeError:  # Module has no attribute 'uninitialize'.
        # unititialize was removed after maya 2018.
        pass


@pytest.fixture(scope='function', autouse=True)
def new_file():
    """Create a new file before each test."""
    cmds.file(new=True, force=True)
