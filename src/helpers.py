import pandas as pd


def time_select(
    load_profile_s: pd.DataFrame, tariff_component_details: dict
) -> pd.DataFrame:
    """Filters a load profile DataFrame based on specified time intervals and days
    of the week/month from tariff component details.

    Args:
        load_profile_s: A DataFrame containing the load profile data with
             a DateTime index.
        tariff_component_details: A dictionary containing the time intervals, weekdays,
            weekends, and months for filtering. The dictionary must have the following key/value
            pairs
            - TimeIntervals: A dictionary where each key is an interval ID
                and each value is a list of two time strings (start and end).
                Time strings in 'TimeIntervals' should be in 'HH:MM' format.
                Time intervals starting at '24:00' are adjusted to '00:00'
                for proper filtering.
            - Weekday: A boolean indicating whether weekdays are included in this
                tariff component.
            - Weekend: A boolean indicating whether weekends are included in this
                tariff component.
            - Month: A list of integers representing the months included in this
                component (e.g., [1, 2, 3] for January, February, March).
            Dict structure looks like:
            tariff_component_details = {
                "Month": [
                    1,
                    2,
                    12
                ],
                "TimeIntervals": {
                    "T1": [
                        "22:00",
                        "07:00"
                    ]
                },
                "Weekday": true,
                "Weekend": false
            }

    Returns:
        load_profile_selected_times: A DataFrame filtered to
            include only the rows that fall within the specified time intervals,
            and match the specified weekday/weekend and month criteria for the
            given tariff component.

    """
    load_profile_selected_times = pd.DataFrame()
    for (
        interval_id,
        time_tuple,
    ) in tariff_component_details["TimeIntervals"].items():
        start_time_str = time_tuple[0]
        end_time_str = time_tuple[1]
        if start_time_str[0:2] == "24":
            start_time_str = time_tuple[1].replace("24", "00")
        if end_time_str[0:2] == "24":
            end_time_str = end_time_str.replace("24", "00")
        if start_time_str != end_time_str:
            lp_between_times = load_profile_s.between_time(
                start_time=start_time_str, end_time=end_time_str, inclusive="right"
            )
        else:
            lp_between_times = load_profile_s.copy()

        if not tariff_component_details["Weekday"]:
            lp_times_and_days = lp_between_times.loc[
                lp_between_times.index.weekday >= 5
            ].copy()
        elif not tariff_component_details["Weekend"]:
            lp_times_and_days = lp_between_times.loc[
                lp_between_times.index.weekday < 5
            ].copy()
        else:
            lp_times_and_days = lp_between_times.copy()
        lp_times_days_months = lp_times_and_days.loc[
            lp_times_and_days.index.month.isin(tariff_component_details["Month"]), :
        ].copy()

        load_profile_selected_times = pd.concat(
            [load_profile_selected_times, lp_times_days_months]
        )
    return load_profile_selected_times


def format_load_pv_data(input_load_pv_data: pd.DataFrame) -> pd.DataFrame:
    """
    Format the input load profile data into a standardised DataFrame for bill calculation.

    Args:
        input_load_pv_data: A DataFrame containing load profile data with a datetime index.
            It should have at least two columns named 'kWh' and 'PV' containing interval
            load and generation data respectively.

    Returns:
        pd.DataFrame: A formatted DataFrame with columns 'load', 'generation',
            'import', 'export', and 'net_load' containing interval (same as input)
            load profile data in kWh. All values are positive.

    Raises:
        ValueError: If input_load_pv_data is empty or None, or if it does not have a datetime index.
    """
    if input_load_pv_data is None or input_load_pv_data.empty:
        raise ValueError("input_load_pv_data is empty or None")

    if not isinstance(input_load_pv_data.index, pd.DatetimeIndex):
        raise ValueError("input_load_pv_data must have a datetime index")

    load_pv_data = input_load_pv_data[["kWh", "PV"]].copy().fillna(0.0)
    load_pv_data = load_pv_data.rename(columns={"kWh": "load", "PV": "generation"})

    load_pv_data["net_load"] = load_pv_data["load"] - load_pv_data["generation"]

    load_pv_data["import"] = load_pv_data["net_load"].clip(lower=0.0)
    load_pv_data["export"] = load_pv_data["net_load"].clip(upper=0.0) * -1

    return load_pv_data[["load", "generation", "import", "export", "net_load"]].copy()


def create_annual_load_profile_summary_single(
    load_profile: pd.DataFrame, site_id: str
) -> pd.DataFrame:
    # 1. avg. daily load per year
    # 2. total load per year
    # 3. avg. daily export per year
    # 4. total export per year

    """
    Calculate a summary of the given load profile's annual energy usage.

    Args:
        load_profile (pd.DataFrame): A DataFrame containing the load profile data with
            a datetime index. It should have at least two columns named 'load' and 'generation'
            containing interval load and generation data respectively.
        site_id (str): The ID of the site associated with the given load profile.

    Returns:
        pd.DataFrame: A DataFrame containing the average daily load per year, total load per year,
            average daily export per year, and total export per year for the given load profile.

    """

    load_profile["Year"] = load_profile.index.year.astype(str)
    load_profile["Day"] = load_profile.index.day.astype(str)
    total_daily = load_profile.groupby(["Year", "Day"])["net_load"].sum()
    average_daily = total_daily.groupby("Year").mean()
    average_daily.name = "Average Daily Net Load (kWh)"

    total_yearly = load_profile.groupby("Year")[
        ["load", "generation", "import", "export"]
    ].sum()

    rename_energy_cols = {
        col: f"Total {col.capitalize()} (kWh)" for col in total_yearly.columns
    }
    total_yearly = total_yearly.rename(columns=rename_energy_cols)

    return total_yearly.merge(
        average_daily, left_index=True, right_index=True
    ).reset_index()
