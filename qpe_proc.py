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
                        'Lat': lats, 'rain': rains}).sort_values(by=['Datetime'])


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

    # params_dict = json.load(open(cfg))
    params_dict = json.loads(cfg)
    # print(params_dict)
    pars = {'stationId':params_dict['stationId'], 'ename': params_dict['params'][0], 
            'proId': params_dict['params'][1], 'timeReso': params_dict['params'][2], 
            'gridReso': params_dict['params'][3], 'A': params_dict['params'][4],
            'b': params_dict['params'][5], 'stn_num': params_dict['params'][6], 
            'prec_th': params_dict['params'][7], 'dis': params_dict['params'][8], 
            'K_min': params_dict['params'][9], 'K_max': params_dict['params'][10]}
    # print(pars)

    # 查询雷达数据（站号，站号数，XX, 时间戳起始时间，时间戳截止时间，时间个数）
    queryRes = query.queryRadarProduct(
        params_dict['stationId'], 
        params_dict['nStation'], 
        params_dict['dependentId'], 
        params_dict['time'] - 360, 
        params_dict['time'], params_dict['limit'], ttl=params_dict['ttl'])
    # 将雷达数据暂时存储为二进制文件
    local_dir = f"qpe_{pars['timeReso']}min"
    local_root = os.path.join(query.getLocalStorePath(), 
                           f'/cdyw/temp/cdyw/localstroe/ywqpe/{local_dir}')
    # print(local_root)
    if int(pars['timeReso']) == 10:  # 10min请求两个文件
        query_num, file_lit, delta_time = 2, 2, 12
    elif int(pars['timeReso']) == 30:  # 30min请求五个文件
        query_num, file_lit, delta_time = 5, 5, 30
    else:
        query_num, file_lit, delta_time = 10, 7, 60  # 1h请求十个文件
    if queryRes.dataCnt > 0:
        single_query(query, queryRes, local_root)
        # 第一次单个文件请求需要请求多次
        if len(os.listdir(local_root)) < query_num:
            for i in range(1, query_num):
                new_queryRes = query.queryRadarProduct(params_dict['stationId'], 
                                                       params_dict['nStation'], 
                                                       params_dict['dependentId'],
                                                       (params_dict['time'] - i * 360) - 360, 
                                                       params_dict['time'] - i * 360, params_dict['limit'], ttl=params_dict['ttl'])
                single_query(query, new_queryRes, local_root)
    
    # 判断文件时间连续性(剔除超过10min/30min/1h的数据文件)
    rad_files = np.array(sorted(glob.glob(f'{local_root}/*.bin')))
    fp_time_delta = [(datetime.strptime(rad_file.split('/')[-1][:-4], "%Y%m%d_%H%M%S")\
                    - datetime.strptime(rad_files[-1].split('/')[-1][:-4], 
                    "%Y%m%d_%H%M%S")).total_seconds() / 60 for rad_file in rad_files]
    for f in rad_files[np.abs(fp_time_delta) >= delta_time]:
        os.remove(f)
    rad_files = sorted(glob.glob(f'{local_root}/*.bin'))
    # print('rad_files:', rad_files)
    
    # 查询自动站数据
    req = NrsReq()
    req.cmd = CmdType.GetAutoStation
    req.autoStation.startTime = params_dict['time'] - 360 * query_num # 查询起始时间
    req.autoStation.endTime = params_dict['time'] # 查询截止时间

    cond = req.autoStation.conds.add()
    cond.dataName = "value"  # 根据获取的降水值来进行条件筛选
    cond.min, cond.max = 0.5, 200.  # 剔除该区间范围之外（区间两端取闭区间）的降水
    resp = sendReq(query, req)
    # print('-- GetAutoStation: ', len(resp.autoStation.data))
    stn = stn_proc(resp.autoStation.data)
    # print(stn)

    if (len(stn) >= pars['stn_num']):  # 自动站文件个数达到计算要求
        if (len(rad_files) >= file_lit):  # 雷达文件个数达到计算要求
            refdt = os.path.split(rad_files[-1])[1].split('.')[0]
            print(f"processing the {refdt}")
            # 定量降水估测
            ds_qpe = core.qpe(rad_files, stn, pars)
        else:  # 雷达文件个数未达到计算要求
            ds_qpe = None
            print(f"not enough radar files={len(rad_files)}(>{file_lit})")
    else:
        if (len(rad_files) >= file_lit):  # 雷达文件个数达到计算要求
            refdt = os.path.split(rad_files[-1])[1].split('.')[0]
            print(f"processing the {refdt}")
            # 定量降水估测
            ds_qpe = core.qpe(rad_files, stn, pars)
        else:  # 雷达文件个数未达到计算要求ds_qpe = None
            ds_qpe = None
            print(f"not enough files, radar files={len(rad_files)}(>{file_lit}), guages={len(stn)}(>{pars['stn_num']})")

    # 数据存储
    if ds_qpe is not None:
        # print(ds_qpe)
        out_name = f"{refdt}.00.{pars['proId']}_M{pars['timeReso']}.0-{pars['gridReso']}00-{pars['A']}.00-{pars['b']}0.000_0.0100.nc"
        output = os.path.join(local_root, out_name)
        ds_qpe.to_netcdf(output)

        buf = open(output, 'rb').read()
        # 输出命名规则：是否为临时产品，站点名称，数据名称，英文名字，产品ID, 数据
        qpe_out_query = query.saveRadarProduct(False,
                                            params_dict['stationId'],
                                            out_name,
                                            pars['ename'],
                                            pars['proId'],
                                            memoryview(buf))

        if qpe_out_query[0]:
            print(f"##nrs: 1, {params_dict['stationId']}, {out_name}##")
        else:
            print(f'##nrs: 0, compute failed!##')
        os.remove(output)


if __name__ == '__main__':
    qpe()
