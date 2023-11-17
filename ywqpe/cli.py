import os
import sys
sys.path.append(os.path.normpath('/cdyw/app/lib/python'))
##AppendLibPath
import json
import click
import glob
import cachepy
import numpy as np
import pandas as pd
from ywqpe import core
from datetime import datetime
from nrsproto.nrsbase_pb2 import *
from google.protobuf.json_format import MessageToJson


def sendReq(query, req:NrsReq):
    data = req.SerializeToString()
    bRet, respT = query.pbReq(data)
    if bRet == False:
        print('error:', respT.decode())
        return None
    else:
        resp = NrsResp()
        resp.ParseFromString(respT)
        return resp

 
def stn_proc(message):
    times = [datetime.fromtimestamp(item.dataTime) for item in message]
    stnids = [item.stationId for item in message]
    lons = [item.lon for item in message]
    lats = [item.lat for item in message]
    rains = [item.rain for item in message]
    return pd.DataFrame({'Datetime': times, 'Station_Id_c': stnids, 'Lon': lons, 
                        'Lat': lats, 'rain': rains})


def single_query(query, queryRes, local_root):
    data = query.getRadarProduct(queryRes.handle, 0)
    name = os.path.split(data.name)[1].split('.')[0]
    bin_file = open(f'{local_root}/{name}.bin', mode='wb')
    bin_file.write(data.data)
    bin_file.close()


@click.group()
def cli():
    pass


@cli.command()
@click.argument('cfg')
def qpe(cfg):
    """: generate QPE product"""

    # 获取APPName
    appName = os.path.basename(__file__).split(".")[0]
    query = cachepy.CachePy("hh")
    query.createClient(appName, "nrsDataCache")
    query.echo()

    params_dict = json.load(open(cfg))

    # 查询雷达数据（站号，站号数，XX, 时间戳起始时间，时间戳截止时间，时间个数）
    queryRes = query.queryRadarProduct(
        params_dict['stationId'], 
        params_dict['nStation'], 
        params_dict['dependentId'], 
        params_dict['time'] - 360, 
        params_dict['time'], 1, ttl=100)
    # 将雷达数据暂时存储为二进制文件
    local_dir = params_dict['params']['local_dir']
    local_root = os.path.join(query.getLocalStorePath(), 
                           f'/cdyw/temp/cdyw/localstroe/ywqpe/{local_dir}')
    if queryRes.dataCnt > 0:
        single_query(query, queryRes, local_root)
        # 第一次单个文件请求需要请求多次
        if len(os.listdir(local_root)) < 10:
            for i in range(1, 10):
                new_queryRes = query.queryRadarProduct(params_dict['stationId'], 
                                                       params_dict['nStation'], 
                                                       params_dict['dependentId'],
                                                       (params_dict['time'] - i * 360) - 360, 
                                                       params_dict['time'] - i * 360, 1, ttl=100)
                single_query(query, new_queryRes, local_root)
    
    # 判断文件时间连续性(剔除超过1h的数据文件)
    rad_files = np.array(sorted(glob.glob(f'{local_root}/*.bin'))) 
    fp_time_delta = [(datetime.strptime(rad_file.split('/')[-1][:-4], "%Y%m%d_%H%M%S")\
                    - datetime.strptime(rad_files[-1].split('/')[-1][:-4], 
                    "%Y%m%d_%H%M%S")).total_seconds() / 60 for rad_file in rad_files]
    for f in rad_files[np.abs(fp_time_delta) >= 60]:
        os.remove(f)
    rad_files = sorted(glob.glob(f'{local_root}/*.bin'))
    
    # 查询自动站数据
    req = NrsReq()
    req.cmd = CmdType.GetAutoStation
    req.autoStation.startTime = params_dict['time'] - 3600 # 查询起始时间
    req.autoStation.endTime = params_dict['time'] # 查询截止时间

    cond = req.autoStation.conds.add()
    cond.dataName = "value"  # 根据获取的降水值来进行条件筛选
    cond.min, cond.max = 0.5, 200.  # 剔除该区间范围之外（区间两端取闭区间）的降水
    resp = sendReq(query, req)
    # print('-- GetAutoStation: ', len(resp.autoStation.data))
    stn = stn_proc(resp.autoStation.data)
    # 判断文件个数是否达到计算要求
    if (len(stn) > 30) and (len(rad_files) > 7):
        refdt = os.path.split(rad_files[-1])[1].split('.')[0]
        print(f'processing the {refdt}')
        # 定量降水估测
        ds_qpe = core.qpe(rad_files, stn, params_dict['params'])

    # 数据存储
        out_name = f"{refdt}.00.{params_dict['params']['proId']}.000_0.0100.nc"
        output = os.path.join(local_root, out_name)
        ds_qpe.to_netcdf(output)

        buf = open(output, 'rb').read()
        # 输出命名规则：是否为临时产品，站点名称，数据名称，英文名字，产品ID, 数据
        qpe_out_query = query.saveRadarProduct(False,
                                               params_dict['stationId'],
                                               out_name,
                                               params_dict['params']['ename'],
                                               params_dict['params']['proId'],
                                               memoryview(buf))

        if qpe_out_query[0]:
            print(f"##nrs: 1, {params_dict['stationId']}, {out_name}##")
        else:
            print(f'##nrs: 0, compute failed!##')
        os.remove(output)
    else:
        print(f'not enough files, guage={len(stn)}(>30), radar={rad_files}(>7)')


if __name__ == '__main__':
    qpe()
