import numpy as np
from numba import jit_module


def _check_azi_diff(daz):
    if daz > 180.:
        return 360. - daz
    elif daz < -180.:
        return 360 + daz
    else:
        return np.abs(daz)


def _bilinear(vm, vp, dm, dp):
    return (vm * dp + vp * dm) / (dm + dp)


def cressman2d(xp, yp, vp, xg, yg, x_r=0.01, y_r=0.01):
    """distance inversed weight interpolation

    Parameters
    ----------
    xp, yp : 1D array
        the coordinates of scatter points
    vp : 1D array
        the value of scatter points
    xg, yg : 1D array
        the coodinates of regular grid
    x_r, y_r : float
        interpolation radius (degrees)

    Returns
    -------
    2D array
        the interpolated value on the regular grids
    """
    dx = np.median(np.diff(xg))
    dy = np.median(np.diff(yg))
    R2 = x_r ** 2. + y_r ** 2.
    vg = np.zeros((len(yg), len(xg)), dtype=vp.dtype)
    wt = np.zeros_like(vg)

    for i in range(len(vp)):
        if xp[i] < (xg[0] - x_r) or xp[i] > (xg[-1] + x_r):
            continue
        if yp[i] < (yg[0] - y_r) or yp[i] > (yg[-1] + y_r):
            continue

        im = int(np.floor((xp[i] - x_r - xg[0]) / dx))
        ip = int(np.ceil((xp[i] + x_r - xg[0]) / dx))
        jm = int(np.floor((yp[i] - y_r - yg[0]) / dy))
        jp = int(np.ceil((yp[i] + y_r - yg[0]) / dy))


        for jj in range(jm, jp+1):
            for ii in range(im, ip+1):
                if ii < 0 or ii > len(xg) - 1 or jj < 0 or jj > len(yg) - 1:
                    continue
                x_dis = xp[i] - xg[ii]
                y_dis = yp[i] - yg[jj]
                if np.abs(x_dis) <= x_r and np.abs(y_dis) <= y_r:
                    rSquare = (x_dis ** 2 + y_dis ** 2) / R2
                    if rSquare < 1:
                        tmp = (1 - rSquare) / (1 + rSquare)
                        wt[jj, ii] = wt[jj, ii] + tmp
                        vg[jj, ii] = vg[jj, ii] + tmp * vp[i]
    for jj in range(len(yg)):
        for ii in range(len(xg)):
            if(wt[jj, ii] > 0.):
                vg[jj, ii] = vg[jj, ii] / wt[jj, ii]
            else:
                vg[jj, ii] = np.nan
    return vg


def sprint(vin, az, rg, xx, yy, beam_width=1.):
    """bilinear interpolation of 2D PPI scan

    Parameters
    ----------
    vin : 2D array-like
        radar data in polar coordinate
    az :
        azimuth angle
    rg :
        distance (meter) from radar
    xx, yy :
        Cartesian coordinate values
    beam_width : float
        radar beam width

    Returns
    -------
    2D array
        input array in cartesian coordinate
    """

    cv = np.full(xx.shape, np.nan, dtype=vin.dtype)
    rreso = np.median(np.diff(rg))
    nrg = len(rg)
    naz = len(az)
    maxrng = rg[-1]
    for j in range(0, xx.shape[0]):
        for i in range(0, xx.shape[1]):
            rr = np.sqrt(xx[j, i]**2 + yy[j, i]**2)
            if rr < maxrng:
                angle = np.arctan2(yy[j, i], xx[j, i])
                angle = (90. - np.rad2deg(angle)) % 360.
                az_flag = np.searchsorted(az, angle)
                iaz_m = (az_flag - 1) % naz
                iaz_p = az_flag % naz
                daz = _check_azi_diff(az[iaz_p] - az[iaz_m])
                if daz <= (2. * beam_width):
                    irg1 = int((rr - rg[0]) / rreso)
                    irg2 = irg1 + 1
                    if irg2 <= (nrg - 1) and irg1 >= 0:
                        drg_m = rr - rg[irg1]
                        drg_p = rg[irg2] - rr
                        daz_m = _check_azi_diff(angle - az[iaz_m])
                        daz_p = _check_azi_diff(az[iaz_p] - angle)
                        cv[j, i] = _bilinear(
                            _bilinear(vin[iaz_m, irg1], vin[iaz_p, irg1],
                                      daz_m, daz_p),
                            _bilinear(vin[iaz_m, irg2], vin[iaz_p, irg2],
                                      daz_m, daz_p),
                            drg_m, drg_p)
    return cv


