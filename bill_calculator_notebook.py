# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "marimo>=0.18.0",
#     "pandas>=2.3.0",
#     "numpy>=2.0.0",
#     "plotly>=5.0.0",
#     "altair==6.0.0",
#     "pyarrow==23.0.0",
# ]
# ///

import marimo

__generated_with = "0.20.4"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def _():
    import altair as alt
    import marimo as mo
    import numpy as np
    import pandas as pd

    return alt, mo, np, pd


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    # Bill Calculator

    This interactive notebook calculates electricity bills for residential and
    small business customers under different tariff structures.

    **Features:**
    - Compare bills with and without solar PV
    - Model battery storage to maximise self-consumption
    - Explore different tariff types (flat rate, time of use, demand charges)
    - Download results for further analysis

    Use the controls below to configure your scenario and explore the outcomes.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ## 1. Load Data

    Choose a data source below: use one of the sample customer profiles, or upload
    your own CSV file(s) with load and PV generation data.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    data_source_toggle = mo.ui.radio(
        options={"Sample Data": "sample", "Upload Custom Data": "upload"},
        value="Sample Data",
        label="Data Source:",
    )
    data_source_toggle
    return (data_source_toggle,)


@app.cell(hide_code=True)
def _(data_source_toggle, mo):
    # Sample data file selector (using GitHub raw URLs for WASM compatibility)
    _base_url = "https://raw.githubusercontent.com/EllieKallmier/bill_calculator/main/sample_data/"
    _sample_files = {
        "S0023": f"{_base_url}S0023_profile.csv",
        "S0033": f"{_base_url}S0033_profile.csv",
        "S0040": f"{_base_url}S0040_profile.csv",
        "S0047": f"{_base_url}S0047_profile.csv",
        "S0057": f"{_base_url}S0057_profile.csv",
        "S0077": f"{_base_url}S0077_profile.csv",
        "S0093": f"{_base_url}S0093_profile.csv",
        "S0153": f"{_base_url}S0153_profile.csv",
        "S0164": f"{_base_url}S0164_profile.csv",
        "S0179": f"{_base_url}S0179_profile.csv",
        "S0182": f"{_base_url}S0182_profile.csv",
        "S0187": f"{_base_url}S0187_profile.csv",
        "S0189": f"{_base_url}S0189_profile.csv",
        "S0232": f"{_base_url}S0232_profile.csv",
        "S0244": f"{_base_url}S0244_profile.csv",
    }
    sample_data_selector = mo.ui.dropdown(
        options=_sample_files,
        value="S0023",
        label="Select load profile:",
    )
    # Only show if sample data is selected
    sample_data_selector if data_source_toggle.value == "sample" else None
    return (sample_data_selector,)


@app.cell(hide_code=True)
def _(data_source_toggle, mo):
    # File upload widget for custom data
    file_upload = mo.ui.file(
        filetypes=[".csv"],
        multiple=True,
        label="Upload CSV file(s):",
    )

    _format_docs = mo.md("""
    ### Required Data Format

    Your CSV file(s) must contain the following columns:

    | Column | Description | Required |
    |--------|-------------|----------|
    | `TS` | Timestamp (see accepted formats below) | Yes |
    | `Wh` or `kWh` | Electricity consumption per interval | Yes |
    | `PV` | Solar PV generation per interval (same units as consumption) | No (defaults to 0) |
    | `CUSTOMER_ID` | Identifier for the customer/site | No (defaults to filename) |

    **Accepted timestamp formats:**
    - `2020-01-01 00:00:00` (ISO format, recommended)
    - `2020-01-01T00:00:00` (ISO with T separator)
    - `01/01/2020 00:00` (day/month/year)
    - `1/01/2020 0:00` (without leading zeros)
    - `2020/01/01 00:00:00` (year first with slashes)
    - `01-Jan-2020 00:00:00` (with month name)

    **Notes:**
    - Data should be at regular intervals (e.g., 5-minute, 15-minute, or 30-minute)
    - If using `Wh`, values will be converted to `kWh` automatically
    - You can upload multiple files to compare different customers/sites
    - Each file should contain data for one customer (or use `CUSTOMER_ID` to distinguish)

    **Example:**
    ```
    TS,Wh,PV
    2020-01-01 00:00:00,250.5,0.0
    2020-01-01 00:30:00,245.2,0.0
    2020-01-01 01:00:00,238.1,0.0
    ...
    ```
    """)

    # Only show if upload is selected
    mo.vstack(
        [file_upload, _format_docs]
    ) if data_source_toggle.value == "upload" else None
    return (file_upload,)


