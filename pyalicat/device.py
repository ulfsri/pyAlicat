from typing import Any, Union

import re
from abc import ABC

import trio
from comm import CommDevice, SerialDevice
from trio import run
from .device import Device

statistics = {
    "Batch_mass_remain.": 12,
    "Batch_vol_remain.": 11,
    "Batch_vol_ext_remain.": 19,
    "Mass_Flow": 5,
    "Mass_Flow_avg": 69,
    "Mass_Flow_max": 175,
    "Mass_Flow_min": 174,
    "Mass_Flow_Peak": 101,
    "Mass_Flow_Setpt": 37,
    "Mass_Flow_Setpt_err": 173,
    "Totalizing_Time": 10,
    "Tot_Mass": 9,
    "Tot_Vol": 8,
    "Tot_Vol_Ext": 18,
    "Volu_Flow": 4,
    "Volu_Flow_avg": 68,
    "Volu_Flow_max": 167,
    "Volu_Flow_min": 166,
    "Volu_Flow_Peak": 100,
    "Volu_Flow_Setpt": 36,
    "Volu_Flow_Setpt_err": 165,
    "Vol_Flow_Ext": 17,
    "Vol_Flow_Ext_avg": 81,
    "Vol_Flow_Ext_max": 271,
    "Vol_Flow_Ext_min": 270,
    "Vol_Flow_Ext_Peak": 113,
    "Vol_Flow_Ext_Setpt": 49,
    "Vol_Flow_Ext_Setpt_err": 268,
    "Abs_Press": 2,
    "Abs_Press_avg": 66,
    "Abs_Press_max": 151,
    "Abs_Press_min": 150,
    "Abs_Press_Peak": 98,
    "Abs_Press_Setpt": 34,
    "Abs_Press_Setpt_err": 149,
    "Baro_Press": 15,
    "Baro_Press_Avg": 79,
    "Baro_Press_Max": 255,
    "Baro_Press_Min": 254,
    "Baro_Press_Peak": 111,
    "Diff_Press": 7,
    "Diff_Press_max": 191,
    "Diff_Press_min": 190,
    "Diff_Press_Setpt": 39,
    "Diff_Press_Setpt_err": 189,
    "Gauge_Press": 6,
    "Gauge_Press_avg": 70,
    "Gauge_Press_max": 183,
    "Gauge_Press_min": 182,
    "Gauge_Press_Peak": 102,
    "Gauge_Press_Setpt": 38,
    "Gauge_Press_Setpt_err": 181,
    "2nd_Abs_Press": 344,
    "2nd_Abs_Press_max": 351,
    "2nd_Abs_Press_min": 350,
    "2nd_Abs_Press_Setpt": 345,
    "2nd_Abs_Press_Setpt_err": 349,
    "2nd_Diff_Press": 360,
    "2nd_Diff_Press_max": 367,
    "2nd_Diff_Press_min": 366,
    "2nd_Diff_Press_Setpt": 361,
    "2nd_Diff_Press_Setpt_err": 365,
    "2nd_Gauge_Press": 352,
    "2nd_Gauge_Press_max": 359,
    "2nd_Gauge_Press_min": 358,
    "2nd_Gauge_Press_Setpt": 353,
    "2nd_Gauge_Press_Setpt_err": 357,
    "None": 1,
    "User_Date": 400,
    "Fluid_Name": 703,
    "Meas_ID": 801,
    "Meas_Stat": 802,
    "Setpt": 32,
    "Setpt_err": 133,
    "Status": 26,
    "Temp_Ext": 16,
    "Temp_Ext_max": 263,
    "Temp_Ext_min": 262,
    "Flow_Temp": 3,
    "Flow_Temp_max": 159,
    "Flow_Temp_min": 158,
    "Flow_Temp_avg": 67,
    "Ext_Vol_Flow_Ref_Temp": 20,
    "Ext_Vol_Flow_Ref_Temp_avg": 84,
    "Ext_Vol_Flow_Ref_Temp_max": 295,
    "Ext_Vol_Flow_Ref_Temp_Peak": 116,
    "Ext_Vol_Flow_Ref_Temp_Src": 21,
    "Ext_Vol_Flow_Ref_Temp_Src_avg": 85,
    "Remain._Time_Meas.": 14,
    "User_Time": 392,
    "Valve_Drive": 13,
    "Valve_Drive_Setpt": 45,
    "Rel_Hum": 25,
    "Rel_Hum_avg": 89,
    "Rel_Hum_max": 335,
    "Rel_Hum_min": 334,
    "Rel_Hum_Peak": 121,
}

