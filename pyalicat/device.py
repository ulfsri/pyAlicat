from typing import Any, Union

import re
from abc import ABC

import trio
from comm import CommDevice, SerialDevice
from trio import run

statistics = {
    "Batch mass remain.": 12,
    "Batch vol remain.": 11,
    "Batch vol ext remain.": 19,
    "Mass Flow": 5,
    "Mass Flow avg": 69,
    "Mass Flow max": 175,
    "Mass Flow min": 174,
    "Mass Flow Peak": 101,
    "Mass Flow Setpt": 37,
    "Mass Flow Setpt err": 173,
    "Totalizing Time": 10,
    "Tot Mass": 9,
    "Tot Vol": 8,
    "Tot Vol Ext": 18,
    "Volu Flow": 4,
    "Volu Flow avg": 68,
    "Volu Flow max": 167,
    "Volu Flow min": 166,
    "Volu Flow Peak": 100,
    "Volu Flow Setpt": 36,
    "Volu Flow Setpt err": 165,
    "Vol Flow Ext": 17,
    "Vol Flow Ext avg": 81,
    "Vol Flow Ext max": 271,
    "Vol Flow Ext min": 270,
    "Vol Flow Ext Peak": 113,
    "Vol Flow Ext Setpt": 49,
    "Vol Flow Ext Setpt err": 268,
    "Abs Press": 2,
    "Abs Press avg": 66,
    "Abs Press max": 151,
    "Abs Press min": 150,
    "Abs Press Peak": 98,
    "Abs Press Setpt": 34,
    "Abs Press Setpt err": 149,
    "Baro Press": 15,
    "Baro Press Avg": 79,
    "Baro Press Max": 255,
    "Baro Press Min": 254,
    "Baro Press Peak": 111,
    "Diff Press": 7,
    "Diff Press max": 191,
    "Diff Press min": 190,
    "Diff Press Setpt": 39,
    "Diff Press Setpt err": 189,
    "Gauge Press": 6,
    "Gauge Press avg": 70,
    "Gauge Press max": 183,
    "Gauge Press min": 182,
    "Gauge Press Peak": 102,
    "Gauge Press Setpt": 38,
    "Gauge Press Setpt err": 181,
    "2nd Abs Press": 344,
    "2nd Abs Press max": 351,
    "2nd Abs Press min": 350,
    "2nd Abs Press Setpt": 345,
    "2nd Abs Press Setpt err": 349,
    "2nd Diff Press": 360,
    "2nd Diff Press max": 367,
    "2nd Diff Press min": 366,
    "2nd Diff Press Setpt": 361,
    "2nd Diff Press Setpt err": 365,
    "2nd Gauge Press": 352,
    "2nd Gauge Press max": 359,
    "2nd Gauge Press min": 358,
    "2nd Gauge Press Setpt": 353,
    "2nd Gauge Press Setpt err": 357,
    "None": 1,
    "User Date": 400,
    "Fluid Name": 703,
    "Meas ID": 801,
    "Meas Stat": 802,
    "Setpt": 32,
    "Setpt err": 133,
    "Status": 26,
    "Temp Ext": 16,
    "Temp Ext max": 263,
    "Temp Ext min": 262,
    "Flow Temp": 3,
    "Flow Temp max": 159,
    "Flow Temp min": 158,
    "Flow Temp avg": 67,
    "Ext Vol Flow Ref Temp": 20,
    "Ext Vol Flow Ref Temp avg": 84,
    "Ext Vol Flow Ref Temp max": 295,
    "Ext Vol Flow Ref Temp min": 294,
    "Ext Vol Flow Ref Temp Peak": 116,
    "Ext Vol Flow Ref Temp Src": 21,
    "Ext Vol Flow Ref Temp Src avg": 85,
    "Remain. Time Meas.": 14,
    "User Time": 392,
    "Valve Drive": 13,
    "Valve Drive Setpt": 45,
    "Rel Hum": 25,
    "Rel Hum avg": 89,
    "Rel Hum max": 335,
    "Rel Hum min": 334,
    "Rel Hum Peak": 121,
}

