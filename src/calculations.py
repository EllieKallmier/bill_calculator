import numpy as np
import pandas as pd

from .helpers import time_select


def calculate_daily_charge(
    load_profile: pd.DataFrame,
    tariff_component: dict,
    results: dict,
    tariff_category: str,
) -> float:
    """Calculates the total daily charges for a bill.

    Args:
        load_profile: A DataFrame containing the load profile data in kWh
            with a DateTime index.
        tariff_component: A dictionary containing tariff details. It should
            include a 'Daily' key with a nested dictionary that has a 'Value' key
            specifying the daily charge rate as follows:
            tariff_component = {
                ...
                'Daily' : {
                    'Unit' : '$/Day',
                    'Value' : 10.0
                }
                ...
            }
        results: dict, not used here, included to simplify control logic.
        tariff_category: A string representing the tariff category, one of 'NUOS'
            or 'Retailer' (not used here, included to simplify control logic).

    Returns:
        float: The bill's total daily charge in dollars ($), calculated as
            num_days_in_load_profile * daily_charge_value.

    """
    num_days = len(load_profile.index.normalize().unique()) - 1
    daily_charge = num_days * tariff_component["Daily"]["Value"]
    return daily_charge


def calculate_fixed_charge(
    load_profile: pd.DataFrame,
    tariff_component: dict,
    results: dict,
    tariff_category: str,
) -> float:
    """Returns the total fixed charges for a bill.

    Args:
        load_profile: A DataFrame containing the load profile data
            with a DateTime index (not used here, included to simplify control
            logic).
        tariff_component: A dictionary containing tariff details. It should
            include a 'Fixed' key with a nested dictionary that has a 'Value' key
            specifying the fixed rate per bill as follows:
            tariff_component = {
                ...
                'Fixed' : {
                    'Unit' : '$/Bill',
                    'Value' : 100.0
                }
                ...
            }
            - 'Unit' must be '$/Bill'
        results: dict, not used here, included to simplify control logic.
        tariff_category: A string representing the tariff category, one of 'NUOS'
            or 'Retailer' (not used here, included to simplify control logic).

    Returns:
        float: The bill's total fixed charge in dollars ($).

    """
    return tariff_component["Fixed"]["Value"]


def calculate_flatrate_charge(
    load_profile: pd.DataFrame,
    tariff_component: dict,
    results: dict,
    tariff_category: str,
) -> float:
    """Calculates the total of all flat rate charges for a bill.

    Args:
        load_profile: DataFrame not used here, included to simplify control logic.
        tariff_component: A dictionary containing tariff details. It should
            include a 'FlatRate' key with a nested dictionary that has a 'Value' key
            specifying the daily charge rate as follows:
            tariff_component = {
                ...
                'FlatRate' : {
                    'Unit' : '$/kWh',
                    'Value' : 0.55
                }
                ...
            }
        results: A dict containing key 'load_information' with a pd.DataFrame
            value that has column 'Annual_kWh' with a single entry at index
            'kWh' that holds the annual energy usage of the given load profile,
            and key tariff_category with a pd.DataFrame that stores tariff component
            results.
            Structured as follows:
            results = {
                'load_information' : pd.DataFrame(
                    columns=['Annual_kWh'],
                    index=['kWh'],
                    data=[6758021.922]
                ),
                tariff_category : pd.DataFrame()
            }
        tariff_category: str, not used here, included to simplify control logic.

    Returns:
        float: The bill's total daily charge in dollars ($), calculated as
            num_days_in_load_profile * daily_charge_value.

    """
    flat_rate_charge = (
        results["load_information"]["Annual_kWh"]
        * tariff_component["FlatRate"]["Value"]
    )
    return flat_rate_charge


