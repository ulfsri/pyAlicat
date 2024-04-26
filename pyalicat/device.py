from typing import Any

import json
import re
from abc import ABC

from comm import SerialDevice
import trio
from trio import run

# from .device import Device

with open("codes.json") as f:
    codes = json.load(f)
statistics = codes["statistics"][0]
units = codes["units"][0]
gases = codes["gases"][0]


async def new_device(port: str, id: str = "A", **kwargs: Any):
    """Creates a new device. Chooses appropriate device based on characteristics.

    Args:
        port (str): The port the device is connected to.
        id (str): The id of the device. Default is "A".
        **kwargs: Any

    Returns:
        Device: The new device.
    """
    if port.startswith("/dev/"):
        device = SerialDevice(port, **kwargs)
    dev_info = await device._write_readall(f"{id}??M*")
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
        if cls.is_model(dev_info["model"]):
            return cls(device, dev_info, id, **kwargs)
    raise ValueError(f"Unknown device model: {dev_info['model']}")


def all_subclasses(cls) -> set:
    """Returns all subclasses of a class.

    Args:
        cls (class): The class to get the subclasses of.

    Returns:
        set: The set of subclasses.
    """
    return set(cls.__subclasses__()).union(
        [s for c in cls.__subclasses__() for s in all_subclasses(c)]
    )