@app.cell(hide_code=True)
def _(data_source_toggle, file_upload, mo, pd):
    # Common datetime formats to try (in order of preference)
    DATETIME_FORMATS = [
        None,  # Let pandas infer first
        "%Y-%m-%d %H:%M:%S",  # 2020-01-01 00:00:00
        "%Y-%m-%dT%H:%M:%S",  # 2020-01-01T00:00:00
        "%d/%m/%Y %H:%M:%S",  # 01/01/2020 00:00:00
        "%d/%m/%Y %H:%M",  # 01/01/2020 00:00
        "%Y/%m/%d %H:%M:%S",  # 2020/01/01 00:00:00
        "%d-%b-%Y %H:%M:%S",  # 01-Jan-2020 00:00:00
        "%d-%m-%Y %H:%M:%S",  # 01-01-2020 00:00:00
        "%m/%d/%Y %H:%M:%S",  # 01/01/2020 00:00:00 (US format)
        "%m/%d/%Y %H:%M",  # 01/01/2020 00:00 (US format)
    ]

    def parse_datetime_column(series):
        """Try multiple datetime formats and return parsed series with status."""
        # First, try pandas automatic inference
        try:
            parsed = pd.to_datetime(series, dayfirst=True)
            # Check if parsing was successful (no NaT values that weren't already null)
            if parsed.isna().sum() <= series.isna().sum():
                return parsed, None, "auto-detected"
        except Exception:
            pass

        # Try each format explicitly
        for fmt in DATETIME_FORMATS:
            if fmt is None:
                continue
            try:
                parsed = pd.to_datetime(series, format=fmt)
                if parsed.isna().sum() <= series.isna().sum():
                    return parsed, None, fmt
            except Exception:
                continue

        # If all formats fail, provide helpful error message
        sample_values = series.dropna().head(3).tolist()
        error_msg = (
            f"Could not parse timestamp column. "
            f"Sample values: {sample_values}. "
            f"Please use a format like `2020-01-01 00:00:00` or `01/01/2020 00:00`."
        )
        return None, error_msg, None

    def validate_and_parse_uploads(files):
        """Validate uploaded CSV files and return parsed DataFrames with validation status."""
        results = []
        errors = []
        warnings = []

        for file in files:
            filename = file.name
            try:
                # Read CSV content
                import io

                content = file.contents.decode("utf-8")
                df = pd.read_csv(io.StringIO(content))

                # Check for required timestamp column
                if "TS" not in df.columns:
                    errors.append(f"**{filename}**: Missing required column `TS`")
                    continue

                # Check for consumption column (Wh or kWh)
                has_wh = "Wh" in df.columns
                has_kwh = "kWh" in df.columns
                if not has_wh and not has_kwh:
                    errors.append(
                        f"**{filename}**: Missing consumption column (`Wh` or `kWh`)"
                    )
                    continue

                # Parse timestamps with robust format detection
                parsed_ts, ts_error, detected_format = parse_datetime_column(df["TS"])
                if ts_error:
                    errors.append(f"**{filename}**: {ts_error}")
                    continue

                df["TS"] = parsed_ts
                df = df.set_index("TS")

                # Check for timezone info and warn if present
                if df.index.tz is not None:
                    df.index = df.index.tz_localize(None)
                    warnings.append(
                        f"**{filename}**: Timezone info removed from timestamps"
                    )

                # Validate timestamps are sorted and check for gaps
                if not df.index.is_monotonic_increasing:
                    df = df.sort_index()
                    warnings.append(
                        f"**{filename}**: Data was not sorted by time; sorted automatically"
                    )

                # Add CUSTOMER_ID if missing (use filename)
                if "CUSTOMER_ID" not in df.columns:
                    customer_id = filename.rsplit(".", 1)[0]
                    df["CUSTOMER_ID"] = customer_id

                # Add PV column if missing
                if "PV" not in df.columns:
                    df["PV"] = 0.0

                # Standardise to kWh
                if has_wh and not has_kwh:
                    df["kWh"] = df["Wh"] * 1e-3
                    df = df.drop(columns=["Wh"])

                # Detect data interval
                if len(df) > 1:
                    intervals = df.index.to_series().diff().dropna()
                    median_interval = intervals.median()
                    interval_minutes = median_interval.total_seconds() / 60
                else:
                    interval_minutes = None

                results.append(
                    {
                        "filename": filename,
                        "df": df,
                        "rows": len(df),
                        "customer_id": df["CUSTOMER_ID"].iloc[0]
                        if "CUSTOMER_ID" in df.columns
                        else filename,
                        "datetime_format": detected_format,
                        "interval_minutes": interval_minutes,
                        "start_date": df.index.min(),
                        "end_date": df.index.max(),
                    }
                )

            except Exception as e:
                errors.append(f"**{filename}**: Error parsing file - {str(e)}")

        return results, errors, warnings

    # Process uploads if in upload mode and files are present
    upload_results = []
    upload_errors = []
    upload_warnings = []
    if data_source_toggle.value == "upload" and file_upload.value:
        upload_results, upload_errors, upload_warnings = validate_and_parse_uploads(
            file_upload.value
        )

    # Display validation status
    _output = None
    if data_source_toggle.value == "upload":
        if not file_upload.value:
            _output = mo.callout(
                mo.md("**Upload one or more CSV files** to begin analysis."),
                kind="info",
            )
        elif upload_errors:
            _error_list = "\n".join([f"- {e}" for e in upload_errors])
            _output = mo.callout(
                mo.md(f"**Validation errors:**\n\n{_error_list}"),
                kind="danger",
            )
        elif upload_results:
            # Build detailed success message
            _success_items = []
            for r in upload_results:
                _interval_str = (
                    f"{r['interval_minutes']:.0f}-min intervals"
                    if r["interval_minutes"]
                    else "unknown interval"
                )
                _date_range = f"{r['start_date'].strftime('%d %b %Y')} to {r['end_date'].strftime('%d %b %Y')}"
                _success_items.append(
                    f"- **{r['filename']}**: {r['rows']:,} rows, {_interval_str}, {_date_range}"
                )
            _success_list = "\n".join(_success_items)

            _warning_section = ""
            if upload_warnings:
                _warning_list = "\n".join([f"- {w}" for w in upload_warnings])
                _warning_section = f"\n\n**Warnings:**\n{_warning_list}"

            _output = mo.callout(
                mo.md(
                    f"**Successfully loaded {len(upload_results)} file(s):**\n\n{_success_list}{_warning_section}"
                ),
                kind="success",
            )
    _output
    return (upload_results,)


@app.cell(hide_code=True)
def _(data_source_toggle, mo, upload_results):
    # Profile selector for uploaded data (when multiple profiles are uploaded)
    uploaded_profile_selector = None
    if (
        data_source_toggle.value == "upload"
        and upload_results
        and len(upload_results) > 1
    ):
        _options = {r["customer_id"]: r["customer_id"] for r in upload_results}
        uploaded_profile_selector = mo.ui.dropdown(
            options=_options,
            value=upload_results[0]["customer_id"],
            label="Select profile to analyse:",
        )
        uploaded_profile_selector
    return (uploaded_profile_selector,)