def calculate_annual_block_charge(
    load_profile: pd.DataFrame,
    tariff_component: dict,
    results: dict,
    tariff_category: str,
) -> float:
    """Calculates the total of all annual block charges for a bill.

    For each block described in the tariff component, energy usage is compared
    against the bounds of the block. Usage up to the upper bound of the block
    is charged at the block's set rate, and the remaining energy use is charged
    under the next block's rate (and so on). For example, with an annual usage
    of 1000kWh and an upper bound of 800kWh for the first block at $0.5/kWh
    and no upper bound for the second block at $0.8/kWh, the annual charge
    is calculated as 800 * 0.5 + 200 * 0.8 = $560.

    Args:
        load_profile: DataFrame not used here, included to simplify control
            logic.
        tariff_component: A dictionary containing tariff details. It should
            include a 'BlockAnnual' key with a nested dictionary with the following
            structure:
            tariff_component = {
            ...
                'BlockAnnual' : {
                    'Block1' : {
                        'Unit' : '$/kWh',
                        'Value' : 0.20,
                        'HighBound' : 60
                    },
                    'Block2' : {
                        'Unit' : '$/kWh',
                        'Value' : 0.55,
                        'HighBound' : Infinity
                    },
                    ...
                }
                ...
            }
        results: A dict containing key 'load_information' with a pd.DataFrame
            value that has column 'Annual_kWh' with a single entry at index
            'kWh' that holds the annual energy usage of the given load profile,
            and key tariff_category with a pd.DataFrame that stores tariff component
            results. Structured as follows:
            results = {
                'load_information' : pd.DataFrame(
                    columns=['Annual_kWh'],
                    index=['kWh'],
                    data=[6758021.922]
                ),
                tariff_category : pd.DataFrame()
            }
        tariff_category: str, not used here, included to simplify control logic.

    Returns:
        float: The bill's total daily charge in dollars ($), calculated as
            num_days_in_load_profile * daily_charge_value.

    """
    block_use = results["load_information"][["Annual_kWh"]].copy()
    block_use_charge = block_use.copy()
    lim = 0
    for k, v in tariff_component["BlockAnnual"].items():
        block_use[k] = block_use["Annual_kWh"]
        block_use[k][block_use[k] > float(v["HighBound"])] = float(v["HighBound"])
        block_use[k] = block_use[k] - lim
        block_use[k][block_use[k] < 0] = 0
        lim = float(v["HighBound"])
        block_use_charge[k] = block_use[k] * v["Value"]
    del block_use["Annual_kWh"]
    del block_use_charge["Annual_kWh"]
    annual_block_charge = block_use_charge.sum(axis=1)

    return annual_block_charge


