"""Set case attributes in the status database"""
import logging
from typing import Optional, Tuple
import click

from cg.apps.avatar.api import Avatar
from cg.constants import CASE_ACTIONS, PRIORITY_OPTIONS, DataDelivery, Pipeline
from cg.models.cg_config import CGConfig
from cg.store import Store, models
from cg.utils.click.EnumChoice import EnumChoice

LOG = logging.getLogger(__name__)


@click.command()
@click.option("-a", "--action", type=click.Choice(CASE_ACTIONS), help="update case action")
@click.option("--avatar-url", type=click.STRING, help="update avatar url")
@click.option("-c", "--customer-id", type=click.STRING, help="update customer")
@click.option(
    "-d",
    "--data-analysis",
    "data_analysis",
    type=EnumChoice(Pipeline),
    help="Update case data analysis",
)
@click.option(
    "-dd",
    "--data-delivery",
    "data_delivery",
    type=EnumChoice(DataDelivery),
    help="Update case data delivery",
)
@click.option("-g", "--panel", "panels", multiple=True, help="update gene panels")
@click.option("-p", "--priority", type=click.Choice(PRIORITY_OPTIONS), help="update priority")
@click.argument("family_id")
@click.pass_obj
def family(
    context: CGConfig,
    action: Optional[str],
    avatar_url: Optional[str],
    data_analysis: Optional[Pipeline],
    data_delivery: Optional[DataDelivery],
    priority: Optional[str],
    panels: Optional[Tuple[str]],
    family_id: str,
    customer_id: Optional[str],
):
    """Update information about a case."""
    status_db: Store = context.status_db
    case_obj: models.Family = status_db.family(family_id)
    if case_obj is None:
        LOG.error("Can't find case %s,", family_id)
        raise click.Abort
    if not any([action, avatar_url, panels, priority, customer_id, data_analysis, data_delivery]):
        LOG.error("Nothing to change")
        raise click.Abort
    if action:
        LOG.info("Update action: %s -> %s", case_obj.action or "NA", action)
        case_obj.action = action
    if avatar_url:
        if not Avatar.is_url_image(avatar_url) or status_db.find_family_by_avatar_url(avatar_url):
            avatar_url = Avatar.get_avatar_url(case_obj.internal_id)
        LOG.info("Update avatar_url: %s -> %s", case_obj.avatar_url or "NA", avatar_url)
        case_obj.avatar_url = avatar_url
    if customer_id:
        customer_obj: models.Customer = status_db.customer(customer_id)
        if customer_obj is None:
            LOG.error("Unknown customer: %s", customer_id)
            raise click.Abort
        LOG.info(f"Update customer: {case_obj.customer.internal_id} -> {customer_id}")
        case_obj.customer = customer_obj
    if data_analysis:
        LOG.info(f"Update data_analysis: {case_obj.data_analysis or 'NA'} -> {data_analysis}")
        case_obj.data_analysis = data_analysis
    if data_delivery:
        LOG.info(f"Update data_delivery: {case_obj.data_delivery or 'NA'} -> {data_delivery}")
        case_obj.data_delivery = data_delivery
    if panels:
        for panel_id in panels:
            panel_obj: models.Panel = status_db.panel(panel_id)
            if panel_obj is None:
                LOG.error(f"unknown gene panel: {panel_id}")
                raise click.Abort
        LOG.info(f"Update panels: {', '.join(case_obj.panels)} -> {', '.join(panels)}")
        case_obj.panels = panels
    if priority:
        LOG.info(f"update priority: {case_obj.priority_human} -> {priority}")
        case_obj.priority_human = priority

    status_db.commit()
