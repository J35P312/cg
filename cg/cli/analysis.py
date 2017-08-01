# -*- coding: utf-8 -*-
import click

from cg.apps import hk, tb, scoutapi
from cg.meta.analysis import AnalysisAPI
from cg.store import Store

priority_option = click.option('-p', '--priority', type=click.Choice(['low', 'normal', 'high']))
email_option = click.option('-e', '--email', help='email to send errors to')


@click.group(invoke_without_command=True)
@priority_option
@email_option
@click.option('-f', '--family', 'family_id', help='link samples within a family')
@click.pass_context
def analysis(context, priority, email, family_id):
    """Start an analysis (MIP) for a family."""
    context.obj['db'] = Store(context.obj['database'])
    hk_api = hk.HousekeeperAPI(context.obj)
    scout_api = scoutapi.ScoutAPI(context.obj)
    context.obj['tb'] = tb.TrailblazerAPI(context.obj)
    context.obj['api'] = AnalysisAPI(context.obj['db'], hk_api, scout_api, context.obj['tb'])

    if context.invoked_subcommand is None:
        if family_id is None:
            click.echo(click.style('you need to provide a family', fg='red'))
            context.abort()

        # execute the analysis!
        context.invoke(config, family_id=family_id)
        context.invoke(link, family_id=family_id)
        context.invoke(panel, family_id=family_id)
        context.invoke(start, family_id=family_id, priority=priority, email=email)


@analysis.command()
@click.option('-d', '--dry', is_flag=True, help='print config to console')
@click.argument('family_id')
@click.pass_context
def config(context, dry, family_id):
    """Generate a config for the family."""
    family_obj = context.obj['db'].family(family_id)
    config_data = context.obj['api'].config(family_obj)
    if dry:
        click.echo(config_data)
    else:
        out_path = context.obj['tb'].save_config(config_data)
        click.echo(click.style(f"saved config to: {out_path}", fg='green'))


@analysis.command()
@click.option('-f', '--family', 'family_id', help='link samples within a family')
@click.argument('sample_id', required=False)
@click.pass_context
def link(context, family_id, sample_id):
    """Link FASTQ files for a sample."""
    if family_id and (sample_id is None):
        # link all samples in a family
        family_obj = context.obj['db'].family(family_id)
        link_objs = family_obj.links
    elif sample_id and (family_id is None):
        # link sample in all its families
        sample_obj = context.obj['db'].sample(sample_id)
        link_objs = sample_obj.links
    elif sample_id and family_id:
        # link only one sample in a family
        link_objs = [context.obj['db'].link(family_id, sample_id)]
    else:
        click.echo(click.style('you need to provide family and/or sample', fg='red'))
        context.abort()

    for link_obj in link_objs:
        context.obj['api'].link_sample(link_obj)


@analysis.command()
@click.option('-p', '--print', 'print_output', is_flag=True, help='print to console')
@click.argument('family_id')
@click.pass_context
def panel(context, print_output, family_id):
    """Write aggregated gene panel file."""
    family_obj = context.obj['db'].family(family_id)
    bed_lines = context.obj['api'].panel(family_obj)
    if print_output:
        for bed_line in bed_lines:
            click.echo(bed_line)
    else:
        context.obj['tb'].write_panel(family_id, bed_lines)


@analysis.command()
@priority_option
@email_option
@click.argument('family_id')
@click.pass_context
def start(context, priority, email, family_id):
    """Start the analysis pipeline for a family."""
    family_obj = context.obj['db'].family(family_id)
    try:
        context.obj['api'].start(family_obj, priority=priority, email=email)
    except tb.MipStartError as error:
        click.echo(click.style(error.message, fg='red'))
