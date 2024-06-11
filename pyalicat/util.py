"""Utilities for manipulating data from Alicat devices.

Author: Grayson Bellamy
Date: 2024-01-07
"""

import glob
import re
import warnings
from threading import Thread
from typing import Any

from anyio import create_task_group, run

from pyalicat import daq
from pyalicat.comm import SerialDevice
from pyalicat.device import Device, all_subclasses


def gas_correction():
    """Calculates the gas correction factor for the Alicat device.

    Returns:
        float: The gas correction factor.
    """
    pass


async def update_dict_dev(devices, port) -> dict[str, dict[str, str | float]]:
    """Updates the dictionary with the new values.

    Args:
        devices (dict): The dictionary of devices.
        port (str): The name of the serial port.

    Returns:
        dict: The dictionary of devices with the updated values.
    """
    dev = await is_alicat_device(port)
    if dev:
        devices.update({port: dev[1]})
    return devices


async def find_devices() -> dict[str, Device]:
    """Finds all connected Alicat devices.

    Find all available serial ports using the `ls` command
    Iterate through all possible baud rates

    If there is an alicat device on that port (copy code form new_device that checks )
        get what device is
    add to dictionary with port name and type of device on port (if no device, don't add to dictionary)
    return dictionary


    Returns:
        dict[str, Omron]: A dictionary of all connected Alicat devices. Port:Object
    """
    # Get the list of available serial ports
    result = glob.glob("/dev/ttyUSB*")

    # Iterate through the output and check for Alicat devices
    devices = {}
    async with create_task_group() as g:
        for port in result:
            g.start_soon(update_dict_dev, devices, port)
    return devices


async def is_alicat_device(
    port: str, id: str = "A", **kwargs: Any
) -> bool | tuple[bool, Device]:
    """Check if the given port is an Alicat device.

    Parameters:
        port (str): The name of the serial port.
        id (str): The device ID. Default is "A".
        **kwargs: Additional keyword arguments.

    Returns:
        bool: True if the port is an Alicat device, False otherwise.
        Device: The device object if the port is an Alicat device.
    """
    try:
        return (True, await Device.new_device(port, **kwargs))
    except ValueError:
        return False


def get_device_type(port):
    """Get the device type for the given port.

    Parameters:
        port (str): The name of the serial port.

    Returns:
        dict[str, str]: A dictionary containing the port name and the type of device on the port.
    """
    # Implement the logic to get the device information
    # You can use any method that suits your needs
    pass


async def diagnose():
    """Run various functions to ensure the device is functioning properly."""
    get_code1 = "Mass_Flow"
    get_code2 = "Abs_Press"
    set_code = "Setpt"
    devs = await find_devices()
    print(f"Devices: {devs}")
    Daq = await daq.DAQ.init({"A": list(devs.keys())[0]})
    print(f"Initiate DAQ with A: {await Daq.dev_list()}")
    await Daq.add_device({"B": list(devs.keys())[1]})
    print(f"Add device B: {await Daq.dev_list()}")
    print(f"Get data (list): {await Daq.get([get_code1, get_code2])}")
    temp = await Daq.get(set_code, "B")
    print(f"Get Data (id, no list): Temp = {temp}")
    await Daq.remove_device(["A"])
    print(f"Remove device A: {await Daq.dev_list()}")
    print(f"Set data (with id).")
    await Daq.set({set_code: (temp["B"][set_code] + 1)}, "B")
    print(f"Get data: {await Daq.get([set_code])}")
    print(f"Set data (without id).")
    await Daq.set({set_code: temp["B"][set_code]})
    print(f"Get data: {await Daq.get([set_code])}")
    await Daq.add_device({"C": list(devs.keys())[0]})
    print(f"Add device C: {await Daq.dev_list()}")