class Device(ABC):
    """Generic device class."""

    def __init__(
        self, device: SerialDevice, dev_info: dict, id: str = "A", **kwargs: Any
    ) -> None:
        """Initialize the Device object.

        Args:
            device (SerialDevice): The SerialDevice object.
            dev_info (dict): The device information dictionary.
            id (str, optional): The device ID. Defaults to "A".
            **kwargs: Additional keyword arguments.
        """
        self._device = device
        self._id = id
        self._dev_info = dev_info
        self._df_units = None
        self._df_format = None
        self._vers = float(
            re.compile(r"[0-9]+v[0-9]+")
            .findall(dev_info["software"])[0]
            .replace("v", ".")
        )

    async def poll(self) -> dict:
        """Gets the current measurements of the device in defined data frame format.

        Returns:
            dict: The current measurements of the device from defined data frame format.
        """
        # Gets the format of the dataframe if it is not already known
        if self._df_format is None:
            await self.get_df_format()
        ret = await self._device._write_readline(self._id)
        df = ret.split()
        for index in [idx for idx, s in enumerate(self._df_ret) if "decimal" in s]:
            df[index] = float(df[index])
        return dict(zip(self._df_format, df))

    async def request(self, stats: list = [], time: int = 1) -> dict:
        """Gets requested measurements averaged over specified time.

        Args:
            stats (list): Names of the statistics to get. Maximum of 13 statistics in one call.
            time (int): The time to average over in milliseconds. Default is 1.

        Returns:
            dict: The requested statistics.
        """
        if len(stats) > 13:
            print("Too many statistics requested, discarding excess")
            stats = stats[:13]
        ret = await self._device._write_readline(
            # Add 150 ms to the given time
            f"{self._id}DV {time} {' '.join(str(statistics[stat]) for stat in stats)}"  # add a parameter for time out here
        )
        ret = ret.split()
        for idx in range(len(ret)):
            try:
                ret[idx] = float(ret[idx])
            except ValueError:
                pass
        return dict(zip(stats, ret))

    async def start_stream(self) -> None:
        """Starts streaming data from device."""
        await self._device._write(f"{self._id}@ @")
        return

    async def stop_stream(self, new_id: str = None) -> None:
        """Stops streaming data from device.

        Args:
            new_id (str): New device ID if desired. Will default to current ID if not given.
        """
        if new_id is None:
            new_id = self._id
        await self._device._write(f"@@ {new_id}")
        self.id = new_id
        return

    async def gas(self, gas: str = "", save: bool = "") -> dict:
        """Gets/Sets the gas of the device.

        Note:
            Devices with firmware versions 10.05 or greater should use this method

        Args:
            gas (str): Name of the gas to set on the device.
            save (bool): If true, will apply this gas on powerup.

        Returns:
            dict: Reports the gas and its code and names.
        """
        LABELS = ["Unit ID", "Gas Code", "Gas", "Gas Long"]
        if gas and self._vers and self._vers < 10.05:
            print("Error: Version earlier than 10v05, running Set Gas")
            return await self.set_gas(gas)
        gas = gases.get(gas, "")
        if not gas:
            save = ""
        if isinstance(save, bool):
            save = "1" if save else "0"
        ret = await self._device._write_readline(f"{self._id}GS {gas} {save}")
        return dict(zip(LABELS, ret.split()))

    async def _set_gas(self, gas: str = "") -> dict:
        """Sets the gas of the device.

        Note:
            Devices with firmware versions lower than 10v05 should use this method

        Args:
            gas (str): Name of the gas to set on the device.

        Returns:
            dict: Dataframe with new gas.
        """
        if self._vers and self._vers >= 10.05:
            print("Error: Version later than 10v05, running Active Gas")
            return await self.gas(gas)
        if self._df_format is None:
            await self.get_df_format()
        gas = gases.get(gas, "")
        ret = await self._device._write_readline(f"{self._id}G {gas}")
        df = ret.split()
        for index in [idx for idx, s in enumerate(self._df_ret) if "decimal" in s]:
            df[index] = float(df[index])
        return dict(zip(self._df_format, df))

    async def gas_list(self) -> dict:
        """Gets the list of available gases for the device.

        Returns:
            dict: List of all gas codes and their names.
        """
        ret = {}
        resp = await self._device._write_readall(f"{self._id}??G*")
        for gas in resp:
            gas = gas.split()
            ret[gas[1]] = gas[2]
        return ret

    async def tare_abs_P(self) -> dict:
        """Tares the absolute pressure of the device, zeros out the absolute pressure reference point.

        Should only be used when no flow and line is not pressurized.

        Note:
            **Untested.**

        Returns:
            dict: Dataframe with zero absolute pressure
        """
        # Gets the format of the dataframe if it is not already known
        if self._df_format is None:
            await self.get_df_format()
        ret = await self._device._write_readline(f"{self._id}PC")
        df = ret.split()
        for index in [idx for idx, s in enumerate(self._df_ret) if "decimal" in s]:
            df[index] = float(df[index])
        return dict(zip(self._df_format, df))

    async def tare_flow(self) -> dict:
        """Creates a no-flow reference point.

        Should only be used when no flow and at operation pressure.

        Note:
            **Untested.**

        Returns:
            dict: Dataframe with zero flow.
        """
        # Gets the format of the dataframe if it is not already known
        if self._df_format is None:
            await self.get_df_format()
        ret = await self._device._write_readline(f"{self._id}V")
        df = ret.split()
        for index in [idx for idx, s in enumerate(self._df_ret) if "decimal" in s]:
            df[index] = float(df[index])
        return dict(zip(self._df_format, df))

    async def tare_gauge_P(self) -> dict:
        """Tares the gauge pressure of the device or differential pressure reference point.

        Should only be used when no flow and open to atmosphere.

        Note:
            **Untested.**

        Returns:
            dict: Dataframe with zero guage pressure.
        """
        # Gets the format of the dataframe if it is not already known
        if self._df_format is None:
            await self.get_df_format()
        ret = await self._device._write_readline(f"{self._id}P")
        df = ret.split()
        for index in [idx for idx, s in enumerate(self._df_ret) if "decimal" in s]:
            df[index] = float(df[index])
        return dict(zip(self._df_format, df))

    async def auto_tare(self, enable: bool = "", delay: float = "") -> dict:
        """Gets/Sets if the controller auto tares.

        Note:
            **Untested: Sets if the controller auto tares.**

        Args:
            enable (bool): Enable or disable auto tare
            delay (float): Amount of time in seconds waited until tare begins 0.1 to 25.5

        Returns:
            dict: If tare is active or not and delay length in seconds
        """
        if self._vers and self._vers < 10.05:
            print("Error: Version earlier than 10v05")
            return
        LABELS = ["Unit ID", "Auto-tare", "Delay (s)"]
        if isinstance(enable, bool):
            enable = "1" if enable else "0"
        ret = await self._device._write_readline(f"{self._id}ZCA {enable} {delay}")
        ret = ret.split()
        output_mapping = {"1": "Enabled", "0": "Disabled"}
        ret[1] = output_mapping.get(str(ret[1]), ret[1])
        ret[2] = float(ret[2])
        return dict(zip(LABELS, ret))

    async def configure_data_frame(self, format: int = "") -> dict:
        """Sets data frame's format.

        Args:
            format (int): What format to set the data frame to.

                - 0 for default: Values have 5 digits, setpoint and totalizer unsigned
                - 1 for setpoint and totalizer signed (+ or -)
                - 2 for signed setpoint and totalizer, number digits based on resolution

        Returns:
            dict: Data Frame in new format
        """
        if self._vers and self._vers < 6.00:
            print("Error: Version earlier than 6v00")
            return
        # Gets the format of the dataframe if it is not already known
        if self._df_format is None:
            await self.get_df_format()
        ret = await self._device._write_readline(f"{self._id}FDF {format}")
        df = ret.split()
        for index in [idx for idx, s in enumerate(self._df_ret) if "decimal" in s]:
            df[index] = float(df[index])
        return dict(zip(self._df_format, df))

    async def engineering_units(
        self,
        statistic_value: str = "",
        group: bool = "",
        unit: str = "",
        override: bool = "",
    ) -> dict:
        """Gets/Sets units for desired statistics.

        Note:
            **Setting is Nonfunctional**

        Args:
            statistic_value (str): Desired statistic to get/set unit for
            group (bool): If setting unit, sets to entire group statisitc is in
            unit (str): Sets unit for statistic
            override (bool): Overwrites any special rules for group changes.

                - 0 for not changing special rules
                - 1 for applying the new units to all statistics in the group.

        Returns:
            dict: Responds with unit
        """
        if self._vers and self._vers < 10.05:
            print("Error: Version earlier than 10v05")
            return
        LABELS = ["Unit ID", "Unit Code", "Unit Label"]
        if isinstance(group, bool):
            group = "1" if group else "0"
        if isinstance(override, bool):
            override = "1" if override else ""
        ret = await self._device._write_readline(
            f"{self._id}DCU {statistics[statistic_value]} {group} {units[unit]} {override}"
        )
        ret = ret.split()
        return dict(zip(LABELS, ret))

    async def flow_press_avg(
        self,
        stat_val: str = "",
        avg_time: int = "",
    ) -> dict:
        """Gets/Set the length of time a statistic is averaged over.

        Args:
            stat_val (str): Desired statistic to get avgerage/set time
            avg_time (int): Time in milliseconds over which averages taken. Ranges from 0 to 9999. If 0, the deivce updates every millisecond.

        Returns:
            dict: Responds value of queried average and avg time const
        """
        if self._vers and self._vers < 10.05:
            print("Error: Version earlier than 10v05")
            return
        LABELS = ["Unit ID", "Value", "Time Const"]
        if stat_val.upper() == "ALL":
            stat_val = 1
        else:
            statistics[stat_val]
        ret = await self._device._write_readline(f"{self._id}DCA {stat_val} {avg_time}")
        ret = ret.split()
        ret[1] = int(ret[1])
        return dict(zip(LABELS, ret))

    async def full_scale_val(self, stat_val: str = "", unit: str = "") -> dict:
        """Gets measurement range of given statistic.

        Args:
            stat_val (str): Desired statistic to get range
            unit (str): Units of range. Defaults if left blank.

        Returns:
            dict: Responds max value of statistic and units
        """
        if self._vers and self._vers < 6.00:
            print("Error: Version earlier than 6v00")
            return
        LABELS = ["Unit ID", "Max Value", "Unit Code", "Unit Label"]
        ret = await self._device._write_readline(
            f"{self._id}FPF {statistics[stat_val]} {units[unit]}"
        )
        ret = ret.split()
        ret[1] = float(ret[1])
        return dict(zip(LABELS, ret))

    async def power_up_tare(self, enable: bool = "") -> dict:
        """Gets/Sets if device tares on power-up.

        Args:
            enable (bool): If Enabled, 0.25 second after sensors stable. Close loop delay, valves stay closed

        Returns:
            dict: If tare is enabled
        """
        if self._vers and self._vers < 10.05:
            print("Error: Version earlier than 10v05")
            return
        LABELS = ["Unit ID", "Power-Up Tare"]
        if isinstance(enable, bool):
            enable = "1" if enable else "0"
        ret = await self._device._write_readline(f"{self._id}ZCP {enable}")
        ret = ret.split()
        output_mapping = {"1": "Enabled", "0": "Disabled"}
        ret[1] = output_mapping.get(str(ret[1]), ret[1])
        return dict(zip(LABELS, ret))

    async def data_frame(self) -> str:
        """Gets info about current data frame.

        Returns:
            str: table that outlines data frame format
        """
        if self._vers and self._vers < 6.00:
            print("Error: Version earlier than 6v00")
            return
        ret = await self._device._write_readall(f"{self._id}??D*")
        return ret

    async def stp_press(
        self, stp: str = "S", unit: str = "", press: float = ""
    ) -> dict:
        """Gets/Sets standard or normal pressure reference point.

        To get Normal pressure reference point, set stp to N.

        Args:
            stp (str): S for standard pressure, N for normal
            unit (str): Pressure units
            press (float): Numeric value of new desired pressure reference point

        Returns:
            dict: Current pressure reference point and units
        """
        if self._vers and self._vers < 10.05:
            print("Error: Version earlier than 10v05")
            return
        LABELS = ["Unit ID", "Curr Press Ref", "Unit Code", "Unit Label"]
        if stp.upper == "NTP":
            stp = "N"
        if stp.upper() != "N":
            stp = "S"
        ret = await self._device._write_readline(
            f"{self._id}DCFRP {stp.upper()} {str(units[unit])} {str(press)}"
        )
        ret = ret.split()
        ret[1] = float(ret[1])
        return dict(zip(LABELS, ret))

    async def stp_temp(self, stp: str = "S", unit: str = "", temp: float = "") -> dict:
        """Gets/Sets standard or normal temperature reference point.

        To get Normal temperature reference point, set stp to N.

        Args:
            stp (str): S for standard temperature, N for normal
            unit (str): Temperature units
            temp (float): Numeric value of new desired temperature reference point

        Returns:
            dict: Current temperature reference point and units
        """
        if self._vers and self._vers < 10.05:
            print("Error: Version earlier than 10v05")
            return
        LABELS = ["Unit ID", "Curr Temp Ref", "Unit Code", "Unit Label"]
        if stp.upper == "NTP":
            stp = "N"
        if stp.upper() != "N":
            stp = "S"
        ret = await self._device._write_readline(
            f"{self._id}DCFRT {stp.upper()} {str(units[unit])} {str(temp)}"
        )
        ret = ret.split()
        ret[1] = float(ret[1])
        return dict(zip(LABELS, ret))

    async def zero_band(self, zb: float = "") -> dict:
        """Gets/Sets the zero band of the device.

        Args:
            zb (float): % of full-scale readings process must exceed before device reports readings

                - 0 to 6.38 range
                - 0 to disable

        Returns:
            dict: Returns current zero band as percent of full scale
        """
        if self._vers and self._vers < 10.05:
            print("Error: Version earlier than 10v05")
            return
        LABELS = ["Unit ID", "Zero Band (%)"]
        if isinstance(zb, (float, int)):
            zb = f"0 {zb}"
        ret = await self._device._write_readline(f"{self._id}DCZ {zb}")
        ret = ret.split()
        ret.pop(1)
        ret[1] = float(ret[1])
        return dict(zip(LABELS, ret))

    async def analog_out_source(
        self, primary: str = "0", val: str = "", unit: str = ""
    ) -> dict:
        """Gets/Sets the source of the analog output.

        Args:
            primary (str): Primary or secondary analog output
            val (str): Statistic being tracked
                - 'MAX' to fix min possible output
                - 'MIN' to fix max possible output
                - Other for statistic
            unit (str): Desired unit. Optional

        Returns:
            dict: Statistic and units
        """
        if self._vers and self._vers < 10.05:
            print("Error: Version earlier than 10v05")
            return
        LABELS = ["Unit ID", "Value", "Unit Code", "Unit Label"]
        if primary.upper() == "SECONDARY" or primary.upper() == "2ND":
            primary = "1"
        if val != "":
            if val.upper() == "MAX":
                val = "0"
            elif val.upper() == "MIN":
                val = "1"
            else:
                val = str(statistics[val])
        ret = await self._device._write_readline(
            f"{self._id}ASOCV {primary} {val} {unit}"
        )
        ret = ret.split()
        if ret[1] == "0":
            ret[1] = "Max"
        elif ret[1] == "1":
            ret[1] = "Min"
        else:
            for stat in statistics:
                if str(statistics[stat]) == ret[1]:
                    ret[1] = stat  # This is not necessarily the correct code
                    break
        return dict(zip(LABELS, ret))

    async def baud(self, new_baud: int = "") -> dict:
        """Gets/Sets the baud rate of the device.

        Note:
            Ensure COM is connected.

        Args:
            new_baud (int): Set to one of the following:

                - 2400 4800, 9600, 19200, 38400, 57600, 115200

                After baud is changed, communication MUST be re-established.

        Returns:
            dict: Baud rate, either current or new
        """
        if self._vers and self._vers < 10.05:
            print("Error: Version earlier than 10v05")
            return
        LABELS = ["Unit ID", "Baud"]
        VALID_BAUD_RATES = [2400, 4800, 9600, 19200, 38400, 57600, 115200]
        if new_baud != "" and int(new_baud) not in VALID_BAUD_RATES:
            new_baud = ""
        ret = await self._device._write_readline(f"{self._id}NCB {new_baud}")
        ret = ret.split()
        ret[1] = int(ret[1])
        return dict(zip(LABELS, ret))

    async def blink(self, dur: int = "") -> dict:
        """Blinks the device. Gets the blinking state.

        Args:
           dur (int): Duration devices flashes.
            - 0 stops blinking.
            - -1 to flash indefinitely.

        Returns:
            dict: If the display is currently blinking
        """
        if self._vers and self._vers < 8.28:
            print("Error: Version earlier than 8v28")
            return
        LABELS = ["Unit ID", "Flashing?"]
        ret = await self._device._write_readline(f"{self._id}FFP {dur}")
        ret = ret.split()
        output_mapping = {"1": "Yes", "0": "No"}
        ret[1] = output_mapping.get(str(ret[1]), ret[1])
        return dict(zip(LABELS, ret))

    async def change_unit_id(self, new_id: str = "") -> None:
        """Sets the unit ID of the device.

        Note:
            **This changes the ID, but the device stops responding**.

        Args:
            new_id (str): New ID for the device. A-Z accepted
        """
        await self._device._write(f"{self._id}@ {new_id}")
        self._id = new_id
        return

    async def firmware_version(self) -> dict:
        """Gets the firmware version of the device.

        Returns:
            dict: Current firmware vesion and its date of creation
        """
        LABELS = ["Unit ID", "Vers", "Creation Date"]
        ret = await self._device._write_readline(f"{self._id}VE")
        ret = ret.split()
        ret[2] = " ".join(ret[2:])
        self._vers = float(ret[1][:-4].replace(".", "").replace("v", "."))
        return dict(zip(LABELS, ret))

    async def lock_display(self) -> dict:
        """Disables buttons on front of the device.

        Returns:
            dict: Data frame with lock status enabled
        """
        if self._df_format is None:
            await self.get_df_format()
        ret = await self._device._write_readline(f"{self._id}L")
        df = ret.split()
        for index in [idx for idx, s in enumerate(self._df_ret) if "decimal" in s]:
            df[index] = float(df[index])
        return dict(zip(self._df_format, df))

    async def manufacturing_info(self) -> list:
        """Gets info about device.

        Returns:
            dict: Info on device, model, serial number, manufacturing, calibration, software
        """
        ret = await self._device._write_readall(f"{self._id}??M*")
        return ret

    async def remote_tare(self, actions: list = []) -> dict:
        """Gets/Sets the remote tare value.

        Note:
            This usually only works on meters and gauges. Not all devices support this.

        Note:
            **Untested: Sets the remote tare effect.**

        Args:
            actions (list): Actions to perform

        Returns:
            dict: Total value of active actions
        """
        if self._vers and self._vers < 10.05:
            print("Error: Version earlier than 10v05")
            return
        LABELS = ["Unit ID", "Active Actions Total"]
        action_dict = {
            "Primary Press": 1,
            "Secondary Press": 2,
            "Flow": 4,
            "Reset Totalizer 1": 8,
            "Reset Totalizer 2": 16,
        }
        act_tot = sum([action_dict.get(act, 0) for act in actions])
        if not actions:
            act_tot = ""
        ret = await self._device._write_readline(f"{self._id}ASRCA {act_tot}")
        ret = ret.split()
        ret[1] = int(ret[1])
        return dict(zip(LABELS, ret))

    async def restore_factory_settings(self) -> str:
        """Restores factory settings of the device.

        Removes any calibrations.

        Note:
            **Untested.**

        Returns:
            Confirmation of restoration
        """
        if self._vers and self._vers < 7.00:
            print("Error: Version earlier than 7v00")
            return
        ret = await self._device._write_readline(f"{self._id}FACTORY RESTORE ALL")
        return ret

    async def user_data(self, slot: int = "", val: str = "") -> dict:
        """Gets/Sets user data in slot.

        Gets the user data from the string is slot.
        Sets the user data in slot to val.

        Args:
            slot (int): Slot number, 0 to 3
            val (str): 32-char ASCII string. Must be encoded.

        Returns:
            dict: Value in called slot (either new or read)
        """
        if self._vers and self._vers < 8.24:
            print("Error: Version earlier than 8v24")
            return
        if val == "":
            LABELS = ["Unit ID", "Curr. Value"]
        else:
            LABELS = ["Unit ID", "New Value"]
        ret = await self._device._write_readline(f"{self._id}UD {slot} {val}")
        ret = ret.split()
        return dict(zip(LABELS, ret))

    async def streaming_rate(self, interval: int = "") -> dict:
        """Gets/Sets the streaming rate of the device.

        Args:
            interval (int): Streaming rate in milliseconds between data frames

        Returns:
            dict: Interval of streaming rate
        """
        if self._vers and self._vers < 10.05:
            print("Error: Version earlier than 10v05")
            return
        LABELS = ["Unit ID", "Interval (ms)"]
        ret = await self._device._write_readline(f"{self._id}NCS {interval}")
        ret = ret.split()
        ret[1] = int(ret[1])
        return dict(zip(LABELS, ret))

    async def unlock_display(self) -> dict:
        """Enables buttons on front of the device.

        Returns:
            dict: Data frame with LCK disabled
        """
        # Gets the format of the dataframe if it is not already known
        if self._df_format is None:
            await self.get_df_format()
        ret = await self._device._write_readline(f"{self._id}U")
        df = ret.split()
        for index in [idx for idx, s in enumerate(self._df_ret) if "decimal" in s]:
            df[index] = float(df[index])
        return dict(zip(self._df_format, df))

    async def create_gas_mix(
        self, name: str = "", number: int = "", gas_dict: dict = {}
    ) -> dict:
        """Sets custom gas mixture.

        This only works with specific gas codes so far

        Note:
            **Untested**

        Args:
            name (str): Name of custom mixture
            number (int): 236 to 255. Gas is saved to this number
            gas_dict (dict): Gas name : Percentage of Mixture. Maximum of 5 gases. Percent is Molar
                            percent up to 2 decimals. Total percentages must sum to 100.00%

            gas[n]P (float): Molar percent up to 2 decimals. Total percentages must sum to 100.00%

                - n is the number (1 to 5) of the gas in the function call
            gas[n]N (str): Name of gas in mixture

                - n is the number (1 to 5) of the gas in the function call

        Returns:
            dict: Gas number of new mix and percentages and names of each constituent
        """
        if self._vers and self._vers < 5.00:
            print("Error: Version earlier than 5v00")
            return
        if len(gas_dict) > 5:
            print("Error: Too many input gases")
            return
        gas_string = ""
        for x in gas_dict:
            gas_string += f" {gas_dict[x]} {gases[x]}"

        LABELS = [
            "Unit ID",
            "Gas Num",
            "Gas1 Name",
            "Gas1 Perc",
            "Gas2 Name",
            "Gas2 Perc",
            "Gas3 Name",
            "Gas3 Perc",
            "Gas4 Name",
            "Gas4 Perc",
            "Gas5 Name",
            "Gas5 Perc",
        ]
        ret = await self._device._write_readline(
            f"{self._id}GM {name} {number}{gas_string}"
        )
        ret = ret.split()
        return dict(zip(LABELS, ret))

    async def delete_gas_mix(self, gasN: str = "") -> dict:
        """Deletes custom gas mixture.

        Note:
            **Nonfunctional**

        Args:
            gasN (str): Number of gas to delete

        Returns:
            dict: Deleted gas' number
        """
        if self._vers and self._vers < 5.00:
            print("Error: Version earlier than 5v00")
            return
        LABELS = ["Unit ID", "Deleted Gas Num"]
        ret = await self._device._write_readline(f"{self._id}GD {gasN}")
        ret = ret.split()
        return dict(zip(LABELS, ret))

    async def query_gas_mix(self, gasN: int = "") -> dict:
        """Gets percentages of gases in mixture.

        Args:
           gasN (int): Number of the custom gas to analyze

        Returns:
            dict: Gas numbers and their percentages in mixture
        """
        if self._vers and self._vers < 9.00:
            print("Error: Version earlier than 9v00")
            return
        LABELS = [
            "Unit ID",
            "Gas Num",
            "Gas1 Name",
            "Gas1 Perc",
            "Gas2 Name",
            "Gas2 Perc",
            "Gas3 Name",
            "Gas3 Perc",
            "Gas4 Name",
            "Gas4 Perc",
            "Gas5 Name",
            "Gas5 Perc",
        ]
        ret = await self._device._write_readall(f"{self._id}GC {gasN}")
        ret = ret[0].replace("=", " ").split()
        for i in range(len(ret)):
            if "Name" in LABELS[i]:
                ret[i] = next(
                    (code for code, value in gases.items() if value == int(ret[i])),
                    ret[i],
                )
        return dict(zip(LABELS, ret))

    async def config_totalizer(
        self,
        totalizer: int = 1,
        flow_stat_val: str = "",
        mode: int = "",
        limit_mode: int = "",
        num: int = "",
        dec: int = "",
    ) -> dict:
        """Enables/Disables and Configures totalizer.

        Args:
            totalizer (int): 1 or 2, which totalizer used
            flow_stat_val (str): Statistic to measure. Use -1 to not change statistic
            mode (int): Manages how to totalizer accumulates flow. -1 to 3

                - -1 = Do not change
                - 0 = add positive flow, ignore negative
                - 1 = add negative flow, ignore positive
                - 2 = add positive flow, subtract negative
                - 3 = add positive flow until flow stops, then reset to 0
            limit_mode (int): Manages what totalizer does when limit reached. -1 to 3

                - -1 = Do not change
                - 0 = Stop count and leave at max, does not set TOV error
                - 1 = Rest to 0, continue count, does not set TOV error
                - 2 = Stop count and leave at max, sets TOV error
                - 3 = Reset to 0, continue count, sets TOV error
            num (int): Value 7 to 10. How many digits in totalizer.
            dec (int): 0 to 9. How many digits after decimal.

        Returns:
            dict: Configuration of totalizer
        """
        if self._vers and self._vers < 10.00:
            print("Error: Version earlier than 10v00")
            return
        LABELS = [
            "Unit ID",
            "Totalizer",
            "Flow Stat Val",
            "Mode",
            "Limit Mode",
            "num Digits",
            "Dec Place",
        ]
        if flow_stat_val != "":
            flow_stat_val = statistics.get(flow_stat_val, -1)
        ret = await self._device._write_readline(
            f"{self._id}TC {totalizer} {flow_stat_val} {mode} {limit_mode} {num} {dec}"
        )
        ret = ret.split()
        return dict(zip(LABELS, ret))  # Need to convert codes to text

    async def reset_totalizer(self, totalizer: int = 1) -> dict:
        """Returns totalizer count to zero and restarts timer.

        Note:
            **Untested.**

        Args:
            totalizer (int): Which totalizer to reset: 1 or 2

        Returns:
            dict: Dataframe with totalizer set to zero.
        """
        if self._vers and self._vers < 8.00:
            print("Error: Version earlier than 8v00")
            return
        # Gets the format of the dataframe if it is not already known
        if self._df_format is None:
            await self.get_df_format()
        ret = await self._device._write_readline(f"{self._id}T {totalizer}")
        df = ret.split()
        for index in [idx for idx, s in enumerate(self._df_ret) if "decimal" in s]:
            df[index] = float(df[index])
        return dict(zip(self._df_format, df))

    async def reset_totalizer_peak(self, totalizer: int = 1) -> dict:
        """Resets peak flow rate that has been measured since last reset.

        Note:
            **Untested.**

        Args:
            totalizer (int): Which totalizer to reset: 1 or 2

        Returns:
            dict: Data frame
        """
        if self._vers and self._vers < 8.00:
            print("Error: Version earlier than 8v00")
            return
        # Gets the format of the dataframe if it is not already known
        if self._df_format is None:
            await self.get_df_format()
        ret = await self._device._write_readline(f"{self._id}TP {totalizer}")
        df = ret.split()
        for index in [idx for idx, s in enumerate(self._df_ret) if "decimal" in s]:
            df[index] = float(df[index])
        return dict(zip(self._df_format, df))

    async def save_totalizer(self, enable: bool = "") -> dict:
        """Enables/disables saving totalizer values.

        If enabled, restore last saved totalizer on power-up.

        Args:
           enable (bool): Whether to enable or disable saving totalizer values on startup

        Returns:
            dict: Says if totalizer is enabled or disabled
        """
        if self._vers and self._vers < 10.05:
            print("Error: Version earlier than 10v05")
            return
        LABELS = ["Unit ID", "Saving"]
        if isinstance(enable, bool):
            enable = "1" if enable else "0"
        ret = await self._device._write_readline(f"{self._id}TCR {enable}")
        ret = ret.split()
        output_mapping = {"1": "Enabled", "0": "Disabled"}
        ret[1] = output_mapping.get(str(ret[1]), ret[1])
        return dict(zip(LABELS, ret))  # Need to convert codes to text

    async def get_df_format(self) -> list:
        """Gets the format of the current dataframe format of the device.

        Returns:
            list: Dataframe format
        """
        resp = await self._device._write_readall(f"{self._id}??D*")
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
        """Gets the units of the current dataframe format of the device.

        Args:
            measurement (dict): Dictionary of statistics

        Returns:
            list: Units of statistics in measurement
        """
        units = [None] * len(measurement)
        for index in [idx for idx, s in enumerate(self._df_ret) if "decimal" in s]:
            ret = await self._device._write_readline(
                f"{self._id}DCU {statistics[list(measurement.keys())[index]]}"
            )
            units[index] = ret.split()[2]
        self._df_units = units
        return units

    async def get(self, measurements: list = ["@"]) -> dict:
        """Gets the value of a measurement from the device.

        Args:
            measurements (list): List of measurements to get

        Returns:
            dict: Dictionary of measurements and their values
        """
        resp = {}
        flag = 0
        reqs = []
        if isinstance(measurements, str):
            measurements = measurements.split()
        # Request
        for meas in measurements:
            if meas in statistics:
                reqs.append(meas)
            elif meas.upper() == "GAS":
                resp.update(await self.gas())
            elif flag == 0:
                resp.update(await self.poll())
                flag = 1
        i = 0
        while i * 13 < len(reqs):
            resp.update(await self.request(reqs[13 * i : 13 + 13 * i]))
            i += 1
        return resp

    async def set(self, comm: dict) -> dict:
        """Sets the values of measurements for the device.

        Args:
            comm (dict): Dictionary with command to set as key, parameters as values. Use a list for multiple parameters

        Returns:
            dict: response of setting function
        """
        resp = {}
        for meas in list(comm.keys()):
            upper_meas = str(meas).upper()
            # Set gas - Param1 = gas: str = "", Param2 = save: bool = ""
            if upper_meas == "GAS":
                resp.update(await self.gas(str(comm[meas][0]), str(comm[meas][1])))
        return resp


