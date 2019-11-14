# -*- coding: utf-8 -*-
import logging
import shutil
import sys
from pathlib import Path

import click
from cg.apps import hk, tb, scoutapi, lims
from cg.apps.balsamic.fastq import BalsamicFastqHandler
from cg.apps.mip.fastq import MipFastqHandler
from cg.apps.usalt.fastq import USaltFastqHandler
from cg.exc import LimsDataError
from cg.meta.analysis import AnalysisAPI
from cg.meta.deliver.api import DeliverAPI
from cg.store import Store

LOG = logging.getLogger(__name__)
PRIORITY_OPTION = click.option('-p', '--priority', type=click.Choice(['low', 'normal', 'high']))
EMAIL_OPTION = click.option('-e', '--email', help='email to send errors to')
START_WITH_PROGRAM = click.option('-sw', '--start-with', help='start mip from this program.')


@click.group(invoke_without_command=True)
@PRIORITY_OPTION
@EMAIL_OPTION
@START_WITH_PROGRAM
@click.option('-f', '--family', 'family_id', help='family to prepare and start an analysis for')
@click.pass_context
def analysis(context, priority, email, family_id, start_with):
    """Prepare and start a MIP analysis for a FAMILY_ID."""
    context.obj['db'] = Store(context.obj['database'])
    hk_api = hk.HousekeeperAPI(context.obj)
    scout_api = scoutapi.ScoutAPI(context.obj)
    lims_api = lims.LimsAPI(context.obj)
    context.obj['tb'] = tb.TrailblazerAPI(context.obj)
    deliver = DeliverAPI(context.obj, hk_api=hk_api, lims_api=lims_api)
    context.obj['api'] = AnalysisAPI(
        db=context.obj['db'],
        hk_api=hk_api,
        tb_api=context.obj['tb'],
        scout_api=scout_api,
        lims_api=lims_api,
        deliver_api=deliver
    )

    if context.invoked_subcommand is None:
        if family_id is None:
            _suggest_cases_to_analyze(context, show_as_error=True)
            context.abort()

        # check everything is ok
        family_obj = context.obj['db'].family(family_id)
        if family_obj is None:
            LOG.error(f"{family_id} not found")
            context.abort()
        is_ok = context.obj['api'].check(family_obj)
        if not is_ok:
            LOG.warning(f"{family_obj.internal_id}: not ready to start")
            # commit the updates to request flowcells
            context.obj['db'].commit()
        else:
            # execute the analysis!
            context.invoke(case_config, family_id=family_id)
            context.invoke(link, family_id=family_id)
            context.invoke(panel, family_id=family_id)
            context.invoke(start, family_id=family_id, priority=priority, email=email,
                           start_with=start_with)


def _suggest_cases_to_analyze(context, show_as_error=False):
    if show_as_error:
        LOG.error('provide a case, suggestions:')
    else:
        LOG.warning('provide a case, suggestions:')
    for family_obj in context.obj['db'].cases_to_mip_analyze()[:50]:
        click.echo(family_obj)


@analysis.command('case-config')
@click.option('-d', '--dry', is_flag=True, help='Print config to console')
@click.argument('family_id', required=False)
@click.pass_context
def case_config(context, dry, family_id):
    """Generate a config for the FAMILY_ID"""

    if family_id is None:
        _suggest_cases_to_analyze(context)
        context.abort()

    family_obj = context.obj['db'].family(family_id)

    if not family_obj:
        LOG.error('Case %s not found', family_id)
        context.abort()

    # pipeline formatted pedigree.yaml config
    config_data = context.obj['api'].config(family_obj)

    if dry:
        print(config_data)
    else:
        # Write to trailblazer root dir / family_id
        out_path = context.obj['tb'].save_config(config_data)
        LOG.info(f"saved config to: {out_path}")


analysis.add_command(case_config, 'config')


@analysis.command()
@click.option('-f', '--family', 'family_id', help='link all samples for a family')
@click.argument('sample_id', required=False)
@click.pass_context
def link(context, family_id, sample_id):
    """Link FASTQ files for a SAMPLE_ID."""

    link_objs = None

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

    if not link_objs:
        LOG.error('provide family and/or sample')
        context.abort()

    for link_obj in link_objs:
        LOG.info("%s: %s link FASTQ files", link_obj.sample.internal_id,
                 link_obj.sample.data_analysis)
        if link_obj.sample.data_analysis and 'balsamic' in link_obj.sample.data_analysis.lower():
            context.obj['api'].link_sample(BalsamicFastqHandler(context.obj),
                                           case=link_obj.family.internal_id,
                                           sample=link_obj.sample.internal_id)
        elif not link_obj.sample.data_analysis or \
                'mip' in link_obj.sample.data_analysis.lower() or \
                'mip-rna' in link_obj.sample.data_analysis.lower():
            mip_fastq_handler = MipFastqHandler(context.obj,
                                                context.obj['db'],
                                                context.obj['tb'])
            context.obj['api'].link_sample(mip_fastq_handler,
                                           case=link_obj.family.internal_id,
                                           sample=link_obj.sample.internal_id)