def calculate_quarterly_block_charge(
    load_profile: pd.DataFrame,
    tariff_component: dict,
    results: dict,
    tariff_category: str,
) -> float:
    """Calculates the quarterly block charge based on the load profile and
    tariff component details.

    This function calculates quarterly consumption for each of the four quarters,
    applies the block tariff charges based on consumption within each block, and
    sums up the charges for each quarter. This total charge is returned as a float.

    Args:
        load_profile (pd.DataFrame): A DataFrame containing half-hourly timeseries
            data with a DateTime index. It should have at least one column named 'kWh'
            containing energy usage (load) values for the corresponding half-hour
            up to index.
        tariff_component (dict): A dictionary containing tariff details. It should
            include a 'BlockQuarterly' key with a nested dictionary where each
            key represents a block and each value is a dictionary with 'HighBound'
            and 'Value' specifying the upper bound and charge rate for that block:
            tariff_component = {
            ...
                'BlockQuarterly' : {
                    'Block1' : {
                        'Unit' : '$/kWh',
                        'Value' : 0.20,
                        'HighBound' : 60
                    },
                    'Block2' : {
                        'Unit' : '$/kWh',
                        'Value' : 0.55,
                        'HighBound' : Infinity
                    },
                    ...
                }
                ...
            }
        results (dict): A dict containing key 'load_information' with a pd.DataFrame
            value that has column 'Annual_kWh' with a single entry at index
            'kWh' that holds the annual energy usage of the given load profile,
            and key <tariff_category> with a pd.DataFrame that stores tariff component
            results. Structured as follows:
            results = {
                'load_information' : pd.DataFrame(
                    columns=['Annual_kWh'],
                    index=['kWh'],
                    data=[6758021.922]
                ),
                <tariff_category> : pd.DataFrame()
            }

        tariff_category (str): A string representing the tariff category, used
            to store the charges in the results dictionary.

    Returns:
        float: The total quarterly block charge calculated from the load profile
            and tariff component details.

    Notes:
        - Quarterly periods are defined as:
            Q1: January - March
            Q2: April - June
            Q3: July - September
            Q4: October - December
    """
    # first: get quarterly consumption and save in the results 'load_information' df:
    for Q in range(1, 5):
        lp_quarterly = load_profile.loc[
            load_profile.index.month.isin(list(range((Q - 1) * 3 + 1, Q * 3 + 1))), :
        ]
        results["load_information"]["kWh_Q" + str(Q)] = [
            np.nansum(lp_quarterly[col].values[lp_quarterly[col].values > 0])
            for col in lp_quarterly.columns
        ]

    # then get the charge for each quarter:
    for Q in range(1, 5):
        block_use = results["load_information"][["kWh_Q" + str(Q)]].copy()
        block_use_charge = block_use.copy()
        lim = 0
        for k, v in tariff_component["BlockQuarterly"].items():
            block_use[k] = block_use["kWh_Q" + str(Q)]
            block_use[k][block_use[k] > float(v["HighBound"])] = float(v["HighBound"])
            block_use[k] = block_use[k] - lim
            block_use[k][block_use[k] < 0] = 0
            lim = float(v["HighBound"])
            block_use_charge[k] = block_use[k] * v["Value"]
        del block_use["kWh_Q" + str(Q)]
        del block_use_charge["kWh_Q" + str(Q)]

        results[tariff_category]["C_BlockQuarterly_" + str(Q)] = block_use_charge.sum(
            axis=1
        )

    quarterly_block_charge = results[tariff_category][
        ["C_BlockQuarterly_" + str(Q) for Q in range(1, 5)]
    ].sum(axis=1)
    return quarterly_block_charge


def calculate_monthly_block_charge(
    load_profile: pd.DataFrame,
    tariff_component: dict,
    results: dict,
    tariff_category: str,
) -> float:
    """Calculates the monthly block charge based on the load profile and
    tariff component details.

    This function calculates consumption within each month, applies the block tariff
    charges based on consumption within each block, and sums up the charges for each
    month. This total charge is returned as a float.

    Args:
        load_profile (pd.DataFrame): A DataFrame containing half-hourly timeseries
            data with a DateTime index. It should have at least one column named 'kWh'
            containing energy usage (load) values for the corresponding half-hour
            up to index.
        tariff_component (dict): A dictionary containing tariff details. It should
            include a 'BlockMonthly' key with a nested dictionary where each
            key represents a block and each value is a dictionary with 'HighBound'
            and 'Value' specifying the upper bound and charge rate for that block:
            tariff_component = {
            ...
                'BlockMonthly' : {
                    'Block1' : {
                        'Unit' : '$/kWh',
                        'Value' : 0.20,
                        'HighBound' : 60
                    },
                    'Block2' : {
                        'Unit' : '$/kWh',
                        'Value' : 0.55,
                        'HighBound' : Infinity
                    },
                    ...
                }
                ...
            }
        results (dict): A dict containing key 'load_information' with a pd.DataFrame
            value that has column 'Annual_kWh' with a single entry at index
            'kWh' that holds the annual energy usage of the given load profile,
            and key <tariff_category> with a pd.DataFrame that stores tariff component
            results. Structured as follows:
            results = {
                'load_information' : pd.DataFrame(
                    columns=['Annual_kWh'],
                    index=['kWh'],
                    data=[6758021.922]
                ),
                <tariff_category> : pd.DataFrame()
            }

        tariff_category (str): A string representing the tariff category, used
            to store the charges in the results dictionary.

    Returns:
        float: The total monthly block charge calculated from the load profile
            and tariff component details.

    """
    # Get monthly consumtion and store in results 'load_information' df:
    for m in range(1, 13):
        lp_monthly = load_profile.loc[load_profile.index.month == m, :]
        results["load_information"]["kWh_m" + str(m)] = [
            np.nansum(lp_monthly[col].values[lp_monthly[col].values > 0])
            for col in lp_monthly.columns
        ]

    # then calculate the charge for each month:
    for m in range(1, 13):
        block_use = results["load_information"][["kWh_m" + str(m)]].copy()
        block_use_charge = block_use.copy()
        lim = 0
        for k, v in tariff_component["BlockMonthly"].items():
            block_use[k] = block_use["kWh_m" + str(m)]
            block_use[k][block_use[k] > float(v["HighBound"])] = float(v["HighBound"])
            block_use[k] = block_use[k] - lim
            block_use[k][block_use[k] < 0] = 0
            lim = float(v["HighBound"])
            block_use_charge[k] = block_use[k] * v["Value"]
        del block_use["kWh_m" + str(m)]
        del block_use_charge["kWh_m" + str(m)]
        results[tariff_category]["C_BlockMonthly_" + str(m)] = block_use_charge.sum(
            axis=1
        )

    monthly_block_charge = results[tariff_category][
        ["C_BlockMonthly_" + str(m) for m in range(1, 13)]
    ].sum(axis=1)
    return monthly_block_charge


