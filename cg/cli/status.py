# -*- coding: utf-8 -*-

import click
from tabulate import tabulate

from cg.store import Store
from cg.constants import FAMILY_ACTIONS, PRIORITY_OPTIONS


CASE_HEADERS = ['Case', 'Ordered', 'Rec', 'Pre', 'Seq', 'Analysed', 'Uploaded', 'Delivered',
                'Invoiced']


@click.group()
@click.pass_context
def status(context):
    """View status of things."""
    context.obj['db'] = Store(context.obj['database'])


@status.command()
@click.pass_context
def analysis(context):
    """Which families will be analyzed?"""
    records = context.obj['db'].families_to_mip_analyze()
    for family_obj in records:
        click.echo(family_obj)


def present_bool(case, param, show_false=False):
    """presents boolean value in a human friendly format"""
    value = case.get(param)
    if show_false:
        return ('-' if value is None else
                '✓' if value is True else
                '✗' if value is False else
                str(value))

    return ('-' if value is None else
            '✓' if value is True else
            '' if value is False else
            str(value))


def present_date(case, param, show_negative, show_time):
    """presents datetime value in a human friendly format"""
    value = case.get(param)

    if not show_time and value and value.date:
        value = value.date()

    if show_negative:
        return str(value)

    return ('' if not value else
            value if value else
            str(value))


@status.command()
@click.pass_context
@click.option('-o', '--output-type', type=click.Choice(['bool', 'count', 'date', 'datetime']),
              default='bool', help='how to display status')
