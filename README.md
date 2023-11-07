# qpe_sys
成都远望QPE工程化脚本

第三方库安装
pip3 install numba, numpy, pandas, xarray
pip3 install pyzstd
代码运行流程
终端输入python3进入python编译器
第三方库导入
import glob
import json
import core.qpe as qpe
from datetime import datetime
from qpe_netcdf import qpe_single_tonetcdf
算法输入
rad_fps = sorted(glob.glob('/Volumes/Extreme/qpe_sys/test_data/HSR/*.zst')) # 查询雷达文件
stn_fp = '/Volumes/Extreme/qpe_sys/test_data/stn/20231025_065300.csv' # 查询自动站文件
cfg = json.load(open('/Volumes/Extreme/qpe_sys/qpe_sys/cfg.json')) # 查询配置文件
算法中间计算
ds = qpe(rad_fps, stn_fp, cfg) # 定量降水估测
算法输出
refdt = os.path.split(rad_fps[-1])[1].split('.')[0]
out_name = f"{cfg['stationId']}_{refdt}.00.{cfg['proId']}.000_0.01.nc"
qpe_single_tonetcdf(ds, datetime.strptime(refdt, "%Y%m%d_%H%M%S"), out_name)
