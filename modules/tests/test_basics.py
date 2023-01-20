#!/usr/bin/env python

'''Basic tests of the optac module'''

import pytest
from PyQt5 import QtCore
from main import main_GUI
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
    app, imageViewer = main_GUI()
    QtTest.QTest.qWait(int(0.5*100))
    qtbotbis = QtBot(app)
    QtTest.QTest.qWait(int(0.5*100))
    return app, imageViewer, qtbotbis


def test_init(Viewer):
    _, imageViewer, qtbot = Viewer
    assert not imageViewer.stop_request
    assert imageViewer.idle
    assert not imageViewer.motor_on
    assert not imageViewer.camera_on
    assert not imageViewer.opt_running


@pytest.mark.parametrize(
    'test_input,expected',
    [("imageViewer.ui.red_ch", 0), ('imageViewer.ui.green_ch', 1),
     ('imageViewer.ui.blue_ch', 2), ('imageViewer.ui.amp_ch', 3)])
def test_channel_funcs(Viewer, test_input, expected):
    _, imageViewer, qtbot = Viewer
    QtTest.QTest.qWait(int(0.5*100))
    qtbot.mouseClick(eval(test_input), QtCore.Qt.LeftButton)
    QtTest.QTest.qWait(int(0.5*100))
    assert imageViewer.channel == expected


# @pytest.mark.parametrize(
#     'test_input,expected',
#     [("app.ui.red_ch", 0), ('app.ui.green_ch', 1),
#      ('app.ui.blue_ch', 2), ('app.ui.amp_ch', 3)])
# def test_channel_funcs(qtbot, app, test_input, expected):
#     qtbot.mouseClick(eval(test_input), QtCore.Qt.LeftButton)
#     assert app.channel == expected


@pytest.mark.parametrize(
    'func, set, attr, expected',
    [('imageViewer.ui.angle.setValue', 123, 'imageViewer.angle', 123),
     ('imageViewer.ui.angle.setValue', -370, 'imageViewer.angle', -360),
     ('imageViewer.ui.angle.setValue', 400, 'imageViewer.angle', 400),
     ('imageViewer.ui.motor_speed.setValue', 432, 'imageViewer.motor_speed', 432),
     ('imageViewer.ui.motor_speed.setValue', -10, 'imageViewer.motor_speed', 100),
     ('imageViewer.ui.motor_speed.setValue', 105, 'imageViewer.motor_speed', 105),
     ('imageViewer.ui.motor_steps.setValue', 73, 'imageViewer.motor_steps', 73),
     ('imageViewer.ui.motor_steps.setValue', -10, 'imageViewer.motor_steps', 2),
     ('imageViewer.ui.frame_rate.setValue', -10, 'imageViewer.frame_rate', 1),
     ('imageViewer.ui.frame_rate.setValue', 30, 'imageViewer.frame_rate', 30),
     ('imageViewer.ui.n_frames.setValue', 0, 'imageViewer.n_frames', 1),
     ('imageViewer.ui.n_frames.setValue', -10, 'imageViewer.n_frames', 1),
     ('imageViewer.ui.n_frames.setValue', 29, 'imageViewer.n_frames', 29),
     ('imageViewer.ui.frames2avg.setValue', 0, 'imageViewer.frames_to_avg', 1),
     ('imageViewer.ui.frames2avg.setValue', 25, 'imageViewer.frames_to_avg', 25),
     ('imageViewer.ui.radon_idx.setValue', -10, 'imageViewer.radon_idx', 0),
     ('imageViewer.ui.radon_idx.setValue', 1010, 'imageViewer.radon_idx', 1010),
     ])
def test_update_func(Viewer, func, set, attr, expected):
    _, imageViewer, qtbot = Viewer
    eval(func + '(set)')
    QtTest.QTest.qWait(int(0.5*100))
    assert eval(attr) == expected


@pytest.mark.parametrize(
    'ui_attr, set, app_attr, expected',
    [("imageViewer.ui.accum_shots", False, 'imageViewer.accum_shots', True),
     ('imageViewer.ui.accum_shots', True, 'imageViewer.accum_shots', False),
     ('imageViewer.ui.live_recon', False, 'imageViewer.live_recon', True),
     ('imageViewer.ui.live_recon', True, 'imageViewer.live_recon', False),
     ('imageViewer.ui.toggle_hist', True, 'imageViewer.toggle_hist', False),
     ('imageViewer.ui.toggle_hist', False, 'imageViewer.toggle_hist', True),
     ])
def test_radios(Viewer, ui_attr, set, app_attr, expected):
    _, imageViewer, qtbot = Viewer
    eval(ui_attr + '.setChecked(set)')
    qtbot.mouseClick(eval(ui_attr), QtCore.Qt.LeftButton, delay=20)
    assert eval(app_attr) == expected


@pytest.mark.parametrize(
    'val_min, val_max, diag1, diag2, expected',
    [(100, 50, True, True, 1),
     (200, 250, True, False, 50),
     (-200, 100, False, False, 100)])
def test_hist(Viewer, val_min, val_max, diag1, diag2, expected):
    _, imageViewer, qtbot = Viewer
    '''ensure that min is lower than max'''
    def handle_dialog():
        mbox = QApplication.activeWindow()
        ok_but = mbox.button(QMessageBox.Ok)
        qtbot.mouseClick(ok_but, QtCore.Qt.LeftButton, delay=20)

    imageViewer.ui.min_hist.setValue(val_min)
    if diag1:
        QtCore.QTimer.singleShot(100, handle_dialog)

    imageViewer.ui.max_hist.setValue(val_max)
    if diag2:
        QtCore.QTimer.singleShot(100, handle_dialog)

    diff = imageViewer.max_hist - imageViewer.min_hist
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
