"""
DAQ Class for managing Alicat devices. Accessible to external API and internal logging module.

Author: Grayson Bellamy
Date: 2024-01-07
"""


class DAQ:
    """
    Class for managing Alicat devices. Accessible to external API and internal logging module. Wraps and allows communication with inidividual or all devices through wrapper class.
    """

    def __init__(self, config: dict) -> None:
        """
        Initializes the DAQ.

        Parameters
        ----------
        config : dict
            The configuration dictionary. {Name : port}
        """

        pass

    def _init_devices(self) -> None:
        """
        Creates and initializes the devices.
        """

        pass

    def get(self, id: str) -> str:
        """
        Gets the data from the device.

        Parameters
        ----------
        id : str
            The ID of the device.

        Returns
        -------
        str
            The data from the device.
        """

        pass

    def get_all(self) -> dict:
        """
        Gets the data from all devices.

        Returns
        -------
        dict
            The data from all devices.
        """

        pass

    def set(self, id: str, command: str) -> None:
        """
        Sets the data of the device.

        Parameters
        ----------
        id : str
            The ID of the device.
        command : str
            The command to send to the device.
        """

        pass


class DAQLogging:
    """
    Class for logging the data from Alicat devices. Creates and saves file to disk with given acquisition rate. Only used for standalone logging. Use external API for use as plugin.
    """

    def __init__(self, config: dict) -> None:
        """
        Initializes the Logging module. Creates and saves file to disk with given acquisition rate.

        Parameters
        ----------
        config : dict
            The configuration dictionary. {Name : port}
        """

        pass