units = {
    "": "",
    "default": 0,
    "unknown": 1,
    "SμL/m": 2,
    "std_microliter_per_min": 2,
    "SmL/s": 3,
    "std_milliliter_per_sec": 3,
    "SmL/m": 4,
    "std_milliliter_per_min": 4,
    "SmL/h": 5,
    "std_milliliter_per_hour": 5,
    "SL/s": 6,
    "std_liter_per_sec": 6,
    "SLPM": 7,
    "std_liter_per_min": 7,
    "SL/h": 8,
    "std_liter_per_hour": 8,
    "SCCS": 11,
    "std_cubic_cm_per_sec": 11,
    "SCCM": 12,
    "std_cubic_cm_per_min": 12,
    "Scm3/h": 13,
    "std_cubic_cm_per_hour": 13,
    "Sm3/m": 14,
    "std_cubic_meter_per_min": 14,
    "Sm3/h": 15,
    "std_cubic_meter_per_hour": 15,
    "Sm3/d": 16,
    "std_cubic_meter_per_day": 16,
    "Sin3/m": 17,
    "std_cubic_inch_per_min": 17,
    "SCFM": 18,
    "std_cubic_foot_per_min": 18,
    "SCFH": 19,
    "std_cubic_foot_per_hour": 19,
    "SCFD": 21,
    "std_cubic_foot_per_day": 21,
    "kSCFM": 20,
    "1000_std_cbft_per_min": 20,
    "NμL/m": 32,
    "norm_microliter_per_min": 32,
    "NmL/s": 33,
    "norm_milliliter_per_sec": 33,
    "NmL/m": 34,
    "norm_milliliter_per_min": 34,
    "NmL/h": 35,
    "norm_milliliter_per_hour": 35,
    "NL/s": 36,
    "norm_liter_per_sec": 36,
    "NLPM": 37,
    "norm_liter_per_min": 37,
    "NL/h": 38,
    "norm_liter_per_hour": 38,
    "NCCS": 41,
    "norm_cubic_cm_per_sec": 41,
    "NCCM": 42,
    "norm_cubic_cm_per_min": 42,
    "Ncm3/h": 43,
    "norm_cubic_meter_per_hour": 43,
    "Nm3/m": 44,
    "norm_cubic_meter_per_min": 44,
    "Nm3/h": 45,
    "norm_cubic_meter_per_hour": 45,
    "Nm3/d": 46,
    "norm_cubic_meter_per_day": 46,
    "count": 62,
    "%": 63,
    "mg/s": 64,
    "milligram_per_sec": 64,
    "mg/m": 65,
    "milligram_per_min": 65,
    "g/s": 66,
    "gram_per_sec": 66,
    "g/m": 67,
    "gram_per_min": 67,
    "g/h": 68,
    "gram_per_hour": 68,
    "kg/m": 69,
    "kilogram_per_min": 69,
    "kg/h": 70,
    "kilogram_per_hour": 70,
    "oz/s": 71,
    "ounce_per_sec": 71,
    "oz/m": 72,
    "ounce_per_min": 72,
    "lb/m": 73,
    "pound_per_min": 73,
    "lb/h": 74,
    "pound_per_hour": 74,
    "SμL": 2,
    "std_microliter": 2,
    "SmL": 3,
    "std_milliliter": 3,
    "SL": 4,
    "std_liter": 4,
    "Scm3": 6,
    "std_cubic_cm": 6,
    "Sm3": 7,
    "std_cubic_meter": 7,
    "Sin3": 8,
    "std_cubic_inch": 8,
    "Sft3": 9,
    "std_cubic_foot": 9,
    "kSft3": 10,
    "std_1000_cubic_foot": 10,
    "NμL": 32,
    "normal_microliter": 32,
    "NmL": 33,
    "normal_milliliter": 33,
    "NL": 34,
    "normal_liter": 34,
    "Ncm3": 36,
    "normal_cubic_cm": 36,
    "Nm3": 37,
    "normal_cubic_meter": 37,
    "μL/m": 2,
    "microliter_per_min": 2,
    "mL/s": 3,
    "milliliter_per_sec": 3,
    "mL/m": 4,
    "milliliter_per_min": 4,
    "mL/h": 5,
    "milliliter_per_hour": 5,
    "L/s": 6,
    "liter_per_sec": 6,
    "LPM": 7,
    "liter_per_min": 7,
    "L/h": 8,
    "liter_per_hour": 8,
    "GPM": 9,
    "gallon_per_min": 9,
    "GPH": 10,
    "gallon_per_hour": 10,
    "CCS": 11,
    "cubic_cm_per_sec": 11,
    "CCM": 12,
    "cubic_cm_per_min": 12,
    "cm3/h": 13,
    "cubic_cm_per_hour": 13,
    "m3/m": 14,
    "cubic_meter_per_min": 14,
    "m3/h": 15,
    "cubic_meter_per_hour": 15,
    "m3/d": 16,
    "cubic_meter_per_day": 16,
    "in3/m": 17,
    "cubic_inch_per_min": 17,
    "CFM": 18,
    "cubic_foot_per_min": 18,
    "CFH": 19,
    "cubic_foot_per_hour": 19,
    "CFD": 21,
    "cubic_foot_per_day": 21,
    "μL": 2,
    "microliter": 2,
    "mL": 3,
    "milliliter": 3,
    "L": 4,
    "liter": 4,
    "GAL": 5,
    "gallon": 5,
    "cm3": 6,
    "cubic_cm": 6,
    "m3": 7,
    "cubic_meter": 7,
    "in3": 8,
    "cubic_inch": 8,
    "ft3": 9,
    "cubic_foot": 9,
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
    "gram_per_square_cm": 8,
    "kg/cm2": 9,
    "kilogram_per_square_cm": 9,
    "PSI": 10,
    "pound_per_square_inch": 10,
    "PSF": 11,
    "pound_per_square_foot": 11,
    "mTorr": 12,
    "millitorr": 12,
    "torr": 13,
    "mmHg": 14,
    "millimeter_of_mercury": 14,
    "inHg": 15,
    "inch_of_mercury": 15,
    "mmH2O": 16,
    "millimeter_of_water": 16,
    "millimeter_of_water_@_60F": 17,
    "cmH2O": 18,
    "centimeter_of_water": 18,
    "centimeter_of_water_@_60F": 19,
    "inH2O": 20,
    "inch_of_water": 20,
    "inch_of_water_@_60F": 21,
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
    "Carbon_Monoxide": 3,
    "CO": 3,
    "Carbon_Dioxide": 4,
    "CO2": 4,
    "Ethane": 5,
    "C2H6": 5,
    "Hydrogen": 6,
    "H2": 6,
    "Helium": 7,
    "He": 7,
    "Nitrogen": 8,
    "N2": 8,
    "Nitrous_Oxide": 9,
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
    "Sulfur_Hexafluoride": 19,
    "SF6": 19,
    "25%_CO2,_75%_Ar": 20,
    "C-25": 20,
    "10%_CO2,_90%_Ar": 21,
    "C-10": 21,
    "8%_CO2,_92%_Ar": 22,
    "C-8": 22,
    "2%_CO2,_98%_Ar": 23,
    "C-2": 23,
    "75%_CO2,_25%_Ar": 24,
    "C-75": 24,
    "25%_He,_75%_Ar": 25,
    "He-25": 25,
    "75%_He,_25%_Ar": 26,
    "He-75": 26,
    "90%_He,_7.5%_Ar,_2.5%_CO2": 27,
    "A1025": 27,
    "Stargon_CS": 28,
    "Star29": 28,
    "5%_CH4,_95%_Ar": 29,
    "P-5": 29,
    "Nitric_Oxide": 30,
    "NO": 30,
    "Nitrogen_Trifluoride": 31,
    "NF3": 31,
    "Ammonia": 32,
    "NH3": 32,
    "Chlorine": 33,
    "Cl2": 33,
    "Hydrogen_Sulphide": 34,
    "H2S": 34,
    "Sulfur_Dioxide": 35,
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
    "Carbonyl_Sulfide": 84,
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
    "44%_R-125,_4%_R-134A,_52%_R-143A": 114,
    "R-404A": 114,
    "23%_R-32,_25%_R-125,_52%_R-143A": 115,
    "R-407C": 115,
    "50%_R-32,_50_R-125": 116,
    "R-410A": 116,
    "50%_R-125,_50%_R-143A": 117,
    "15%_CO2,_85%_Ar": 140,
    "C-15": 140,
    "20%_CO2,_80%_Ar": 141,
    "C-20": 141,
    "50%_CO2,_50%_Ar": 142,
    "C-50": 142,
    "50%_He,_50%_Ar": 143,
    "He-50": 143,
    "90%_He,_10%_Ar": 144,
    "He-90": 144,
    "5%_CH4,_95%_CO2": 145,
    "Bio5M": 145,
    "10_CH4,_90%_CO2": 146,
    "Bio10M": 146,
    "15%_CH4,_85%_CO2": 147,
    "Bio15M": 147,
    "20%_CH4,_80%_CO2": 148,
    "Bio20M": 148,
    "25%_CH4,_75%_CO2": 149,
    "Bio25M": 149,
    "30%_CH4,_70%_CO2": 150,
    "Bio30M": 150,
    "35%_CH4,_65%_CO2": 151,
    "Bio35M": 151,
    "40%_CH4,_60%_CO2": 152,
    "Bio40M": 152,
    "45%_CH4,_55%_CO2": 153,
    "Bio45M": 153,
    "50%_CH4,_50%_CO2": 154,
    "Bio50M": 154,
    "55%_CH4,_45%_CO2": 155,
    "Bio55M": 155,
    "60%_CH4,_40%_CO2": 156,
    "Bio60M": 156,
    "65%_CH4,_35%_CO2": 157,
    "Bio65M": 157,
    "70%_CH4,_30%_CO2": 158,
    "Bio70M": 158,
    "75%_CH4,_25%_CO2": 159,
    "Bio75M": 159,
    "80%_CH4,_20%_CO2": 160,
    "Bio80M": 160,
    "85%_CH4,_15%_CO2": 161,
    "Bio85M": 161,
    "90%_CH4,_10%_CO2": 162,
    "Bio90M": 162,
    "95%_CH4,_5%_CO2": 163,
    "Bio95M": 163,
    "32%_O2,_68%_N2": 164,
    "EAN-32": 164,
    "36%_O2,_64%_N2": 165,
    "EAN-36": 165,
    "40%_O2,_60%_N2": 166,
    "EAN-40": 166,
    "20%_O2,_80%_He": 167,
    "HeOx20": 167,
    "21%_O2,_79%_He": 168,
    "HeOx21": 168,
    "30%_O2,_70%_He": 169,
    "HeOx30": 169,
    "40%_O2,_60%_He": 170,
    "HeOx40": 170,
    "50%_O2,_50%_He": 171,
    "HeOx50": 171,
    "60%_O2,_40%_He": 172,
    "HeOx60": 172,
    "80%_O2,_20%_He": 173,
    "HeOx80": 173,
    "99%_O2,_1%_He": 174,
    "HeOx99": 174,
    "Enriched_Air_40%_O2": 175,
    "EA-40": 175,
    "Enriched_Air_60%_O2": 176,
    "EA-60": 176,
    "Enriched_Air_80%_O2": 177,
    "EA-80": 177,
    "Metab": 178,
    "Metabolic_Exhalant": 178,
    "16%_O2,_78.04%_N2,_5%_CO2,_0.96%_Ar": 178,
    "4.5%_CO2,_13.5%_N2,_82%_He": 179,
    "LG-4.5": 179,
    "6%_CO2,_14%_N2,_80%_He": 180,
    "LG-6": 180,
    "7%_CO2,_14%_N2,_79%_He": 181,
    "LG-7": 181,
    "9%_CO2,_15%_N2,_76%_He": 182,
    "LG-9": 182,
    "9%_Ne,_91%_He": 183,
    "HeNe9": 183,
    "9.4%_CO2,_19.25%_N2,_71.35%_He": 184,
    "LG-9.4": 184,
    "40%_H2,_29%_CO,_20%_CO2,_11%_CH4": 185,
    "SynG-1": 185,
    "64%_H2,_28%_CO,_1%_CO2,_7%_CH4": 186,
    "SynG-2": 186,
    "70%_H2,_4%_CO,_25%_CO2,_1%_CH4": 187,
    "SynG-3": 187,
    "83%_H2,_14%_CO,_3%_CH4": 188,
    "SynG-4": 188,
    "93%_CH4,_3%_C2H6,_1%_C3H8,_2%_N2,_1%_CO2": 189,
    "NatG-1": 189,
    "95%_CH4,_3%_C2H6,_1%_N2,_1%_CO2": 190,
    "NatG-2": 190,
    "95.2%_CH4,_2.5%_C2H6,_0.2%_C3H8,_0.1%_C4H10,_1.3%_N2,_0.7%_CO2": 191,
    "NatG-3": 191,
    "50%_H2,_35%_CH4,_10%_CO,_5%_C2H4": 192,
    "CoalG": 192,
    "75%_H2,_25%_N2": 193,
    "Endo": 193,
    "66.67%_H2,_33.33%_O2": 194,
    "HHO": 194,
    "LPG:_96.1%_C3H8,_1.5%_C2H6,_0.4%_C3H6,_1.9%_n-C4H10": 195,
    "HD-5": 195,
    "LPG:_85%_C3H8,_10%_C3H6,_5%_n-C4H10": 196,
    "HD-10": 196,
    "89%_O2,_7%_N2,_4%_Ar": 197,
    "OCG-89": 197,
    "93%_O2,_3%_N2,_4%_Ar": 198,
    "OCG-93": 198,
    "95%_O2,_1%_N2,_4%_Ar": 199,
    "OCG-95": 199,
    "2.5%_O2,_10.8%_CO2,_85.7%_N2,_1%_Ar": 200,
    "FG-1": 200,
    "2.9%_O2,_14%_CO2,_82.1%_N2,_1%_Ar": 201,
    "FG-2": 201,
    "3.7%_O2,_15%_CO2,_80.3%_N2,_1%_Ar": 202,
    "FG-3": 202,
    "7%_O2,_12%_CO2,_80%_N2,_1%_Ar": 203,
    "FG-4": 203,
    "10%_O2,_9.5%_CO2,_79.5%_N2,_1%_Ar": 204,
    "FG-5": 204,
    "13%_O2,_7%_CO2,_79%_N2,_1% Ar": 205,
    "FG-6": 205,
    "10%_CH4,_90%_Ar": 206,
    "P-10": 206,
    "Deuterium": 210,
    "D-2": 210,
}

