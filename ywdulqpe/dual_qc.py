import numpy as np
import xarray as xr


def snr_comp(dbz):
    """

    Parameters
    ---------
    dbz : 2d xr.DataArray
        reflectivity
  
    Returns
    -------
    2d xr.DataArray
    """

    snr = dbz - np.nanmin(dbz, axis=0)
    return snr


def noise_corr_zdr(dbz, zdr):
    """

    Parameters
    ----------
    dbz : 2d xr.DataArray
        reflectivity
    zdr : 2d xr.DataArray
        differential reflectivity
   
    Returns
    -------
    2d xr.DataArray
    """
    snr = snr_comp(dbz)
    zdr_tr = np.power(10, 0.1 * zdr)
    zdr_snr = 10 * np.log((snr - 1) / (snr - zdr_tr))
    return zdr_snr


def noise_corr_rhv(dbz, rhv, rhv_th=0.8):
    """

    Parameters
    ----------
    dbz : 2d xr.DataArray
        signal noise ratio
    rhv : 2d xr.DataArray
        cross-correlation coefficient
    rhv_th : float
        threshold for filter clutter
    
    Returns
    -------
    2d xr.DataArray
    """

    rhv_flt = xr.where(rhv >= rhv_th, rhv, np.nan)
    snr = snr_comp(dbz)
    snr_tr = np.power(10, 0.1 * snr)
    rhv_qc = rhv_flt * (1 + 1 / snr_tr)
    return rhv_qc


def da_flag(dbz, lvl0=7, lvl1=5, lvl2=3):
    """
    
    Parameters
    ----------
    dbz : 2d numpy.ndarray
        reflectivity
    lvl0, lvl1, lvl2 : int
        smooth windowsize for different reflectivity

    Returns
    -------
    2d numpy.ndarray
    """

    flag = np.where(np.logical_and(dbz >= 35, dbz <= 45), lvl1, np.nan)
    flag = np.where(dbz > 45, lvl2, flag)
    flag = np.where(dbz < 35, lvl0, flag)
    return flag


def move_avg(data, size):
    """

    Parameters
    ----------
    data : 1d numpy.ndarray

    size : int
        smooth windowsize
    
    Returns
    -------
    1d numpy.ndarray
    """

    weights = np.repeat(1.0, size) / size
    smoothed_data = np.convolve(data, weights, 'valid')
    return smoothed_data


def smooth_flt(dbz, da, lvl0=7, lvl1=5, lvl2=3):
    """

    Parameters
    ----------
    dbz : 2d numpy.ndarray
        reflectivity
    da : 2d numpy.ndarray

    lvl0, lvl1, lvl2 : int
        smooth windowsize for different reflectivity

    Returns
    -------
    2d numpy.ndarray   
    """

    dbz_flag = da_flag(dbz, lvl0=lvl0, lvl1=lvl1, lvl2=lvl2)
    da_mask = np.ma.masked_invalid(da)
    for iazi in range(dbz_flag.shape[0]):
        for irng in range(3, dbz_flag.shape[1] - 3):
            if ~np.isnan(dbz_flag[iazi, irng]):
                size = dbz_flag[iazi, irng]
                temp = da_mask[iazi, irng - int(size / 2): irng + int(size / 2) + 1]
                da[iazi, irng] = move_avg(temp, size)
    return da