units = {
    "": "",
    "default": 0,
    "unknown": 1,
    "SμL/m": 2,
    "std microliter per min": 2,
    "SmL/s": 3,
    "std milliliter per sec": 3,
    "S mL/m": 4,
    "std milliliter per min": 4,
    "S mL/h": 5,
    "std milliliter per hour": 5,
    "SL/s": 6,
    "std liter per sec": 6,
    "SLPM": 7,
    "std liter per min": 7,
    "S L/h": 8,
    "std liter per hour": 8,
    "SCCS": 11,
    "std cubic cm per sec": 11,
    "SCCM": 12,
    "std cubic cm per min": 12,
    "Scm3/h": 13,
    "std cubic cm per hour": 13,
    "Sm3/m": 14,
    "std cubic meter per min": 14,
    "Sm3/h": 15,
    "std cubic meter per hour": 15,
    "Sm3/d": 16,
    "std cubic meter per day": 16,
    "Sin3/m": 17,
    "std cubic inch per min": 17,
    "SCFM": 18,
    "std cubic foot per min": 18,
    "SCFH": 19,
    "std cubic foot per hour": 19,
    "SCFD": 21,
    "std cubic foot per day": 21,
    "kSCFM": 20,
    "1000 std cbft per min": 20,
    "NμL/m": 32,
    "norm microliter per min": 32,
    "NmL/s": 33,
    "norm milliliter per sec": 33,
    "NmL/m": 34,
    "norm milliliter per min": 34,
    "NmL/h": 35,
    "norm milliliter per hour": 35,
    "NL/s": 36,
    "norm liter per sec": 36,
    "NLPM": 37,
    "norm liter per min": 37,
    "NL/h": 38,
    "norm liter per hour": 38,
    "NCCS": 41,
    "norm cubic cm per sec": 41,
    "NCCM": 42,
    "norm cubic cm per min": 42,
    "Ncm3/h": 43,
    "norm cubic meter per hour": 43,
    "Nm3/m": 44,
    "norm cubic meter per min": 44,
    "Nm3/h": 45,
    "norm cubic meter per hour": 45,
    "Nm3/d": 46,
    "norm cubic meter per day": 46,
    "count": 62,
    "%": 63,
    "mg/s": 64,
    "milligram per sec": 64,
    "mg/m": 65,
    "milligram per min": 65,
    "g/s": 66,
    "gram per sec": 66,
    "g/m": 67,
    "gram per min": 67,
    "g/h": 68,
    "gram per hour": 68,
    "kg/m": 69,
    "kilogram per min": 69,
    "kg/h": 70,
    "kilogram per hour": 70,
    "oz/s": 71,
    "ounce per sec": 71,
    "oz/m": 72,
    "ounce per min": 72,
    "lb/m": 73,
    "pound per min": 73,
    "lb/h": 74,
    "pound per hour": 74,
    "SμL": 2,
    "std microliter": 2,
    "SmL": 3,
    "std milliliter": 3,
    "SL": 4,
    "std liter": 4,
    "Scm3": 6,
    "std cubic cm": 6,
    "Sm3": 7,
    "std cubic meter": 7,
    "Sin3": 8,
    "std cubic inch": 8,
    "Sft3": 9,
    "std cubic foot": 9,
    "kSft3": 10,
    "std 1000 cubic foot": 10,
    "NμL": 32,
    "normal microliter": 32,
    "NmL": 33,
    "normal milliliter": 33,
    "NL": 34,
    "normal liter": 34,
    "Ncm3": 36,
    "normal cubic cm": 36,
    "Nm3": 37,
    "normal cubic meter": 37,
    "μL/m": 2,
    "microliter per min": 2,
    "mL/s": 3,
    "milliliter per sec": 3,
    "mL/m": 4,
    "milliliter per min": 4,
    "mL/h": 5,
    "milliliter per hour": 5,
    "L/s": 6,
    "liter per sec": 6,
    "LPM": 7,
    "liter per min": 7,
    "L/h": 8,
    "liter per hour": 8,
    "GPM": 9,
    "gallon per min": 9,
    "GPH": 10,
    "gallon per hour": 10,
    "CCS": 11,
    "cubic cm per sec": 11,
    "CCM": 12,
    "cubic cm per min": 12,
    "cm3/h": 13,
    "cubic cm per hour": 13,
    "m3/m": 14,
    "cubic meter per min": 14,
    "m3/h": 15,
    "cubic meter per hour": 15,
    "m3/d": 16,
    "cubic meter per day": 16,
    "in3/m": 17,
    "cubic inch per min": 17,
    "CFM": 18,
    "cubic foot per min": 18,
    "CFH": 19,
    "cubic foot per hour": 19,
    "CFD": 21,
    "cubic foot per day": 21,
    "μL": 2,
    "microliter": 2,
    "mL": 3,
    "milliliter": 3,
    "L": 4,
    "liter": 4,
    "GAL": 5,
    "gallon": 5,
    "cm3": 6,
    "cubic cm": 6,
    "m3": 7,
    "cubic meter": 7,
    "in3": 8,
    "cubic inch": 8,
    "ft3": 9,
    "cubic foot": 9,
    "μP": 61,
    "micropoise": 61,
    "Pa": 2,
    "pascal": 2,
    "hPa": 3,
    "hectopascal": 3,
    "kPa": 4,
    "kilopascal": 4,
    "MPa": 5,
    "megapascal": 5,
    "mbar": 6,
    "millibar": 6,
    "bar": 7,
    "g/cm2": 8,
    "gram per square cm": 8,
    "kg/cm2": 9,
    "kilogram per square cm": 9,
    "PSI": 10,
    "pound per square inch": 10,
    "PSF": 11,
    "pound per square foot": 11,
    "mTorr": 12,
    "millitorr": 12,
    "torr": 13,
    "mmHg": 14,
    "millimeter of mercury": 14,
    "inHg": 15,
    "inch of mercury": 15,
    "mmH2O": 16,
    "millimeter of water": 16,
    "millimeter of water @ 60F": 17,
    "cmH2O": 18,
    "centimeter of water": 18,
    "centimeter of water @ 60F": 19,
    "inH2O": 20,
    "inch of water": 20,
    "inch of water @ 60F": 21,
    "atm": 22,
    "atmosphere": 22,
    "V": 61,
    "volt": 61,
    "C": 2,
    "Celsius": 2,
    "F": 3,
    "Fahrenheit": 3,
    "K": 4,
    "Kelvin": 4,
    "Ra": 5,
    "Rankine": 5,
    "h:m:s": 2,
    "hours:minutes:seconds": 2,
    "ms": 3,
    "millisecond": 3,
    "s": 4,
    "second": 4,
    "m": 5,
    "minute": 5,
    "h": 6,
    "hour": 6,
    "d": 7,
    "day": 7,
}