def calculate_daily_block_charge(
    load_profile: pd.DataFrame,
    tariff_component: dict,
    results: dict,
    tariff_category: str,
) -> float:
    """Calculates the daily block charge based on the load profile and
    tariff component details.

    This function calculates consumption within each month, applies the block tariff
    charges based on consumption within each block, and sums up the charges for each
    month. This total charge is returned as a float.

    Args:
        load_profile (pd.DataFrame): A DataFrame containing half-hourly timeseries
            data with a DateTime index. It should have at least one column named 'kWh'
            containing energy usage (load) values for the corresponding half-hour
            up to index.
        tariff_component (dict): A dictionary containing tariff details. It should
            include a 'BlockDaily' key with a nested dictionary where each
            key represents a block and each value is a dictionary with 'HighBound'
            and 'Value' specifying the upper bound and charge rate for that block:
            tariff_component = {
            ...
                'BlockDaily' : {
                    'Block1' : {
                        'Unit' : '$/kWh',
                        'Value' : 0.20,
                        'HighBound' : 60
                    },
                    'Block2' : {
                        'Unit' : '$/kWh',
                        'Value' : 0.55,
                        'HighBound' : Infinity
                    },
                    ...
                }
                ...
            }
        results (dict): dict, not used here, included to simplify control logic.
        tariff_category (str): str, not used here, included to simplify control logic.

    Returns:
        float: The total daily block charge calculated from the load profile
            and tariff component details.

    """

    # First, resample the load profile to get daily usage:
    daily_kwh_usage = load_profile.resample("D").sum()
    block_use_temp_charge = daily_kwh_usage.copy()
    block_use_temp_charge.iloc[:, :] = 0
    lim = 0
    # then apply the daily blocks to find daily charges:
    for block, details in tariff_component["BlockDaily"].items():
        block_use_temp = daily_kwh_usage.copy()
        block_use_temp[block_use_temp > float(details["HighBound"])] = float(
            details["HighBound"]
        )
        block_use_temp = block_use_temp - lim
        block_use_temp[block_use_temp < 0] = 0
        lim = float(details["HighBound"])
        block_use_temp_charge = (
            block_use_temp_charge + block_use_temp * details["Value"]
        )
    daily_block_charge = block_use_temp_charge.sum(axis=0)
    return daily_block_charge


