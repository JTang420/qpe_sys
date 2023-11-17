import numpy as np
from numpy.linalg import solve


def rcoef(R, a, choice):
    if choice == 0:
        return np.exp(-R/a)
    elif choice == 1:
        return np.exp(-R**2/a)
    else:
        print('please input the right number:0 or 1')


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