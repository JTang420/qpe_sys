import netCDF4


def qpe_single_tonetcdf(ds, time, out_name):
    """
    """
    qpe_out = netCDF4.Dataset(out_name, mode='w')
    qpe_out.description = 'Quantitative precipitation estimation'
    qpe_out.center_lon = ds.center_lon
    qpe_out.center_lat = ds.center_lat
    qpe_out.center_alt = ds.center_alt
    qpe_out.lon_min = ds.lon_min
    qpe_out.lon_max = ds.lon_max
    qpe_out.lat_min = ds.lat_min
    qpe_out.lat_max = ds.lat_max
    qpe_out.stn_id = ds.stn_id
    # qpe_out.rmse = ds.rmse

    qpe_rawgrp = qpe_out.createGroup("QPE")
    ntimes = qpe_rawgrp.createDimension("time", 1)
    nlons = qpe_rawgrp.createDimension("longitude", ds.qpe.lon.size)
    nlats = qpe_rawgrp.createDimension("latitude", ds.qpe.lat.size)

    times = qpe_rawgrp.createVariable("time", "f8", ("time",))
    lons = qpe_rawgrp.createVariable("longitude", "f4", ("longitude",))
    lats = qpe_rawgrp.createVariable("latitude", "f4", ("latitude",))
    data = qpe_rawgrp.createVariable("data", "f4", ("latitude", "longitude"))

    times[:] = netCDF4.date2num(time, units="minutes since 1970-01-01 00:00:00")
    lons[:] = ds.lon.data
    lats[:] = ds.lat.data
    data[:] = ds.qpe.data
    lons.units = "degrees east"
    lats.units = "degrees north"
    data.units = "mm/h"

    if 'qpe_oi' in ds:
        qpe_oigrp = qpe_out.createGroup("QPE_OI")
        ntimes = qpe_oigrp.createDimension("time", 1)
        nlons = qpe_oigrp.createDimension("longitude", ds.qpe_oi.lon.size)
        nlats = qpe_oigrp.createDimension("latitude", ds.qpe_oi.lat.size)

        times = qpe_oigrp.createVariable("time", "f8", ("time",))
        lons = qpe_oigrp.createVariable("longitude", "f4", ("longitude",))
        lats = qpe_oigrp.createVariable("latitude", "f4", ("latitude",))
        data = qpe_oigrp.createVariable("data", "f4", ("latitude", "longitude"))

        times[:] = netCDF4.date2num(time, units="minutes since 1970-01-01 00:00:00")
        lons[:] = ds.lon.data
        lats[:] = ds.lat.data
        data[:] = ds.qpe_oi.data
        lons.units = "degrees east"
        lats.units = "degrees north"
        data.units = "mm/h"
    qpe_out.close()

