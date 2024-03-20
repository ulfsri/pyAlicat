from typing import Any, Union

import re
from abc import ABC

import trio
from comm import CommDevice, SerialDevice
from trio import run

import json

# from .device import Device

with open('codes.json', 'r') as f:
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
        # Add 150 ms to the given time
        ret = await self._device._write_readline(
            f"{self._id}DV {time} {' '.join(str(statistics[stat]) for stat in stats)}" # add a parameter for time out here
        )
        ret = ret.split()
        for idx in range(len(ret)):
            try:
                ret[idx] = float(ret[idx])
            except ValueError:
                pass
        return dict(zip(stats, ret))

    async def start_stream(self):
        """
        Starts streaming data from device.
        """
        await self._device._write(f"{self._id}@ @")
        return

    async def stop_stream(self, new_id: str = "A"):
        """
        Stops streaming data from device.
        """
        await self._device._write(f"@@ {new_id}")
        self.id = new_id
        return

    async def gas(self, gas: str = "", save: str = ""):
        """
        Gets the gas of the device.
        Sets the gas of the device.
        """
        gas = gases.get(gas, "")
        if not gas:
            save = ""
        ret = await self._device._write_readline(f"{self._id}GS {gas} {save}")
        df = ["Unit ID", "Gas Code", "Gas", "Gas Long"]
        return dict(zip(df, ret.split()))

    async def gas_list(self):
        """
        Gets the list of avaiable gases for the device.
        """
        ret = {}
        resp = await self._device._write_readall(f"{self._id}??G*")
        for gas in resp:
            gas = gas.split()
            ret[gas[1]] = gas[2]
        return ret

    async def setpoint(self, value: str = "", unit: str = ""):
        """
        Gets the setpoint of the device.
        Sets the setpoint of the device.
        """
        ret = await self._device._write_readline(f"{self._id}LS {value} {units[unit]}")
        df = ["Unit ID", "Current Setpt", "Requested Setpt", "Unit Code", "Unit Label"]
        return dict(zip(df, ret.split()))

    async def tare_abs_P(self):
        """
        Tares the absolute pressure of the device, zeros out the abs P reference point # Untested
        """
        # Gets the format of the dataframe if it is not already known
        if self._df_format is None:
            await self.get_df_format()
        ret = await self._device._write_readline(f"{self._id}PC")
        df = ret.split()
        for index in [idx for idx, s in enumerate(self._df_ret) if "decimal" in s]:
            df[index] = float(df[index])
        return dict(zip(self._df_format, df))

    async def tare_flow(self):
        """
        Creates a no-flow reference point # Untested
        """
        # Gets the format of the dataframe if it is not already known
        if self._df_format is None:
            await self.get_df_format()
        ret = await self._device._write_readline(f"{self._id}V")
        df = ret.split()
        for index in [idx for idx, s in enumerate(self._df_ret) if "decimal" in s]:
            df[index] = float(df[index])
        return dict(zip(self._df_format, df))

    async def tare_gauge_P(self):
        """
        Tares the gauge pressure of the device, zeros out the diff P reference point # Untested
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
        self, totalizer: str = "1", batch_vol: str = "", unit_vol: str = ""
    ):
        """
        Directs controller to flow a set amount then close the valve.   # Untested
        Must accept a totalizer value. Defaults to totalizer 1.
        set batch volume to size of desired flow. Set to 0 to disable batch.
        """
        ret = await self._device._write_readline(
            f"{self._id}TB {totalizer} {batch_vol} {unit_vol}"
        )
        df = ["Unit ID", "Totalizer", "Batch Size", "Unit Code", "Unit Label"]
        return dict(zip(df, ret.split()))

    async def deadband_limit(self, save: str = "", limit: str = ""):
        """
        Gets the range the controller allows for drift around setpoint
        Sets the range the controller allows for drift around setpoint # Untested
        """
        ret = await self._device._write_readline(f"{self._id}LCDB {save} {limit}")
        df = ["Unit ID", "Deadband", "Unit Code", "Unit Label"]
        return dict(zip(df, ret.split()))

    async def deadband_mode(self, mode: str = ""):
        """
        Gets the reaction the controller has for values around setpoint
        Sets the reaction the controller has for values around setpoint # Untested
        """
        ret = await self._device._write_readline(f"{self._id}LCDM {mode}")
        df = ["Unit ID", "Mode"]
        ret = ret.split()
        output_mapping = {"1": "Hold valve at current", "2": "Close valve"}
        ret[1] = output_mapping.get(str(ret[1]), ret[1])
        return dict(zip(df, ret))

    async def loop_control_alg(self, algorithm: str = ""):
        """
        Gets the control algorithm the controller uses
        Sets the control algorithm the controller uses # Untested
        algorithm 1 = PD/PDF, algorithm 2 = PD2I
        """
        ret = await self._device._write_readline(f"{self._id}LCA {algorithm}")
        df = ["Unit ID", "Algorithm"]
        ret = ret.split()
        algorithm_mapping = {"1": "PD/PDF", "2": "PD2I"}
        ret[1] = algorithm_mapping.get(str(ret[1]), ret[1])
        return dict(zip(df, ret))

    async def loop_control_var(self, var: str = ""):
        """
        Sets the statistic the setpoint controls
        """
        # If the user did not specify setpoint, assume Setpt
        if var[-6:] != "_Setpt":
            var += "_Setpt"
        ret = await self._device._write_readline(f"{self._id}LV {statistics[var]}")
        df = ["Unit ID", "Loop Var Val"]
        return dict(zip(df, ret.split()))

    async def loop_control_setpoint(
        self, var: str = "", unit: str = "", min: str = "", max: str = ""
    ):
        """
        Gets the control range of the statistic the setpoint controls
        Sets the control range of the statistic the setpoint controls # Untested
        """
        ret = await self._device._write_readline(
            f"{self._id}LR {var} {unit} {min} {max}"
        )
        df = ["Unit ID", "Loop Var", "Min", "Max", "Unit Code", "Unit Label"]
        ret = ret.split()
        ret[1] = next((code for code, value in statistics.items() if value == int(ret[1])), ret[1])
        return dict(zip(df, ret))

    async def max_ramp_rate(self, max: str = "", unit: str = ""):
        """
        Gets how fast controller moves to new setpoint
        Sets how fast controller moves to new setpoint # Untested
        max = 0 to disable ramping (still must include unit)
        """
        ret = await self._device._write_readline(f"{self._id} SR {max} {unit}")
        df = ["Unit ID", "Max Ramp Rate", "Unit Code", "Time Code", "Units"]
        return dict(zip(df, ret.split()))

    async def pdf_gains(self, save: str = "", p_gain="", d_gain=""):
        """
        Gets the proportional and intregral gains of the PD/PDF controller
        Sets the proportional and intregral gains of the PD/PDF controller # Untested
        """
        save = f"0 {save}" if save else save
        ret = await self._device._write_readline(
            f"{self._id}LCGD {save} {p_gain} {d_gain}"
        )
        df = ["Unit ID", "P  Gain", "D Gain"]
        return dict(zip(df, ret.split()))

    async def pd2i_gains(self, save: str = "", p_gain="", i_gain="", d_gain=""):
        """
        Gets the proportional, intregral, and derivative gains of the PD2I controller
        Sets the proportional, intregral, and derivative gains of the PD2I controller # Untested
        """
        save = f"0 {save}" if save else save
        ret = await self._device._write_readline(
            f"{self._id} LCG {save} {p_gain} {i_gain} {d_gain}"
        )
        df = ["Unit ID", "P  Gain", "I Gain", "D Gain"]
        return dict(zip(df, ret.split()))

    async def power_up_setpoint(self, val: str = ""):
        """
        Enables immediate setpoint on power-up # Untested
        val = 0 to disable start-up setpoint
        """
        # Gets the format of the dataframe if it is not already known
        if self._df_format is None:
            await self.get_df_format()
        ret = await self._device._write_readline(f"{self._id}SPUE {val}")
        df = ret.split()
        for index in [idx for idx, s in enumerate(self._df_ret) if "decimal" in s]:
            df[index] = float(df[index])
        return dict(zip(self._df_format, df))

    async def overpressure(self, limit: str = ""):
        """
        Sets the overpressure limit of the device. # Untested
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
    ):
        """
        Gets the ramp settings of the device.
        Sets the ramp settings of the device. # Untested
        """
        ret = await self._device._write_readline(
            f"{self._id} LSRC {up} {down} {zero} {power_up}"
        )
        df = ["Unit ID", "Ramp Up", "Ramp Down", "Zero Ramp", "Power Up Ramp"]
        ret = ret.split()
        output_mapping = {"1": "Enabled", "0": "Disabled"}
        ret = [output_mapping.get(str(val), val) for val in ret]
        return dict(zip(df, ret))

    async def setpoint_source(self, mode: str = ""):
        """
        Gets how the setpoint is given to the controller
        Sets how the setpoint is given to the controller # Untested
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
        self, save: str = "", initial_offset: str = "", closed_offset: str = ""
    ):
        """
        Gets how much power driven to valve when first opened or considered closed
        Sets how much power driven to valve when first opened or considered closed # Untested
        """
        save = f"0 {save}" if save else save
        ret = await self._device._write_readline(
            f"{self._id}LCVO {save} {initial_offset} {closed_offset}"
        )
        df = ["Unit ID", "Init Offser (%)", "Closed Offset (%)"]
        ret = ret.split()
        return dict(zip(df, ret))

    async def zero_pressure_control(self, enable: str = ""):
        """
        Gets how controller reacts to 0 Pressure setpoint
        Sets how controller reacts to 0 Pressure setpoint # Untested
        """
        ret = await self._device._write_readline(f"{self._id}LCZA {enable}")
        df = ["Unit ID", "Active Ctrl"]
        ret = ret.split()
        output_mapping = {"1": "Enabled", "0": "Disabled"}
        ret[1] = output_mapping.get(str(ret[1]), ret[1])
        return dict(zip(df, ret))

    async def auto_tare(self, enable: str = "", delay: str = ""):
        """
        Gets if the controller auto tares
        Sets if the controller auto tares # Untested
        """
        ret = await self._device._write_readline(f"{self._id}ZCA {enable} {delay}")
        df = ["Unit ID", "Auto-tare", "Delay (s)"]
        ret = ret.split()
        output_mapping = {"1": "Enabled", "0": "Disabled"}
        ret[1] = output_mapping.get(str(ret[1]), ret[1])
        return dict(zip(df, ret))

    async def configure_data_frame(self, format: str = ""):
        """
        Sets data frame's format # Untested
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
        unit_val: str = "",
        override: str = "",
    ):
        """
        Gets units for desired statistics
        Sets units for desired statistics # Untested
        """
        group = "1" if group.upper() in ["Y", "YES"] else "0" if group.upper() in ["N", "NO"] else group
        override = "1" if override.upper() in ["Y", "YES"] else ""
        ret = await self._device._write_readline(
            f"{self._id}DCU {statistics[statistic_value]} {group} {units[unit_val]} {override}"
        )
        df = ["Unit ID", "Unit Code", "Unit Label"]
        ret = ret.split()
        return dict(zip(df, ret))

    async def flow_press_avg(
        self,
        stat_val: str = "",
        avg_time: str = "",
    ):
        """
        Gets average value of statistic
        Sets time statistic is averaged over # Untested
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

    async def full_scale_val(self, stat_val: str = "", unit_val: str = ""):
        """
        Gets measurement range of given statistic
        """
        ret = await self._device._write_readline(
            f"{self._id}FPF {statistics[stat_val]} {units[unit_val]}"
        )
        df = ["Unit ID", "Max Value", "Unit Code", "Unit Label"]
        ret = ret.split()
        return dict(zip(df, ret))

    async def power_up_tare(self, enable: str = ""):
        """
        Gets if device tares on power-up
        Sets if device tares on power-up
        """
        enable = "1" if enable.upper() in ["Y", "YES"] else "0" if enable.upper() in ["N", "NO"] else enable
        ret = await self._device._write_readline(f"{self._id}ZCP {enable}")
        df = ["Unit ID", "Power-Up Tare"]
        ret = ret.split()
        output_mapping = {"1": "Enabled", "0": "Disabled"}
        ret[1] = output_mapping.get(str(ret[1]), ret[1])
        return dict(zip(df, ret))

    async def data_frame(self):
        """
        Gets info about current data frame
        """
        ret = await self._device._write_readall(f"{self._id}??D*")
        return ret

    async def stp_press(self, stp: str = "S", unit: str = "", press: str = ""):
        """
        Gets pressure reference point.
        Sets pressure reference point. # Untested
        To get Normal pressure reference point, set stp to N
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

    async def stp_temp(self, stp: str = "S", unit: str = "", temp: str = ""):
        """
        Gets temperature reference point.
        Sets temperature reference point. # Untested
        To get Normal pressure reference point, set stp to N
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

    async def zero_band(self, zb: str = ""):
        """
        Gets the zero band of the device.
        Sets the zero band of the device. # Untested
        """
        ret = await self._device._write_readline(f"{self._id}DCZ {zb}")
        df = ["Unit ID", "Zero Band (%)"]
        ret = ret.split()
        ret.pop(1)
        return dict(zip(df, ret))

    async def analog_out_source(
        self, primary: str = "0", val: str = "", unit: str = ""
    ):
        """
        Gets the source of the analog output.
        Sets the source of the analog output. # Untested
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

    async def baud(self, new_baud: str = ""):
        """
        Gets the baud rate of the device.
        Sets the baud rate of the device. # Untested
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
        """
        if type(dur) == int:
            dur = str(dur)
        ret = await self._device._write_readline(f"{self._id}FFP {dur}")
        df = ["Unit ID", "Flashing?"]
        ret = ret.split()
        output_mapping = {"1": "Yes", "0": "No"}
        ret[1] = output_mapping.get(str(ret[1]), ret[1])
        return dict(zip(df, ret))

    async def change_unit_id(self, new_id: str = ""):
        """
        Sets the unit ID of the device. # Untested
        """
        ret = await self._device._write_readline(f"{self._id}@ {new_id}")
        self.id = new_id
        return ret

    async def firmware_version(self):
        """
        Gets the firmware version of the device.
        """
        ret = await self._device._write_readline(f"{self._id}VE")
        df = ["Unit ID", "Vers", "Creation Date"]
        ret = ret.split()
        ret[2] = " ".join(ret[2:])
        return dict(zip(df, ret))

    async def lock_display(self):
        """
        Disables buttons on front of the device.
        """
        # Gets the format of the dataframe if it is not already known
        if self._df_format is None:
            await self.get_df_format()
        ret = await self._device._write_readline(f"{self._id}L")
        df = ret.split()
        for index in [idx for idx, s in enumerate(self._df_ret) if "decimal" in s]:
            df[index] = float(df[index])
        return dict(zip(self._df_format, df))

    async def manufacturing_info(self):
        """
        Gets info about current data frame
        """
        ret = await self._device._write_readall(f"{self._id}??M*")
        return ret

    async def remote_tare(self, actions: list = []):
        """
        Gets the remote tare value
        Sets the remote tare effect. # Untested
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

    async def restore_factory_settings(self):
        """
        Restores factory settings of the device. # Untested
        """
        ret = await self._device._write_readline(f"{self._id}FACTORY RESTORE ALL")
        return ret

    async def user_data(self, slot: str = "", val: str = ""):
        """
        Gets the user data of the device.
        Sets the user data in slot to val. # Untested
        """
        if type(slot) == int:
            slot = str(slot)
        ret = await self._device._write_readline(f"{self._id}UD {slot} {val}")
        if val == "":
            df = ["Unit ID", "Curr. Value"]
        else:
            df = ["Unit ID", "New Value"]
        ret = ret.split()
        return dict(zip(df, ret))

    async def streaming_rate(self, interval: str = ""):
        """
        Gets the streaming rate of the device.
        Sets the streaming rate of the device. # Untested
        """
        ret = await self._device._write_readline(f"{self._id}NCS {interval}")
        df = ["Unit ID", "Interval (ms)"]
        ret = ret.split()
        return dict(zip(df, ret))

    async def unlock_display(self):
        """
        Disables buttons on front of the device.
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
        number: str = "",
        gas1P: str = "",
        gas1N: str = "",
        gas2P: str = "",
        gas2N: str = "",
        gas3P: str = "",
        gas3N: str = "",
        gas4P: str = "",
        gas4N: str = "",
        gas5P: str = "",
        gas5N: str = "",
    ):
        """
        Sets custom gas mixture. # Untested
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

    async def delete_gas_mix(self, gasN: str = ""):
        """
        Deletes custom gas mixture. # Untested
        """
        ret = await self._device._write_readline(f"{self._id}GD {gasN}")
        df = ["Unit ID", "Deleted Gas Num"]
        ret = ret.split()
        return dict(zip(df, ret))

    async def query_gas_mix(self, gasN: str = ""):
        """
        Gets Percentages of gases in mixture. # Untested
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
        return dict(zip(df, ret))

    async def config_totalizer(
        self,
        totalizer: str = "1",
        flow_stat_val="",
        mode="",
        lmit_mode="",
        num="",
        dec="",
    ):
        """
        Configures totalizer. # Untested
        """
        ret = await self._device._write_readline(
            f"{self._id}TC {totalizer} {flow_stat_val} {mode} {lmit_mode} {num} {dec}"
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

    async def reset_totalizer(self, totalizer: str = "1"):
        """
        Returns totalizer count to zero and restarts timer. # Untested
        """
        # Gets the format of the dataframe if it is not already known
        if self._df_format is None:
            await self.get_df_format()
        ret = await self._device._write_readline(f"{self._id}T {totalizer}")
        df = ret.split()
        for index in [idx for idx, s in enumerate(self._df_ret) if "decimal" in s]:
            df[index] = float(df[index])
        return dict(zip(self._df_format, df))

    async def reset_totalizer_peak(self, totalizer: str = "1"):
        """
        Returns totalizer count to zero and restarts timer. # Untested
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
        Enables/disables saving totalizer values.
        """
        ret = await self._device._write_readline(f"{self._id}TCR {enable}")
        df = ["Unit ID", "Saving"]
        ret = ret.split()
        output_mapping = {"1": "Enabled", "0": "Disabled"}
        ret[1] = output_mapping.get(str(ret[1]), ret[1])
        return dict(zip(df, ret))  # Need to convert codes to text

    async def canc_valve_hold(self):
        """
        Removes valve holds. # Untested
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
        while i*13 < len(reqs):
            resp.update(await self.request(reqs[13*i:13+13*i]))
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
