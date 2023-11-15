import numpy as np
import xarray as xr
from numba import njit
from numpy.linalg import solve


@njit(fastmath=True)
def rcoef(R, a, choice):
    if choice == 0:
        return np.exp(-R/a)
    elif choice == 1:
        return np.exp(-R**2/a)
    else:
        print('please input the right number:0 or 1')


@njit(fastmath=True)
def select_gauge(Ro, lon0, lat0, dis):
    """select gauge observations

    Parameters
    ----------
    Ro: 2D array
        all gauge observation with columns ('lon', 'lat', 'rain')
    lon0, lat0: float
        coordinates of a reference point
    dis: float
        max distance below which will be selected
    """

    r = np.sqrt((lon0 - Ro[:, 0])**2. + (lat0 - Ro[:, 1])**2.)
    return Ro[r < dis, :]


@njit(fastmath=True)
def distance(x, y):
    """Euclidean square distance matrix

    Parameters
    ----------
    x: (M,K) numpy array
    y: (N,K) numpy array

    Returns
    -------
    (M, N) numpy array
        contains the distance from every vector in x to every vector in y.
    """
    dmatrix = np.zeros((len(x), len(y)))
    for j in range(len(x)):
        for i in range(len(y)):
            dmatrix[j, i] = np.sqrt(((x[j]-y[i])**2.).sum())
    return dmatrix


@njit
def oi_calib(lon, lat, Rb, Ro, a, dis, choice, min_pts=5):
    """optimal interpolation core"""

    Ny, Nx = Rb.shape
    Ra = np.zeros_like(Rb)

    for i in range(Ny):
        lat0 = lat[i]
        for j in range(Nx):
            lon0 = lon[j]
            pt0 = np.array([[lon0, lat0]])
            R_o = select_gauge(Ro, lon0, lat0, dis)
            if len(R_o) > min_pts:
                pts = R_o[:, :2]
                R_kl = distance(pts, pts)
                O_ij = np.eye(R_kl.shape[0]) * 0.01
                u_kl = rcoef(R_kl, a, choice) + O_ij
                R_kj = distance(pts, pt0)
                u_kj = rcoef(R_kj, a, choice)

                w_l = solve(u_kl, u_kj[:, 0])
                Ra[i, j] = Rb[i, j] + np.dot(w_l, R_o[:, 2]-R_o[:, 3])
            else:
                Ra[i, j] = Rb[i, j]
    return Ra


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
            lon=xr.DataArray(df.lon, dims=('index')),
            lat=xr.DataArray(df.lat, dims=('index')))\
        .to_dataframe()[[da.name]]
    df = df.dropna()

    Ro = df[['lon', 'lat', 'rain', 'Rb']].values
    Ra = oi_calib(da.lon.data, da.lat.data, da.data, Ro, a, dis, choice)
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
    R0 = da.interp(lon=xr.DataArray(df.lon, dims=('index')), 
                                    lat=xr.DataArray(df.lat, dims=('index')))
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
            lon=xr.DataArray(df.lon, dims=('index')),
            lat=xr.DataArray(df.lat, dims=('index')))\
        .to_dataframe()
    di['rain'] = df.rain
    di = di.dropna()
    if len(di.index) > 0:
        K = di.rain.values.sum() / di[[da.name]].values.sum()
        K = np.clip(K, K_min, K_max)
    else:
        K = 1.
    print(f'global correction factor: {K:.2f}')
    return xr.DataArray(K * da.data, dims=['lat', 'lon'])
