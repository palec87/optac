import napari
import numpy as np
from magicgui import magicgui, widgets


@magicgui(
        call_button=False,
        result={'enabled':False},
        auto_call=True,
        
)
def my_ui(num1: float=5, num2: float=2, result: float=8):
    my_ui.result.value = num1 + num2


@my_ui.num1.changed.connect
@my_ui.num2.changed.connect
def on_change():
    my_ui.result.value = my_ui.num1.value + my_ui.num2.value

my_ui.show(run=True)