@app.cell(hide_code=True)
def _(
    data_source_toggle,
    pd,
    sample_data_selector,
    upload_results,
    uploaded_profile_selector,
):
    # Load data based on selected source
    load_profile = None

    if data_source_toggle.value == "sample":
        # Load selected sample data from GitHub
        _base_url = "https://raw.githubusercontent.com/EllieKallmier/bill_calculator/main/sample_data/"
        _filepath = sample_data_selector.value or f"{_base_url}S0023_profile.csv"
        sample_load_profile = pd.read_csv(
            _filepath,
            parse_dates=["TS"],
            index_col="TS",
        )

        # Pre-process the sample data
        load_profile = sample_load_profile.drop(columns=["CUSTOMER_ID"])
        load_profile = load_profile.fillna(0.0)
        load_profile = load_profile * 1e-3  # Convert Wh to kWh
        load_profile = load_profile.rename(columns={"Wh": "kWh"})
        load_profile = load_profile.resample("30min").sum()
        load_profile = load_profile[load_profile.index.year == 2020]

    elif data_source_toggle.value == "upload" and upload_results:
        # Use uploaded data
        if len(upload_results) == 1:
            # Single file uploaded
            _df = upload_results[0]["df"].copy()
        else:
            # Multiple files - use the selected profile
            _selected_id = (
                uploaded_profile_selector.value
                if uploaded_profile_selector
                else upload_results[0]["customer_id"]
            )
            _df = next(
                (r["df"] for r in upload_results if r["customer_id"] == _selected_id),
                upload_results[0]["df"],
            ).copy()

        # Pre-process uploaded data
        if "CUSTOMER_ID" in _df.columns:
            _df = _df.drop(columns=["CUSTOMER_ID"])
        load_profile = _df.fillna(0.0)
        # Resample to 30-minute intervals
        load_profile = load_profile.resample("30min").sum()
    return (load_profile,)


@app.cell(hide_code=True)
def _(load_profile, mo):
    # Display data summary
    _output = None
    if load_profile is not None and not load_profile.empty:
        annual_load = load_profile["kWh"].sum()
        annual_pv = load_profile["PV"].sum()

        _output = mo.callout(
            mo.md(
                f"""
                **Data Summary:**
                - **Period:** {load_profile.index.min().strftime("%d %b %Y")} to {load_profile.index.max().strftime("%d %b %Y")}
                - **Annual Load:** {annual_load:,.0f} kWh
                - **Annual PV Generation:** {annual_pv:,.0f} kWh
                - **Data Points:** {len(load_profile):,} (half-hourly intervals)
                """
            ),
            kind="info",
        )
    _output
    return