gases = {
    "Air": 0,
    "Argon": 1,
    "Ar": 1,
    "Methane": 2,
    "CH4": 2,
    "Carbon Monoxide": 3,
    "CO": 3,
    "Carbon Dioxide": 4,
    "CO2": 4,
    "Ethane": 5,
    "C2H6": 5,
    "Hydrogen": 6,
    "H2": 6,
    "Helium": 7,
    "He": 7,
    "Nitrogen": 8,
    "N2": 8,
    "Nitrous Oxide": 9,
    "N2O": 9,
    "Neon": 10,
    "Ne": 10,
    "Oxygen": 11,
    "O2": 11,
    "Propane": 12,
    "C3H8": 12,
    "Butane": 13,
    "C4H10": 13,
    "Acetylene": 14,
    "C2H2": 14,
    "Ethylene": 15,
    "C2H4": 15,
    "Isobutane": 16,
    "i-C4H10": 16,
    "Krypton": 17,
    "Kr": 17,
    "Xenon": 18,
    "Xe": 18,
    "Sulfur Hexafluoride": 19,
    "SF6": 19,
    "25% CO2, 75% Ar": 20,
    "C-25": 20,
    "10% CO2, 90% Ar": 21,
    "C-10": 21,
    "8% CO2, 92% Ar": 22,
    "C-8": 22,
    "2% CO2, 98% Ar": 23,
    "C-2": 23,
    "75% CO2, 25% Ar": 24,
    "C-75": 24,
    "25% He, 75% Ar": 25,
    "He-25": 25,
    "75% He, 25% Ar": 26,
    "He-75": 26,
    "90% He, 7.5% Ar, 2.5% CO2": 27,
    "A1025": 27,
    "Stargon CS": 28,
    "Star29": 28,
    "5% CH4, 95% Ar": 29,
    "P-5": 29,
    "Nitric Oxide": 30,
    "NO": 30,
    "Nitrogen Trifluoride": 31,
    "NF3": 31,
    "Ammonia": 32,
    "NH3": 32,
    "Chlorine": 33,
    "Cl2": 33,
    "Hydrogen Sulphide": 34,
    "H2S": 34,
    "Sulfur Dioxide": 35,
    "SO2": 35,
    "Propylene": 36,
    "C3H6": 36,
    "1-Butylene": 80,
    "1Butene": 80,
    "Cis-Butene": 81,
    "cButene": 81,
    "Isobutene": 82,
    "iButen": 82,
    "Trans-2-Butene": 83,
    "tButen": 83,
    "Carbonyl Sulfide": 84,
    "COS": 84,
    "Dimethylether": 85,
    "C2H6O": 85,
    "DMES": 85,
    "Silane": 86,
    "SiH4": 86,
    "Trichlorofluoromethane": 100,
    "CCl3F": 100,
    "R-11": 100,
    "Chloroppentafluoroethane": 101,
    "C2ClF5": 101,
    "R-115": 101,
    "Hexafluoroethane": 102,
    "C2F6": 102,
    "R-116": 102,
    "Chlorotetrafluoroethane": 103,
    "C2HClF4": 103,
    "R-124": 103,
    "Pentafluoroethane": 104,
    "CF3CHF2": 104,
    "R-125": 104,
    "Tetrafluoroethane": 105,
    "CH2FCF3": 105,
    "R-134A": 105,
    "Tetrafluoromethane": 106,
    "CF4": 106,
    "R-14": 106,
    "Chlorodifluoroethane": 107,
    "CH3CClF2": 107,
    "R-142B": 107,
    "Trifluoroethane": 108,
    "C2H3F3": 108,
    "R-143A": 108,
    "Difluoroethane": 109,
    "C2H4F2": 109,
    "R-152A": 109,
    "Difluoromonochloromethane": 110,
    "CHClF2": 110,
    "R-22": 110,
    "Trifluoromethane": 111,
    "CHF3": 111,
    "R-23": 111,
    "Difluoromethane": 112,
    "CH2F2": 112,
    "R-32": 112,
    "Octafluorocyclobutane": 113,
    "C4F8": 113,
    "R-318": 113,
    "44% R-125, 4% R-134A, 52% R-143A": 114,
    "R-404A": 114,
    "23% R-32, 25% R-125, 52% R-143A": 115,
    "R-407C": 115,
    "50% R-32, 50 R-125": 116,
    "R-410A": 116,
    "50% R-125, 50% R-143A": 117,
    "15% CO2, 85% Ar": 140,
    "C-15": 140,
    "20% CO2, 80% Ar": 141,
    "C-20": 141,
    "50% CO2, 50% Ar": 142,
    "C-50": 142,
    "50% He, 50% Ar": 143,
    "He-50": 143,
    "90% He, 10% Ar": 144,
    "He-90": 144,
    "5% CH4, 95% CO2": 145,
    "Bio5M": 145,
    "10% CH4, 90% CO2": 146,
    "Bio10M": 146,
    "15% CH4, 85% CO2": 147,
    "Bio15M": 147,
    "20% CH4, 80% CO2": 148,
    "Bio20M": 148,
    "25% CH4, 75% CO2": 149,
    "Bio25M": 149,
    "30% CH4, 70% CO2": 150,
    "Bio30M": 150,
    "35% CH4, 65% CO2": 151,
    "Bio35M": 151,
    "40% CH4, 60% CO2": 152,
    "Bio40M": 152,
    "45% CH4, 55% CO2": 153,
    "Bio45M": 153,
    "50% CH4, 50% CO2": 154,
    "Bio50M": 154,
    "55% CH4, 45% CO2": 155,
    "Bio55M": 155,
    "60% CH4, 40% CO2": 156,
    "Bio60M": 156,
    "65% CH4, 35% CO2": 157,
    "Bio65M": 157,
    "70% CH4, 30% CO2": 158,
    "Bio70M": 158,
    "75% CH4, 25% CO2": 159,
    "Bio75M": 159,
    "80% CH4, 20% CO2": 160,
    "Bio80M": 160,
    "85% CH4, 15% CO2": 161,
    "Bio85M": 161,
    "90% CH4, 10% CO2": 162,
    "Bio90M": 162,
    "95% CH4, 5% CO2": 163,
    "Bio95M": 163,
    "32% O2, 68% N2": 164,
    "EAN-32": 164,
    "36% O2, 64% N2": 165,
    "EAN-36": 165,
    "40% O2, 60% N2": 166,
    "EAN-40": 166,
    "20% O2, 80% He": 167,
    "HeOx20": 167,
    "21% O2, 79% He": 168,
    "HeOx21": 168,
    "30% O2, 70% He": 169,
    "HeOx30": 169,
    "40% O2, 60% He": 170,
    "HeOx40": 170,
    "50% O2, 50% He": 171,
    "HeOx50": 171,
    "60% O2, 40% He": 172,
    "HeOx60": 172,
    "80% O2, 20% He": 173,
    "HeOx80": 173,
    "99% O2, 1% He": 174,
    "HeOx99": 174,
    "Enriched Air 40% O2": 175,
    "EA-40": 175,
    "Enriched Air 60% O2": 176,
    "EA-60": 176,
    "Enriched Air 80% O2": 177,
    "EA-80": 177,
    "Metab": 178,
    "Metabolic Exhalant": 178,
    "16% O2, 78.04% N2, 5% CO2, 0.96% Ar": 178,
    "4.5% CO2, 13.5% N2, 82% He": 179,
    "LG-4.5": 179,
    "6% CO2, 14% N2, 80% He": 180,
    "LG-6": 180,
    "7% CO2, 14% N2, 79% He": 181,
    "LG-7": 181,
    "9% CO2, 15% N2, 76% He": 182,
    "LG-9": 182,
    "9% Ne, 91% He": 183,
    "HeNe9": 183,
    "9.4% CO2, 19.25% N2, 71.35% He": 184,
    "LG-9.4": 184,
    "40% H2, 29% CO, 20% CO2, 11% CH4": 185,
    "SynG-1": 185,
    "64% H2, 28% CO, 1% CO2, 7% CH4": 186,
    "SynG-2": 186,
    "70% H2, 4% CO, 25% CO2, 1% CH4": 187,
    "SynG-3": 187,
    "83% H2, 14% CO, 3% CH4": 188,
    "SynG-4": 188,
    "93% CH4, 3% C2H6, 1% C3H8, 2% N2, 1% CO2": 189,
    "NatG-1": 189,
    "95% CH4, 3% C2H6, 1% N2, 1% CO2": 190,
    "NatG-2": 190,
    "95.2% CH4, 2.5% C2H6, 0.2% C3H8, 0.1% C4H10, 1.3% N2, 0.7% CO2": 191,
    "NatG-3": 191,
    "50% H2, 35% CH4, 10% CO, 5% C2H4": 192,
    "CoalG": 192,
    "75% H2, 25% N2": 193,
    "Endo": 193,
    "66.67% H2, 33.33% O2": 194,
    "HHO": 194,
    "LPG: 96.1% C3H8, 1.5% C2H6, 0.4% C3H6, 1.9% n-C4H10": 195,
    "HD-5": 195,
    "LPG: 85% C3H8, 10% C3H6, 5% n-C4H10": 196,
    "HD-10": 196,
    "89% O2, 7% N2, 4% Ar": 197,
    "OCG-89": 197,
    "93% O2, 3% N2, 4% Ar": 198,
    "OCG-93": 198,
    "95% O2, 1% N2, 4% Ar": 199,
    "OCG-95": 199,
    "2.5% O2, 10.8% CO2, 85.7% N2, 1% Ar": 200,
    "FG-1": 200,
    "2.9% O2, 14% CO2, 82.1% N2, 1% Ar": 201,
    "FG-2": 201,
    "3.7% O2, 15% CO2, 80.3% N2, 1% Ar": 202,
    "FG-3": 202,
    "7% O2, 12% CO2, 80% N2, 1% Ar": 203,
    "FG-4": 203,
    "10% O2, 9.5% CO2, 79.5% N2, 1% Ar": 204,
    "FG-5": 204,
    "13% O2, 7% CO2, 79% N2, 1% Ar": 205,
    "FG-6": 205,
    "10% CH4, 90% Ar": 206,
    "P-10": 206,
    "Deuterium": 210,
    "D-2": 210,
}

