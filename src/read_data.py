from glob import glob

import pandas as pd

from .helpers import format_load_pv_data


def read_single_sample_load_profile(file_path: str) -> dict[str, pd.DataFrame]:
    # reads in and renames useful columns/updates units for a single SAMPLE load
    # profile (ported with this script).
    # SAMPLE load profile have structure:
    # TS,       CUSTOMER_ID,    Wh,             PV
    # datetime, str,            float,          float
    # (5 min),  (id),           (watt-hours),   (watt-hours)

    load_data = pd.read_csv(file_path, parse_dates=["TS"], index_col="TS")
    # validate the input data structure and dtypes, returning useful error messages:
    if not set(load_data.columns).issuperset({"CUSTOMER_ID", "Wh", "PV"}):
        raise ValueError("Expected input data to have columns CUSTOMER_ID, Wh, and PV.")

    site_id = load_data["CUSTOMER_ID"].unique()[0]

    load_data = load_data.drop(columns=["CUSTOMER_ID"])
    load_data /= 1000
    load_data = load_data.rename(columns={"Wh": "kWh"})

    formatted_load_data = format_load_pv_data(load_data)

    return {site_id: formatted_load_data}


def read_n_sample_load_profiles(dir_path: str, n: int) -> dict[str, pd.DataFrame]:
    all_available_profiles = glob(f"{dir_path}/*.csv")

    n_profiles = {}
    for i in range(n):
        n_profiles.update(read_single_sample_load_profile(all_available_profiles[i]))

    return n_profiles


def get_sample_load_profile_metadata(dir_path: str) -> dict[str, int | list]:
    all_available_profiles = glob(f"{dir_path}/*.csv")
    total_samples = len(all_available_profiles)
    site_ids = [
        profile.split("/")[-1].split("_")[0] for profile in all_available_profiles
    ]

    return {
        "N": total_samples,
        "site_ids": site_ids,
    }