@app.cell(hide_code=True)
def _(alt, load_profile, mo):
    # Interactive chart of load and PV data
    _output = None
    if load_profile is not None and not load_profile.empty:
        long_form_load = (
            load_profile.reset_index()
            .rename(columns={"PV": "Generation", "kWh": "Load"})
            .melt("TS", var_name="Data", value_name="Energy (kWh)")
        )

        _colour = {
            "field": "Data",
            "scale": {
                "domain": ["Generation", "Load"],
                "range": ["gold", "dodgerblue"],
            },
        }

        _interval = alt.selection_interval(encodings=["x"])
        base_simple = (
            alt.Chart(
                long_form_load,
            )
            .mark_line()
            .encode(
                x="TS:T",
                y="Energy (kWh):Q",
                color=_colour,
            )
        )
        chart_simple = base_simple.encode(
            x=alt.X("TS:T").scale(domain=_interval)
        ).properties(width=1200, height=300, title="Load and generation profile")
        view_simple = base_simple.add_params(
            _interval,
        ).properties(width=1200, height=100, title="Click and drag to explore detail")

        _chart = chart_simple & view_simple
        _output = mo.ui.altair_chart(_chart)
    _output
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ## 2. Select Tariffs

    Use the dropdowns below to filter and select tariffs for comparison.
    The tariffs are sourced from the CEEM electricity tariff database.
    """)
    return


@app.cell(hide_code=True)
def _(
    customer_dropdown,
    distributor_dropdown,
    mo,
    state_dropdown,
    type_dropdown,
):
    mo.hstack(
        [state_dropdown, distributor_dropdown, type_dropdown, customer_dropdown],
        justify="start",
        gap=1,
    )
    return


@app.cell(hide_code=True)
def _(mo, tariff_selector):
    mo.vstack([mo.md("### Choose Tariffs"), tariff_selector])
    return


@app.cell(hide_code=True)
def _(custom_tariffs_list, mo, tariff_selector):
    # Show selected tariff count (including custom tariffs if added)
    _selected = tariff_selector.value if hasattr(tariff_selector, "value") else []
    _api_count = len(_selected)
    _custom_count = len(custom_tariffs_list) if custom_tariffs_list else 0
    _total_count = _api_count + _custom_count

    _output = None
    if _total_count > 0:
        _custom_note = ""
        if _custom_count > 0:
            _custom_names = ", ".join([t["Name"] for t in custom_tariffs_list])
            _custom_note = (
                f" (including {_custom_count} custom tariff(s): *{_custom_names}*)"
            )
        _output = mo.callout(
            mo.md(
                f"**{_total_count} tariff(s) selected** for comparison{_custom_note}."
            ),
            kind="success",
        )
    _output
    return


@app.cell(hide_code=True)
def _(fetch_all_tariffs):
    # Fetch all available tariffs
    all_tariffs, filter_options = fetch_all_tariffs()
    return all_tariffs, filter_options


@app.cell(hide_code=True)
def _(filter_options, mo):
    # Create filter dropdowns
    state_dropdown = mo.ui.dropdown(
        options={"All States": None} | {s: s for s in filter_options["states"]},
        value=None,
        label="State",
    )

    distributor_dropdown = mo.ui.dropdown(
        options={"All Distributors": None}
        | {d: d for d in filter_options["distributors"]},
        value=None,
        label="Distributor (DNSP)",
    )

    type_dropdown = mo.ui.dropdown(
        options={"All Types": None} | {t: t for t in filter_options["types"]},
        value=None,
        label="Tariff Type",
    )

    customer_dropdown = mo.ui.dropdown(
        options={"All Customers": None}
        | {c: c for c in filter_options["customer_types"]},
        value="Residential",
        label="Customer Type",
    )
    return (
        customer_dropdown,
        distributor_dropdown,
        state_dropdown,
        type_dropdown,
    )


@app.cell(hide_code=True)
def _(
    all_tariffs,
    customer_dropdown,
    distributor_dropdown,
    filter_tariffs,
    state_dropdown,
    type_dropdown,
):
    # Filter tariffs based on selections
    filtered_tariffs = filter_tariffs(
        all_tariffs,
        distributor=distributor_dropdown.value,
        state=state_dropdown.value,
        tariff_type=type_dropdown.value,
        customer_type=customer_dropdown.value,
    )
    return (filtered_tariffs,)


@app.cell(hide_code=True)
def _(filtered_tariffs, mo):
    # Create tariff selection dropdown
    if not filtered_tariffs:
        tariff_selector = mo.md(
            "**No tariffs match your filters.** Try adjusting the filters above."
        )
    else:
        tariff_options = {t["Name"]: t for t in filtered_tariffs}
        # Use the first tariff's name as the default value (not the dict)
        default_selection = [filtered_tariffs[0]["Name"]] if filtered_tariffs else []
        tariff_selector = mo.ui.multiselect(
            options=tariff_options,
            label="Select tariffs to compare (choose one or more)",
            value=default_selection,
        )
    return (tariff_selector,)


@app.cell(hide_code=True)
def _(mo):
    mo.accordion(
        {
            "Expand to add custom tariffs (Optional)": mo.md("""
    ### Add Custom Tariffs (Optional)

    You can define your own tariffs by editing the list in the code cell below.
    Multiple tariffs can be added to the list and will be included in the bill
    calculations alongside any tariffs you've selected above.

    **Instructions:**
    1. Make sure this notebook view is set so that you can see a Python code cell below ('Toggle app view' button)
    2. Click into the code cell below (or use the cell settings to 'Unhide') to edit contents
    3. Add tariff dictionaries to the `custom_tariffs` list
    4. Run the cell to apply your changes

    **Tariff structure guide:**
    - `Name`: Display name for your tariff
    - `Daily`: Fixed daily supply charge in $/day
    - `FlatRate`: Single energy rate in $/kWh (for single rate tariffs)
    - `TOU`: Time-of-use components with rates, time intervals, and day/month applicability
    - `FiT`: Feed-in tariff credit rate in $/kWh
    """)
        }
    )
    return


@app.cell(hide_code=True)
def _():
    # CUSTOM TARIFFS CONFIGURATION (OPTIONAL)
    # Add your custom tariffs to this list. Each tariff should be a dictionary
    # following the structure shown in the examples below.
    # ============================================================

    custom_tariffs = [
        # ------------------------------------------------------------
        # EXAMPLE 1: Simple Single Rate Tariff
        # ------------------------------------------------------------
        # {
        #     "Name": "My Custom Single Rate",
        #     "Type": "Single Rate",
        #     "ProviderType": "Retailer",
        #     "CustomerType": "Residential",
        #     "State": "Custom",
        #     "Distributor": "Custom",
        #     "Parameters": {
        #         "Daily": {"Unit": "$/day", "Value": 1.00},
        #         "FlatRate": {"Unit": "$/kWh", "Value": 0.25},
        #         "FiT": {"Unit": "$/kWh", "Value": 0.05},
        #     },
        # },
        # ------------------------------------------------------------
        # EXAMPLE 2: Time of Use Tariff
        # ------------------------------------------------------------
        # {
        #     "Name": "My Custom TOU Tariff",
        #     "Type": "TOU",
        #     "ProviderType": "Retailer",
        #     "CustomerType": "Residential",
        #     "State": "Custom",
        #     "Distributor": "Custom",
        #     "Parameters": {
        #         "Daily": {"Unit": "$/day", "Value": 1.00},
        #         "TOU": {
        #             "Peak": {
        #                 "Unit": "$/kWh",
        #                 "Value": 0.35,
        #                 "TimeIntervals": {"T1": ["14:00", "20:00"]},
        #                 "Weekday": True,
        #                 "Weekend": False,
        #                 "Month": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
        #             },
        #             "Shoulder": {
        #                 "Unit": "$/kWh",
        #                 "Value": 0.25,
        #                 "TimeIntervals": {"T1": ["07:00", "14:00"], "T2": ["20:00", "22:00"]},
        #                 "Weekday": True,
        #                 "Weekend": False,
        #                 "Month": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
        #             },
        #             "OffPeak": {
        #                 "Unit": "$/kWh",
        #                 "Value": 0.15,
        #                 "TimeIntervals": {"T1": ["22:00", "07:00"]},
        #                 "Weekday": True,
        #                 "Weekend": True,
        #                 "Month": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
        #             },
        #         },
        #         "FiT": {"Unit": "$/kWh", "Value": 0.05},
        #     },
        # },
        # ------------------------------------------------------------
        # Add more tariffs here by copying and modifying the examples above
        # ------------------------------------------------------------
    ]

    # Export the list for use in calculations
    custom_tariffs_list = custom_tariffs if custom_tariffs else []
    return (custom_tariffs_list,)


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ## 3. Battery Configuration

    Optionally add a battery to the scenario. The battery uses a simple
    algorithm to maximise self-consumption of solar PV generation.
    """)
    return


@app.cell(hide_code=True)
def _(battery_form, include_battery, mo):
    mo.vstack(
        [
            include_battery,
            battery_form if include_battery.value else mo.md(""),
        ]
    )
    return


@app.cell(hide_code=True)
def _(mo):
    # Battery configuration form
    battery_form = mo.ui.form(
        mo.md("""
        **Battery Specifications**

        {power}

        {capacity}

        {efficiency}
        """).batch(
            power=mo.ui.number(
                start=0.0,
                stop=50.0,
                step=0.5,
                value=5.0,
                label="Max. power rating (kW):",
            ),
            capacity=mo.ui.number(
                start=0.0,
                stop=100.0,
                step=0.5,
                value=10.0,
                label="Capacity (kWh):",
            ),
            efficiency=mo.ui.number(
                start=0.5,
                stop=1.0,
                step=0.01,
                value=0.90,
                label="Round-trip Efficiency:",
            ),
        ),
        submit_button_label="Apply Battery Settings",
    )
    return (battery_form,)