def calculate_time_of_use_charge(
    load_profile: pd.DataFrame,
    tariff_component: dict,
    results: dict,
    tariff_category: str,
) -> float:
    """Calculates the total time of use energy charge based on the load profile and
    tariff component details.

    This function calculates consumption within each defined time of use period,
    applies the tariff rate based on consumption within each period, and sums up
    all time of use charges.

    Args:
        load_profile (pd.DataFrame): A DataFrame containing half-hourly timeseries
            data with a DateTime index. It should have at least one column named 'kWh'
            containing energy usage (load) values for the corresponding half-hour
            up to index.
        tariff_component (dict): A dictionary containing tariff details. It should
            include a 'TOU' key with a nested dictionary where each key represents
            a charging period and each value is a dictionary with details specifying
            month, time and weekdays during which the charge applies, as well as
            the units ($/kWh) and rate of the charge itself.
        results (dict): A dict containing key 'load_information' with a pd.DataFrame
            value that has column 'Annual_kWh' with a single entry at index
            'kWh' that holds the annual energy usage of the given load profile,
            and key <tariff_category> with a pd.DataFrame that stores tariff component
            results. Structured as follows:
            results = {
                'load_information' : pd.DataFrame(
                    columns=['Annual_kWh'],
                    index=['kWh'],
                    data=[6758021.922]
                ),
                <tariff_category> : pd.DataFrame()
            }
        tariff_category (str): A string representing the tariff category, used
            to store the charges in the results dictionary.

    Returns:
        float: The total TOU charge calculated from the load profile and tariff
            component details.

    """
    # First set up temporary dfs to hold interim results:
    time_of_use_consumption = pd.DataFrame()
    time_of_use_consumption_charge = pd.DataFrame()
    # Loop over each TOU component (e.g. Peak, Weekend Off-Peak, Shoulder etc)
    # and fill in any missing details with default values
    for tou_component, details in tariff_component["TOU"].items():
        details_copy = details.copy()
        if "Weekday" not in details_copy:
            details_copy["Weekday"] = True
            details_copy["Weekend"] = True
        if "TimeIntervals" not in details_copy:
            details_copy["TimeIntervals"] = {"T1": ["00:00", "00:00"]}
        if "Month" not in details_copy:
            details_copy["Month"] = list(range(1, 13))

        # Then call time_select to get the load_profile for times during which
        # this charge component applies. Calculate usage then total charge for
        # this period:
        lp_time_of_use = time_select(load_profile, details_copy)
        time_of_use_consumption[tou_component] = lp_time_of_use.sum()
        results[tariff_category]["kWh_" + tou_component] = time_of_use_consumption[
            tou_component
        ].copy()
        time_of_use_consumption_charge[tou_component] = (
            details_copy["Value"] * time_of_use_consumption[tou_component]
        )
        results[tariff_category]["TOU_" + tou_component] = (
            time_of_use_consumption_charge[tou_component].copy()
        )

    time_of_use_charge = time_of_use_consumption_charge.sum(axis=1)
    return time_of_use_charge


