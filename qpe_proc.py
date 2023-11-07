import os
import json
import click
from core import qpe
from datetime import datetime


@cli.command()
@click.argument('cfg')
@click.option('--rad_root', '-rot', default='')
@click.option('--stn_root', '-sot', default='')
def qpe_proc(cfg, rad_root, stn_root):
    """: generate qpe"""
    appName = os.path.basename(__file__).split(".")[0]
    query  = cachepy.CachePy("hh")
    query.createClient(appName, "nrsDataCache")
    query.echo()
    params_dict = json.loads(cfg)
   
    # 查询雷达混合扫描反射率数据(1h数据)
    # rad_files = query.queryRadarProduct(params_dict['stationId'], params_dict['nStation'], 
    #     params_dict['dependentId'], params_dict['time'] - 3600, params_dict['time'], 10, ttl=100)
    # print(queryRes.dataCnt)
    
    rad_files = f'{rad_root}/{cfg['stationId']}/{refdt[:8]/{refdt[:8]_refdt[8:].00.cfg['productId'].000_0.01.zst}}'
    # 查询自动站数据
    refdt = os.path.split(rad_files[-1])[1].split('.')[0]
    stn_file = f'{stn_root}/tran/{refdt[:-2]}00.csv'
    # 判断文件个数是否达到计算要求
    if os.path.exists(stn_file) and (len(rad_files) > 7):
        print(f'processing the {refdt[:-1]}')
        # 定量降水估测
        ds_qpe = qpe(rad_files, stn_file, cfg)
        # 数据存储
        out_name = f"{params_dict['stationId']}_{refdt}.00.{params_dict['proId']}.000_0.01.nc"
        qpe_single_netcdf(ds_qpe, datetime.strptime(refdt, "%Y%m%d_%H%M%S"), out_name)
    else:
        print(f'not enough files, radar={rad_files}(>7)')
