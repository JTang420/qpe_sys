import numpy as np
import pandas as pd
import xarray as xr
from ywqpe import calib
from ywqpe.io import hsr_decode
from ywqpe.remap import to_enu, xy2ll


def _to_rain(dbz, A, b):
    """convert dBZ to rainrate

    Parameters
    ----------
    dbz : 2D xr.DataArray

    A : int

    b : float

    Returns
    -------
    2D xr.DataArray
        6min qpe form radar
    """
    Z = np.power(10., dbz/10.)
    R = np.power(Z / A, 1. / b)
    R = np.where(~np.isnan(R), R, 0.)
    return R


def _stn_proc(df):
    """

    Parameters
    ----------
    df : pd.DataFrame
        minutes observations of gauges

    Returns
    -------
    pd.DataFrame
        accumulated rain of the past hour (columns=['PRE', 'Lon', 'Station_Id_C', 'Lat', 'Datetime'])
    """

    stnids, times, pre_1h, lons, lats = [], [], [], [], []
    for b, g in df.groupby('Station_Id_c'):  # 按照自动站分组进行小时降水累加
        stnids.append(b)
        times.append(g['Datetime'].values[-1])
        pre_1h.append(g['rain'].sum(skipna=True))
        lons.append(g['Lon'].values[0])
        lats.append(g['Lat'].values[0])
    return pd.DataFrame({'Datetime': times, 'Station_Id_c': stnids, 'lon': lons, 
                        'lat': lats, 'rain': pre_1h})


def hybrid_proc(fp, grid_reso=1e3):
    """read hybrid scan radar dBZ

    Parameters
    ----------
    fp : str
        radar file path
    grid_reso : float
        grid resolution in meters

    Returns
    -------
    2D xr.Dataset
        contains variable 'dbz' with coordinates('lat', 'lon')
    """

    hsr_dbz = hsr_decode(fp)
    hsr_dbz = hsr_dbz.where(hsr_dbz.data != -33.) # 缺测值处理
    rng = hsr_dbz[hsr_dbz.dims[-1]]
    grid_reso = grid_reso or (rng[-1] - rng[0])
    max_rng = rng[-1]
    x = np.arange(-max_rng, max_rng + grid_reso / 2, grid_reso)
    xx, yy = np.meshgrid(x, x)
    hsr_enu = to_enu(xx, yy, hsr_dbz.isel(valid_time=0), method='sprint', beam_width=1.)

    lon, lat = xy2ll(xx[0, :] / 1e3, yy[:, 1] / 1e3, hsr_dbz.rad_lon, hsr_dbz.rad_lat)
    hsr_enu = xr.Dataset(data_vars={'dbz': (['y', 'x'], hsr_enu.astype('float32'))}, 
                            coords={'x': ('x', xx[0, :]), 'y': ('y', yy[:, 1])},
                attrs={'center_lon': hsr_dbz.rad_lon, 'center_lat': hsr_dbz.rad_lat, 'center_alt': hsr_dbz.rad_alt})
    hsr_enu = hsr_enu.assign_coords(coords={'longitude': ('x', lon.astype('float32')), 
                                            'latitude': ('y', lat.astype('float32'))})
    hsr_enu = hsr_enu.swap_dims({'x': 'longitude', 'y': 'latitude'})
    hsr_enu = hsr_enu.drop(['y', 'x'], dim=None)
    return hsr_enu


def qpe(radar_fps, df, params):  
    """1h qpe for radar_fps files

    Parameters
    ----------
    radar_fps : list of str
        1h radar files path
    df : pd.DataFrame
        observations of gauges
    params : dict
        config params for qpe

    Returns
    -------
    2D xr.Dataset
        contains variable ('dbz', 'qpe', 'qpe_g', 'qpe_c') with coordinates('lat', 'lon')
    """
    ds = xr.concat([hybrid_proc(fp,
                                grid_reso=(params.get('gridReso') / 0.01) * 1e3,
                                ) for fp in radar_fps], dim='valid_time')

    qpe_1h = _to_rain(ds.dbz.data, A=params.get('A', 300.), b=params.get('b', 1.4))
    ds['qpe'] = (('latitude', 'longitude'), qpe_1h.mean(axis=0))
    ds['qpe'].values = np.where(ds.qpe != 0., ds.qpe.values, np.nan)

    # 自动站数据读取、处理
    if len(df) > 0:  # 获取到自动站观测数据
        # df = pd.read_csv(stn_file, usecols=['PRE', 'Lon', 'Station_Id_C', 'Lat', 'Datetime'], 
        #                     na_values=[999998.0, 999999.0])
        df_1h = _stn_proc(df)
        df_1h = df_1h[df_1h['rain'] >= params.get('prec_th', 0.6)]
        if len(df_1h) > params.get('stn_num', 30):
            global calibrate  # 利用全局平均订正因子进行初步降水订正
            ds['qpe_g'] = calib.global_calibrate(ds.qpe, df_1h,
                                                K_min=params.get('K_min', 0.5),
                                                K_max=params.get('K_max', 2.))

            # local calibrate # 利用分析格点搜索范围内(dis=0.2~20km)的自动站点进行分析格点降水订正
            qpe_oi = calib.oi(ds.qpe_g, df_1h, a=0.2, dis=params.get('dis', 0.2))
            ds['qpe_oi'] = (('latitude', 'longitude'), qpe_oi)
        else:
            print(f"not enough gauge={len(df_1h)}(>{params.get('stn_num', 30)})")
    ds.attrs['longitude_min'] = np.around(ds.longitude.values[0], 3)
    ds.attrs['longitude_max'] = np.around(ds.longitude.values[-1], 3)
    ds.attrs['latitude_min'] = np.around(ds.latitude.values[0], 3)
    ds.attrs['latitude_max'] = np.around(ds.latitude.values[-1], 3)
    ds.attrs['LenofWin'] = np.around(ds.longitude.values[1] - ds.longitude.values[0], 3)
    ds.attrs['radar_id'] = params.get('stationId', 'Z9280')
    if 'qpe_oi' in ds:
        ds_temp = ds[['qpe', 'qpe_oi']]
    else:
        ds_temp = ds['qpe']
    return ds_temp