def calculate_demand_charge_component(
    dem_component_details: dict,
    num_peaks: int,
    load_profile_selected_times: pd.DataFrame,
    tariff_category: str,
    demand_component: str,
    results: dict,
) -> float:
    """Calculate the demand charge based on demand component details and load profile data.

    This function computes the demand charge based on the provided demand component details,
    the number of peaks to consider, and the load profile. It updates a results DataFrame
    with the average demand and the total demand charge for the given tariff category and
    demand component.

    Args:
        dem_component_details: A dictionary containing details about the demand component,
            such as minimum demand and charge values. Expected keys are 'Value', 'Unit' ($/kW/day),
            'Min Demand (kW)' and 'Min Demand Charge ($)'.
        num_peaks: The number of peaks to consider when calculating the demand charge.
        load_profile_selected_times: DataFrame containing the load profile with
            datetime index and at least one column named 'kWh' containing half-hourly
            load data. This dataframe will contain load data for selected periods
            based on the tariff component, calculated before being passed to this function.
        tariff_category: A string representing the tariff category, used
            to store the charges in the results dictionary.
        demand_component:A string naming the demand charge component, used
            to store the charges in the results dictionary.
        results:A dict containing key 'load_information' with a pd.DataFrame
            value that has column 'Annual_kWh' with a single entry at index
            'kWh' that holds the annual energy usage of the given load profile,
            and key <tariff_category> with a pd.DataFrame that stores tariff component
            results.

    Returns:
        float: The total demand charge calculated based on the demand component details and load
            profile data.

    Notes:
        - The function updates the `results[<tariff_category>]` DataFrame with two new columns for the specified
          `demand_component`:
            - 'Avg_kW_Dem_<demand_component>': The average demand in kW.
            - 'Demand_<demand_component>': The total demand charge in dollars.
    """

    # Get any value(s) for min demand present in the tariff definition:
    min_demand = 0
    min_demand_from_charge = 0
    if "Min Demand (kW)" in dem_component_details:
        min_demand = dem_component_details["Min Demand (kW)"]
    if "Min Demand Charge ($)" in dem_component_details:
        if dem_component_details["Value"] > 0:
            min_demand_from_charge = (
                dem_component_details["Min Demand Charge ($)"]
                / dem_component_details["Value"]
            )

    # Set up an empty array to hold peak values:
    average_peaks_all = np.empty((0, load_profile_selected_times.shape[1]), dtype=float)

    # Loop through each month present in the tariff component definition to find
    # peaks
    for m in dem_component_details["Month"]:
        arr = np.copy(
            load_profile_selected_times.loc[
                load_profile_selected_times.index.month == m, :
            ]
            .copy()
            .values
        )
        arr.sort(axis=0)
        arr = arr[::-1]

        # 2 * -> to change units from kWh to kW. Get the average of the peaks (if
        # the number of peaks is > 1)
        average_peaks_all = np.append(
            average_peaks_all, [2 * arr[:num_peaks, :].mean(axis=0)], axis=0
        )

    # If there is a minimum demand set in the tariff component, depending on the
    # type of minimum set, apply here:
    if min_demand_from_charge > 0:
        # If the minimum demand comes from min_demand_from_charge, apply it as
        # a clipping value
        average_peaks_all = np.clip(
            average_peaks_all, a_min=min_demand_from_charge, a_max=None
        )
    else:
        # Otherwise, if it's coming from min_demand (or is <= 0), any 'peak' value
        # less than the min_demand is set to zero.
        average_peaks_all[average_peaks_all < min_demand] = 0

    # Sum all average peaks form each month together and use this sum to calculate
    # the total demand charge for this bill.
    average_peaks_all_sum = average_peaks_all.sum(axis=0)
    results[tariff_category]["Avg_kW_Dem_" + demand_component] = (
        average_peaks_all_sum / len(dem_component_details["Month"])
    )
    results[tariff_category]["Demand_" + demand_component] = (
        average_peaks_all_sum * dem_component_details["Value"] * 365 / 12
    )  # the charges in demand charge should be in $/kW/day

    dem_charge = average_peaks_all_sum * dem_component_details["Value"] * 365 / 12

    return dem_charge


def calculate_demand_charge(
    load_profile: pd.DataFrame,
    tariff_component: dict,
    results: dict,
    tariff_category: str,
) -> float:
    """Calculate the total demand charge for all `Demand` tariff components.

    This function acts as a wrapper for `calculate_demand_charge_component()`, passing each component of a
    `Demand` tariff individually to calculate the charge for that component only.
    It also calls `time_select()` to pass only relevant parts of the load profile
    to calculate the demand charge.

    Args:
        load_profile (pd.DataFrame): A DataFrame containing half-hourly timeseries
            data with a DateTime index. It should have at least one column named 'kWh'
            containing energy usage (load) values for the corresponding half-hour
            up to index.
        tariff_component (dict): A dictionary containing tariff details. It should
            include a `Demand` key with a nested dictionary where each key represents
            a demand period and each value is a dictionary with details specifying
            month, time and weekdays during which the charge applies, as well as
            the units ($/kW/day) and rate of the charge itself.
        results (dict): A dict containing key 'load_information' with a pd.DataFrame
            value that has column 'Annual_kWh' with a single entry at index
            'kWh' that holds the annual energy usage of the given load profile,
            and key <tariff_category> with a pd.DataFrame that stores tariff component
            results. Structured as follows:
            results = {
                'load_information' : pd.DataFrame(
                    columns=['Annual_kWh'],
                    index=['kWh'],
                    data=[6758021.922]
                ),
                <tariff_category> : pd.DataFrame()
            }
        tariff_category (str): A string representing the tariff category, used
            to store the charges in the results dictionary.

    Returns:
        float: The sum of demand charges calculated based on the sum of component
            charges.

    """
    demand_charge_total = 0.0
    for demand_component, demand_component_details in tariff_component[
        "Demand"
    ].items():
        if "Number of Peaks" not in demand_component_details:
            num_of_peaks = 1
        else:
            num_of_peaks = demand_component_details["Number of Peaks"]

        lp = load_profile.copy()
        lp_selected_times = time_select(lp, demand_component_details)

        demand_charge_total += calculate_demand_charge_component(
            demand_component_details,
            num_of_peaks,
            lp_selected_times,
            tariff_category,
            demand_component,
            results,
        )

    return demand_charge_total


