#!/usr/bin/env python

'''Basic tests of the optac module'''

import pytest
from PyQt5 import QtCore
from optac.main import main_GUI
from PyQt5 import QtTest
from pytestqt.plugin import QtBot
from PyQt5.QtWidgets import (
    QApplication,
    QMessageBox
)

__author__ = 'David Palecek'
__credits__ = ['Teresa M Correia', 'Rui Guerra']
__license__ = 'GPL'


def divide(x, y):
    return x / y


def test_raises():
    with pytest.raises(ZeroDivisionError):
        divide(3, 0)


@pytest.fixture(scope='session')
def qtbot_session(qapp, request):
    print("  SETUP qtbot")
    result = QtBot(qapp)
    return result


@pytest.fixture(scope='session')
def Viewer(request):
    print("  SETUP GUI")
    app, view = main_GUI()
    QtTest.QTest.qWait(int(0.5*100))
    qtbotbis = QtBot(app)
    QtTest.QTest.qWait(int(0.5*100))
    return app, view, qtbotbis


def test_init(Viewer):
    _, view, qtbot = Viewer
    assert not view.stop_request
    assert view.idle
    assert not view.motor_on
    assert not view.camera_on
    assert not view.opt_running


@pytest.mark.parametrize(
    'test_input,expected',
    [("view.ui.red_ch", 0), ('view.ui.green_ch', 1),
     ('view.ui.blue_ch', 2), ('view.ui.amp_ch', 3)])
def test_channel_funcs(Viewer, test_input, expected):
    _, view, qtbot = Viewer
    QtTest.QTest.qWait(int(0.5*100))
    qtbot.mouseClick(eval(test_input), QtCore.Qt.LeftButton)
    QtTest.QTest.qWait(int(0.5*100))
    assert view.channel == expected


# @pytest.mark.parametrize(
#     'test_input,expected',
#     [("app.ui.red_ch", 0), ('app.ui.green_ch', 1),
#      ('app.ui.blue_ch', 2), ('app.ui.amp_ch', 3)])
# def test_channel_funcs(qtbot, app, test_input, expected):
#     qtbot.mouseClick(eval(test_input), QtCore.Qt.LeftButton)
#     assert app.channel == expected


@pytest.mark.parametrize(
    'func, set, attr, expected',
    [('view.ui.angle.setValue', 123, 'view.angle', 123),
     ('view.ui.angle.setValue', -370, 'view.angle', -360),
     ('view.ui.angle.setValue', 400, 'view.angle', 400),
     ('view.ui.motor_speed.setValue', 432, 'view.motor_speed', 432),
     ('view.ui.motor_speed.setValue', -10, 'view.motor_speed', 100),
     ('view.ui.motor_speed.setValue', 105, 'view.motor_speed', 105),
     ('view.ui.motor_steps.setValue', 73, 'view.motor_steps', 73),
     ('view.ui.motor_steps.setValue', -10, 'view.motor_steps', 2),
     ('view.ui.n_frames.setValue', 0, 'view.n_frames', 1),
     ('view.ui.n_frames.setValue', -10, 'view.n_frames', 1),
     ('view.ui.n_frames.setValue', 29, 'view.n_frames', 29),
     ('view.ui.frames2avg.setValue', 0, 'view.frames_to_avg', 1),
     ('view.ui.frames2avg.setValue', 25, 'view.frames_to_avg', 25),
     ('view.ui.radon_idx.setValue', -10, 'view.radon_idx', 0),
     ('view.ui.radon_idx.setValue', 1010, 'view.radon_idx', 1010),
     ])
def test_update_func(Viewer, func, set, attr, expected):
    _, view, qtbot = Viewer
    eval(func + '(set)')
    QtTest.QTest.qWait(int(0.5*100))
    assert eval(attr) == expected


@pytest.mark.parametrize(
    'ui_attr, set, app_attr, expected',
    [("view.ui.accum_shots", False, 'view.accum_shots', True),
     ('view.ui.accum_shots', True, 'view.accum_shots', False),
     ('view.ui.live_recon', False, 'view.live_recon', True),
     ('view.ui.live_recon', True, 'view.live_recon', False),
     ('view.ui.toggle_hist', True, 'view.toggle_hist', False),
     ('view.ui.toggle_hist', False, 'view.toggle_hist', True),
     ])
def test_radios(Viewer, ui_attr, set, app_attr, expected):
    _, view, qtbot = Viewer
    eval(ui_attr + '.setChecked(set)')
    qtbot.mouseClick(eval(ui_attr), QtCore.Qt.LeftButton, delay=20)
    assert eval(app_attr) == expected


@pytest.mark.parametrize(
    'val_min, val_max, diag1, diag2, expected',
    [(100, 50, True, True, 1),
     (200, 250, True, False, 50),
     (-200, 100, False, False, 100)])
def test_hist(Viewer, val_min, val_max, diag1, diag2, expected):
    _, view, qtbot = Viewer
    """
    ensure that min is lower than max
    """
    def handle_dialog():
        mbox = QApplication.activeWindow()
        ok_but = mbox.button(QMessageBox.Ok)
        qtbot.mouseClick(ok_but, QtCore.Qt.LeftButton, delay=20)
    # preset the initial values
    view.ui.min_hist.setValue(0)
    view.ui.max_hist.setValue(200)

    view.ui.min_hist.setValue(val_min)
    if diag1:
        QtCore.QTimer.singleShot(100, handle_dialog)

    view.ui.max_hist.setValue(val_max)
    if diag2:
        QtCore.QTimer.singleShot(100, handle_dialog)

    diff = view.max_hist - view.min_hist
    assert diff == expected


# def test_check_hist(app):
#     app._check_hist_vals()
#     assert 1


# def test_camera_port_update(app):
#     app.ui.port.setValue(2)
#     assert app.camera_port == 2


# def test_camera_port_find(app):
#     '''testing automatic identification of the cameras connected'''
#     pass


# # def test_folder_path(qtbot, tmpdir, app):
# #     '''test folder diolog window
# #     dont know how to refer to the dialog instance, perhaps
# #        cannot use static func
# #     '''
# #     tmpdir.join('test_folder\\').ensure()
# #     # diag = qtbot.mouseClick(app.ui.folder_btn, QtCore.Qt.LeftButton)
# #     print(vars(diag))
# #     # print(this.directory)
# #     # print(diag)
# #     qtbot.directoryEntered(tmpdir)
# #     qtbot.keyClicks(app.folderComboBox, 'test_folder')
# #     assert 0


# def test_select_folder(app):
#     '''do not know how to test as above'''
#     pass