@analysis.command('link-microbial')
@click.option('-o', '--order', 'order_id', help='link all microbial samples for an order')
@click.argument('sample_id', required=False)
@click.pass_context
def link_microbial(context, order_id, sample_id):
    """Link FASTQ files for a SAMPLE_ID."""

    sample_objs = None

    if order_id and (sample_id is None):
        # link all samples in a case
        sample_objs = context.obj['db'].microbial_order(order_id).microbial_samples
    elif sample_id and (order_id is None):
        # link sample in all its families
        sample_objs = [context.obj['db'].microbial_sample(sample_id)]
    elif sample_id and order_id:
        # link only one sample in a case
        sample_objs = [context.obj['db'].microbial_sample(sample_id)]

    if not sample_objs:
        LOG.error('provide order and/or sample')
        context.abort()

    for sample_obj in sample_objs:
        LOG.info("%s: link FASTQ files", sample_obj.internal_id)
        context.obj['api'].link_sample(USaltFastqHandler(context.obj),
                                       case=sample_obj.microbial_order.internal_id,
                                       sample=sample_obj.internal_id)


@analysis.command()
@click.option('-p', '--print', 'print_output', is_flag=True, help='print to console')
@click.argument('family_id', required=False)
@click.pass_context
def panel(context, print_output, family_id):
    """Write aggregated gene panel file."""

    if family_id is None:
        _suggest_cases_to_analyze(context)
        context.abort()

    family_obj = context.obj['db'].family(family_id)
    bed_lines = context.obj['api'].panel(family_obj)
    if print_output:
        for bed_line in bed_lines:
            print(bed_line)
    else:
        context.obj['tb'].write_panel(family_id, bed_lines)


@analysis.command()
@PRIORITY_OPTION
@EMAIL_OPTION
@START_WITH_PROGRAM
@click.argument('family_id', required=False)
@click.pass_context
def start(context: click.Context, family_id: str, priority: str = None, email: str = None,
          start_with: str = None):
    """Start the analysis pipeline for a family."""

    if family_id is None:
        _suggest_cases_to_analyze(context)
        context.abort()

    family_obj = context.obj['db'].family(family_id)
    if family_obj is None:
        LOG.error(f"{family_id}: family not found")
        context.abort()
    if context.obj['tb'].analyses(family=family_obj.internal_id, temp=True).first():
        LOG.warning(f"{family_obj.internal_id}: analysis already running")
    else:
        context.obj['api'].start(family_obj, priority=priority, email=email, start_with=start_with)


@analysis.command()
@click.option('-d', '--dry-run', 'dry_run', is_flag=True, help='print to console, '
                                                               'without actualising')
@click.pass_context
def auto(context: click.Context, dry_run):
    """Start all analyses that are ready for analysis."""
    exit_code = 0

    cases = [case_obj.internal_id for case_obj in context.obj['db'].cases_to_mip_analyze()]

    for case_id in cases:

        case_obj = context.obj['db'].family(case_id)

        if AnalysisAPI.is_dna_only_case(case_obj):
            LOG.info("%s: start analysis", case_obj.internal_id)
        else:
            LOG.warning("%s: contains non-dna samples, skipping", case_obj.internal_id)
            continue

        priority = ('high' if case_obj.high_priority else
                    ('low' if case_obj.low_priority else 'normal'))

        if dry_run:
            continue

        try:
            context.invoke(analysis, priority=priority, family_id=case_obj.internal_id)
        except tb.MipStartError as error:
            LOG.exception(error.message)
            exit_code = 1
        except LimsDataError as error:
            LOG.exception(error.message)
            exit_code = 1

    sys.exit(exit_code)


@analysis.command()
@click.option('-f', '--family', 'family_id', help='remove fastq folder for a case')
@click.pass_context
def remove_fastq(context, family_id):
    """remove fastq folder"""

    wrk_dir = Path(f"{context.obj['balsamic']['root']}/{family_id}/fastq")

    if wrk_dir.exists():
        shutil.rmtree(wrk_dir)