jit_module(nopython=True, cache=True, error_model='numpy')


def to_enu(xx, yy, *args, method='nearest', **kargs):
    """interpolate a radar PPI to ENU cartesian coordinate

    Parameters
    ----------
    xx, yy : 2D array
        cartesian coordinates (meters) of output to interpolate
    args : variable argument
        a PPI scan represented by a DataArray contains or four arrays
        (vin, az, el, rg). az, rg are 1D, and el can be 1D array or float. rg
        should in kilometers
    method : str
        interpolation method: 'nearest', 'sprint', 'reorder'
    beam_width: float
        beam_width of radar

    Returns
    -------
    2D array
        vin in the cartesian coordinate with the same shape as xx (yy)

    Notes
    -----
    this function assumes the PPI is in full-circle, which means 'az' spans
    0~360 with no gap.
    """

    if len(args) == 1:
        arr = args[0].values
        az = args[0].azimuth.values
        el = args[0].elevation.values.mean()
        rg = args[0][args[0].dims[-1]].values
    elif len(args) == 4:
        arr = np.asarray(args[0])
        az = np.asarray(args[1])
        el = np.asarray(args[2]).mean()
        rg = np.asarray(args[3])
    else:
        raise ValueError('args should be a single DataArray or four arrays')

    sortidx = np.argsort(az)
    az = az[sortidx]
    arr = arr[sortidx, :]
    cos_el = np.cos(np.deg2rad(el))

    beam_width = kargs.pop('beam_width', 1.)
    if method == 'nearest':
        return interp.nearest_op_numba(arr, az, rg * cos_el, xx, yy, beam_width)
    elif method == 'sprint':
        return sprint(arr, az, rg * cos_el, xx, yy, beam_width)
    elif method == 'reorder':
        rad_azi = np.deg2rad(az)
        xp = np.sin(rad_azi[:, np.newaxis]) * rg[np.newaxis, :] * cos_el
        yp = np.cos(rad_azi[:, np.newaxis]) * rg[np.newaxis, :] * cos_el
        flag = np.logical_not(np.isnan(arr))
        xg = xx[0, :]
        yg = np.array(yy[:, 0])
        vg = cressman2d(xp[flag], yp[flag], arr[flag],
                                 xg, yg, **kargs)
        return vg
    else:
        raise ValueError(f'interp method "{method}" not implemented')


def xy2ll(dx, dy, lon0, lat0):
    """compute the cartesian coordinate (lon, lat) of a point (dx, dy) relative
    to another point (lon0, lat0)

    Parameters
    ----------
    dx, dy : float or array-like
        the distance (in kilometers) from the reference point in the x and y 
        direction
    lon0, lat0: float or array-like
        the lon, lat of the reference point

    Returns
    -------
    lon, lat : float or array-like
        longitude and latitude of the target point
    """

    LatRadians = np.deg2rad(lat0)
    fac_lat = 111.13209 - 0.56605 * np.cos(2.0 * LatRadians) + \
        0.00012 * np.cos(4.0 * LatRadians) - \
        0.000002 * np.cos(6.0 * LatRadians)
    fac_lon = 111.41513 * np.cos(LatRadians) - \
        0.09455 * np.cos(3.0 * LatRadians) + \
        0.00012 * np.cos(5.0 * LatRadians)
    return dx / fac_lon + lon0, dy / fac_lat + lat0
