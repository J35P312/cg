import datetime as dt
import logging
from typing import List

import petname
from cg.apps.avatar.api import Avatar

from cg.constants import PRIORITY_MAP, DataDelivery, Pipeline
from cg.store import models
from cg.store.api.base import BaseHandler

LOG = logging.getLogger(__name__)


class AddHandler(BaseHandler):
    """Methods related to adding new data to the store."""

    def generate_unique_petname(self) -> str:
        while True:
            random_id = petname.Generate(3, separator="")
            if not self.sample(random_id):
                return random_id

    def add_customer(
        self,
        internal_id: str,
        name: str,
        customer_group: models.CustomerGroup,
        invoice_address: str,
        invoice_reference: str,
        scout_access: bool = False,
        *args,
        **kwargs,
    ) -> models.Customer:
        """Build a new customer record."""

        return self.Customer(
            internal_id=internal_id,
            name=name,
            scout_access=scout_access,
            customer_group=customer_group,
            invoice_address=invoice_address,
            invoice_reference=invoice_reference,
            **kwargs,
        )

    def add_customer_group(self, internal_id: str, name: str, **kwargs) -> models.CustomerGroup:
        """Build a new customer group record."""

        return self.CustomerGroup(internal_id=internal_id, name=name, **kwargs)

    def add_user(
        self, customer: models.Customer, email: str, name: str, is_admin: bool = False
    ) -> models.User:
        """Build a new user record."""

        new_user = self.User(name=name, email=email, is_admin=is_admin)
        new_user.customers.append(customer)
        return new_user

    def add_application(
        self,
        tag: str,
        category: str,
        description: str,
        percent_kth: int,
        percent_reads_guaranteed: int,
        is_accredited: bool = False,
        **kwargs,
    ) -> models.Application:
        """Build a new application  record."""

        new_record = self.Application(
            tag=tag,
            prep_category=category,
            description=description,
            is_accredited=is_accredited,
            percent_kth=percent_kth,
            percent_reads_guaranteed=percent_reads_guaranteed,
            **kwargs,
        )
        return new_record

    def add_version(
        self,
        application: models.Application,
        version: int,
        valid_from: dt.datetime,
        prices: dict,
        **kwargs,
    ) -> models.ApplicationVersion:
        """Build a new application version record."""

        new_record = self.ApplicationVersion(version=version, valid_from=valid_from, **kwargs)
        for price_key in ["standard", "priority", "express", "research"]:
            setattr(new_record, f"price_{price_key}", prices[price_key])
        new_record.application = application
        return new_record

    def add_bed(self, name: str, **kwargs) -> models.Bed:
        """Build a new bed record."""

        new_record = self.Bed(name=name, **kwargs)
        return new_record

    def add_bed_version(
        self, bed: models.Bed, version: int, filename: str, **kwargs
    ) -> models.BedVersion:
        """Build a new bed version record."""

        new_record = self.BedVersion(version=version, filename=filename, **kwargs)
        new_record.bed = bed
        return new_record

    def add_sample(
        self,
        name: str,
        sex: str,
        comment: str = None,
        control: str = None,
        downsampled_to: int = None,
        internal_id: str = None,
        order: str = None,
        ordered: dt.datetime = None,
        priority: str = None,
        received: dt.datetime = None,
        ticket: int = None,
        tumour: bool = False,
        **kwargs,
    ) -> models.Sample:
        """Build a new Sample record."""

        internal_id = internal_id or self.generate_unique_petname()
        priority_human = priority or ("research" if downsampled_to else "standard")
        priority_db = PRIORITY_MAP[priority_human]
        return self.Sample(
            comment=comment,
            control=control,
            downsampled_to=downsampled_to,
            internal_id=internal_id,
            is_tumour=tumour,
            name=name,
            order=order,
            ordered_at=ordered or dt.datetime.now(),
            priority=priority_db,
            received_at=received,
            sex=sex,
            ticket_number=ticket,
            **kwargs,
        )

    def add_case(
        self,
        data_analysis: Pipeline,
        data_delivery: DataDelivery,
        name: str,
        panels: List[str],
        cohorts: List[str] = None,
        priority: str = "standard",
        synopsis: str = None,
    ) -> models.Family:
        """Build a new Family record."""

        # generate a unique case id
        while True:
            internal_id = petname.Generate(2, separator="")
            if self.family(internal_id) is None:
                break
            else:
                LOG.debug(f"{internal_id} already used - trying another id")

        avatar_url = None
        try:
            avatar_urls = Avatar.get_avatar_urls(internal_id)
            for avatar_url in avatar_urls:
                if avatar_url and self.find_family_by_avatar_url(avatar_url=avatar_url) is None:
                    break
                else:
                    LOG.debug(f"{avatar_url} already used - trying another url")
        except Exception as e:
            LOG.error(
                "Could not fetch case avatar url for case: %s, Error: %s", internal_id, str(e)
            )

        priority_db = PRIORITY_MAP[priority]
        new_case = self.Family(
            avatar_url=avatar_url,
            cohorts=cohorts,
            data_analysis=str(data_analysis),
            data_delivery=str(data_delivery),
            internal_id=internal_id,
            name=name,
            panels=panels,
            priority=priority_db,
            synopsis=synopsis,
        )
        return new_case

    def relate_sample(
        self,
        family: models.Family,
        sample: models.Sample,
        status: str,
        mother: models.Sample = None,
        father: models.Sample = None,
    ) -> models.FamilySample:
        """Relate a sample record to a family record."""

        new_record = self.FamilySample(status=status)
        new_record.family = family
        new_record.sample = sample
        new_record.mother = mother
        new_record.father = father
        return new_record

    def add_flowcell(
        self, name: str, sequencer: str, sequencer_type: str, date: dt.datetime
    ) -> models.Flowcell:
        """Build a new Flowcell record."""

        new_record = self.Flowcell(
            name=name, sequencer_name=sequencer, sequencer_type=sequencer_type, sequenced_at=date
        )
        return new_record

    def add_analysis(
        self,
        pipeline: Pipeline,
        version: str = None,
        completed_at: dt.datetime = None,
        primary: bool = False,
        uploaded: dt.datetime = None,
        started_at: dt.datetime = None,
        **kwargs,
    ) -> models.Analysis:
        """Build a new Analysis record."""

        new_record = self.Analysis(
            pipeline=str(pipeline),
            pipeline_version=version,
            completed_at=completed_at,
            is_primary=primary,
            uploaded_at=uploaded,
            started_at=started_at,
            **kwargs,
        )
        return new_record

    def add_panel(
        self,
        customer: models.Customer,
        name: str,
        abbrev: str,
        version: float,
        date: dt.datetime = None,
        genes: int = None,
    ) -> models.Panel:
        """Build a new panel record."""

        new_record = self.Panel(
            name=name, abbrev=abbrev, current_version=version, date=date, gene_count=genes
        )
        new_record.customer = customer
        return new_record

    def add_pool(
        self,
        customer: models.Customer,
        name: str,
        order: str,
        ordered: dt.datetime,
        application_version: models.ApplicationVersion,
        ticket: int = None,
        comment: str = None,
        received: dt.datetime = None,
        capture_kit: str = None,
    ) -> models.Pool:
        """Build a new Pool record."""

        new_record = self.Pool(
            name=name,
            ordered_at=ordered or dt.datetime.now(),
            order=order,
            ticket_number=ticket,
            received_at=received,
            comment=comment,
            capture_kit=capture_kit,
        )
        new_record.customer = customer
        new_record.application_version = application_version
        return new_record

    def add_delivery(
        self,
        destination: str,
        sample: models.Sample = None,
        pool: models.Pool = None,
        comment: str = None,
    ) -> models.Delivery:
        """Build a new Delivery record."""

        if not any([sample, pool]):
            raise ValueError("you have to provide a sample or a pool")
        new_record = self.Delivery(destination=destination, comment=comment)
        new_record.sample = sample
        new_record.pool = pool
        return new_record

    def add_invoice(
        self,
        customer: models.Customer,
        samples: List[models.Sample] = None,
        microbial_samples: List[models.Sample] = None,
        pools: List[models.Pool] = None,
        comment: str = None,
        discount: int = 0,
        record_type: str = None,
    ):
        """Build a new Invoice record."""

        new_id = self.new_invoice_id()
        new_invoice = self.Invoice(
            comment=comment, discount=discount, id=new_id, record_type=record_type
        )
        new_invoice.customer = customer
        for sample in samples or []:
            new_invoice.samples.append(sample)
        for microbial_sample in microbial_samples or []:
            new_invoice.samples.append(microbial_sample)
        for pool in pools or []:
            new_invoice.pools.append(pool)
        return new_invoice

    def add_organism(
        self,
        internal_id: str,
        name: str,
        reference_genome: str = None,
        verified: bool = False,
        **kwargs,
    ) -> models.Organism:
        """Build a new Organism record."""

        new_organism = self.Organism(
            internal_id=internal_id,
            name=name,
            reference_genome=reference_genome,
            verified=verified,
            **kwargs,
        )
        return new_organism
