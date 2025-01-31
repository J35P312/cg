import logging
from pathlib import Path
from typing import Iterator, List, Optional

import alchy
import sqlalchemy as sqa
from cg.apps.cgstats.crud import find
from cg.apps.cgstats.db import models
from cg.models.cgstats.flowcell import StatsFlowcell, StatsSample

LOG = logging.getLogger(__name__)


class StatsAPI(alchy.Manager):

    Project = models.Project
    Sample = models.Sample
    Unaligned = models.Unaligned
    Supportparams = models.Supportparams
    Datasource = models.Datasource
    Demux = models.Demux
    Flowcell = models.Flowcell

    def __init__(self, config: dict):
        LOG.info("Instantiating cgstats api")
        alchy_config = dict(SQLALCHEMY_DATABASE_URI=config["cgstats"]["database"])
        super(StatsAPI, self).__init__(config=alchy_config, Model=models.Model)
        self.root_dir = Path(config["cgstats"]["root"])

    @staticmethod
    def get_curated_sample_name(sample_name: str) -> str:
        """Create new sample name"""
        raw_sample_name: str = sample_name.split("_", 1)[0]
        return raw_sample_name.rstrip("AB")

    def get_flowcell_samples(self, flowcell_object: models.Flowcell) -> List[StatsSample]:
        flowcell_samples: List[StatsSample] = []
        for sample_obj in self.flowcell_samples(flowcell_obj=flowcell_object):
            curated_sample_name: str = self.get_curated_sample_name(sample_obj.samplename)
            sample_data = {"name": curated_sample_name, "reads": 0, "fastqs": []}
            for fc_data in self.sample_reads(sample_obj):
                if fc_data.type == "hiseqga" and fc_data.q30 >= 80:
                    sample_data["reads"] += fc_data.reads
                elif fc_data.type == "hiseqx" and fc_data.q30 >= 75:
                    sample_data["reads"] += fc_data.reads
                elif fc_data.type == "novaseq" and fc_data.q30 >= 75:
                    sample_data["reads"] += fc_data.reads
                else:
                    LOG.warning(
                        f"q30 too low for {curated_sample_name} on {fc_data.name}:"
                        f"{fc_data.q30} < {80 if fc_data.type == 'hiseqga' else 75}%"
                    )
                    continue
                for fastq_path in self.fastqs(fc_data.name, sample_obj):
                    if self.is_lane_pooled(
                        flowcell_obj=flowcell_object, lane=fc_data.lane
                    ) and "Undetermined" in str(fastq_path):
                        continue
                    sample_data["fastqs"].append(str(fastq_path))
            flowcell_samples.append(StatsSample(**sample_data))
        return flowcell_samples

    def flowcell(self, flowcell_name: str) -> StatsFlowcell:
        """Fetch information about a flowcell."""
        flowcell_object: models.Flowcell = self.Flowcell.query.filter_by(
            flowcellname=flowcell_name
        ).first()
        flowcell_data = {
            "name": flowcell_object.flowcellname,
            "sequencer": flowcell_object.demux[0].datasource.machine,
            "sequencer_type": flowcell_object.hiseqtype,
            "date": flowcell_object.time,
            "samples": self.get_flowcell_samples(flowcell_object),
        }

        return StatsFlowcell(**flowcell_data)

    def flowcell_samples(self, flowcell_obj: models.Flowcell) -> Iterator[models.Sample]:
        """Fetch all the samples from a flowcell."""
        return self.Sample.query.join(models.Sample.unaligned, models.Unaligned.demux).filter(
            models.Demux.flowcell == flowcell_obj
        )

    def is_lane_pooled(self, flowcell_obj: models.Flowcell, lane: str) -> bool:
        """Check whether a lane is pooled or not."""
        query = (
            self.session.query(sqa.func.count(models.Unaligned.sample_id).label("sample_count"))
            .join(models.Unaligned.demux)
            .filter(models.Demux.flowcell == flowcell_obj)
            .filter(models.Unaligned.lane == lane)
        )
        return query.first().sample_count > 1

    def sample_reads(self, sample_obj: models.Sample) -> alchy.Query:
        """Calculate reads for a sample."""
        return (
            self.session.query(
                models.Flowcell.flowcellname.label("name"),
                models.Flowcell.hiseqtype.label("type"),
                models.Unaligned.lane,
                sqa.func.sum(models.Unaligned.readcounts).label("reads"),
                sqa.func.min(models.Unaligned.q30_bases_pct).label("q30"),
            )
            .join(models.Flowcell.demux, models.Demux.unaligned)
            .filter(models.Unaligned.sample == sample_obj)
            .group_by(models.Flowcell.flowcellname)
        )

    @staticmethod
    def sample(sample_name: str) -> models.Sample:
        """Fetch a sample for the database by name."""
        return find.get_sample(sample_name).first()

    def fastqs(self, flowcell: str, sample_obj: models.Sample) -> Iterator[Path]:
        """Fetch FASTQ files for a sample."""
        base_pattern = "*{}/Unaligned*/Project_*/Sample_{}/*.fastq.gz"
        alt_pattern = "*{}/Unaligned*/Project_*/Sample_{}_*/*.fastq.gz"
        for fastq_pattern in (base_pattern, alt_pattern):
            pattern = fastq_pattern.format(flowcell, sample_obj.samplename)
            files = self.root_dir.glob(pattern)
            yield from files

    def document_path(self, flowcell_name: str) -> str:
        """Get the latest document path of a flowcell from supportparams"""
        query = (
            self.session.query(
                models.Supportparams.document_path,
            )
            .join(models.Flowcell.demux, models.Demux.datasource, models.Datasource.supportparams)
            .filter(models.Flowcell.flowcellname == flowcell_name)
            .order_by(models.Supportparams.supportparams_id.desc())
            .first()
        )
        return query.document_path

    def run_name(self, flowcell_name: str) -> str:
        """Get the latest run name of a flowcell from datasource"""
        query = (
            self.session.query(models.Datasource.runname)
            .join(models.Flowcell.demux, models.Demux.datasource)
            .filter(models.Flowcell.flowcellname == flowcell_name)
            .order_by(models.Datasource.time.desc())
            .first()
        )
        return query.runname
