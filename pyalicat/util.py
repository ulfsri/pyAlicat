"""Utilities for manipulating data from Alicat devices.

Author: Grayson Bellamy
Date: 2024-01-07
"""

import glob
from comm import SerialDevice
from device import all_subclasses, Device
from trio import run
import trio
import re
from typing import Any


def gas_correction():
    """Calculates the gas correction factor for the Alicat device.

    Returns:
    -------
    float
        The gas correction factor.
    """
    pass


async def find_devices():
    """Finds all connected Alicat devices.

    Find all available serial ports using the `ls` command
    Iterate through all possible baud rates

    If there is an alicat device on that port (copy code form new_device that checks )
        get what device is
    add to dictionary with port name and type of device on port (if no device, don't add to dictionary)
    return dictionary


    Returns:
    -------
    list
        A list of all connected Alicat devices.
    """
    # Get the list of available serial ports
    result = glob.glob("/dev/ttyUSB*")

    # Iterate through the output and check for Alicat devices
    devices = {}
    for port in result:
        # Check if the port is an Alicat device
        dev = await is_alicat_device(port)
        if dev:
            devices.update({port: dev[1]})
    return devices


async def is_alicat_device(port, id: str = "A", **kwargs: Any):
    """Check if the given port is an Alicat device.

    Parameters:
    ----------
    port : str
        The name of the serial port.

    Returns:
    -------
    bool
        True if the port is an Alicat device, False otherwise.
    """
    if port.startswith("/dev/"):
        device = SerialDevice(port, **kwargs)
    dev_info = await device._write_readall(f"{id}??M*")
    if not dev_info:
        return False
    INFO_KEYS = [
        "manufacturer",
        "website",
        "phone",
        "website",
        "model",
        "serial",
        "manufactured",
        "calibrated",
        "calibrated_by",
        "software",
    ]
    dev_info = dict(
        zip(INFO_KEYS, [i[re.search(r"M\d\d", i).end() + 1 :] for i in dev_info])
    )

    for cls in all_subclasses(Device):
        if cls.is_model(dev_info.get("model", "")):
            return (True, cls.__name__)
    return False


def get_device_type(port):
    """Get the device type for the given port.

    Parameters:
    ----------
    port : str
        The name of the serial port.

    Returns:
    -------
    dict
        A dictionary containing the port name and the type of device on the port.
    """
    # Implement the logic to get the device information
    # You can use any method that suits your needs
    pass