@app.cell(hide_code=True)
def _(mo):
    # Include battery checkbox and form display
    include_battery = mo.ui.checkbox(label="Include battery in analysis", value=False)
    return (include_battery,)


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ## 4. Calculate Bills

    Once your tariffs have been selected and you've input battery parameters (if you want to add a battery to the calculations), the bill calculations for your input scenario(s) will automatically run.
    """)
    return


@app.cell(hide_code=True)
def _(
    battery_form,
    bill_calculator,
    custom_tariffs_list,
    include_battery,
    load_profile,
    pd,
    run_battery_self_consumption,
    tariff_selector,
):
    # Get selected tariffs from the multiselect
    _tariffs_to_calculate = list(
        tariff_selector.value
        if hasattr(tariff_selector, "value") and tariff_selector.value
        else []
    )

    # Add all custom tariffs to the calculation list
    if custom_tariffs_list:
        _tariffs_to_calculate.extend(custom_tariffs_list)

    # Get battery parameters from form (use defaults if not yet submitted)
    _battery_params = battery_form.value or {}
    _battery_kw = _battery_params.get("power", 5.0)
    _battery_kwh = _battery_params.get("capacity", 10.0)
    _battery_eff = _battery_params.get("efficiency", 0.90)

    all_bill_results = []
    for _tariff in _tariffs_to_calculate:
        # Scenario 1: No solar, no battery
        _lp_no_pv = load_profile.copy()
        _lp_no_pv["PV"] = 0.0
        _results_no_pv = bill_calculator(_lp_no_pv, _tariff)
        _bill_no_pv = _results_no_pv["bill_outcomes"].copy()
        _bill_no_pv["Tariff"] = _tariff["Name"]
        _bill_no_pv["Scenario"] = "No Solar"
        all_bill_results.append(_bill_no_pv)

        # Scenario 2: With solar (always calculated)
        _results_solar = bill_calculator(load_profile, _tariff)
        _bill_solar = _results_solar["bill_outcomes"].copy()
        _bill_solar["Tariff"] = _tariff["Name"]
        _bill_solar["Scenario"] = "With Solar"
        all_bill_results.append(_bill_solar)

        # Scenario 3: With solar and battery (if battery enabled)
        if include_battery.value:
            _lp_battery = run_battery_self_consumption(
                load_profile,
                battery_kw=_battery_kw,
                battery_kwh=_battery_kwh,
                battery_eff=_battery_eff,
            )
            _results_battery = bill_calculator(_lp_battery[["kWh", "PV"]], _tariff)
            _bill_battery = _results_battery["bill_outcomes"].copy()
            _bill_battery["Tariff"] = _tariff["Name"]
            _bill_battery["Scenario"] = "Solar + Battery"
            all_bill_results.append(_bill_battery)

    # Combine all results
    if all_bill_results:
        combined_results = pd.concat(all_bill_results, axis=0).reset_index(drop=True)
    else:
        combined_results = pd.DataFrame()

    # Combine all load profiles with an extra column to hold "Scenario"
    lp_no_pv = _lp_no_pv.copy().reset_index()
    lp_no_pv["Scenario"] = "No Solar"
    all_load_profiles = [lp_no_pv]

    lp_solar_only = load_profile.copy().reset_index()
    lp_solar_only["Scenario"] = "With Solar"
    all_load_profiles.append(lp_solar_only)

    if include_battery.value:
        lp_solar_battery = _lp_battery.copy().reset_index()
        lp_solar_battery["Scenario"] = "Solar + Battery"
        all_load_profiles.append(lp_solar_battery)

    # Combine all load profiles into a single DataFrame
    all_load_profiles = pd.concat(all_load_profiles, axis=0)
    return all_load_profiles, combined_results


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ## 5. Results

    The table and chart below show the calculated bill outcomes for each
    scenario.
    """)
    return


@app.cell(hide_code=True)
def _(combined_results, mo):
    # Display results table
    _output = None
    if combined_results.empty:
        _output = mo.callout(
            mo.md("**No results yet.** Select at least one tariff above."),
            kind="warn",
        )
    else:
        # Select key columns for display
        _display_cols = [
            "Tariff",
            "Scenario",
            "Charge_Daily",
            "energy_charges",
            "demand_charges",
            "Charge_FiT_Rebate",
            "total_bill",
        ]
        _available_cols = [c for c in _display_cols if c in combined_results.columns]
        _display_df = combined_results[_available_cols].copy()

        # Rename columns for readability
        _rename_map = {
            "Charge_Daily": "Daily Charges ($)",
            "energy_charges": "Energy Charges ($)",
            "demand_charges": "Demand Charges ($)",
            "Charge_FiT_Rebate": "FiT Credit ($)",
            "total_bill": "Total Bill ($)",
        }
        _display_df = _display_df.rename(columns=_rename_map)
        _format_map = {col_name: "{:.2f}".format for col_name in _rename_map.values()}

        _output = mo.ui.table(
            _display_df, label="Bill Calculation Results", format_mapping=_format_map
        )

    _output
    return


@app.cell(hide_code=True)
def _(alt, combined_results, mo):
    # Create comparison bar chart using Altair
    _output = None
    if not combined_results.empty and "total_bill" in combined_results.columns:
        # Color scale for scenarios
        _color_scale = alt.Scale(
            domain=["No Solar", "With Solar", "Solar + Battery"],
            range=["#1f77b4", "#ff7f0e", "#2ca02c"],
        )
        _chart = (
            alt.Chart(combined_results)
            .mark_bar()
            .encode(
                x=alt.X("Tariff:N", title="Tariff Name"),
                y=alt.Y("total_bill:Q", title="Total Bill ($)"),
                color=alt.Color("Scenario:N", scale=_color_scale, title="Scenario"),
                xOffset="Scenario:N",
            )
            .properties(title="Total Annual Bill Comparison", width=1200, height=300)
        )
        _output = mo.ui.altair_chart(_chart)

    _output
    return