@click.option('--verbose', is_flag=True, help='show status information otherwise left out')
@click.option('--days', default=31, help='days to go back')
@click.option('--internal-id', help='search by internal id')
@click.option('--name', help='search by name given by customer')
@click.option('--action', type=click.Choice(FAMILY_ACTIONS), help='filter by action')
@click.option('--priority', type=click.Choice(PRIORITY_OPTIONS), help='filter by priority')
@click.option('--data-analysis', help='filter on data_analysis')
@click.option('--sample-id', help='filter by sample id')
@click.option('-c', '--customer-id', help='filter by customer')
@click.option('-C', '--exclude-customer-id', help='exclude customer')
@click.option('-r', '--only-received', is_flag=True, help='only completely received cases')
@click.option('-R', '--exclude-received', is_flag=True, help='exclude completely received cases')
@click.option('-p', '--only-prepared', is_flag=True, help='only completely prepared cases')
@click.option('-P', '--exclude-prepared', is_flag=True, help='exclude completely prepared cases')
@click.option('-s', '--only-sequenced', is_flag=True, help='only completely sequenced cases')
@click.option('-S', '--exclude-sequenced', is_flag=True, help='exclude completely sequenced cases')
@click.option('-a', '--only-analysed', is_flag=True, help='only analysed cases')
@click.option('-A', '--exclude-analysed', is_flag=True, help='exclude analysed cases')
@click.option('-u', '--only-uploaded', is_flag=True, help='only uploaded cases')
@click.option('-U', '--exclude-uploaded', is_flag=True, help='exclude uploaded cases')
@click.option('-d', '--only-delivered', is_flag=True, help='only completely delivered cases')
@click.option('-D', '--exclude-delivered', is_flag=True, help='exclude completely delivered cases')
@click.option('-i', '--only-invoiced', is_flag=True, help='only completely invoiced cases')
@click.option('-I', '--exclude-invoiced', is_flag=True, help='exclude completely invoiced cases')
def cases(context, output_type, verbose, days, internal_id, name, action, priority,
          customer_id, data_analysis, sample_id,
          only_received,
          only_prepared,
          only_sequenced,
          only_analysed,
          only_uploaded,
          only_delivered,
          only_invoiced,
          exclude_customer_id,
          exclude_received,
          exclude_prepared,
          exclude_sequenced,
          exclude_analysed,
          exclude_uploaded,
          exclude_delivered,
          exclude_invoiced,
          ):
    """progress of each case"""
    records = context.obj['db'].cases(
        days=days,
        internal_id=internal_id,
        name=name,
        action=action,
        priority=priority,
        customer_id=customer_id,
        exclude_customer_id=exclude_customer_id,
        data_analysis=data_analysis,
        sample_id=sample_id,
        only_received=only_received,
        only_prepared=only_prepared,
        only_sequenced=only_sequenced,
        only_analysed=only_analysed,
        only_uploaded=only_uploaded,
        only_delivered=only_delivered,
        only_invoiced=only_invoiced,
        exclude_received=exclude_received,
        exclude_prepared=exclude_prepared,
        exclude_sequenced=exclude_sequenced,
        exclude_analysed=exclude_analysed,
        exclude_uploaded=exclude_uploaded,
        exclude_delivered=exclude_delivered,
        exclude_invoiced=exclude_invoiced,
    )
    case_rows = []

    for case in records:
        title = f"{case.get('internal_id')}"
        if name:
            title = f"{title} ({case.get('name')})"
        if data_analysis:
            title = f"{title} {case.get('samples_data_analyses')}"

        show_time = output_type == 'datetime'

        ordered = present_date(case, 'ordered_at', verbose, show_time)

        if output_type == 'bool':
            received = present_bool(case, 'samples_received_bool', verbose)
            prepared = present_bool(case, 'samples_prepared_bool', verbose)
            sequenced = present_bool(case, 'samples_sequenced_bool', verbose)
            analysed = present_bool(case, 'analysis_completed_bool', verbose)
            uploaded = present_bool(case, 'analysis_uploaded_bool', verbose)
            delivered = present_bool(case, 'samples_delivered_bool', verbose)
            invoiced = present_bool(case, 'samples_invoiced_bool', verbose)

        elif output_type == 'count':
            received = f"{case.get('samples_received')}/{case.get('samples_to_receive')}"
            prepared = f"{case.get('samples_prepared')}/{case.get('samples_to_prepare')}"
            sequenced = f"{case.get('samples_sequenced')}/{case.get('samples_to_sequence')}"

            analysed = present_date(case, 'analysis_completed_at', verbose, show_time)
            uploaded = present_date(case, 'analysis_uploaded_at', verbose, show_time)

            delivered = f"{case.get('samples_delivered')}/{case.get('samples_to_deliver')}"
            invoiced = f"{case.get('samples_invoiced')}/{case.get('samples_to_invoice')}"

        elif output_type in ('date', 'datetime'):
            received = present_date(case, 'samples_received_at', verbose, show_time)
            prepared = present_date(case, 'samples_prepared_at', verbose, show_time)
            sequenced = present_date(case, 'samples_sequenced_at', verbose, show_time)
            analysed = present_date(case, 'analysis_completed_at', verbose, show_time)
            uploaded = present_date(case, 'analysis_uploaded_at', verbose, show_time)
            delivered = present_date(case, 'samples_delivered_at', verbose, show_time)
            invoiced = present_date(case, 'samples_invoiced_at', verbose, show_time)

        case_row = [title, ordered, received, prepared, sequenced, analysed, uploaded, delivered,
                    invoiced]
        case_rows.append(case_row)

    click.echo(tabulate(case_rows, headers=CASE_HEADERS, tablefmt='psql'))


@status.command()
@click.option('-s', '--skip', default=0, help='skip initial records')
@click.pass_context
def samples(context, skip):
    """View status of samples."""
    records = context.obj['db'].samples().offset(skip).limit(30)
    for record in records:
        message = f"{record.internal_id} ({record.customer.internal_id})"
        if record.sequenced_at:
            color = 'green'
            message += f" [SEQUENCED: {record.sequenced_at.date()}]"
        elif record.received_at and record.reads:
            color = 'orange'
            message += f" [READS: {record.reads}]"
        elif record.received_at:
            color = 'blue'
            message += f" [RECEIVED: {record.received_at.date()}]"
        else:
            color = 'white'
            message += ' [NOT RECEIVED]'
        click.echo(click.style(message, fg=color))


@status.command()
@click.option('-s', '--skip', default=0, help='skip initial records')
@click.pass_context
def families(context, skip):
    """View status of families."""
    click.echo('red: prio > 1, blue: prio = 1, green: completed, yellow: action')
    records = context.obj['db'].families().offset(skip).limit(30)
    for family_obj in records:
        color = 'red' if family_obj.priority > 1 else 'blue'
        message = f"{family_obj.internal_id} ({family_obj.priority})"
        if family_obj.analyses:
            message += f" {family_obj.analyses[0].completed_at.date()}"
            color = 'green'
        if family_obj.action:
            message += f" [{family_obj.action.upper()}]"
            color = 'yellow'
        click.echo(click.style(message, fg=color))
