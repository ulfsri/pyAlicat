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

        TODO: Pass dictionary of names and addresses to initialize devices. Same async issue.

        """
        global dev_list
        dev_list = {}

        """
        for name in devs:
            dev = device.new_device(devs[name])
            dev_list.update({name: dev})
        """
        return

    @classmethod
    async def init(cls, devs: dict[str, str]) -> "DAQ":
        """Initializes the DAQ.

        Args:
            devs (dict[str, str]): The dictionary of devices to add. Name:Port

        Returns:
            DAQ: The DAQ object.
        """
        daq = cls()
        await daq.add_device(devs)
        return daq

    async def add_device(self, devs: dict[str, str]) -> None:
        """Creates and initializes the devices.

        Args:
            devs (dict[str, str]): The dictionary of devices to add. Name:Port
        """
        if isinstance(devs, str):
            devs = devs.split()
            # This works if the string is the format "Name Port"
            devs = {devs[0]: devs[1]}
        for name in devs:
            dev = await device.Device.new_device(devs[name])
            dev_list.update({name: dev})
        return

    async def remove_device(self, name: list[str]) -> None:
        """Creates and initializes the devices.

        Args:
            name (list[str]): The list of devices to remove.
        """
        for n in name:
            await dev_list[n]._device.close()
            del dev_list[n]
        return

    async def dev_list(self) -> dict[str, device.Device]:
        """Displays the list of devices.

        Returns:
            dict[str, device.Device]: The list of devices and their objects.
        """
        return dev_list

    async def get(
        self, val: list[str] = "", id: list[str] = ""
    ) -> dict[str, dict[str | float]]:
        """Gets the data from the device.

        If id not specified, returns data from all devices.

        Args:
           val (list): The values to get from the device.
           id (list): The IDs of the devices to read from. If not specified, returns data from all devices.

        Returns:
            dict: The dictionary of devices with the data for each value.
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

    async def set(self, command: dict[str, str | float], id: str = "") -> None:
        """Sets the data of the device.

        Args:
           command (dict): The commands and their relevant parameters to send to the device.
           id (list): The IDs of the devices to read from. If not specified, returns data from all devices.

        Returns:
            dict: The dictionary of devices with the data for each value.
        """
        ret_dict = {}
        if isinstance(command, str):
            command = command.split()
        if not id:
            for dev in dev_list:
                ret_dict.update({dev: await dev_list[dev].set(command)})
        if isinstance(id, str):
            id = id.split()
        for i in id:
            ret_dict.update({i: await dev_list[i].set(command)})
        return ret_dict


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
