import pytest
from PyQt5 import QtCore, QtWidgets
from optac_main import Gui


def divide(x, y):
    return x / y


def test_raises():
    with pytest.raises(ZeroDivisionError):
        divide(3, 0)


@pytest.fixture
def app(qtbot):
    test_app = Gui()
    qtbot.addWidget(test_app)
    return test_app


def test_init(app):
    assert not app.stop_request
    assert app.idle
    assert not app.motor_on
    assert not app.camera_on
    assert not app.opt_running
    assert not app.save_images
    assert not app.live_recon
    assert not app.accum_shots


@pytest.mark.parametrize(
    'test_input,expected',
    [("app.ui.red_ch", 0), ('app.ui.green_ch', 1),
     ('app.ui.blue_ch', 2), ('app.ui.amp_ch', 3)])
def test_channel_funcs(qtbot, app, test_input, expected):
    qtbot.mouseClick(eval(test_input), QtCore.Qt.LeftButton)
    assert app.channel == expected

def test_update_func(qtbot, app):
    pass
