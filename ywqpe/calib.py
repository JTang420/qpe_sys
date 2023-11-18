import numpy as np
import xarray as xr
from ywqpe.oi_core import oi_calib


def oi(da, df, **kargs):
    """optimal interpolation

    Parameters
    ----------
    da : xr.DataArray
        radar observation and QPE based on climate statistics
    df : pd.DataFrame
        gauge observation
    kargs : dict
        keyword argument for calibration methods

    Returns
    -------
    2D numpy array
        QPE after calibration
    """

    a = kargs.get('a', 0.2)
    dis = kargs.get('dis', 0.1)
    choice = kargs.get('choice', 0)
    df['Rb'] = da.interp(
            longitude=xr.DataArray(df.lon, dims=('index')),
            latitude=xr.DataArray(df.lat, dims=('index')))\
        .to_dataframe()[[da.name]]
    df = df.dropna()

    Ro = df[['lon', 'lat', 'rain', 'Rb']].values
    Ra = oi_calib(da.longitude.data, da.latitude.data, da.data, Ro, a, dis, choice)
    return Ra


def correct_factor(da, df):
    """correction factor

    Parameters
    ----------
    da : xr.DataArray
        2D DataArray representing a QPE result
    df : pd.DataFrame
        gauge observation with 'lon', 'lat', and 'rain' as fields

    Returns
    -------
    pd.DataFrame

    """
    R0 = da.interp(longitude=xr.DataArray(df.lon, dims=('index')), 
                   latitude=xr.DataArray(df.lat, dims=('index')))
    df['gi'] = df['rain'] / R0
    df = df.dropna()
    return df


def global_calibrate(da, df, K_min, K_max):
    """global calibrate

    Parameters
    ----------
    da : xr.DataArray
        2D DataArray representing a QPE result
    df : pd.DataFrame
        gauge observation with 'lon', 'lat', and 'rain' as fields

    Returns
    -------
    xr.DataArray
        new DataArray representing a calibrated QPE result
    """
    di = da.interp(
            longitude=xr.DataArray(df.lon, dims=('index')),
            latitude=xr.DataArray(df.lat, dims=('index')))\
        .to_dataframe()
    di['rain'] = df.rain
    di = di.dropna()
    if len(di.index) > 0:
        K = di.rain.values.sum() / di[[da.name]].values.sum()
        K = np.clip(K, K_min, K_max)
    else:
        K = 1.
    print(f'global correction factor: {K:.2f}')
    return xr.DataArray(K * da.data, dims=['latitude', 'longitude'])