@app.cell(hide_code=True)
def _(all_load_profiles, alt, mo):
    # Net load visualization: full year overview + zoomed single day detail
    _output = None

    if not all_load_profiles.empty:
        # Calculate net load (consumption - generation)
        _lp = all_load_profiles.copy()
        # Only grab one month of data to avoid "too many rows" error and simplify stuff:
        _lp = _lp[_lp["TS"].dt.month == 1].copy()
        _lp["Net_Load_kWh"] = _lp["kWh"] - _lp["PV"]

        # Color scale for scenarios
        _color_scale = alt.Scale(
            domain=["No Solar", "With Solar", "Solar + Battery"],
            range=["#1f77b4", "#ff7f0e", "#2ca02c"],
        )

        # Full year overview (top chart - for brush selection)
        _overview = (
            alt.Chart(_lp)
            .mark_line(opacity=0.7)
            .encode(
                x=alt.X("TS:T", title="Date"),
                y=alt.Y("Net_Load_kWh:Q", title="Net Load (kWh)"),
                color=alt.Color("Scenario:N", scale=_color_scale, title="Scenario"),
            )
            .properties(
                height=100, width=1200, title="January Overview (drag to select a day)"
            )
        )

        # Create interval selection for brushing
        _brush = alt.selection_interval(encodings=["x"])

        _overview_with_brush = _overview.add_params(_brush)

        # Detail view (bottom chart - responds to brush)
        _detail = (
            alt.Chart(_lp)
            .mark_line()
            .encode(
                x=alt.X("TS:T", title="Time"),
                y=alt.Y("Net_Load_kWh:Q", title="Net Load (kWh)"),
                color=alt.Color("Scenario:N", scale=_color_scale, title="Scenario"),
            )
            .properties(height=300, width=1200, title="Detailed View")
            .transform_filter(_brush)
        )

        # Combine charts vertically
        _combined_chart = alt.vconcat(_overview_with_brush, _detail).resolve_scale(
            color="shared"
        )

        _output = mo.vstack(
            [
                mo.md("### Net Load by Scenario"),
                mo.md(
                    "*Net load = Consumption - PV Generation. Negative values indicate export to grid.*"
                ),
                _combined_chart,
            ]
        )

    _output
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ## 6. Download Results

    Download the full results table as a CSV file for further analysis.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    # Filename inputs for downloads
    bill_filename_input = mo.ui.text(
        value="bill_results",
        label="Bill results filename:",
        placeholder="Enter filename (without .csv)",
    )
    load_filename_input = mo.ui.text(
        value="load_profile_results",
        label="Load profile filename:",
        placeholder="Enter filename (without .csv)",
    )
    return bill_filename_input, load_filename_input