# -------------------- Bill Calculator function for residential and small business tariffs -----------
def bill_calculator(formatted_load_pv_data: pd.DataFrame, tariff: dict) -> dict:
    """
    Calculate the billing charges for residential or small business tariffs.

    This function computes the energy bill for a residential or small business load
    profile, including daily, fixed, flat rate, block, time-of-use (TOU), and demand
    charges. It also handles retailer-specific tariff adjustments and calculates
    feed-in tariff credits. The results are stored in a dictionary with detailed
    billing information for each tariff component.

    Args:
        formatted_load_pv_data: DataFrame containing the load profile data for one
            year. It should have a datetime index and two columns: "kWh" (load) and
            "PV" (generation).
        tariff: Dictionary containing tariff details, including tariff parameters
            and types of charges.

    Returns:
        A dictionary containing billing results for each tariff component:
            - 'load_information': DataFrame with annual consumption information.
            - 'bill_outcomes': DataFrame with charges calculated for each component
              present in the chosen tariff.

    Notes:
        - The function uses a dictionary of functions to calculate different types
          of charges based on the tariff parameters.
        - If the tariff provider is a retailer, it adjusts the tariff parameters
          accordingly.
        - The function assumes that the load profile data is provided in half-hourly
          intervals.

    """
    # Prepare load profile with net load calculation
    load_profile = formatted_load_pv_data[["kWh", "PV"]].copy().fillna(0.0)
    load_profile["Net Load"] = load_profile["kWh"] - load_profile["PV"]
    load_profile = load_profile.rename(columns={"kWh": "Load", "Net Load": "kWh"})
    load_profile = pd.DataFrame(load_profile["kWh"])

    # Initialise results dictionary
    results = {}

    # Calculate imports and exports
    temp_import = load_profile.values.copy()
    temp_export = load_profile.values.copy()
    temp_import[temp_import < 0] = 0
    temp_export[temp_export > 0] = 0

    lp_net_import = pd.DataFrame(
        temp_import, columns=load_profile.columns, index=load_profile.index
    )
    lp_net_export = pd.DataFrame(
        temp_export, columns=load_profile.columns, index=load_profile.index
    )

    # Annual summary
    results["load_information"] = pd.DataFrame(
        index=[col for col in load_profile.columns],
        data=np.sum(lp_net_import.values, axis=0),
        columns=["Annual_kWh"],
    )

    results["load_information"]["Annual_kWh_exp"] = -1 * np.sum(
        lp_net_export.values, axis=0
    )

    # If it is retailer put retailer as a component to make it similar to network tariffs
    if tariff["ProviderType"] == "Retailer":
        tariff_temp = tariff.copy()
        del tariff_temp["Parameters"]
        tariff_temp["Parameters"] = {"bill_outcomes": tariff["Parameters"]}
        tariff = tariff_temp.copy()

    func_dict = {
        "Daily": (calculate_daily_charge, "Charge_Daily"),
        "Fixed": (calculate_fixed_charge, "Charge_Fixed"),
        "FlatRate": (calculate_flatrate_charge, "Charge_FlatRate"),
        "BlockAnnual": (calculate_annual_block_charge, "Charge_BlockAnnual"),
        "BlockQuarterly": (calculate_quarterly_block_charge, "Charge_BlockQuarterly"),
        "BlockMonthly": (calculate_monthly_block_charge, "Charge_BlockMonthly"),
        "BlockDaily": (calculate_daily_block_charge, "Charge_BlockDaily"),
        "TOU": (calculate_time_of_use_charge, "Charge_TOU"),
        "Demand": (calculate_demand_charge, "Charge_Demand"),
    }

    # Set up another entry to results dict to contain charge/bill results for
    # the network component (called "Retailer" for Large Comms for consistency)
    # with small business/residential.
    for component_type, component_details in tariff["Parameters"].items():
        results[component_type] = pd.DataFrame(index=results["load_information"].index)
        results[component_type]["Charge_FiT_Rebate"] = 0

        # Calculate the FiT
        if "BlockDailyFiT" in component_details.keys():
            daily_export = lp_net_export.resample("D").sum()
            daily_export["kWh"] = (
                -1 * daily_export["kWh"]
            )  # here daily_export["kWh"] is POSITIVE

            block_fit_credit_total = 0
            prev_highbound = 0
            for block_name, block_details in component_details["BlockDailyFiT"].items():
                kwh_in_block = (
                    (daily_export["kWh"] - prev_highbound)
                    .clip(lower=0.0, upper=float(block_details["HighBound"]))
                    .sum()
                )
                credit_from_block = kwh_in_block * block_details["Value"]
                block_fit_credit_total += credit_from_block

                prev_highbound = float(block_details["HighBound"])

            # Store the result - make it negative here to match sign conventions elsewhere!
            results[component_type]["Charge_FiT_Rebate"] = -1 * block_fit_credit_total
        elif "FiT_TOU" in component_details.keys():
            load_profile_ti_exp = pd.DataFrame()
            load_profile_ti_exp_charge = pd.DataFrame()
            for k, v in component_details["FiT_TOU"].items():
                this_part = v.copy()
                if "Weekday" not in this_part:
                    this_part["Weekday"] = True
                    this_part["Weekend"] = True
                if "TimeIntervals" not in this_part:
                    this_part["TimeIntervals"] = {"T1": ["00:00", "00:00"]}
                if "Month" not in this_part:
                    this_part["Month"] = list(range(1, 13))
                load_profile_t_a = time_select(lp_net_export, this_part)
                load_profile_ti_exp[k] = load_profile_t_a.sum()
                results[component_type]["kWh_Exp" + k] = load_profile_ti_exp[k].copy()
                load_profile_ti_exp_charge[k] = (
                    this_part["Value"] * load_profile_ti_exp[k]
                )
                results[component_type]["FiT_C_TOU" + k] = load_profile_ti_exp_charge[
                    k
                ].copy()
            results[component_type]["Charge_FiT_Rebate"] = (
                load_profile_ti_exp_charge.sum(axis=1)
            )
        elif "FiT" in component_details.keys():
            results[component_type]["Charge_FiT_Rebate"] = (
                -1
                * results["load_information"]["Annual_kWh_exp"]
                * component_details["FiT"]["Value"]
            )

        # Loop through each charge component in the tariff (e.g. TOU, Demand)
        # and calculate the amount to be charged under this component
        for charge_type in component_details.keys():
            if "FiT" not in charge_type:
                results[component_type][func_dict[charge_type][1]] = func_dict[
                    charge_type
                ][0](lp_net_import, component_details, results, component_type)

    energy_comp_list = [
        "BlockAnnual",
        "BlockQuarterly",
        "BlockMonthly",
        "BlockDaily",
        "FlatRate",
        "TOU",
    ]

    for k, v in results.items():
        if k != "load_information":
            results[k]["total_bill"] = results[k][
                [col for col in results[k].columns if col.startswith("Charge")]
            ].sum(axis=1)
            results[k]["energy_charges"] = results[k][
                [
                    col
                    for col in results[k].columns
                    if (
                        col.startswith("Charge")
                        and col.endswith(tuple(energy_comp_list))
                    )
                ]
            ].sum(axis=1)
            results[k]["demand_charges"] = results[k][
                [
                    col
                    for col in results[k].columns
                    if (col.startswith("Charge") and col.endswith("Demand"))
                ]
            ].sum(axis=1)

    return results