class FlowMeter(Device):
    """A class used to represent a flow meter."""

    @classmethod
    def is_model(cls, model: str) -> bool:
        """Checks if the flow meter is of a certain model.

        Args:
            model (str): Model of flow meter.

        Returns:
            bool: True if model matches.
        """
        cls._models = [" M-", " MS-", " MQ-", " MW-"]
        return any([bool(re.search(i, model)) for i in cls._models])

    def __init__(
        self, device: SerialDevice, dev_info: dict, id: str = "A", **kwargs: Any
    ) -> None:
        """Connects to the flow device.

        Args:
            device (Device): The Device object.
            dev_info (dict): The device information dictionary.
            id (str, optional): Unit ID of Alicat flow device. Defaults to "A".
            **kwargs (Any): Additional keyword arguments.
        """
        super().__init__(device, dev_info, id, **kwargs)


class FlowController(FlowMeter):
    """A class used to represent a flow controller. Extends flow meter."""

    @classmethod
    def is_model(cls, model: str) -> bool:
        """Checks if the flow meter is of a certain model.

        Args:
            model (str): Model of flow meter.

        Returns:
            bool: True if model matches.
        """
        cls._models = [" MC-", " MCS-", " MCQ-", " MCW-"]
        return any([bool(re.search(i, model)) for i in cls._models])

    def __init__(
        self, device: SerialDevice, dev_info: dict, id: str = "A", **kwargs: Any
    ) -> None:
        """Connects to the flow controller.

        Args:
            device (Device): The Device object.
            dev_info (dict): The device information dictionary.
            id (str, optional): Unit ID of Alicat flow controller. Defaults to "A".
            **kwargs (Any): Additional keyword arguments.
        """
        super().__init__(device, dev_info, id, **kwargs)

    async def setpoint(self, value: float = "", unit: str = "") -> dict:
        """Gets/Sets the setpoint of the device.

        Note:
            Devices with firmware versions 9.00 or greater should use this method

        Args:
            value (float): Desired setpoint value for the controller. Set to 0 to close valve.
            unit (str): Set setpoint units.

        Returns:
            dict: Reports setpoint with units
        """
        if self._vers and self._vers < 9.00:
            print("Error: Version later than 9v00, running Change Setpoint")
            return await self.change_setpoint(value)
        LABELS = [
            "Unit ID",
            "Current Setpt",
            "Requested Setpt",
            "Unit Code",
            "Unit Label",
        ]
        ret = await self._device._write_readline(f"{self._id}LS {value} {units[unit]}")
        ret = ret.split()
        ret[1], ret[2] = float(ret[1]), float(ret[2])
        return dict(zip(LABELS, ret))

    async def _change_setpoint(self, value: float = "") -> dict:
        """Changes the setpoint of the device.

        Note:
            Devices with firmware versions less than 9.00 should use this method

        Args:
            value (float): Desired setpoint value for the controller. Set to 0 to close valve.

        Returns:
            dict: Dataframe with new setpoint
        """
        if self._vers and self._vers < 4.33:
            print("Error: Version earlier than 4v33")
            return
        if self._vers and self._vers >= 9.00:
            print("Error: Version later than 9v00, running Query/Change Setpoint")
            return await self.setpoint(value)
        if self._df_format is None:
            await self.get_df_format()
        ret = await self._device._write_readline(f"{self._id}S {value}")
        df = ret.split()
        for index in [idx for idx, s in enumerate(self._df_ret) if "decimal" in s]:
            df[index] = float(df[index])
        return dict(zip(self._df_format, df))

    async def batch(
        self, totalizer: int = 1, batch_vol: int = "", unit: str = ""
    ) -> dict:
        """Directs controller to flow a set amount then close the valve.

        Note:
            **Untested.**

        Args:
            totalizer (int): Totalizer (1 or 2) to use/query. Defaults to 1.
            batch_vol (int): Size of desired batch flow. Set to 0 to disable batch.
            unit (str): Volume units for flow.

        Returns:
            dict: Reports totalizer, batch size, units.
        """
        if self._vers and self._vers < 10.00:
            print("Error: Version earlier than 10v00")
            return
        LABELS = ["Unit ID", "Totalizer", "Batch Size", "Unit Code", "Unit Label"]
        ret = await self._device._write_readline(
            f"{self._id}TB {totalizer} {batch_vol} {units[unit]}"
        )
        return dict(zip(LABELS, ret.split()))

    async def deadband_limit(self, save: bool = "", limit: float = "") -> dict:
        """Gets/Sets the range the controller allows for drift around setpoint.

        Args:
            save (bool): Whether to save the deadband limit on startup
            limit (float): Value of deadband limit

        Returns:
            dict: Reports deadband with units
        """
        LABELS = ["Unit ID", "Deadband", "Unit Code", "Unit Label"]
        if isinstance(save, bool):
            save = "1" if save else "0"
        ret = await self._device._write_readline(f"{self._id}LCDB {save} {limit}")
        ret = ret.split()
        ret[1] = float(ret[1])
        return dict(zip(LABELS, ret))

    async def deadband_mode(self, mode: str = "") -> dict:
        """Gets/Sets the reaction the controller has for values around setpoint.

        Args:
            mode (str): "Hold" or "Current" holds valve and current positions until outside the limits. "Close" closes valve until outside the limits.

        Returns:
            dict: Reports mode
        """
        if self._vers and self._vers < 10.05:
            print("Error: Version earlier than 10v05")
            return
        LABELS = ["Unit ID", "Mode"]
        mode = (
            "1"
            if mode.upper() in ["HOLD", "CURRENT"]
            else "2"
            if mode.upper() in ["CLOSE"]
            else mode
        )
        ret = await self._device._write_readline(f"{self._id}LCDM {mode}")
        ret = ret.split()
        output_mapping = {"1": "Hold valve at current", "2": "Close valve"}
        ret[1] = output_mapping.get(str(ret[1]), ret[1])
        return dict(zip(LABELS, ret))

    async def loop_control_alg(self, algo: str = "") -> dict:
        """Gets/Sets the control algorithm the controller uses.

        - algorithm 1 = PD/PDF
        - algorithm 2 = PD2I

        Args:
            algo (str): Algorithm used for loop control. "PD", "PDF", "PD/PDF", "PD2I"

        Returns:
            dict: Reports algorithm
        """
        if self._vers and self._vers < 10.05:
            print("Error: Version earlier than 10v05")
            return
        LABELS = ["Unit ID", "Algorithm"]
        algo = (
            "2"
            if algo.upper() in ["PD2I"]
            else "1"
            if algo.upper() in ["PD", "PDF", "PD/PDF"]
            else algo
        )
        ret = await self._device._write_readline(f"{self._id}LCA {algo}")
        ret = ret.split()
        algorithm_mapping = {"1": "PD/PDF", "2": "PD2I"}
        ret[1] = algorithm_mapping.get(str(ret[1]), ret[1])
        return dict(zip(LABELS, ret))

    async def loop_control_var(self, var: str = "") -> dict:
        """Sets the statistic the setpoint controls.

        Args:
            var (str): Desired statistic

        Returns:
            dict: Reports new loop variable
        """
        if self._vers and self._vers < 9.00:
            print("Error: Version earlier than 9v00")
            return
        LABELS = ["Unit ID", "Loop Var Val"]
        # If the user did not specify setpoint, assume Setpt
        if var and var[-6:] != "_Setpt":
            var += "_Setpt"
        ret = await self._device._write_readline(f"{self._id}LV {statistics[var]}")
        ret = ret.split()
        ret[1] = next(
            (code for code, value in statistics.items() if value == int(ret[1])), ret[1]
        )
        return dict(zip(LABELS, ret))

    async def loop_control_range(
        self, var: str = "", unit: str = "", min: float = "", max: float = ""
    ) -> dict:
        """Gets/Sets the control range of the statistic the setpoint controls.

        Args:
            var (str): Desired statistic to be queried/modified
            unit (str): Units of var
            min (float): Min allowable setpoint
            max (float): Max allowable setpoint

        Returns:
            dict: Reports loop variable, units, min, and max
        """
        if self._vers and self._vers < 9.00:
            print("Error: Version earlier than 9v00")
            return
        LABELS = ["Unit ID", "Loop Var", "Min", "Max", "Unit Code", "Unit Label"]
        if self._vers and self._vers < 10.05:
            print("Error: Version earlier than 9v00, max and min not supported")
            LABELS = LABELS[:-2]
            min = ""
            max = ""
        ret = await self._device._write_readline(
            f"{self._id}LR {statistics[var]} {units[unit]} {min} {max}"
        )
        ret = ret.split()
        ret[1] = next(
            (code for code, value in statistics.items() if value == int(ret[1])), ret[1]
        )
        ret[2], ret[3] = float(ret[2]), float(ret[3])
        return dict(zip(LABELS, ret))

    async def max_ramp_rate(self, max: float = "", unit: str = "") -> dict:
        """Gets/Sets how fast controller moves to new setpoint.

        Args:
            max (float): Indicates step size for movement to setpoint. 0 to disable ramping (still must include unit)
            unit (str): unit for rate

        Returns:
            dict: Reports max ramp rate with unit
        """
        if self._vers and self._vers < 7.11:
            print("Error: Version earlier than 7v11")
            return
        LABELS = ["Unit ID", "Max Ramp Rate", "Unit Code", "Time Code", "Units"]
        ret = await self._device._write_readline(f"{self._id}SR {max} {units[unit]}")
        ret = ret.split()
        ret[1] = float(ret[1])
        return dict(zip(LABELS, ret))

    async def pdf_gains(
        self, save: bool = "", p_gain: int = "", d_gain: int = ""
    ) -> dict:
        """Gets/Sets the proportional and intregral gains of the PD/PDF controller.

        Manual is incorrect, this does not have an insignifcant 0 in the command

        Args:
            save (bool): Whether to save gains on power-up
            p_gain (int): Integral gain. Range is 0 to 65535
            d_gain (int): Proportional gain. Range is 0 to 65535

        Returns:
            dict: Reports P and D gains
        """
        if self._vers and self._vers < 10.05:
            print("Error: Version earlier than 10v05")
            return
        LABELS = ["Unit ID", "P  Gain", "D Gain"]
        if isinstance(save, bool):
            save = "1" if save else "0"
        ret = await self._device._write_readline(
            f"{self._id}LCGD {save} {p_gain} {d_gain}"
        )
        ret = ret.split()
        ret[1], ret[2] = int(ret[1]), int(ret[2])
        return dict(zip(LABELS, ret))

    async def pd2i_gains(
        self, save: bool = "", p_gain: int = "", i_gain: int = "", d_gain: int = ""
    ) -> dict:
        """Gets/Sets the proportional, intregral, and derivative gains of the PD2I controller.

        Note:
            **Setting is nonfunctional**

        Args:
            save (bool): Whether to save gains on power-up
            p_gain (int): Proportional gain. Range is 0 to 65535
            i_gain (int): Integral gain. Range is 0 to 65535
            d_gain (int): Derivative gain. Range is 0 to 65535. Optional.

        Returns:
            dict: Reports P, I, and D gains
        """
        if self._vers and self._vers < 10.05:
            print("Error: Version earlier than 10v05")
            return
        LABELS = ["Unit ID", "P  Gain", "I Gain", "D Gain"]
        if isinstance(save, bool):
            save = "1" if save else "0"
        ret = await self._device._write_readline(
            f"{self._id}LCG {save} {p_gain} {i_gain} {d_gain}"
        )
        ret = ret.split()
        ret[1], ret[2], ret[3] = int(ret[1]), int(ret[2]), int(ret[3])
        return dict(zip(LABELS, ret))

    async def power_up_setpoint(self, val: float = "") -> dict:
        """Enables immediate setpoint on power-up.

        Note:
            **Untested.**

        Args:
            val (float): Setpoint on power-up. 0 to disable start-up setpoint

        Returns:
            dict: Dataframe with current (not power-up) setpoint
        """
        if self._vers and self._vers < 8.04:
            print("Error: Version earlier than 8v04")
            return
        # Gets the format of the dataframe if it is not already known
        if self._df_format is None:
            await self.get_df_format()
        ret = await self._device._write_readline(f"{self._id}SPUE {val}")
        df = ret.split()
        for index in [idx for idx, s in enumerate(self._df_ret) if "decimal" in s]:
            df[index] = float(df[index])
        return dict(zip(self._df_format, df))

    async def overpressure(self, limit: float = "") -> dict:
        """Sets the overpressure limit of the device. Flow is stopped if pressure exceeds.

        Note:
            **Untested.**

        Args:
            limit (float): Upper limit of pressure. Disabled if above pressure full scale or <= 0

        Returns:
            dict: Dataframe
        """
        if self._vers and self._vers < 5.09:
            print("Error: Version earlier than 5v09")
            return
        # Gets the format of the dataframe if it is not already known
        if self._df_format is None:
            await self.get_df_format()
        ret = await self._device._write_readline(f"{self._id}OPL {limit}")
        df = ret.split()
        for index in [idx for idx, s in enumerate(self._df_ret) if "decimal" in s]:
            df[index] = float(df[index])
        return dict(zip(self._df_format, df))

    async def ramp(
        self, up: bool = "", down: bool = "", zero: bool = "", power_up: bool = ""
    ) -> dict:
        """Gets/Sets the ramp settings of the device.

        Args:
            up (bool): When setpoint is made higher. Disabled = immediate move. Enabled = Follow ramp rate
            down (bool): When setpoint is made lower. Disabled = immediate move. Enabled = Follow ramp rate
            zero (bool): When setpoint is zero. Disabled = immediate move. Enabled = Follow ramp rate
            power_up (bool): To setpoint on power-up. Disabled = immediate move. Enabled = Follow ramp rate

        Returns:
            dict: Dataframe
        """
        if self._vers and self._vers < 10.05:
            print("Error: Version earlier than 10v05")
            return
        LABELS = ["Unit ID", "Ramp Up", "Ramp Down", "Zero Ramp", "Power Up Ramp"]
        if isinstance(up, bool):
            up = "1" if up else "0"
        if isinstance(down, bool):
            down = "1" if down else "0"
        if isinstance(zero, bool):
            zero = "1" if zero else "0"
        if isinstance(power_up, bool):
            power_up = "1" if power_up else "0"
        ret = await self._device._write_readline(
            f"{self._id}LSRC {up} {down} {zero} {power_up}"
        )
        output_mapping = {"1": "Enabled", "0": "Disabled"}
        ret = ret.split()
        ret = [output_mapping.get(str(val), val) for val in ret]
        return dict(zip(LABELS, ret))

    async def setpoint_source(self, mode: str = "") -> dict:
        """Gets/Sets how the setpoint is given to the controller.

        Note:
            **This appears to function for the meter for some reason**

        Args:
            mode (str): Desired source for setpoint input

                - A for Analog
                - S for Display or Serial Communications. Saves and restores setpoint on pwower-up
                - U for Display or Serial Communications. Does not save.

        Returns:
            dict: Setpoint source mode
        """
        if self._vers and self._vers < 10.05:
            print("Error: Version earlier than 10v05")
            return
        LABELS = ["Unit ID", "Mode"]
        ret = await self._device._write_readline(f"{self._id}LSS {mode}")
        ret = ret.split()
        mapping = {
            "A": "Analog",
            "S": "Serial/Display, Saved",
            "U": "Serial/Display, Unsaved",
        }
        ret[1] = mapping.get(ret[1], ret[1])
        return dict(zip(LABELS, ret))

    async def valve_offset(
        self, save: bool = "", initial_offset: float = "", closed_offset: float = ""
    ) -> dict:
        """Gets/Sets how much power driven to valve when first opened or considered closed.

        Args:
            save (bool): Whether to save offset values on power-up
            initial_offset (float): 0-100% of total electrcity to first open closed valve
            closed_offset (float): 0-100% of total electrcity for device to consider valve closed

        Returns:
            dict: Offset values
        """
        if self._vers and self._vers < 10.05:
            print("Error: Version earlier than 10v05")
            return
        LABELS = ["Unit ID", "Init Offset (%)", "Closed Offset (%)"]
        if isinstance(save, bool):
            save = "0 1" if save else "0 0"
        ret = await self._device._write_readline(
            f"{self._id}LCVO {save} {initial_offset} {closed_offset}"
        )
        ret = ret.split()
        ret[1], ret[2] = float(ret[1]), float(ret[2])
        return dict(zip(LABELS, ret))

    async def zero_pressure_control(self, enable: bool = "") -> dict:
        """Gets/Sets how controller reacts to 0 Pressure setpoint.

        Args:
            enable (bool): If disabled, valve opens/closes completely. If enabled, uses close-loop

        Returns:
            dict: If active control is active or not
        """
        if self._vers and self._vers < 10.05:
            print("Error: Version earlier than 10v05")
            return
        LABELS = ["Unit ID", "Active Ctrl"]
        if isinstance(enable, bool):
            enable = "1" if enable else "0"
        ret = await self._device._write_readline(f"{self._id}LCZA {enable}")
        ret = ret.split()
        output_mapping = {"1": "Enabled", "0": "Disabled"}
        ret[1] = output_mapping.get(str(ret[1]), ret[1])
        return dict(zip(LABELS, ret))

    async def cancel_valve_hold(self) -> dict:
        """Removes valve holds on the device

         Note:
             **Untested.**

        Returns:
             dict: Returns data frame without 'hold' status
        """
        if self._df_format is None:
            await self.get_df_format()
        gas = gases.get(gas, "")
        ret = await self._device._write_readline(f"{self._id}C")
        df = ret.split()
        for index in [idx for idx, s in enumerate(self._df_ret) if "decimal" in s]:
            df[index] = float(df[index])
        return dict(zip(self._df_format, df))

    async def exhaust(self) -> dict:
        """Closes upstream valve and opens downstream 100%

         Note:
             **Untested.**

        Returns:
             dict: Returns data frame with 'hold' status
        """
        if self._vers and self._vers < 4.37:
            print("Error: Version earlier than 4v37")
            return
        if self._df_format is None:
            await self.get_df_format()
        gas = gases.get(gas, "")
        ret = await self._device._write_readline(f"{self._id}E")
        df = ret.split()
        for index in [idx for idx, s in enumerate(self._df_ret) if "decimal" in s]:
            df[index] = float(df[index])
        return dict(zip(self._df_format, df))

    async def hold_valves(self) -> dict:
        """Maintains valve position

         Note:
             **Untested.**

        Returns:
             dict: Returns data frame with 'hold' status
        """
        if self._vers and self._vers < 5.07:
            print("Error: Version earlier than 5v07")
            return
        if self._df_format is None:
            await self.get_df_format()
        gas = gases.get(gas, "")
        ret = await self._device._write_readline(f"{self._id}HP")
        df = ret.split()
        for index in [idx for idx, s in enumerate(self._df_ret) if "decimal" in s]:
            df[index] = float(df[index])
        return dict(zip(self._df_format, df))

    async def hold_valves_closed(self) -> dict:
        """Maintains closed valve position.

        Note:
            **Untested.**

        Returns:
            dict: Returns data frame with 'hold' status
        """
        if self._vers and self._vers < 5.07:
            print("Error: Version earlier than 5v07")
            return
        if self._df_format is None:
            await self.get_df_format()
        gas = gases.get(gas, "")
        ret = await self._device._write_readline(f"{self._id}HC")
        df = ret.split()
        for index in [idx for idx, s in enumerate(self._df_ret) if "decimal" in s]:
            df[index] = float(df[index])
        return dict(zip(self._df_format, df))

    async def query_valve(self) -> dict:
        """Gives the percent of total electrciity sent to valve(s).

        Note:
            **Untested.**

        Returns:
            dict: Valve drive percentages
        """
        if self._vers and self._vers < 8.18:
            print("Error: Version earlier than 8v18")
            return
        LABELS = ["Unit ID", "Upstream Valve", "Downstream Valve", "Exhaust Valve"]
        if isinstance(enable, bool):
            enable = "1" if enable else "0"
        ret = await self._device._write_readline(f"{self._id}LCZA {enable}")
        ret = ret.split()
        for i in range(len(ret)):
            if not i == 0:
                ret[i] = float(ret[i])
        return dict(zip(LABELS, ret))

    '''
I'm going to double check the new set does exactly what we want before I delete this
    async def set(self, meas: str, param1: str, param2: str) -> dict:
        """Gets the value of a measurement from the device.

        Args:
            meas (str): Measurement to set
            param1 (str): First parameter of setting function
            param2 (str): Second parameter of setting function

        Returns:
            dict: response of setting function
        """
        resp = {}
        upper_meas = str(meas).upper()
        # Set gas - Param1 = gas: str = "", Param2 = save: bool = ""
        if upper_meas == "GAS":
            resp.update(await self.gas(str(param1), str(param2)))
        # Set setpoint - Param1 = value: float = "", Param2 = unit: str = ""
        elif upper_meas in ["SETPOINT", "STPT"]:
            resp.update(await self.setpoint(str(param1), str(param2)))
        # Set loop control variable - Param1 = statistic: str = ""
        elif upper_meas in ["LOOP", "LOOP CTRL"]:
            resp.update(await self.loop_control_var(str(param1)))
        return resp
    '''

    async def set(self, comm: dict) -> dict:
        """Sets the values of measurements for the device.

        Args:
            comm (dict): Dictionary with command to set as key, parameters as values. Use a list for multiple parameters

        Returns:
            dict: Response of setting function
        """
        resp = {}
        for meas in list(comm.keys()):
            upper_meas = str(meas).upper()
            # Set gas - Param1 = gas: str = "", Param2 = save: bool = ""
            if upper_meas == "GAS":
                resp.update(await self.gas(str(comm[meas][0]), str(comm[meas][1])))
            # Set setpoint - Param1 = value: float = "", Param2 = unit: str = ""
            elif upper_meas in ["SETPOINT", "STPT"]:
                resp.update(await self.setpoint(str(comm[meas][0]), str(comm[meas][1])))
            # Set loop control variable - Param1 = statistic: str = ""
            elif upper_meas in ["LOOP", "LOOP CTRL"]:
                resp.update(await self.loop_control_var(str(comm[meas][0])))
        return resp

    async def get(self, measurements: list = ["@"]) -> dict:
        """Gets the value of a measurement from the device.

        Args:
            measurements (list): List of measurements to get

        Returns:
            dict: Dictionary of measurements
        """
        resp = {}
        flag = 0
        reqs = []
        if isinstance(measurements, str):
            measurements = measurements.split()
        # Request
        for meas in measurements:
            if meas in statistics:
                reqs.append(meas)
            elif meas.upper() == "GAS":
                resp.update(await self.gas())
            elif meas.upper() in ["SETPOINT", "STPT"]:
                resp.update(await self.setpoint())
            elif flag == 0:
                resp.update(await self.poll())
                flag = 1
        i = 0
        while i * 13 < len(reqs):
            resp.update(await self.request(reqs[13 * i : 13 + 13 * i]))
            i += 1
        return resp
