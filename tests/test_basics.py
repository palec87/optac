#!/usr/bin/env python

'''Basic tests of the optac module'''

import pytest
from PyQt5 import QtCore, QtWidgets
from optac_main import Gui
import time

__author__ = 'David Palecek'
__credits__ = ['Teresa M Correia', 'Rui Guerra']
__license__ = 'GPL'


def divide(x, y):
    return x / y


def test_raises():
    with pytest.raises(ZeroDivisionError):
        divide(3, 0)


@pytest.fixture
def app(qtbot):
    test_app = Gui('lif.json')
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


# @pytest.mark.parametrize(
#     'test_input,expected',
#     [("app.ui.red_ch", 0), ('app.ui.green_ch', 1),
#      ('app.ui.blue_ch', 2), ('app.ui.amp_ch', 3)])
# def test_channel_funcs(qtbot, app, test_input, expected):
#     qtbot.mouseClick(eval(test_input), QtCore.Qt.LeftButton)
#     assert app.channel == expected


# @pytest.mark.parametrize(
#     'func, set, attr, expected',
#     [('app.ui.angle.setValue', 123, 'app.angle', 123),
#      ('app.ui.angle.setValue', -370, 'app.angle', -360),
#      ('app.ui.angle.setValue', 400, 'app.angle', 400),
#      ('app.ui.motor_speed.setValue', 432, 'app.motor_speed', 432),
#      ('app.ui.motor_speed.setValue', -10, 'app.motor_speed', 100),
#      ('app.ui.motor_speed.setValue', 105, 'app.motor_speed', 105),
#      ('app.ui.motor_steps.setValue', 73, 'app.motor_steps', 73),
#      ('app.ui.motor_steps.setValue', -10, 'app.motor_steps', 2),
#      ('app.ui.frame_rate.setValue', -10, 'app.frame_rate', 1),
#      ('app.ui.frame_rate.setValue', 30, 'app.frame_rate', 30),
#      ('app.ui.n_frames.setValue', 0, 'app.n_frames', 1),
#      ('app.ui.n_frames.setValue', -10, 'app.n_frames', 1),
#      ('app.ui.n_frames.setValue', 29, 'app.n_frames', 29),
#      ('app.ui.frames2avg.setValue', 0, 'app.frames_to_avg', 1),
#      ('app.ui.frames2avg.setValue', 25, 'app.frames_to_avg', 25),
#      ('app.ui.recon_px.setValue', -10, 'app.radon_idx', 0),
#      ('app.ui.recon_px.setValue', 1010, 'app.radon_idx', 1010),
#      ])
# def test_update_func(app, func, set, attr, expected):
#     eval(func + '(set)')
#     time.sleep(0.1)
#     assert eval(attr) == expected


# @pytest.mark.parametrize(
#     'ui_attr, set, app_attr, expected',
#     [("app.ui.accum_shots", False, 'app.accum_shots', True),
#      ('app.ui.accum_shots', True, 'app.accum_shots', False),
#      ('app.ui.live_reconstruct', False, 'app.live_recon', True),
#      ('app.ui.live_reconstruct', True, 'app.live_recon', False),
#      ('app.ui.toggle_hist', True, 'app.toggle_hist', False),
#      ('app.ui.toggle_hist', False, 'app.toggle_hist', True),
#      ])
# def test_radios(qtbot, app, ui_attr, set, app_attr, expected):
#     eval(ui_attr + '.setChecked(set)')
#     qtbot.mouseClick(eval(ui_attr), QtCore.Qt.LeftButton, delay=20)
#     assert eval(app_attr) == expected


# @pytest.mark.parametrize(
#     'val_min, val_max, diag, expected',
#     [(100, 50, True, 1), (200, 250, False, 50), (-200, 100, False, 100)])
# def test_hist(qtbot, app, val_min, val_max, diag, expected):
#     '''ensure that min is lower than max'''
#     def handle_dialog():
#         mbox = QtWidgets.QApplication.activeWindow()
#         ok_but = mbox.button(QtWidgets.QMessageBox.Ok)
#         qtbot.mouseClick(ok_but, QtCore.Qt.LeftButton, delay=20)

#     app.ui.min_hist.setValue(val_min)
#     if diag:
#         QtCore.QTimer.singleShot(100, handle_dialog)
#     app.ui.max_hist.setValue(val_max)
#     diff = app.max_hist - app.min_hist
#     assert diff == expected


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
