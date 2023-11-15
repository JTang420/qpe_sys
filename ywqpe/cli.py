import click


@click.group()
def cli():
    pass


@cli.command()
@click.argument('cfg')
@click.option('--rad_root', '-rot', default='')
@click.option('--stn_root', '-sot', default='')
def qpe(cfg, rad_root, stn_root):
    """: generate QPE product"""

    print('generating QPE ...')