@app.cell(hide_code=True)
def _(
    all_load_profiles,
    bill_filename_input,
    combined_results,
    load_filename_input,
    mo,
):
    # Download buttons with custom filenames
    _output = None
    if not combined_results.empty:
        _csv_data = combined_results.to_csv(index=False)
        _bill_filename = f"{bill_filename_input.value or 'bill_results'}.csv"
        bill_calc_download = mo.download(
            data=_csv_data.encode("utf-8"),
            filename=_bill_filename,
            label="Download Bill Results (CSV)",
        )

        _load_data = all_load_profiles.to_csv(index=False)
        _load_filename = f"{load_filename_input.value or 'load_profile'}.csv"
        load_data_download = mo.download(
            data=_load_data.encode("utf-8"),
            filename=_load_filename,
            label="Download Load & PV Data (CSV)",
        )

        _output = mo.hstack(
            [
                mo.vstack([bill_filename_input, bill_calc_download], align="center"),
                mo.vstack([load_filename_input, load_data_download], align="center"),
            ],
            justify="center",
        )
    else:
        _output = mo.md("*No results to download yet.*")

    _output
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ---

    ## Further Exploration

    **For advanced students:**
    - Expand the hidden code cells below to see how the calculation functions work
    - Try modifying the battery algorithm or tariff calculations
    - Test custom tariffs or explore network vs. retail components of tariffs
    """)
    return


@app.cell(hide_code=True)
def _(pd):
    # ---------------------------------------------------------------------------
    # Time selection helper function
    # ---------------------------------------------------------------------------
    def time_select(
        load_profile_s: pd.DataFrame, tariff_component_details: dict
    ) -> pd.DataFrame:
        """Filters a load profile DataFrame based on specified time intervals and days."""
        load_profile_selected_times = pd.DataFrame()
        for interval_id, time_tuple in tariff_component_details[
            "TimeIntervals"
        ].items():
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

    return (time_select,)


@app.cell(hide_code=True)
def _(np, pd, time_select):
    # ---------------------------------------------------------------------------
    # Charge calculation functions
    # ---------------------------------------------------------------------------
    def calculate_daily_charge(
        load_profile: pd.DataFrame,
        tariff_component: dict,
        results: dict,
        tariff_category: str,
    ) -> float:
        """Calculates the total daily charges for a bill."""
        num_days = len(load_profile.index.normalize().unique()) - 1
        daily_charge = num_days * tariff_component["Daily"]["Value"]
        return daily_charge

    def calculate_fixed_charge(
        load_profile: pd.DataFrame,
        tariff_component: dict,
        results: dict,
        tariff_category: str,
    ) -> float:
        """Returns the total fixed charges for a bill."""
        return tariff_component["Fixed"]["Value"]

    def calculate_flatrate_charge(
        load_profile: pd.DataFrame,
        tariff_component: dict,
        results: dict,
        tariff_category: str,
    ) -> float:
        """Calculates the total of all flat rate charges for a bill."""
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
        """Calculates the total of all annual block charges for a bill."""
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
        """Calculates the quarterly block charge based on the load profile."""
        for Q in range(1, 5):
            lp_quarterly = load_profile.loc[
                load_profile.index.month.isin(list(range((Q - 1) * 3 + 1, Q * 3 + 1))),
                :,
            ]
            results["load_information"]["kWh_Q" + str(Q)] = [
                np.nansum(lp_quarterly[col].values[lp_quarterly[col].values > 0])
                for col in lp_quarterly.columns
            ]

        for Q in range(1, 5):
            block_use = results["load_information"][["kWh_Q" + str(Q)]].copy()
            block_use_charge = block_use.copy()
            lim = 0
            for k, v in tariff_component["BlockQuarterly"].items():
                block_use[k] = block_use["kWh_Q" + str(Q)]
                block_use[k][block_use[k] > float(v["HighBound"])] = float(
                    v["HighBound"]
                )
                block_use[k] = block_use[k] - lim
                block_use[k][block_use[k] < 0] = 0
                lim = float(v["HighBound"])
                block_use_charge[k] = block_use[k] * v["Value"]
            del block_use["kWh_Q" + str(Q)]
            del block_use_charge["kWh_Q" + str(Q)]
            results[tariff_category]["C_BlockQuarterly_" + str(Q)] = (
                block_use_charge.sum(axis=1)
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
        """Calculates the monthly block charge based on the load profile."""
        for m in range(1, 13):
            lp_monthly = load_profile.loc[load_profile.index.month == m, :]
            results["load_information"]["kWh_m" + str(m)] = [
                np.nansum(lp_monthly[col].values[lp_monthly[col].values > 0])
                for col in lp_monthly.columns
            ]

        for m in range(1, 13):
            block_use = results["load_information"][["kWh_m" + str(m)]].copy()
            block_use_charge = block_use.copy()
            lim = 0
            for k, v in tariff_component["BlockMonthly"].items():
                block_use[k] = block_use["kWh_m" + str(m)]
                block_use[k][block_use[k] > float(v["HighBound"])] = float(
                    v["HighBound"]
                )
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
        """Calculates the daily block charge based on the load profile."""
        daily_kwh_usage = load_profile.resample("D").sum()
        block_use_temp_charge = daily_kwh_usage.copy()
        block_use_temp_charge.iloc[:, :] = 0
        lim = 0
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
        """Calculates the total time of use energy charge."""
        time_of_use_consumption = pd.DataFrame()
        time_of_use_consumption_charge = pd.DataFrame()
        for tou_component, details in tariff_component["TOU"].items():
            details_copy = details.copy()
            if "Weekday" not in details_copy:
                details_copy["Weekday"] = True
                details_copy["Weekend"] = True
            if "TimeIntervals" not in details_copy:
                details_copy["TimeIntervals"] = {"T1": ["00:00", "00:00"]}
            if "Month" not in details_copy:
                details_copy["Month"] = list(range(1, 13))

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
        """Calculate the demand charge based on demand component details."""
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

        average_peaks_all = np.empty(
            (0, load_profile_selected_times.shape[1]), dtype=float
        )

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
            average_peaks_all = np.append(
                average_peaks_all, [2 * arr[:num_peaks, :].mean(axis=0)], axis=0
            )

        if min_demand_from_charge > 0:
            average_peaks_all = np.clip(
                average_peaks_all, a_min=min_demand_from_charge, a_max=None
            )
        else:
            average_peaks_all[average_peaks_all < min_demand] = 0

        average_peaks_all_sum = average_peaks_all.sum(axis=0)
        results[tariff_category]["Avg_kW_Dem_" + demand_component] = (
            average_peaks_all_sum / len(dem_component_details["Month"])
        )
        results[tariff_category]["Demand_" + demand_component] = (
            average_peaks_all_sum * dem_component_details["Value"] * 365 / 12
        )

        dem_charge = average_peaks_all_sum * dem_component_details["Value"] * 365 / 12
        return dem_charge

    def calculate_demand_charge(
        load_profile: pd.DataFrame,
        tariff_component: dict,
        results: dict,
        tariff_category: str,
    ) -> float:
        """Calculate the total demand charge for all Demand tariff components."""
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

    return (
        calculate_annual_block_charge,
        calculate_daily_block_charge,
        calculate_daily_charge,
        calculate_demand_charge,
        calculate_fixed_charge,
        calculate_flatrate_charge,
        calculate_monthly_block_charge,
        calculate_quarterly_block_charge,
        calculate_time_of_use_charge,
    )


@app.cell(hide_code=True)
def _(
    calculate_annual_block_charge,
    calculate_daily_block_charge,
    calculate_daily_charge,
    calculate_demand_charge,
    calculate_fixed_charge,
    calculate_flatrate_charge,
    calculate_monthly_block_charge,
    calculate_quarterly_block_charge,
    calculate_time_of_use_charge,
    np,
    pd,
    time_select,
):
    # ---------------------------------------------------------------------------
    # Main bill calculator function
    # ---------------------------------------------------------------------------
    def bill_calculator(formatted_load_pv_data: pd.DataFrame, tariff: dict) -> dict:
        """Calculate the billing charges for residential or small business tariffs."""
        load_profile = formatted_load_pv_data[["kWh", "PV"]].copy().fillna(0.0)
        load_profile["Net Load"] = load_profile["kWh"] - load_profile["PV"]
        load_profile = load_profile.rename(columns={"kWh": "Load", "Net Load": "kWh"})
        load_profile = pd.DataFrame(load_profile["kWh"])

        results = {}

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

        results["load_information"] = pd.DataFrame(
            index=[col for col in load_profile.columns],
            data=np.sum(lp_net_import.values, axis=0),
            columns=["Annual_kWh"],
        )
        results["load_information"]["Annual_kWh_exp"] = -1 * np.sum(
            lp_net_export.values, axis=0
        )

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
            "BlockQuarterly": (
                calculate_quarterly_block_charge,
                "Charge_BlockQuarterly",
            ),
            "BlockMonthly": (calculate_monthly_block_charge, "Charge_BlockMonthly"),
            "BlockDaily": (calculate_daily_block_charge, "Charge_BlockDaily"),
            "TOU": (calculate_time_of_use_charge, "Charge_TOU"),
            "Demand": (calculate_demand_charge, "Charge_Demand"),
        }

        for component_type, component_details in tariff["Parameters"].items():
            results[component_type] = pd.DataFrame(
                index=results["load_information"].index
            )
            results[component_type]["Charge_FiT_Rebate"] = 0

            if "BlockDailyFiT" in component_details.keys():
                daily_export = lp_net_export.resample("D").sum()
                daily_export["kWh"] = -1 * daily_export["kWh"]
                block_fit_credit_total = 0
                prev_highbound = 0
                for block_name, block_details in component_details[
                    "BlockDailyFiT"
                ].items():
                    kwh_in_block = (
                        (daily_export["kWh"] - prev_highbound)
                        .clip(lower=0.0, upper=float(block_details["HighBound"]))
                        .sum()
                    )
                    credit_from_block = kwh_in_block * block_details["Value"]
                    block_fit_credit_total += credit_from_block
                    prev_highbound = float(block_details["HighBound"])
                results[component_type]["Charge_FiT_Rebate"] = (
                    -1 * block_fit_credit_total
                )
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
                    results[component_type]["kWh_Exp" + k] = load_profile_ti_exp[
                        k
                    ].copy()
                    load_profile_ti_exp_charge[k] = (
                        this_part["Value"] * load_profile_ti_exp[k]
                    )
                    results[component_type]["FiT_C_TOU" + k] = (
                        load_profile_ti_exp_charge[k].copy()
                    )
                results[component_type]["Charge_FiT_Rebate"] = (
                    load_profile_ti_exp_charge.sum(axis=1)
                )
            elif "FiT" in component_details.keys():
                results[component_type]["Charge_FiT_Rebate"] = (
                    -1
                    * results["load_information"]["Annual_kWh_exp"]
                    * component_details["FiT"]["Value"]
                )

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

    return (bill_calculator,)


@app.cell(hide_code=True)
def _(pd):
    # ---------------------------------------------------------------------------
    # Battery simulation function
    # ---------------------------------------------------------------------------
    def run_battery_self_consumption(
        load_pv_profile: pd.DataFrame,
        battery_kw: float,
        battery_kwh: float,
        battery_eff: float = 0.90,
        interval_per_hour: int = 2,
    ) -> pd.DataFrame:
        """Simulate a simple battery algorithm to maximise self-consumption of PV energy."""
        if battery_kwh <= 0 or battery_kw <= 0:
            result = load_pv_profile.copy()
            result["SOC"] = 0.0
            result["net_load"] = result["kWh"] - result["PV"]
            return result

        profiles = load_pv_profile.copy() * interval_per_hour
        profiles = profiles.reset_index().rename(
            columns={"kWh": "demand", "PV": "generation"}
        )

        profiles["SOC"] = 0.0
        profiles["excess_generation"] = (
            profiles["generation"] - profiles["demand"]
        ).clip(lower=0, upper=battery_kw)
        profiles["excess_demand"] = (profiles["demand"] - profiles["generation"]).clip(
            lower=0, upper=battery_kw
        )

        one_way_eff = battery_eff**0.5

        for i in range(1, len(profiles)):
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

        profiles["energy_change"] = profiles["energy_change"].apply(
            lambda x: x * one_way_eff if x < 0 else x / one_way_eff
        )

        profiles["charging"] = (
            profiles["energy_change"].clip(lower=0) * interval_per_hour
        )
        profiles["discharging"] = (
            profiles["energy_change"].clip(upper=0) * interval_per_hour
        )

        profiles["net_demand"] = (
            profiles["demand"]
            - profiles["generation"]
            + profiles["energy_change"] * interval_per_hour
        )
        profiles["demand_with_battery"] = profiles["demand"] + profiles["discharging"]
        profiles["generation_with_battery"] = (
            profiles["generation"] - profiles["charging"]
        )

        index_col = profiles.columns[0]

        result = profiles[
            [
                index_col,
                "net_demand",
                "demand_with_battery",
                "generation_with_battery",
                "SOC",
            ]
        ].set_index(index_col)

        result["SOC"] = result["SOC"] / battery_kwh * 100

        result = result.rename(
            columns={
                "net_demand": "net_load",
                "demand_with_battery": "kWh",
                "generation_with_battery": "PV",
            }
        )

        result["kWh"] = result["kWh"] / interval_per_hour
        result["PV"] = result["PV"] / interval_per_hour
        result["net_load"] = result["net_load"] / interval_per_hour

        return result

    return (run_battery_self_consumption,)


@app.cell(hide_code=True)
def _():
    # ---------------------------------------------------------------------------
    # Tariff data URL (GitHub raw URL for WASM compatibility)
    # ---------------------------------------------------------------------------
    SAMPLE_TARIFFS_URL = "https://raw.githubusercontent.com/EllieKallmier/bill_calculator/main/sample_tariffs/sample_ausgrid_tariffs.json"
    return (SAMPLE_TARIFFS_URL,)


@app.cell(hide_code=True)
def _(SAMPLE_TARIFFS_URL):
    import json
    import urllib.request

    def fetch_all_tariffs() -> tuple[list[dict], dict]:
        """Load all available tariffs from the GitHub URL."""
        with urllib.request.urlopen(SAMPLE_TARIFFS_URL) as response:
            all_tariffs = json.loads(response.read().decode("utf-8"))

        filter_options = {
            "types": sorted(
                set(t["Type"] for t in all_tariffs if "Feed" not in t.get("Type", ""))
            ),
            "distributors": sorted(
                set(t.get("Distributor", "Unknown") for t in all_tariffs)
            ),
            "states": sorted(
                set(t.get("State", "Unknown") for t in all_tariffs if t.get("State"))
            ),
            "customer_types": sorted(
                set(t.get("CustomerType", "Unknown") for t in all_tariffs)
            ),
        }

        return all_tariffs, filter_options

    def filter_tariffs(
        all_tariffs: list[dict],
        distributor: str | None = None,
        state: str | None = None,
        tariff_type: str | None = None,
        customer_type: str | None = None,
    ) -> list[dict]:
        """Filter tariffs based on specified criteria."""
        selected_tariffs = []

        for tariff in all_tariffs:
            if "Feed" in tariff.get("Type", ""):
                continue
            if distributor and tariff.get("Distributor") != distributor:
                continue
            if state and tariff.get("State") != state:
                continue
            if tariff_type and tariff.get("Type") != tariff_type:
                continue
            if customer_type and tariff.get("CustomerType") != customer_type:
                continue

            selected_tariffs.append(tariff)

        return selected_tariffs

    return fetch_all_tariffs, filter_tariffs


if __name__ == "__main__":
    app.run()
