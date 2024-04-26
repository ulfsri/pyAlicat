"""DAQ Class for managing Alicat devices. Accessible to external API and internal logging module.

Author: Grayson Bellamy
Date: 2024-01-07
"""

import device
from trio import run


class DAQ:
    """Class for managing Alicat devices. Accessible to external API and internal logging module. Wraps and allows communication with inidividual or all devices through wrapper class."""

    def __init__(self) -> None:
        """Initializes the DAQ.

        Args:

        Parameters
        ----------
        config : dict
            The configuration dictionary. {Name : port}
        """
        global dev_list
        dev_list = {}
        pass

    async def _add_device(self, port: str, name: str) -> None:
        """Creates and initializes the devices.

        Args:
            id : str
            The ID of the device.

        Returns:
            str
            The data from the device.
        """
        dev = await device.new_device(port)
        dev_list.update({name: dev})
        pass

    async def _remove_device(self) -> None:
        pass

    async def get(self, val: list, id: list = "") -> str:
        """Gets the data from the device.

        If id not specified, returns data from all devices.

        Parameters
        ----------
        id : str
            The ID of the device.
        val (str): The value to get from the device.

        Returns:
        -------
        str
            The data from the device.
        """
        ret_dict = {}
        if isinstance(val, str):
            val = val.split()
        if not id:
            for dev in dev_list:
                ret_dict.update({dev: await dev_list[dev].get(val)})
        if isinstance(id, str):
            id = id.split()
        for i in id:
            ret_dict.update({i: await dev_list[i].get(val)})
        return ret_dict

    async def set(self, id: str, command: str) -> None:
        """Sets the data of the device.

        Parameters
        ----------
        id : str
            The ID of the device.
        command : str
            The command to send to the device.
        """
        pass


class DAQLogging:
    """Class for logging the data from Alicat devices. Creates and saves file to disk with given acquisition rate. Only used for standalone logging. Use external API for use as plugin."""

    def __init__(self, config: dict) -> None:
        """Initializes the Logging module. Creates and saves file to disk with given acquisition rate.

        Parameters
        ----------
        config : dict
            The configuration dictionary. {Name : port}
        """
        pass
