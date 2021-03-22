from typing import Optional, List

from cg.constants import Pipeline
from cg.constants.gene_panel import GENOME_BUILD_38
from cg.meta.workflow.mip import MipAnalysisAPI
from cg.utils import Process


class MipRNAAnalysisAPI(MipAnalysisAPI):
    def __init__(self, config: dict, pipeline: Pipeline = Pipeline.MIP_RNA):
        super().__init__(config, pipeline)

    @property
    def root(self) -> str:
        return self.config["mip-rd-rna"]["root"]

    @property
    def conda_env(self) -> str:
        return self.config["mip-rd-rna"]["conda_env"]

    @property
    def mip_pipeline(self) -> str:
        return self.config["mip-rd-rna"]["pipeline"]

    @property
    def script(self) -> str:
        return self.config["mip-rd-rna"]["script"]

    @property
    def threshold_reads(self):
        return True

    @property
    def process(self) -> Process:
        if not self._process:
            self._process = Process(
                binary=f"{self.script} {self.mip_pipeline}",
                config=self.config["mip-rd-rna"]["mip_config"],
                environment=self.conda_env,
            )
        return self._process

    def config_sample(self, link_obj, panel_bed: Optional[str] = None) -> dict:
        sample_data = self.get_sample_data(link_obj)
        if link_obj.mother:
            sample_data["mother"] = link_obj.mother.internal_id
        if link_obj.father:
            sample_data["father"] = link_obj.father.internal_id
        return sample_data

    def panel(self, case_id: str, genome_build: str = GENOME_BUILD_38) -> List[str]:
        """Create the aggregated gene panel file"""
        case_obj: models.Family = self.status_db.family(case_id)
        all_panels = self.convert_panels(case_obj.customer.internal_id, case_obj.panels)
        return self.scout_api.export_panels(build=genome_build, panels=all_panels)
