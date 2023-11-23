""" Function to get NWP data and create fake PV dataset"""
import json
import ssl
from datetime import datetime

import numpy as np
import pandas as pd
import requests
import xarray as xr

from quartz_solar_forecast.pydantic_models import PVSite

ssl._create_default_https_context = ssl._create_unverified_context


def get_gfs_nwp(site: PVSite, ts:datetime) -> xr.Dataset:
    """
    Get GFS NWP data for a point time space and time

    :param site: the PV site
    :param ts: the timestamp for when you want the forecast for
    :return: nwp forecast in xarray
    """

    variables = [
        "visibility",
        "windspeed_10m",
        "temperature_2m",
        "precipitation",
        "shortwave_radiation",
        "direct_radiation",
        "cloudcover_low",
        "cloudcover_mid",
        "cloudcover_high",
    ]

    start = ts.date()
    end = start + pd.Timedelta(days=7)

    # Getting GFS, from OPEN METEO
    url = (
        f"https://api.open-meteo.com/v1/gfs?"
        f"latitude={site.latitude}&longitude={site.longitude}"
        f"&hourly={','.join(variables)}"
        f"&start_date={start}&end_date={end}"
    )
    r = requests.get(url)
    d = json.loads(r.text)

    # convert data into xarray
    df = pd.DataFrame(d["hourly"])
    df["time"] = pd.to_datetime(df["time"])
    df = df.rename(
        columns={
            "visibility": "vis",
            "windspeed_10m": "si10",
            "temperature_2m": "t",
            "precipitation": "prate",
            "shortwave_radiation": "dswrf",
            "direct_radiation": "dlwrf",
            "cloudcover_low": "lcc",
            "cloudcover_mid": "mcc",
            "cloudcover_high": "hcc",
        }
    )
    df = df.set_index("time")
    data_xr = xr.DataArray(
        data=df.values,
        dims=["step", "variable"],
        coords=dict(
            step=("step", df.index - df.index[0]),
            variable=df.columns,
        ),
    )
    data_xr = data_xr.to_dataset(name="gfs")
    data_xr = data_xr.assign_coords({"x": [site.longitude], "y": [site.latitude], "time": [df.index[0]]})

    return data_xr


def make_pv_data(site: PVSite, ts) -> xr.Dataset:
    """
    Make fake PV data for the site

    Later we could add PV history here

    :param site: the PV site
    :param ts: the timestamp of the site
    :return: The fake PV dataset in xarray form
    """

    # make fake pv data, this is where we could add history of a pv system
    generation_wh = [[np.nan]]
    lon = [site.longitude]
    lat = [site.latitude]
    timestamp = [ts]
    pv_id = [1]

    # would be nice to not use ss_id, should be pv_id
    da = xr.DataArray(
        data=generation_wh,
        dims=["pv_id", "timestamp"],
        coords=dict(
            longitude=(["pv_id"], lon),
            latitude=(["pv_id"], lat),
            timestamp=timestamp,
            pv_id=pv_id,
            kwp=(["pv_id"], [site.capacity_kwp]),
            tilt=(["pv_id"], [0]),
            orientation=(["pv_id"], [0]),
        ),
    )
    da = da.to_dataset(name="generation_wh")

    return da