loop_var = {
    34: "Abs_Press",
    345: "2nd_Abs_Press",
    39: "Press_Diff",
    361: "2nd_Press_Diff",
    38: "Gauge_Press",
    353: "2nd_Gauge_Press",
    37: "Mass_Flow",
    36: "Vol_Flow",
}


async def new_device(port: str, id: str = "A", **kwargs: Any) -> Device:
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
        self._df_format = None
        self._df_units = None

    async def poll(self) -> dict:
        """
        Gets the current value of the device.

        Returns:
            dict: The current value of the device.
        """
        if self._df_format is None:
            await self.get_df_format()  # Gets the format of the dataframe if it is not already known
        ret = await self._device._write_readline(self._id)
        df = ret.split()
        for index in [idx for idx, s in enumerate(self._df_ret) if "decimal" in s]:
            df[index] = float(df[index])
        return dict(zip(self._df_format, df))

    async def request(self, stats: list = [], time: str = "1") -> dict:
        """
        Gets specified values averaged over specified time.
        time in ms

        Args:
            stats (list): The statistics to get.
            time (str): The time to average over.

        Returns:
            dict: The requested statistics.
        """
        ret = await self._device._write_readline(f"{self._id}DV {time} {' '.join(str(statistics[stat]) for stat in stats)}")
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
        await self._device._write_readline(f"{self._id}@ @")
        return

    async def stop_stream(self, new_id: str = "A"):
        """
        Stops streaming data from device.
        """
        await self._device._write_readline(f"@@ {new_id}")
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
        ret = await self._device._write_readline(
            f"{self._id}GS {gas} {save}"
        )
        df = ["Unit ID", "Gas Code", "Gas", "Gas Long"]
        return dict(zip(df, ret.split()))

    async def gas_list(self):
        """
        Gets the list of avaiable gases for the device.
        """
        ret = await self._device._write_readall(f"{self._id}??G*")
        return ret

    async def setpoint(self, value: str = "", unit: str = ""):
        """
        Gets the setpoint of the device.
        Sets the setpoint of the device.
        """
        ret = await self._device._write_readline(
            f"{self._id}LS {value} {units[unit]}"
        )
        df = ["Unit ID", "Current Setpt", "Requested Setpt", "Unit Code", "Unit Label"]
        return dict(zip(df, ret.split()))

    async def tare_abs_P(self):
        """
        Tares the absolute pressure of the device, zeros out the abs P reference point # Untested
        """
        ret = await self._device._write_readline(f"{self._id}PC")
        df = ret.split()
        for index in [idx for idx, s in enumerate(self._df_ret) if "decimal" in s]:
            df[index] = float(df[index])
        return dict(zip(self._df_format, df))

    async def tare_flow(self):
        """
        Creates a no-flow reference point # Untested
        """
        ret = await self._device._write_readline(f"{self._id}V")
        df = ret.split()
        for index in [idx for idx, s in enumerate(self._df_ret) if "decimal" in s]:
            df[index] = float(df[index])
        return dict(zip(self._df_format, df))

    async def tare_gauge_P(self):
        """
        Tares the gauge pressure of the device, zeros out the diff P reference point # Untested
        """
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
        ret = await self._device._write_readline(
            f"{self._id}LCDB {save} {limit}"
        )
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
        Sets the statistic the setpoint controls # Untested
        """
        for code in self.loop_var:
            if self.loop_var[code] == var:
                var = code
        ret = await self._device._write_readline(f"{self._id}LV {var}")
        df = ["Unit ID", "Loop Var Val"]
        return dict(zip(df, ret.split()))

    async def loop_control_setpoint(
        self, var: str = "", unit: str = "", min: str = "", max: str = ""
    ):
        """
        Gets the statistic the setpoint controls
        Sets the statistic the setpoint controls # Untested
        """
        ret = await self._device._write_readline(
            f"{self._id}LR {var} {unit} {min} {max}"
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
        ret = await self._device._write_readline(f"{self._id}SPUE {val}")
        df = ret.split()
        for index in [idx for idx, s in enumerate(self._df_ret) if "decimal" in s]:
            df[index] = float(df[index])
        return dict(zip(self._df_format, df))

    async def overpressure(self, limit: str = ""):
        """
        Sets the overpressure limit of the device. # Untested
        """
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
        mapping = {"A": "Analog", "S": "Serial/Display, Saved", "U": "Serial/Display, Unsaved"}
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
        ret = await self._device._write_readline(
            f"{self._id}ZCA {enable} {delay}"
        )
        df = ["Unit ID", "Auto-tare", "Delay (s)"]
        ret = ret.split()
        output_mapping = {"1": "Enabled", "0": "Disabled"}
        ret[1] = output_mapping.get(str(ret[1]), ret[1])
        return dict(zip(df, ret))

    async def configure_data_frame(self, format: str = ""):
        """
        Sets data frame's format # Untested
        """
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
        if group.upper() == "Y" or group.upper() == "YES":
            group = "1"
        elif group.upper() == "N" or group.upper() == "NO":
            group = "0"
        if override.upper() == "Y" or override.upper() == "YES":
            override = "1"
        else:
            override = "0"
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
        if enable.upper() == "Y" or enable.upper() == "YES":
            enable = "1"
        elif enable.upper() == "N" or enable.upper() == "NO":
            enable = "0"
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
        act_tot = sum([1 if act == "Primary Press" else 2 if act == "Secondary Press" else 4 if act == "Flow" else 8 if act == "Reset Totalizer 1" else 16 if act == "Reset Totalizer 2" else 0 for act in actions])
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
        ret = await self._device._write_readline(f"{self._id}T {totalizer}")
        df = ret.split()
        for index in [idx for idx, s in enumerate(self._df_ret) if "decimal" in s]:
            df[index] = float(df[index])
        return dict(zip(self._df_format, df))

    async def reset_totalizer_peak(self, totalizer: str = "1"):
        """
        Returns totalizer count to zero and restarts timer. # Untested
        """
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
        ret = await self._device._write_readline(f"{self._id}C")
        df = ret.split()
        for index in [idx for idx, s in enumerate(self._df_ret) if "decimal" in s]:
            df[index] = float(df[index])
        return dict(zip(self._df_format, df))

    async def exhaust(self):
        """
        Closes upstream valve, opens downstream valve 100% # Untested
        """
        ret = await self._device._write_readline(f"{self._id}E")
        df = ret.split()
        for index in [idx for idx, s in enumerate(self._df_ret) if "decimal" in s]:
            df[index] = float(df[index])
        return dict(zip(self._df_format, df))

    async def hold_valve(self):
        """
        Hold valves at current position # Untested
        """
        ret = await self._device._write_readline(f"{self._id}HP")
        df = ret.split()
        for index in [idx for idx, s in enumerate(self._df_ret) if "decimal" in s]:
            df[index] = float(df[index])
        return dict(zip(self._df_format, df))

    async def hold_valve_closed(self):
        """
        Close all valves # Untested
        """
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
        if isinstance(measurements, str):
            measurements = measurements.split()
        # Request
        for meas in measurements:
            if meas in statistics:
                resp.update(await self.request([meas]))
            elif meas.upper() == "GAS":
                resp.update(await self.gas())
            elif meas.upper() in ["SETPOINT", "STPT"]:
                resp.update(await self.setpoint())
            elif flag == 0:
                resp.update(await self.poll())
                flag = 1
        return resp

    async def set(self, meas: str, param1: str, param2: str) -> dict:
        """
        Gets the value of a measurement from the device
        """
        resp = {}
        # Set gas - Param1 = value, Param2 = save
        upper_meas = str(meas).upper()
        if upper_meas == "GAS":
            resp.update(await self.gas(str(param1), str(param2)))
        elif upper_meas in ["SETPOINT", "STPT"]:
            resp.update(await self.setpoint(str(param1), str(param2)))
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
