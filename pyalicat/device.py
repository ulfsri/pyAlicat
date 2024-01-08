import trio
from trio import run
from comm import CommDevice, SerialDevice
from typing import Any, Union
from abc import ABC
import re


statistics = {
    "Mass Flow": 5,
    "Mass Flow Setpt": 37,
    "Volu Flow": 4,
    "Volu Flow Setpt": 36,
    "Abs Press": 2,
    "Flow Temp": 3,
    "Rel Hum": 25,
}


async def new_device(port: str, id: str = "A", **kwargs: Any):
    """
    Creates a new device. Chooses appropriate device based on characteristics.
    """
    if port.startswith("/dev/"):
        device = SerialDevice(port, **kwargs)
    dev_info = await device._write_readall(id + "??M*")
    info_keys = [
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
        zip(info_keys, [i[re.search(r"M\d\d", i).end() + 1 :] for i in dev_info])
    )
    for cls in all_subclasses(Device):
        if cls.is_model(dev_info["model"]):
            return cls(device, dev_info, id, **kwargs)
    raise ValueError(f"Unknown device model: {dev_info['model']}")


def all_subclasses(cls):
    return set(cls.__subclasses__()).union(
        [s for c in cls.__subclasses__() for s in all_subclasses(c)]
    )


class Device(ABC):
    """
    Generic device class.
    """

    def __init__(
        self, device: SerialDevice, dev_info: dict, id: str = "A", **kwargs: Any
    ) -> None:
        self._device = device
        self._id = id
        self._dev_info = dev_info
        self._df_format = None
        self._df_units = None

    async def get(self) -> str:
        """
        Gets the current value of the device.
        """
        if self._df_format is None:
            await self.get_df_format()
        ret = await self._device._write_readline(self._id)
        df = ret.split()
        for index in [idx for idx, s in enumerate(self._df_ret) if "decimal" in s]:
            df[index] = float(df[index])
        return dict(zip(self._df_format, df))

    async def get_df_format(self) -> str:
        """
        Gets the format of the current dataframe format of the device
        """
        resp = await self._device._write_readall(self._id + "??D*")
        splits = []
        for match in re.finditer(r"\s", resp[0]):
            splits.append(match.start())
        df_table = [
            [k[i + 1 : j] for i, j in zip(splits, splits[1:] + [None])] for k in resp
        ]
        df_format = [
            i[[idx for idx, s in enumerate(df_table[0]) if "NAME" in s][0]].strip()
            for i in df_table[1:-1]
        ]
        df_ret = [
            i[[idx for idx, s in enumerate(df_table[0]) if "TYPE" in s][0]].strip()
            for i in df_table[1:-1]
        ]
        df_stand = [i for i in df_format if not (i.startswith("*"))]
        df_stand_ret = [i for i in df_ret[: len(df_stand)]]
        self._df_format = df_format
        self._df_ret = df_ret
        return [df_stand, df_stand_ret]

    async def get_units(self, measurement: dict) -> dict:
        """
        Gets the units of the current dataframe format of the device
        """
        units = [None] * len(measurement)
        for index in [idx for idx, s in enumerate(self._df_ret) if "decimal" in s]:
            ret = await self._device._write_readline(
                self._id + "DCU " + str(statistics[list(measurement.keys())[index]])
            )
            units[index] = ret.split()[2]
        self._df_units = units
        return units


class FlowMeter(Device):
    """
    A class used to represent a flow meter.
    """

    @classmethod
    def is_model(cls, model: str) -> bool:
        """Checks if the flow meter is of a certain model.

        Args:
            model (str): Model of flow meter.

        Returns:
            bool: True if model matches.
        """
        cls._models = ["M-", "MS-", "MQ-", "MW-"]
        return any([bool(re.search(i, model)) for i in cls._models])

    def __init__(
        self, device: SerialDevice, dev_info: dict, id: str = "A", **kwargs: Any
    ) -> None:
        """Connects to the flow device.

        Args:
            port (str): COM port/address of Alicat flow device.
            id (str, optional): Unit ID of Alicat flow device. Defaults to "A".
        """
        super().__init__(device, dev_info, id, **kwargs)


class FlowController(FlowMeter):
    """
    A class used to represent a flow controller. Extends flow meter.
    """

    @classmethod
    def is_model(cls, model: str) -> bool:
        """Checks if the flow meter is of a certain model.

        Args:
            model (str): Model of flow meter.

        Returns:
            bool: True if model matches.
        """
        cls._models = ["MC-", "MCS-", "MCQ-", "MCW-"]
        return any([bool(re.search(i, model)) for i in cls._models])

    def __init__(
        sself, device: SerialDevice, dev_info: dict, id: str = "A", **kwargs: Any
    ) -> None:
        """Connects to the flow controller.

        Args:
            port (str): COM port/address of Alicat flow controller.
            id (str, optional): Unit ID of Alicat flow controller. Defaults to "A".
        """
        super().__init__(device, dev_info, id, **kwargs)
