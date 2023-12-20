import os
import struct
import numpy as np
import xarray as xr
from pyzstd import ZstdFile
from datetime import datetime


def hsr_decode(fp):
    if fp.endswith('.zst'):
        f = ZstdFile(fp)
    else:
        f = open(fp, 'rb')

    # 文件头
    _ = f.read(142) # 地址参数
    lon, lat, alt = struct.unpack('3i', f.read(12))
    lon, lat, alt = lon / 3.6 / 1e5, lat / 3.6 / 1e5, alt / 1e3
    _ = f.read(6)
    
    perf_bits = f.read(40) # 性能参数

    ## 观测参数
    _ = f.read(446)
    rng_num = struct.unpack('30H', f.read(60))[0] # 各层的反射率距离库数
    azi_num = struct.unpack('30H', f.read(60))[0] # 各层采样的径向数
    _ = f.read(60)
    rng_len = struct.unpack('30H', f.read(60))[0] # 各层反射率库长
    rng_fr = struct.unpack('30H', f.read(60))[0] # 各层径向上的第一个距离库的开始距离
    _ = f.read(320)

    # 产品数据
    refdt = os.path.split(fp)[1].split('.')[0]
    dbz = np.zeros((azi_num, rng_num), dtype='u1')
    azimuth = np.array(np.arange(0, 360, 360 / azi_num), dtype='f8')
    elevation = np.array(np.ones_like(azimuth) * 0.5, dtype='f8')
    rng = np.array(np.arange(rng_len, rng_num * rng_len + 1, rng_len), dtype='f8')
    time = np.array(np.arange(0, azi_num), dtype=np.float64)

    for iazi in range(0, azi_num):
        time[iazi] = iazi
        _ = f.read(64) # 读取当前径向的径向头数据
        data_buf = struct.unpack(str(rng_num)+'B', f.read(rng_num))  # 读取当前径向的径向数据
        for irng in range(0, rng_num):
            dbz[iazi, irng] = data_buf[irng]

    hybrid_dbz = xr.DataArray(dbz / 2 - 33, dims=('time', 'range'), name='dBZ',
                     coords=[('time', time), ('range', rng)])
    t = datetime.strptime(os.path.split(fp)[1].split('_')[4], "%Y%m%d%H%M%S")
    hybrid_dbz = hybrid_dbz.expand_dims(valid_time=[t], axis=0)
    hybrid_dbz.coords['azimuth'] = (('time'), azimuth)
    hybrid_dbz.coords['elevation'] = (('time'), elevation)
    hybrid_dbz.attrs['rad_lon'] = lon
    hybrid_dbz.attrs['rad_lat'] = lat
    hybrid_dbz.attrs['rad_alt'] = alt
    return hybrid_dbz
