"""Simple battery simulation for maximising self-consumption."""

import pandas as pd


def run_battery_self_consumption(
    load_pv_profile: pd.DataFrame,
    battery_kw: float,
    battery_kwh: float,
    battery_eff: float = 0.90,
    interval_per_hour: int = 2,
) -> pd.DataFrame:
    """
    Simulate a simple battery algorithm to maximise self-consumption of PV energy.

    The battery charges using excess PV generation that is not consumed by the load
    and discharges to minimise grid import. It updates the state of charge (SOC)
    and net_load accordingly.

    Args:
        load_pv_profile: DataFrame containing 'kWh' (load) and 'PV' (generation)
            columns with a datetime index. Values should be in kWh per interval.
        battery_kw: Battery power rating in kW (max charge/discharge rate).
        battery_kwh: Battery energy capacity in kWh.
        battery_eff: Battery round-trip efficiency (default is 0.90, i.e. 90%).
        interval_per_hour: Number of intervals per hour in the data (default is 2
            for 30-minute intervals).

    Returns:
        DataFrame with the original data plus additional columns:
            - 'SOC': State of charge in kWh
            - 'net_load': Net load after battery operation in kWh
            - 'kWh': Load with battery discharging applied
            - 'PV': PV with battery charging applied

    Example:
        >>> profile = pd.DataFrame({
        ...     'kWh': [1.0, 0.5, 0.8],
        ...     'PV': [0.0, 2.0, 1.5]
        ... }, index=pd.date_range('2020-01-01', periods=3, freq='30min'))
        >>> result = run_battery_self_consumption(profile, battery_kw=5, battery_kwh=10)

    """
    if battery_kwh <= 0 or battery_kw <= 0:
        # No battery - return original profile with added columns
        result = load_pv_profile.copy()
        result["SOC"] = 0.0
        result["net_load"] = result["kWh"] - result["PV"]
        return result

    # Convert to kW from kWh for power calculations
    profiles = load_pv_profile.copy() * interval_per_hour
    profiles = profiles.reset_index().rename(
        columns={"kWh": "demand", "PV": "generation"}
    )

    # Initialise columns
    profiles["SOC"] = 0.0
    profiles["excess_generation"] = (profiles["generation"] - profiles["demand"]).clip(
        lower=0, upper=battery_kw
    )
    profiles["excess_demand"] = (profiles["demand"] - profiles["generation"]).clip(
        lower=0, upper=battery_kw
    )

    # One-way efficiency (square root of round-trip)
    one_way_eff = battery_eff**0.5

    # Simulate battery operation
    for i in range(1, len(profiles)):
        # Calculate new SOC based on charging/discharging
        charge_energy = (
            one_way_eff * profiles.loc[i, "excess_generation"] / interval_per_hour
        )
        discharge_energy = (
            profiles.loc[i, "excess_demand"] / one_way_eff / interval_per_hour
        )

        new_soc = profiles.loc[i - 1, "SOC"] + charge_energy - discharge_energy
        profiles.loc[i, "SOC"] = max(0, min(battery_kwh, new_soc))

        profiles.loc[i, "energy_change"] = (
            profiles.loc[i, "SOC"] - profiles.loc[i - 1, "SOC"]
        )

    # Apply efficiency to excess charge values
    profiles["energy_change"] = profiles["energy_change"].apply(
        lambda x: x * one_way_eff if x < 0 else x / one_way_eff
    )

    # Calculate charging and discharging in kWh
    profiles["charging"] = profiles["energy_change"].clip(lower=0) * interval_per_hour
    profiles["discharging"] = (
        profiles["energy_change"].clip(upper=0) * interval_per_hour
    )

    # Calculate Net load and adjusted load/PV
    profiles["net_demand"] = (
        profiles["demand"]
        - profiles["generation"]
        + profiles["energy_change"] * interval_per_hour
    )
    profiles["demand_with_battery"] = profiles["demand"] + profiles["discharging"]
    profiles["generation_with_battery"] = profiles["generation"] - profiles["charging"]

    # Get index column name (could be 'TS' or 'index')
    index_col = profiles.columns[0]

    # Prepare output DataFrame
    result = profiles[
        [
            index_col,
            "net_demand",
            "demand_with_battery",
            "generation_with_battery",
            "SOC",
        ]
    ].set_index(index_col)

    # Make the SOC into a percentage of the battery capacity
    result["SOC"] = result["SOC"] / battery_kwh * 100

    result = result.rename(
        columns={
            "net_demand": "net_load",
            "demand_with_battery": "kWh",
            "generation_with_battery": "PV",
        }
    )

    # Convert back to kWh per interval
    result["kWh"] = result["kWh"] / interval_per_hour
    result["PV"] = result["PV"] / interval_per_hour
    result["net_load"] = result["net_load"] / interval_per_hour

    return result
