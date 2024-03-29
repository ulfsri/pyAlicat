from typing import Any

import json
import re
from abc import ABC

from comm import SerialDevice

# from .device import Device

with open("codes.json") as f:
    codes = json.load(f)
statistics = codes["statistics"][0]
units = codes["units"][0]
gases = codes["gases"][0]


async def new_device(port: str, id: str = "A", **kwargs: Any):
    """
    Creates a new device. Chooses appropriate device based on characteristics.

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


def all_subclasses(cls) -> set:
    """
    Returns all subclasses of a class.

    Args:
        cls (class): The class to get the subclasses of.

    Returns:
        set: The set of subclasses.
    """
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
        self._df_units = None
        self._df_format = None

    async def poll(self) -> dict:
        """
        Gets the current value of the device.

        Returns:
            dict: The current value of the device.
        """
        # Gets the format of the dataframe if it is not already known
        if self._df_format is None:
            await self.get_df_format()
        ret = await self._device._write_readline(self._id)
        df = ret.split()
        for index in [idx for idx, s in enumerate(self._df_ret) if "decimal" in s]:
            df[index] = float(df[index])
        return dict(zip(self._df_format, df))

    async def read(self):
        # Gets the format of the dataframe if it is not already known
        if self._df_format is None:
            await self.get_df_format()
        ret = await self._device._readline(self._id)
        df = ret.split()
        for index in [idx for idx, s in enumerate(self._df_ret) if "decimal" in s]:
            df[index] = float(df[index])
        return dict(zip(self._df_format, df))

    async def request(self, stats: list = [], time: int = 1) -> dict:
        """
        Gets specified values averaged over specified time.
        time in ms

        Args:
            stats (list): The statistics to get. Maximum of 13 stats in one call.
            time (str): The time to average over in milliseconds.

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
        """
        Starts streaming data from device.
        """
        await self._device._write(f"{self._id}@ @")
        return

    async def stop_stream(self, new_id: str = "A") -> None:
        """
        Stops streaming data from device.
        """
        ret = await self._device._write(f"@@ {new_id}")
        self.id = new_id
        return ret

    async def gas(self, gas: str = "", save: str = "") -> dict:
        """
        Gets the gas of the device.
        Sets the gas of the device.

        Args:
            gas (str): Name of the gas to set the device.
            save (str): Set to y/n. If yes, changes default on power-up

        Returns:
            dict: Reports the gas and its code and names.
        """
        gas = gases.get(gas, "")
        save = (
            "1"
            if save.upper() in ["Y", "YES"]
            else "0"
            if save.upper() in ["N", "NO"]
            else save
        )
        if not gas:
            save = ""
        ret = await self._device._write_readline(f"{self._id}GS {gas} {save}")
        df = ["Unit ID", "Gas Code", "Gas", "Gas Long"]
        return dict(zip(df, ret.split()))

    async def gas_list(self) -> dict:
        """
        Gets the list of available gases for the device.

        Returns:
            dict: List of all gase codes and their names.
        """
        ret = {}
        resp = await self._device._write_readall(f"{self._id}??G*")
        for gas in resp:
            gas = gas.split()
            ret[gas[1]] = gas[2]
        return ret

    async def setpoint(self, value: int = "", unit: str = "") -> dict:
        """
        Gets the setpoint of the device.
        Sets the setpoint of the device.

        Args:
            value (int): Desired setpoint value for the controller.
                         Set to 0 to close valve
            unit (str): Set setpoint units

        Returns:
            dict: Reports setpoint with units
        """
        ret = await self._device._write_readline(f"{self._id}LS {value} {units[unit]}")
        df = ["Unit ID", "Current Setpt", "Requested Setpt", "Unit Code", "Unit Label"]
        return dict(zip(df, ret.split()))

    async def tare_abs_P(self) -> dict:
        """
        Tares the absolute pressure of the device, zeros out the abs P reference point # Untested
           Should only be used when no flow and not pressurized line.

        Returns:
            dict: Dataframe with zero Abs Pressure
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
        """
        Creates a no-flow reference point # Untested
           Should only be used when no flow and at operation pressure.

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
        """
        Tares the gauge pressure of the device, zeros out the diff P reference point # Untested
           Should only be used when no flow and at operation pressure.

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

    async def batch(
        self, totalizer: int = 1, batch_vol: str = "", unit: str = ""
    ) -> dict:
        """
        Directs controller to flow a set amount then close the valve.   # Untested
        Must accept a totalizer value. Defaults to totalizer 1.
        set batch volume to size of desired flow. Set to 0 to disable batch.

        Args:
            totalizer (int): Totalizer (1 or 2) to use/query.
            batch_vol (int): Size of desired batch flow
                Set to 0 to disable batch
            unit (str): Volume units for flow

        Returns:
            dict: Reports totalizer, batch size, units.
        """
        ret = await self._device._write_readline(
            f"{self._id}TB {totalizer} {batch_vol} {units[unit]}"
        )
        df = ["Unit ID", "Totalizer", "Batch Size", "Unit Code", "Unit Label"]
        return dict(zip(df, ret.split()))

    async def deadband_limit(self, save: str = "", limit: float = "") -> dict:
        """
        Gets the range the controller allows for drift around setpoint
        Sets the range the controller allows for drift around setpoint # Untested

        Args:
            save (str): Set to y/n. If yes, keeps limit on power-up
            limit (float): Set setpoint units

        Returns:
            dict: Reports deadband with units
        """
        save = (
            "1"
            if save.upper() in ["Y", "YES"]
            else "0"
            if save.upper() in ["N", "NO"]
            else save
        )
        ret = await self._device._write_readline(f"{self._id}LCDB {save} {limit}")
        df = ["Unit ID", "Deadband", "Unit Code", "Unit Label"]
        return dict(zip(df, ret.split()))

    async def deadband_mode(self, mode: str = "") -> dict:
        """
        Gets the reaction the controller has for values around setpoint
        Sets the reaction the controller has for values around setpoint # Untested

        Args:
            mode (str): 1 for Hold Valve at Current, 2 for close valve

        Returns:
            dict: Reports mode
        """
        mode = (
            "1"
            if mode.upper() in ["HOLD", "CURRENT"]
            else "0"
            if mode.upper() in ["CLOSE"]
            else mode
        )
        ret = await self._device._write_readline(f"{self._id}LCDM {mode}")
        df = ["Unit ID", "Mode"]
        ret = ret.split()
        output_mapping = {"1": "Hold valve at current", "2": "Close valve"}
        ret[1] = output_mapping.get(str(ret[1]), ret[1])
        return dict(zip(df, ret))

    async def loop_control_alg(self, algo: str = "") -> dict:
        """
        Gets the control algorithm the controller uses
        Sets the control algorithm the controller uses # Untested
        algorithm 1 = PD/PDF, algorithm 2 = PD2I

        Args:
            algo (str): Algorithm used for loop control

        Returns:
            dict: Reports algorithm
        """
        algo = (
            "2"
            if algo.upper() in ["PD21"]
            else "0"
            if algo.upper() in ["PD", "PDF", "PD/PDF"]
            else algo
        )
        ret = await self._device._write_readline(f"{self._id}LCA {algo}")
        df = ["Unit ID", "Algorithm"]
        ret = ret.split()
        algorithm_mapping = {"1": "PD/PDF", "2": "PD2I"}
        ret[1] = algorithm_mapping.get(str(ret[1]), ret[1])
        return dict(zip(df, ret))

    async def loop_control_var(self, var: str = "") -> dict:
        """
        Sets the statistic the setpoint controls

        Args:
            var (str): Desired statistic

        Returns:
            dict: Reports new loop variable
        """
        # If the user did not specify setpoint, assume Setpt
        if var[-6:] != "_Setpt":
            var += "_Setpt"
        ret = await self._device._write_readline(f"{self._id}LV {statistics[var]}")
        df = ["Unit ID", "Loop Var Val"]
        ret = ret.split()
        ret[1] = next(
            (code for code, value in statistics.items() if value == int(ret[1])), ret[1]
        )
        return dict(zip(df, ret))

    async def loop_control_setpoint(
        self, var: str = "", unit: str = "", min: int = "", max: int = ""
    ) -> dict:
        """
        Gets the control range of the statistic the setpoint controls
        Sets the control range of the statistic the setpoint controls # Untested

        Args:
            var (str): Desired statistic to be queried/modified
            unit (str): Units of var
            min (int): Min allowable setpoint
            max (int): Max allowable setpoint

        Returns:
            dict: Reports loop variable, units, min, and max
        """
        ret = await self._device._write_readline(
            f"{self._id}LR {var} {units[unit]} {min} {max}"
        )
        df = ["Unit ID", "Loop Var", "Min", "Max", "Unit Code", "Unit Label"]
        ret = ret.split()
        ret[1] = next(
            (code for code, value in statistics.items() if value == int(ret[1])), ret[1]
        )
        return dict(zip(df, ret))

    async def max_ramp_rate(self, max: int = "", unit: str = "") -> dict:
        """
        Gets how fast controller moves to new setpoint
        Sets how fast controller moves to new setpoint # Untested

        Args:
            max (int): Indicates step size for movement to setpoint
                max = 0 to disable ramping (still must include unit)
            unit (str): unit for rate

        Returns:
            dict: Reports max ramp rate with unit
        """
        ret = await self._device._write_readline(f"{self._id} SR {max} {units(unit)}")
        df = ["Unit ID", "Max Ramp Rate", "Unit Code", "Time Code", "Units"]
        return dict(zip(df, ret.split()))

    async def pdf_gains(
        self, save: str = "", p_gain: float = "", d_gain: float = ""
    ) -> dict:
        """
        Gets the proportional and intregral gains of the PD/PDF controller
        Sets the proportional and intregral gains of the PD/PDF controller # Untested

        Args:
            save (str): Set to y/n. If yes, keeps gains on power-up
            p_gain (float): Integral gain. Range is 0 to 65535
            d_gain (float): Proportional gain. Range is 0 to 65535

        Returns:
            dict: Reports P and D gains
        """
        save = (
            "0 1"
            if save.upper() in ["Y", "YES"]
            else "0 0"
            if save.upper() in ["N", "NO"]
            else save
        )
        ret = await self._device._write_readline(
            f"{self._id}LCGD {save} {p_gain} {d_gain}"
        )
        df = ["Unit ID", "P  Gain", "D Gain"]
        return dict(zip(df, ret.split()))

    async def pd2i_gains(
        self, save: str = "", p_gain: float = "", i_gain: float = "", d_gain: float = ""
    ) -> dict:
        """
        Gets the proportional, intregral, and derivative gains of the PD2I controller
        Sets the proportional, intregral, and derivative gains of the PD2I controller # Untested

        Args:
            save (str): Set to y/n. If yes, keeps gains on power-up
            p_gain (float): Integral gain. Range is 0 to 65535
            i_gain (float): Integral gain. Range is 0 to 65535
            d_gain (float): Proportional gain. Range is 0 to 65535. Optional.

        Returns:
            dict: Reports P, I, and D gains
        """
        save = (
            "0 1"
            if save.upper() in ["Y", "YES"]
            else "0 0"
            if save.upper() in ["N", "NO"]
            else save
        )
        ret = await self._device._write_readline(
            f"{self._id} LCG {save} {p_gain} {i_gain} {d_gain}"
        )
        df = ["Unit ID", "P  Gain", "I Gain", "D Gain"]
        return dict(zip(df, ret.split()))

    async def power_up_setpoint(self, val: float = "") -> dict:
        """
        Enables immediate setpoint on power-up # Untested

        Args:
            val (float): Setpoint on power-up
                0 to disable start-up setpoint

        Returns:
            dict: Dataframe with current (not power-up) setpoint
        """
        # Gets the format of the dataframe if it is not already known
        if self._df_format is None:
            await self.get_df_format()
        ret = await self._device._write_readline(f"{self._id}SPUE {val}")
        df = ret.split()
        for index in [idx for idx, s in enumerate(self._df_ret) if "decimal" in s]:
            df[index] = float(df[index])
        return dict(zip(self._df_format, df))

    async def overpressure(self, limit: str = "") -> dict:
        """
        Sets the overpressure limit of the device. Flow is stopped if pressure exceeds # Untested

        Args:
            limit (float): Upper limit of pressure
                Disabled if above pressure full scale or <= 0

        Returns:
            dict: Dataframe
        """
        # Gets the format of the dataframe if it is not already known
        if self._df_format is None:
            await self.get_df_format()
        ret = await self._device._write_readline(f"{self._id}OPL {limit}")
        df = ret.split()
        for index in [idx for idx, s in enumerate(self._df_ret) if "decimal" in s]:
            df[index] = float(df[index])
        return dict(zip(self._df_format, df))

    async def ramp(
        self, up: str = "", down: str = "", zero: str = "", power_up: str = ""
    ) -> dict:
        """
        Gets the ramp settings of the device.
        Sets the ramp settings of the device. # Untested

        Args:
            up (str): When setpoint is made higher. Disabled = immediate move. Enabled = Follow ramp rate
            down (str): When setpoint is made lower. Disabled = immediate move. Enabled = Follow ramp rate
            zero (str): When setpoint is zero. Disabled = immediate move. Enabled = Follow ramp rate
            power_up (str): To setpoint on power-up. Disabled = immediate move. Enabled = Follow ramp rate

        Returns:
            dict: Dataframe
        """
        up = (
            "1"
            if up.upper() in ["Y", "YES"]
            else "0"
            if up.upper() in ["N", "NO"]
            else up
        )
        down = (
            "1"
            if down.upper() in ["Y", "YES"]
            else "0"
            if down.upper() in ["N", "NO"]
            else down
        )
        zero = (
            "1"
            if zero.upper() in ["Y", "YES"]
            else "0"
            if zero.upper() in ["N", "NO"]
            else zero
        )
        power_up = (
            "1"
            if power_up.upper() in ["Y", "YES"]
            else "0"
            if power_up.upper() in ["N", "NO"]
            else power_up
        )
        ret = await self._device._write_readline(
            f"{self._id} LSRC {up} {down} {zero} {power_up}"
        )
        df = ["Unit ID", "Ramp Up", "Ramp Down", "Zero Ramp", "Power Up Ramp"]
        ret = ret.split()
        output_mapping = {"1": "Enabled", "0": "Disabled"}
        ret = [output_mapping.get(str(val), val) for val in ret]
        return dict(zip(df, ret))

    async def setpoint_source(self, mode: str = "") -> dict:
        """
        Gets how the setpoint is given to the controller
        Sets how the setpoint is given to the controller # Untested

        Args:
            mode (str):
                A for Analog
                S for Display or Serial Communications. Saves and restores setpoint on pwower-up
                D for Display or Serial Communications. Does not save.

        Returns:
            dict: Setpoint source mode
        """
        ret = await self._device._write_readline(f"{self._id}LSS {mode}")
        df = ["Unit ID", "Mode"]
        ret = ret.split()
        mapping = {
            "A": "Analog",
            "S": "Serial/Display, Saved",
            "U": "Serial/Display, Unsaved",
        }
        ret[1] = mapping.get(ret[1], ret[1])
        return dict(zip(df, ret))

    async def valve_offset(
        self, save: str = "", initial_offset: float = "", closed_offset: float = ""
    ) -> dict:
        """
        Gets how much power driven to valve when first opened or considered closed
        Sets how much power driven to valve when first opened or considered closed # Untested

        Args:
            save (str): y/n for if offset % is saved on power cycle
            initial_offset (float): 0-100% of total electrcity to first open closed valve
            closed_offset (float): 0-100% of total electrcity for device to consider valve closed

        Returns:
            dict: Offset values
        """
        save = (
            "0 1"
            if save.upper() in ["Y", "YES"]
            else "0 0"
            if save.upper() in ["N", "NO"]
            else save
        )
        ret = await self._device._write_readline(
            f"{self._id}LCVO {save} {initial_offset} {closed_offset}"
        )
        df = ["Unit ID", "Init Offser (%)", "Closed Offset (%)"]
        ret = ret.split()
        return dict(zip(df, ret))

    async def zero_pressure_control(self, enable: str = "") -> dict:
        """
        Gets how controller reacts to 0 Pressure setpoint
        Sets how controller reacts to 0 Pressure setpoint # Untested

        Args:
            enable (str): If disabled, valve opens/closes completely. If enabled, uses close-loop

        Returns:
            dict: If active control is active or not
        """
        enable = (
            "1"
            if enable.upper() in ["Y", "YES"]
            else "0"
            if enable.upper() in ["N", "NO"]
            else enable
        )
        ret = await self._device._write_readline(f"{self._id}LCZA {enable}")
        df = ["Unit ID", "Active Ctrl"]
        ret = ret.split()
        output_mapping = {"1": "Enabled", "0": "Disabled"}
        ret[1] = output_mapping.get(str(ret[1]), ret[1])
        return dict(zip(df, ret))

    async def auto_tare(self, enable: str = "", delay: float = "") -> dict:
        """
        Gets if the controller auto tares
        Sets if the controller auto tares # Untested

        Args:
            enable (str): Enable or disable auto tare
            delay (float): amount of time in seconds waited until tare begins 0.1 to 25.5

        Returns:
            dict: If tare is active or not and delay length (s)
        """
        enable = (
            "1"
            if enable.upper() in ["Y", "YES"]
            else "0"
            if enable.upper() in ["N", "NO"]
            else enable
        )
        ret = await self._device._write_readline(f"{self._id}ZCA {enable} {delay}")
        df = ["Unit ID", "Auto-tare", "Delay (s)"]
        ret = ret.split()
        output_mapping = {"1": "Enabled", "0": "Disabled"}
        ret[1] = output_mapping.get(str(ret[1]), ret[1])
        return dict(zip(df, ret))

    async def configure_data_frame(self, format: str = "") -> dict:
        """
        Sets data frame's format # Untested

        Args:
            format (str):
                '0' for default, values have 5 digits, setpoint and totalizer unsigned
                '1' for setpoint and totalizer signed (+ or -)
                '2' for signed setpoint and totalizer, number digits based on resolution

        Returns:
            dict: Data Frame in new format
        """
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
        group: str = "",
        unit: str = "",
        override: str = "",
    ) -> dict:
        """
        Gets units for desired statistics
        Sets units for desired statistics # Untested

        Args:
            statistic_value (str): Desired statistic to get/set unit for
            group (str): If setting unit, sets to entire group statisitc is in
            unit (str): Sets unit for statistic
            override (str): Overwrites any special rules for group changes

        Returns:
            dict: Responds with unit
        """
        group = (
            "1"
            if group.upper() in ["Y", "YES"]
            else "0"
            if group.upper() in ["N", "NO"]
            else group
        )
        override = "1" if override.upper() in ["Y", "YES"] else ""
        ret = await self._device._write_readline(
            f"{self._id}DCU {statistics[statistic_value]} {group} {units[unit]} {override}"
        )
        df = ["Unit ID", "Unit Code", "Unit Label"]
        ret = ret.split()
        return dict(zip(df, ret))

    async def flow_press_avg(
        self,
        stat_val: str = "",
        avg_time: float = "",
    ) -> dict:
        """
        Gets average value of statistic
        Sets time statistic is averaged over # Untested

        Args:
            stat_val (str): Desired statistic to get avgerage/set time
            avg_time (float): Time in ms over which averages taken. 0 to 9999.

        Returns:
            dict: Responds value of queried average and avg time const
        """
        stat_vals = {
            "All_Press": "1",
            "Abs_Press": "2",
            "Vol_Flow": "4",
            "Mass_Flow": "5",
            "Gauge_Press": "6",
            "Diff_Press": "7",
            "Ext_Vol_Flow": "17",
            "2nd_Abs_Press": "344",
            "2nd_Gauge_Press": "352",
            "2nd_Diff_Press": "360",
        }
        ret = await self._device._write_readline(
            f"{self._id}DCA {stat_vals[stat_val]} {avg_time}"
        )
        df = ["Unit ID", "Value", "Time Const"]
        ret = ret.split()
        return dict(zip(df, ret))

    async def full_scale_val(self, stat_val: str = "", unit: str = "") -> dict:
        """
        Gets measurement range of given statistic

        Args:
            stat_val (str): Desired statistic to get range
            unit (str): Units of range. Defaults if left blank.

        Returns:
            dict: Responds max value of statistic and units
        """
        ret = await self._device._write_readline(
            f"{self._id}FPF {statistics[stat_val]} {units[unit]}"
        )
        df = ["Unit ID", "Max Value", "Unit Code", "Unit Label"]
        ret = ret.split()
        return dict(zip(df, ret))

    async def power_up_tare(self, enable: str = "") -> dict:
        """
        Gets if device tares on power-up
        Sets if device tares on power-up

        Args:
            enable (str): If Enabled, 0.25 second after sensors stable. Close loop delay, valves stay closed

        Returns:
            dict: If tare is enabled
        """
        enable = (
            "1"
            if enable.upper() in ["Y", "YES"]
            else "0"
            if enable.upper() in ["N", "NO"]
            else enable
        )
        ret = await self._device._write_readline(f"{self._id}ZCP {enable}")
        df = ["Unit ID", "Power-Up Tare"]
        ret = ret.split()
        output_mapping = {"1": "Enabled", "0": "Disabled"}
        ret[1] = output_mapping.get(str(ret[1]), ret[1])
        return dict(zip(df, ret))

    async def data_frame(self) -> str:
        """
        Gets info about current data frame

        Returns:
            str: table that outlines data frame format
        """
        ret = await self._device._write_readall(f"{self._id}??D*")
        return ret

    async def stp_press(
        self, stp: str = "S", unit: str = "", press: float = ""
    ) -> dict:
        """
        Gets pressure reference point.
        Sets pressure reference point. # Untested
        To get Normal pressure reference point, set stp to N

        Args:
            stp (str): S for standard pressure, N for normal
            unit (str): Pressure units
            press (float): Numeric value of new desired pressure reference point

        Returns:
            dict: Current pressure reference point and units
        """
        if stp.upper == "NTP":
            stp = "N"
        if stp.upper() != "N":
            stp = "S"
        ret = await self._device._write_readline(
            f"{self._id}DCFRP {stp.upper()} {str(units[unit])} {str(press)}"
        )
        df = ["Unit ID", "Curr Press Ref", "Unit Code", "Unit Label"]
        ret = ret.split()
        return dict(zip(df, ret))

    async def stp_temp(self, stp: str = "S", unit: str = "", temp: str = "") -> dict:
        """
        Gets temperature reference point.
        Sets temperature reference point. # Untested
        To get Normal pressure reference point, set stp to N

        Args:
            stp (str): S for standard temperature, N for normal
            unit (str): Temperature units
            press (float): Numeric value of new desired temperature reference point

        Returns:
            dict: Current temperature reference point and units
        """
        if stp.upper == "NTP":
            stp = "N"
        if stp.upper() != "N":
            stp = "S"
        ret = await self._device._write_readline(
            f"{self._id}DCFRT {stp.upper()} {str(units[unit])} {str(temp)}"
        )
        df = ["Unit ID", "Curr Temp Ref", "Unit Code", "Unit Label"]
        ret = ret.split()
        return dict(zip(df, ret))

    async def zero_band(self, zb: float = "") -> dict:
        """
        Gets the zero band of the device.
        Sets the zero band of the device. # Untested

        Args:
            zb (float): % of full-scale readnigs process must exceed before device reports readings
                0 to 6.38 value
                0 to disable

        Returns:
            dict: Returns current zero band as percent of full scale
        """
        zb = f"0 {zb}" if zb else zb
        ret = await self._device._write_readline(f"{self._id}DCZ {zb}")
        df = ["Unit ID", "Zero Band (%)"]
        ret = ret.split()
        ret.pop(1)
        return dict(zip(df, ret))

    async def analog_out_source(
        self, primary: str = "0", val: str = "", unit: str = ""
    ) -> dict:
        """
        Gets the source of the analog output.
        Sets the source of the analog output. # Untested

        Args:
            primary (str): Primary of secondary analog output
            val (int): Statistic being tracked
                '0' to fix min possible output
                '1' to fix max possible output
                Other for statistic
                unit: Desired unit. Optional

        Returns:
            dict: Statistic and units
        """
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
        df = ["Unit ID", "Value", "Unit Code", "Unit Label"]
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
        return dict(zip(df, ret))

    async def baud(self, new_baud: int = "") -> dict:
        """
        Gets the baud rate of the device.
        Sets the baud rate of the device. # Untested
        Ensure COM is connected.

        Args:
           new_baud (int): Set to one of the following:
               2400, 4800, 9600, 19200, 38400, 57600, 115200

        Returns:
            dict: Baud rate, either current or new
        """
        valid_baud_rates = [2400, 4800, 9600, 19200, 38400, 57600, 115200]
        if new_baud != "" and int(new_baud) not in valid_baud_rates:
            new_baud = ""
        ret = await self._device._write_readline(f"{self._id}NCB {new_baud}")
        df = ["Unit ID", "Baud"]
        ret = ret.split()
        return dict(zip(df, ret))

    async def blink(self, dur: str = ""):
        """
        Gets the blinking state
        Blinks the device.

        Args:
           dur (int): Duration devices flashes. 0 stops blinking. -1 to flash indefinitely.

        Returns:
            dict: If the display is currently blinking
        """
        if isinstance(dur, int):
            dur = str(dur)
        ret = await self._device._write_readline(f"{self._id}FFP {dur}")
        df = ["Unit ID", "Flashing?"]
        ret = ret.split()
        output_mapping = {"1": "Yes", "0": "No"}
        ret[1] = output_mapping.get(str(ret[1]), ret[1])
        return dict(zip(df, ret))

    async def change_unit_id(self, new_id: str = "") -> None:
        """
        Sets the unit ID of the device.
        **This changes the ID, but the device stops responding**

        Args:
           new_id (str): New ID. A-Z accepted

        Returns:
            dict: If the display is currently blinking
        """
        await self._device._write(f"{self._id}@ {new_id}")
        self.id = new_id
        return

    async def firmware_version(self) -> dict:
        """
        Gets the firmware version of the device.

        Returns:
            dict:Current firmware vesion and its date of creation
        """
        ret = await self._device._write_readline(f"{self._id}VE")
        df = ["Unit ID", "Vers", "Creation Date"]
        ret = ret.split()
        ret[2] = " ".join(ret[2:])
        return dict(zip(df, ret))

    async def lock_display(self) -> dict:
        """
        Disables buttons on front of the device.

        Returns:
            dict: Data frame with lock status enabled
        """
        # Gets the format of the dataframe if it is not already known
        if self._df_format is None:
            await self.get_df_format()
        ret = await self._device._write_readline(f"{self._id}L")
        df = ret.split()
        for index in [idx for idx, s in enumerate(self._df_ret) if "decimal" in s]:
            df[index] = float(df[index])
        return dict(zip(self._df_format, df))

    async def manufacturing_info(self) -> list:
        """
        Gets info about device

        Returns:
            dict: Info on device, model, serial number, manufacturing, calibration, software
        """
        ret = await self._device._write_readall(f"{self._id}??M*")
        return ret

    async def remote_tare(self, actions: list = []) -> dict:
        """
        Gets the remote tare value
        Sets the remote tare effect. # Untested

        Args:
           actions (list): Actions to perform

        Returns:
            dict: Total value of Active Actions
        """
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
        df = ["Unit ID", "Active Actions Total"]
        ret = ret.split()
        return dict(zip(df, ret))

    async def restore_factory_settings(self) -> str:
        """
        Restores factory settings of the device. # Untested
        Removes any calibrations

        Returns:
            Confirmation of restoration
        """
        ret = await self._device._write_readline(f"{self._id}FACTORY RESTORE ALL")
        return ret

    async def user_data(self, slot: int = "", val: str = "") -> dict:
        """
        Gets the user data from the string is slot
        Sets the user data in slot to val. # Untested

        Args:
           slot (int): Slot number, 0 to 3
           val (str): 32-char ASCII string. Must be encoded.

        Returns:
            dict: Value in called slot (either new or read)
        """
        if isinstance(slot, int):
            slot = str(slot)
        ret = await self._device._write_readline(f"{self._id}UD {slot} {val}")
        if val == "":
            df = ["Unit ID", "Curr. Value"]
        else:
            df = ["Unit ID", "New Value"]
        ret = ret.split()
        return dict(zip(df, ret))

    async def streaming_rate(self, interval: float = "") -> dict:
        """
        Gets the streaming rate of the device.
        Sets the streaming rate of the device. # Untested

        Args:
           dinterval (float): Streaming rate in ms between data frames

        Returns:
            dict: Interval
        """
        ret = await self._device._write_readline(f"{self._id}NCS {interval}")
        df = ["Unit ID", "Interval (ms)"]
        ret = ret.split()
        return dict(zip(df, ret))

    async def unlock_display(self) -> dict:
        """
        Disables buttons on front of the device.

        Return:
            dict: Data Frame with LCK disabled
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
        self,
        name: str = "",
        number: int = "",
        gas1P: float = "",
        gas1N: str = "",
        gas2P: float = "",
        gas2N: str = "",
        gas3P: float = "",
        gas3N: str = "",
        gas4P: float = "",
        gas4N: str = "",
        gas5P: float = "",
        gas5N: str = "",
    ) -> dict:
        """
        Sets custom gas mixture. # Untested

        Args:
           name (str): Name of custom mixture
           number (int): 236 to 255. Gas is saved to this number

            n is the number (1 to 5) of the gas in the function call
           gas[n]P (float): Molar percent up to 2 decimals. Total percentages must sum to 100.00%
           gas[n]N (str): Name of gas in mixture

        Returns:
            dict: Gas number of new mix and percentages and names of each constituent
        """
        ret = await self._device._write_readline(
            f"{self._id}GM {name} {number} {gas1P} {gas1N} {gas2P} {gas2N} {gas3P} {gas3N} {gas4P} {gas4N} {gas5P} {gas5N}"
        )
        df = [
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
        ret = ret.split()
        return dict(zip(df, ret))

    async def delete_gas_mix(self, gasN: str = "") -> dict:
        """
        Deletes custom gas mixture. # Untested

        Args:
           gasN (str): Number of gas to delete

        Returns:
            dict: Deleted gas' number
        """
        ret = await self._device._write_readline(f"{self._id}GD {gasN}")
        df = ["Unit ID", "Deleted Gas Num"]
        ret = ret.split()
        return dict(zip(df, ret))

    async def query_gas_mix(self, gasN: int = ""):
        """
        Gets Percentages of gases in mixture. # Untested

        Args:
           gasN (int): nNumber of custom gas to analyze

        Returns:
            dict: Gas numbers and their percentages in mixture
        """
        ret = await self._device._write_readall(f"{self._id}GC {gasN}")
        df = [
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
        ret = ret.split()
        # Verify if this returns numbers or names
        return dict(zip(df, ret))

    async def config_totalizer(
        self,
        totalizer: int = 1,
        flow_stat_val: str = "",
        mode: int = "",
        limit_mode: int = "",
        num: int = "",
        dec: int = "",
    ):
        """
        Enables/Disables and Configures totalizer. # Untested

        Args:
           totalizer (int): 1 or 2, which totalizer used
           flow_stat_val (str): Statistic to measure. Use -1 to not change statistic
           mode (int):
           num (int): Value 7 to 10. How many digits in totalizer.
           dec (int): 0 to 9. How many digits after decimal.

        Returns:
            dict: COnfiguration of totalizer
        """
        if flow_stat_val != "":
            flow_stat_val = statistics.get(flow_stat_val, -1)
        ret = await self._device._write_readline(
            f"{self._id}TC {totalizer} {flow_stat_val} {mode} {limit_mode} {num} {dec}"
        )
        df = [
            "Unit ID",
            "Totalizer",
            "Flow Stat Val",
            "Mode",
            "Limit Mode",
            "num Digits",
            "Dec Place",
        ]
        ret = ret.split()
        return dict(zip(df, ret))  # Need to convert codes to text

    async def reset_totalizer(self, totalizer: int = 1) -> dict:
        """
        Returns totalizer count to zero and restarts timer. # Untested

        Args:
           totalizer (int): 1 or 2, which totalizer used

        Returns:
            dict: Dataframe with totalizer set to zero.
        """
        # Gets the format of the dataframe if it is not already known
        if self._df_format is None:
            await self.get_df_format()
        ret = await self._device._write_readline(f"{self._id}T {totalizer}")
        df = ret.split()
        for index in [idx for idx, s in enumerate(self._df_ret) if "decimal" in s]:
            df[index] = float(df[index])
        return dict(zip(self._df_format, df))

    async def reset_totalizer_peak(self, totalizer: int = 1) -> dict:
        """
        Returns totalizer count to zero and restarts timer. # Untested

        Args:
           totalizer (int): 1 or 2, which totalizer used

        Returns:
            dict: Dataframe
        """
        # Gets the format of the dataframe if it is not already known
        if self._df_format is None:
            await self.get_df_format()
        ret = await self._device._write_readline(f"{self._id}TP {totalizer}")
        df = ret.split()
        for index in [idx for idx, s in enumerate(self._df_ret) if "decimal" in s]:
            df[index] = float(df[index])
        return dict(zip(self._df_format, df))

    async def save_totalizer(self, enable: str = ""):
        """
        Enables/disables saving totalizer values. If enabled, restore last saved totalizer on power-up

        Args:
           enable (str): y/n

        Returns:
            dict: Says if enabled or disabled
        """
        enable = (
            "1"
            if enable.upper() in ["Y", "YES"]
            else "0"
            if enable.upper() in ["N", "NO"]
            else enable
        )
        ret = await self._device._write_readline(f"{self._id}TCR {enable}")
        df = ["Unit ID", "Saving"]
        ret = ret.split()
        output_mapping = {"1": "Enabled", "0": "Disabled"}
        ret[1] = output_mapping.get(str(ret[1]), ret[1])
        return dict(zip(df, ret))  # Need to convert codes to text

    async def canc_valve_hold(self):
        """
        Removes valve holds. # Untested

        Returns:
            dict: Dataframe
        """
        # Gets the format of the dataframe if it is not already known
        if self._df_format is None:
            await self.get_df_format()
        ret = await self._device._write_readline(f"{self._id}C")
        df = ret.split()
        for index in [idx for idx, s in enumerate(self._df_ret) if "decimal" in s]:
            df[index] = float(df[index])
        return dict(zip(self._df_format, df))

    async def exhaust(self):
        """
        Closes upstream valve, opens downstream valve 100% # Untested

        Returns:
            dict: Dataframe
        """
        # Gets the format of the dataframe if it is not already known
        if self._df_format is None:
            await self.get_df_format()
        ret = await self._device._write_readline(f"{self._id}E")
        df = ret.split()
        for index in [idx for idx, s in enumerate(self._df_ret) if "decimal" in s]:
            df[index] = float(df[index])
        return dict(zip(self._df_format, df))

    async def hold_valve(self):
        """
        Hold valves at current position # Untested

        Returns:
            dict: Dataframe
        """
        # Gets the format of the dataframe if it is not already known
        if self._df_format is None:
            await self.get_df_format()
        ret = await self._device._write_readline(f"{self._id}HP")
        df = ret.split()
        for index in [idx for idx, s in enumerate(self._df_ret) if "decimal" in s]:
            df[index] = float(df[index])
        return dict(zip(self._df_format, df))

    async def hold_valve_closed(self):
        """
        Close all valves # Untested

        Returns:
            dict: Dataframe
        """
        # Gets the format of the dataframe if it is not already known
        if self._df_format is None:
            await self.get_df_format()
        ret = await self._device._write_readline(f"{self._id}HC")
        df = ret.split()
        for index in [idx for idx, s in enumerate(self._df_ret) if "decimal" in s]:
            df[index] = float(df[index])
        return dict(zip(self._df_format, df))

    async def query_valve_drive_state(self):  # Why does this return 4 values?
        """
        Gets current percentage of total possible electricity to valve

        Returns:
            dict: Upstream valve, downstream valve, exhaust valve, fourth value
        """
        ret = await self._device._write_readline(f"{self._id}VD")
        df = ["Unit ID", "Valve 1 %", "Valve 2 %", "Valve 3 %", "Valve 4 %"]
        ret = ret.split()
        return dict(zip(df, ret))

    async def get_df_format(self) -> str:
        """
        Gets the format of the current dataframe format of the device
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
        """
        Gets the units of the current dataframe format of the device
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
        """
        Gets the value of a measurement from the device
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

    async def set(self, meas: str, param1: str, param2: str) -> dict:
        """
        Gets the value of a measurement from the device
        """
        resp = {}
        upper_meas = str(meas).upper()
        # Set gas - Param1 = value, Param2 = save
        if upper_meas == "GAS":
            resp.update(await self.gas(str(param1), str(param2)))
        # Set setpoint - Param1 = value, Param2 = unit
        elif upper_meas in ["SETPOINT", "STPT"]:
            resp.update(await self.setpoint(str(param1), str(param2)))
        # Set gas - Param1 = statistic
        elif upper_meas in ["LOOP", "LOOP CTRL"]:
            resp.update(await self.loop_control_var(str(param1)))
        return resp


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