loop_var = {
    34: "Abs Press",
    345: "2nd Abs Press",
    39: "Press Diff",
    361: "2nd Press Diff",
    38: "Gauge Press",
    353: "2nd Gauge Press",
    37: "Mass Flow",
    36: "Vol Flow",
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
    # print(dev_info)
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

    async def poll(self) -> dict:
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

    async def request(self, time: str, stats: list) -> dict:
        """
        Gets specified values averaged over specified time.
        time in ms
        """
        if self._df_format is None:
            await self.get_df_format()
        append = "DV " + str(time)
        for stat in stats:
            append = append + " " + str(statistics[stat])
        ret = await self._device._write_readline(self._id + append)
        ret = ret.split()
        for idx in range(len(ret)):
            try:
                ret[idx] = float(ret[idx])
            except ValueError:
                ret[idx] = ret[idx]
        return dict(zip(stats, ret))

    async def start_stream(self):  # Untested
        """
        Starts streaming data from device.
        """
        await self._device._write_readline(self._id + "@ @")
        return

    async def stop_stream(self, new_id: str = "B"):  # Untested
        """
        Stops streaming data from device.
        """
        await self._device._write_readline("@@" + new_id)
        self.id = new_id
        return

    async def gas(self, gas: str = "", save: str = ""):
        """
        Gets the gas of the device.
        Sets the gas of the device.  # Untested
        """
        try:
            gas = gases[gas]
        except KeyError:
            gas = gas
        ret = await self._device._write_readline(self._id + "GS " + gas + " " + save)
        return ret

    async def gas_list(self):
        """
        Gets the list of avaiable gases for the device.
        """
        ret = await self._device._write_readall(self._id + "??G*")
        return ret

    async def setpoint(self, value: str = "", unit: str = ""):
        """
        Gets the setpoint of the device.
        Sets the setpoint of the device.  # Untested
        """
        ret = await self._device._write_readline(
            self._id + "LS " + value + " " + units[unit]
        )
        df = ["Unit ID", "Current Setpt", "Requested Setpt", "Unit Code", "Unit Label"]
        return dict(zip(df, ret.split()))

    async def tare_abs_P(self):
        """
        Tares the absolute pressure of the device, zeros out the abs P reference point # Untested
        """
        ret = await self._device._write_readline(self._id + "PC")
        df = ret.split()
        for index in [idx for idx, s in enumerate(self._df_ret) if "decimal" in s]:
            df[index] = float(df[index])
        return dict(zip(self._df_format, df))

    async def tare_flow(self):
        """
        Creats a no-flow reference point # Untested
        """
        ret = await self._device._write_readline(self._id + "V")
        df = ret.split()
        for index in [idx for idx, s in enumerate(self._df_ret) if "decimal" in s]:
            df[index] = float(df[index])
        return dict(zip(self._df_format, df))

    async def tare_gauge_P(self):
        """
        Tares the gauge pressure of the device, zeros out the diff P reference point # Untested
        """
        ret = await self._device._write_readline(self._id + "P")
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
            self._id + "TB " + totalizer + " " + batch_vol + " " + unit_vol
        )
        df = ["Unit ID", "Totalizer", "Batch Size", "Unit Code", "Unit Label"]
        return dict(zip(df, ret.split()))

    async def deadband_limit(self, save: str = "", limit: str = ""):
        """
        Gets the range the controller allows for drift around setpoint
        Sets the range the controller allows for drift around setpoint # Untested
        """
        ret = await self._device._write_readline(
            self._id + "LCDB " + save + " " + limit
        )
        df = ["Unit ID", "Deadband", "Unit Code", "Unit Label"]
        return dict(zip(df, ret.split()))

    async def deadband_mode(self, mode: str = ""):
        """
        Gets the reaction the controller has for values around setpoint
        Sets the reaction the controller has for values around setpoint # Untested
        """
        ret = await self._device._write_readline(self._id + "LCDM " + mode)
        df = ["Unit ID", "Mode"]
        ret = ret.split()
        if str(ret[1]) == "1":
            ret[1] = "Hold valve at current"
        elif str(ret[1]) == "2":
            ret[1] = "Close valve"
        return dict(zip(df, ret))

    async def loop_control_alg(self, algorithm: str = ""):
        """
        Gets the control algorithm the controller uses
        Sets the control algorithm the controller uses # Untested
        algorithm 1 = PD/PDF, algorithm 2 = PD2I
        """
        ret = await self._device._write_readline(self._id + "LCA " + algorithm)
        df = ["Unit ID", "Algorithm"]
        ret = ret.split()
        if str(ret[1]) == "1":
            ret[1] = "PD/PDF"
        elif str(ret[1]) == "2":
            ret[1] = "PD2I"
        return dict(zip(df, ret))

    async def loop_control_var(self, var: str = ""):
        """
        Sets the statistic the setpoint controls # Untested
        """
        for code in self.loop_var:
            if self.loop_var[code] == var:
                var = code
        ret = await self._device._write_readline(self._id + "LV " + var)
        df = ["Unit ID", "Loop Var Val"]
        ret = ret.split()
        return dict(zip(df, ret))

    async def loop_control_setpoint(
        self, var: str = "", unit: str = "", min: str = "", max: str = ""
    ):
        """
        Gets the statistic the setpoint controls
        Sets the statistic the setpoint controls # Untested
        """
        ret = await self._device._write_readline(
            self._id + "LR " + var + " " + unit + " " + min + " " + max
        )
        df = ["Unit ID", "Loop Var", "Min", "Max", "Unit Code", "Unit Label"]
        ret = ret.split()
        ret[1] = self.loop_var[int(ret[1])]
        return dict(zip(df, ret))

    async def max_ramp_rate(self, max: str = "", unit: str = ""):
        """
        Gets how fast controller moves to new setpoint
        Sets how fast controller moves to new setpoint # Untested
        max = 0 to disable ramping (still must include unit)
        """
        ret = await self._device._write_readline(self._id + "SR " + max + " " + unit)
        df = ["Unit ID", "Max Ramp Rate", "Unit Code", "Time Code", "Units"]
        ret = ret.split()
        return dict(zip(df, ret))

    async def pdf_gains(self, save: str = "", p_gain="", d_gain=""):
        """
        Gets the proportional and intregral gains of the PD/PDF controller
        Sets the proportional and intregral gains of the PD/PDF controller # Untested
        """
        if save != "":
            save = "0 " + save
        ret = await self._device._write_readline(
            self._id + "LCGD " + save + " " + p_gain + " " + d_gain
        )
        df = ["Unit ID", "P  Gain", "D Gain"]
        ret = ret.split()
        return dict(zip(df, ret))

    async def pd2i_gains(self, save: str = "", p_gain="", i_gain="", d_gain=""):
        """
        Gets the proportional, intregral, and derivative gains of the PD2I controller
        Sets the proportional, intregral, and derivative gains of the PD2I controller # Untested
        """
        if save != "":
            save = "0 " + save
        ret = await self._device._write_readline(
            self._id + "LCG " + save + " " + p_gain + " " + i_gain + " " + d_gain
        )
        df = ["Unit ID", "P  Gain", "I Gain", "D Gain"]
        ret = ret.split()
        return dict(zip(df, ret))

    async def power_up_setpoint(self, val: str = ""):
        """
        Enables immediate setpoint on power-up # Untested
        val = 0 to siable start-up setpoint
        """
        ret = await self._device._write_readline(self._id + "SPUE " + val)
        df = ret.split()
        for index in [idx for idx, s in enumerate(self._df_ret) if "decimal" in s]:
            df[index] = float(df[index])
        return dict(zip(self._df_format, df))

    async def overpressure(self, limit: str = ""):
        """
        Sets the overpressure limit of the device. # Untested
        """
        ret = await self._device._write_readline(self._id + "OPL " + limit)
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
            self._id + "LSRC " + up + " " + down + " " + zero + " " + power_up
        )
        df = ["Unit ID", "Ramp Up", "Ramp Down", "Zero Ramp", "Power Up Ramp"]
        ret = ret.split()
        for i in range(len(ret)):
            if ret[i] == "1":
                ret[i] = "Enabled"
            elif ret[i] == "0":
                ret[i] = "Disabled"
        return dict(zip(df, ret))

    async def setpoint_source(self, mode: str = ""):
        """
        Gets how the setpoint is given to the controller
        Sets how the setpoint is given to the controller # Untested
        """
        ret = await self._device._write_readline(self._id + "LSS " + mode)
        df = ["Unit ID", "Mode"]
        ret = ret.split()
        if ret[1] == "A":
            ret[1] = "Analog"
        elif ret[1] == "S":
            ret[1] = "Serial/Display, Saved"
        elif ret[1] == "U":
            ret[1] = "Serial/Display, Unsaved"
        return dict(zip(df, ret))

    async def valve_offset(
        self, save: str = "", initial_offset: str = "", closed_offset: str = ""
    ):
        """
        Gets how much power driven to valve when first opened or considered closed
        Sets how much power driven to valve when first opened or considered closed # Untested
        """
        if save != "":
            save = "0 " + save
        ret = await self._device._write_readline(
            self._id + "LCVO " + save + " " + initial_offset + " " + closed_offset
        )
        df = ["Unit ID", "Init Offser (%)", "Closed Offset (%)"]
        ret = ret.split()
        return dict(zip(df, ret))

    async def zero_pressure_control(self, enable: str = ""):
        """
        Gets how controller reacts to 0 Pressure setpoint
        Sets how controller reacts to 0 Pressure setpoint # Untested
        """
        ret = await self._device._write_readline(self._id + "LCZA " + enable)
        df = ["Unit ID", "Active Ctrl"]
        ret = ret.split()
        if ret[1] == "1":
            ret[1] = "Enabled"
        elif ret[1] == "0":
            ret[1] = "Disabled"
        return dict(zip(df, ret))

    async def auto_tare(self, enable: str = "", delay: str = ""):
        """
        Gets if the controller auto tares
        Sets if the controller auto tares # Untested
        """
        ret = await self._device._write_readline(
            self._id + "ZCA " + enable + " " + delay
        )
        df = ["Unit ID", "Auto-tare", "Delay (s)"]
        ret = ret.split()
        if ret[1] == "1":
            ret[1] = "Enabled"
        elif ret[1] == "0":
            ret[1] = "Disabled"
        return dict(zip(df, ret))

    async def configure_data_frame(self, format: str = ""):
        """
        Sets data frame's format # Untested
        """
        ret = await self._device._write_readline(self._id + "FDF " + format)
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
        if group.upper() == "Y" or group.upper() == "YES":
            group = "1"
        elif group.upper() == "N" or group.upper() == "NO":
            group = "0"
        if override.upper() == "Y" or override.upper() == "YES":
            override = "1"
        else:
            override = "0"
        ret = await self._device._write_readline(
            self._id
            + "DCU "
            + str(statistics[statistic_value])
            + " "
            + group
            + " "
            + units[unit_val]
            + " "
            + override
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
            "All Press": "1",
            "Abs Press": "2",
            "Vol Flow": "4",
            "Mass Flow": "5",
            "Gauge Press": "6",
            "Diff Press": "7",
            "Ext Vol Flow": "17",
            "2nd Abs Press": "344",
            "2nd Gauge Press": "352",
            "2nd Diff Press": "360",
        }
        ret = await self._device._write_readline(
            self._id + "DCA " + stat_vals[stat_val] + " " + avg_time
        )
        df = ["Unit ID", "Value", "Time Const"]
        ret = ret.split()
        return dict(zip(df, ret))

    async def full_scale_val(self, stat_val: str = "", unit_val: str = ""):
        """
        Gets measurement range of given statistic
        """
        ret = await self._device._write_readline(
            self._id + "FPF " + str(statistics[stat_val]) + " " + str(units[unit_val])
        )
        df = ["Unit ID", "Max Value", "Unit Code", "Unit Label"]
        ret = ret.split()
        return dict(zip(df, ret))

    async def power_up_tare(self, enable: str = ""):
        """
        Gets if device tares on power-up
        Sets if device tares on power-up
        """
        if enable.upper() == "Y" or enable.upper() == "YES":
            enable = "1"
        elif enable.upper() == "N" or enable.upper() == "NO":
            enable = "0"
        ret = await self._device._write_readline(self._id + "ZCP " + enable)
        df = ["Unit ID", "Power-Up Tare"]
        ret = ret.split()
        if ret[1] == "1":
            ret[1] = "Enabled"
        elif ret[1] == "0":
            ret[1] = "Disabled"
        return dict(zip(df, ret))

    async def data_frame(self):
        """
        Gets info about current data frame
        """
        ret = await self._device._write_readall(self._id + "??D*")
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
            self._id
            + "DCFRP "
            + stp.upper()
            + " "
            + str(units[unit])
            + " "
            + str(press)
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
            self._id + "DCFRT " + stp.upper() + " " + str(units[unit]) + " " + str(temp)
        )
        df = ["Unit ID", "Curr Temp Ref", "Unit Code", "Unit Label"]
        ret = ret.split()
        return dict(zip(df, ret))

    async def zero_band(self, zb: str = ""):
        """
        Gets the zero band of the device.
        Sets the zero band of the device. # Untested
        """
        ret = await self._device._write_readline(self._id + "DCZ " + zb)
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
            self._id + "ASOCV " + primary + " " + val + " " + unit
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
        if new_baud != "" and int(new_baud) not in [
            2400,
            4800,
            9600,
            19200,
            38400,
            57600,
            115200,
        ]:
            new_baud = ""
        ret = await self._device._write_readline(self._id + "NCB " + new_baud)
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
        ret = await self._device._write_readline(self._id + "FFP " + dur)
        df = ["Unit ID", "Flashing?"]
        ret = ret.split()
        if ret[1] == "0":
            ret[1] = "No"
        elif ret[1] == "1":
            ret[1] = "Yes"
        return dict(zip(df, ret))

    async def change_unit_id(self, new_id: str = ""):
        """
        Sets the unit ID of the device. # Untested
        """
        ret = await self._device._write_readline(self._id + "@ " + new_id)
        self.id = new_id
        return ret

    async def firmware_version(self):
        """
        Gets the firmware version of the device.
        """
        ret = await self._device._write_readline(self._id + "VE")
        df = ["Unit ID", "Vers", "Creation Date"]
        ret = ret.split()
        ret[2] = " ".join(ret[2:])
        return dict(zip(df, ret))

    async def lock_display(self):
        """
        Disables buttons on front of the device.
        """
        ret = await self._device._write_readline(self._id + "L")
        df = ret.split()
        for index in [idx for idx, s in enumerate(self._df_ret) if "decimal" in s]:
            df[index] = float(df[index])
        return dict(zip(self._df_format, df))

    async def manufacturing_info(self):
        """
        Gets info about current data frame
        """
        ret = await self._device._write_readall(self._id + "??M*")
        return ret

    async def remote_tare(self, actions: list = []):
        """
        Gets the remote tare value
        Sets the remote tare effect. # Untested
        """
        act_tot = 0
        for act in actions:
            if act == "Primary Press":
                act_tot += 1
            elif act == "Secondary Press":
                act_tot += 2
            elif act == "Flow":
                act_tot += 4
            elif act == "Reset Totalizer 1":
                act_tot += 8
            elif act == "Reset Totalizer 2":
                act_tot += 16
        if not actions:
            act_tot = ""
        ret = await self._device._write_readline(self._id + "ASRCA " + act_tot)
        df = ["Unit ID", "Active Actions Total"]
        ret = ret.split()
        return dict(zip(df, ret))

    async def restore_factory_settings(self):
        """
        Restores factory settings of the device. # Untested
        """
        ret = await self._device._write_readline(self._id + "FACTORY RESTORE ALL")
        return ret

    async def user_data(self, slot: str = "", val: str = ""):
        """
        Gets the user data of the device.
        Sets the user data in slot to val. # Untested
        """
        if type(slot) == int:
            slot = str(slot)
        ret = await self._device._write_readline(self._id + "UD " + slot + " " + val)
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
        ret = await self._device._write_readline(self._id + "NCS " + interval)
        df = ["Unit ID", "Interval (ms)"]
        ret = ret.split()
        return dict(zip(df, ret))

    async def unlock_display(self):
        """
        Disables buttons on front of the device.
        """
        ret = await self._device._write_readline(self._id + "U")
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
            self._id
            + "GM "
            + name
            + " "
            + number
            + " "
            + gas1P
            + " "
            + gas1N
            + " "
            + gas2P
            + " "
            + gas2N
            + " "
            + gas3P
            + " "
            + gas3N
            + " "
            + gas4P
            + " "
            + gas4N
            + " "
            + gas5P
            + " "
            + gas5N
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
        ret = await self._device._write_readline(self._id + "GD " + gasN)
        df = ["Unit ID", "Deleted Gas Num"]
        ret = ret.split()
        return dict(zip(df, ret))

    async def query_gas_mix(self, gasN: str = ""):
        """
        Gets Percentages of gases in mixture. # Untested
        """
        ret = await self._device._write_readall(self._id + "GC " + gasN)
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
            self._id
            + "TC "
            + totalizer
            + " "
            + flow_stat_val
            + " "
            + mode
            + " "
            + lmit_mode
            + " "
            + num
            + " "
            + dec
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
        ret = await self._device._write_readline(self._id + "T " + totalizer)
        df = ret.split()
        for index in [idx for idx, s in enumerate(self._df_ret) if "decimal" in s]:
            df[index] = float(df[index])
        return dict(zip(self._df_format, df))

    async def reset_totalizer_peak(self, totalizer: str = "1"):
        """
        Returns totalizer count to zero and restarts timer. # Untested
        """
        ret = await self._device._write_readline(self._id + "TP " + totalizer)
        df = ret.split()
        for index in [idx for idx, s in enumerate(self._df_ret) if "decimal" in s]:
            df[index] = float(df[index])
        return dict(zip(self._df_format, df))

    async def save_totalizer(self, enable: str = ""):
        """
        Enables/disables saving totalizer values.
        """
        ret = await self._device._write_readline(self._id + "TCR " + enable)
        df = ["Unit ID", "Saving"]
        ret = ret.split()
        if ret[1] == "0":
            ret[1] = "Disabled"
        elif ret[1] == "1":
            ret[1] = "Enabled"
        return dict(zip(df, ret))  # Need to convert codes to text

    async def canc_valve_hold(self):
        """
        Removes valve holds. # Untested
        """
        ret = await self._device._write_readline(self._id + "C")
        df = ret.split()
        for index in [idx for idx, s in enumerate(self._df_ret) if "decimal" in s]:
            df[index] = float(df[index])
        return dict(zip(self._df_format, df))

    async def exhaust(self):
        """
        Closes upstream valve, opens downstream valve 100% # Untested
        """
        ret = await self._device._write_readline(self._id + "E")
        df = ret.split()
        for index in [idx for idx, s in enumerate(self._df_ret) if "decimal" in s]:
            df[index] = float(df[index])
        return dict(zip(self._df_format, df))

    async def hold_valve(self):
        """
        Hold valves at current position # Untested
        """
        ret = await self._device._write_readline(self._id + "HP")
        df = ret.split()
        for index in [idx for idx, s in enumerate(self._df_ret) if "decimal" in s]:
            df[index] = float(df[index])
        return dict(zip(self._df_format, df))

    async def hold_valve_closed(self):
        """
        Close all valves # Untested
        """
        ret = await self._device._write_readline(self._id + "HC")
        df = ret.split()
        for index in [idx for idx, s in enumerate(self._df_ret) if "decimal" in s]:
            df[index] = float(df[index])
        return dict(zip(self._df_format, df))

    async def query_valve_drive_state(self):  # Why does this return 4 values?
        """
        Gets current percentage of total possible electricity to valve
        """
        ret = await self._device._write_readline(self._id + "VD")
        df = ["Unit ID", "Valve 1 %", "Valve 2 %", "Valve 3 %", "Valve 4 %"]
        ret = ret.split()
        return dict(zip(df, ret))

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

    async def get(self, measurement: str) -> dict:
        """
        Gets the value of a measurement from the device
        """
        # Poll
        # Request
        # Get gas
        # Get setpoint
        return

    async def set(self, measurement: str) -> dict:
        """
        Gets the value of a measurement from the device
        """
        # Set gas
        # Set setpoint
        # Set loop control variable
        return


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
