"""
    Module for interacting with crunchy to perform:
        1. Compressing: FASTQ to SPRING
        2. Decompressing: SPRING to FASTQ
    along with the helper methods
"""

import datetime
import logging
from pathlib import Path
from typing import Dict, Optional

from cg.apps.crunchy import files
from cg.apps.slurm.slurm_api import SlurmAPI
from cg.constants import FASTQ_DELTA
from cg.models import CompressionData
from cg.models.slurm.sbatch import Sbatch
from cgmodels.crunchy.metadata import CrunchyFile, CrunchyMetadata

from .sbatch import (
    FASTQ_TO_SPRING_COMMANDS,
    FASTQ_TO_SPRING_ERROR,
    SPRING_TO_FASTQ_COMMANDS,
    SPRING_TO_FASTQ_ERROR,
)

LOG = logging.getLogger(__name__)


FLAG_PATH_SUFFIX = ".crunchy.txt"
PENDING_PATH_SUFFIX = ".crunchy.pending.txt"


class CrunchyAPI:
    """
    API for crunchy
    """

    def __init__(self, config: dict):
        self.slurm_account = config["crunchy"]["slurm"]["account"]
        self.crunchy_env = config["crunchy"]["slurm"]["conda_env"]
        self.mail_user = config["crunchy"]["slurm"]["mail_user"]
        self.reference_path = config["crunchy"]["cram_reference"]
        self.slurm_api = SlurmAPI()
        self.dry_run = False

    def set_dry_run(self, dry_run: bool) -> None:
        """Update dry run"""
        LOG.info("Updating compress api")
        LOG.info("Set dry run to %s", dry_run)
        self.dry_run = dry_run
        self.slurm_api.set_dry_run(dry_run=dry_run)

    # Methods to check compression status
    @staticmethod
    def is_compression_pending(compression_obj: CompressionData) -> bool:
        """Check if compression/decompression has started but not finished"""
        if compression_obj.pending_exists():
            LOG.info("Compression/decompression is pending for %s", compression_obj.run_name)
            return True
        LOG.info("Compression/decompression is not running")
        return False

    @staticmethod
    def is_fastq_compression_possible(compression_obj: CompressionData) -> bool:
        """Check if FASTQ compression is possible

        There are three possible answers to this question:

         - Compression is running          -> Compression NOT possible
         - SPRING archive exists           -> Compression NOT possible
         - Not compressed and not running  -> Compression IS possible
        """
        if CrunchyAPI.is_compression_pending(compression_obj):
            return False

        if compression_obj.spring_exists():
            LOG.info("SPRING file found")
            return False

        LOG.info("FASTQ compression is possible")

        return True

    @staticmethod
    def is_spring_decompression_possible(compression_obj: CompressionData) -> bool:
        """Check if SPRING decompression is possible

        There are three possible answers to this question:

            - Compression/Decompression is running      -> Decompression is NOT possible
            - The FASTQ files are not compressed        -> Decompression is NOT possible
            - Compression has been performed            -> Decompression IS possible

        """
        if compression_obj.pending_exists():
            LOG.info("Compression/decompression is pending for %s", compression_obj.run_name)
            return False

        if not compression_obj.spring_exists():
            LOG.info("No SPRING file found")
            return False

        if compression_obj.pair_exists():
            LOG.info("FASTQ files already exists")
            return False

        LOG.info("Decompression is possible")

        return True

    @staticmethod
    def is_fastq_compression_done(compression_obj: CompressionData) -> bool:
        """Check if FASTQ compression is finished

        This is checked by controlling that the SPRING files that are produced after FASTQ
        compression exists.

        The following has to be fulfilled for FASTQ compression to be considered done:

            - A SPRING archive file exists
            - A SPRING archive metadata file exists
            - The SPRING archive has not been unpacked before FASTQ delta (21 days)

        Note:
        'updated_at' indicates at what date the SPRING archive was unarchived last.
        If the SPRING archive has never been unarchived 'updated_at' is None

        """
        LOG.info("Check if FASTQ compression is finished")
        LOG.info("Check if SPRING file %s exists", compression_obj.spring_path)
        if not compression_obj.spring_exists():
            LOG.info("No SPRING file for %s", compression_obj.run_name)
            return False
        LOG.info("SPRING file found")

        LOG.info("Check if SPRING metadata file %s exists", compression_obj.spring_metadata_path)
        if not compression_obj.metadata_exists():
            LOG.info("No metadata file found")
            return False
        LOG.info("SPRING metadata file found")

        # We want this to raise exception if file is malformed
        crunchy_metadata: CrunchyMetadata = files.get_crunchy_metadata(
            compression_obj.spring_metadata_path
        )

        # Check if the SPRING archive has been unarchived
        updated_at: Optional[datetime.date] = files.get_file_updated_at(crunchy_metadata)
        if updated_at is None:
            LOG.info("FASTQ compression is done for %s", compression_obj.run_name)
            return True

        LOG.info("Files where unpacked %s", updated_at)

        if not CrunchyAPI.check_if_update_spring(updated_at):
            return False

        LOG.info("FASTQ compression is done for %s", compression_obj.run_name)

        return True

    @staticmethod
    def is_spring_decompression_done(compression_obj: CompressionData) -> bool:
        """Check if SPRING decompression if finished.

        This means that all three files specified in SPRING metadata should exist.
        That is

            - First read in FASTQ pair should exist
            - Second read in FASTQ pair should exist
            - SPRING archive file should still exist
        """

        spring_metadata_path: Path = compression_obj.spring_metadata_path
        LOG.info("Check if SPRING metadata file %s exists", spring_metadata_path)

        if not compression_obj.metadata_exists():
            LOG.info("No SPRING metadata file found")
            return False

        # We want this to exit hard if the metadata is malformed
        crunchy_metadata: CrunchyMetadata = files.get_crunchy_metadata(spring_metadata_path)

        for file_info in crunchy_metadata.files:
            if not Path(file_info.path).exists():
                LOG.info("File %s does not exist", file_info.path)
                return False
            if not file_info.updated:
                LOG.info("Files have not been unarchived")
                return False

        LOG.info("SPRING decompression is done for run %s", compression_obj.run_name)

        return True

    @staticmethod
    def create_pending_file(pending_path: Path, dry_run: bool) -> None:
        LOG.info("Creating pending flag %s", pending_path)
        if dry_run:
            return
        pending_path.touch(exist_ok=False)

    # These are the compression/decompression methods
    def fastq_to_spring(self, compression_obj: CompressionData, sample_id: str = "") -> int:
        """
        Compress FASTQ files into SPRING by sending to sbatch SLURM

        """
        CrunchyAPI.create_pending_file(
            pending_path=compression_obj.pending_path, dry_run=self.dry_run
        )
        log_dir: Path = files.get_log_dir(compression_obj.spring_path)
        # Generate the error function
        error_function = FASTQ_TO_SPRING_ERROR.format(
            spring_path=compression_obj.spring_path, pending_path=compression_obj.pending_path
        )
        # Generate the commands
        commands = FASTQ_TO_SPRING_COMMANDS.format(
            conda_env=self.crunchy_env,
            tmp_dir=files.get_tmp_dir(
                prefix="spring_", suffix="_compress", base=compression_obj.analysis_dir.as_posix()
            ),
            fastq_first=compression_obj.fastq_first,
            fastq_second=compression_obj.fastq_second,
            spring_path=compression_obj.spring_path,
            pending_path=compression_obj.pending_path,
        )
        sbatch_info = {
            "job_name": "_".join([sample_id, compression_obj.run_name, "fastq_to_spring"]),
            "account": self.slurm_account,
            "number_tasks": 12,
            "memory": 50,
            "log_dir": log_dir.as_posix(),
            "email": self.mail_user,
            "hours": 24,
            "commands": commands,
            "error": error_function,
        }
        sbatch_content: str = self.slurm_api.generate_sbatch_content(Sbatch.parse_obj(sbatch_info))
        sbatch_path: Path = files.get_fastq_to_spring_sbatch_path(
            log_dir=log_dir, run_name=compression_obj.run_name
        )
        sbatch_number: int = self.slurm_api.submit_sbatch(
            sbatch_content=sbatch_content, sbatch_path=sbatch_path
        )
        LOG.info("Fastq compression running as job %s", sbatch_number)
        return sbatch_number

    def spring_to_fastq(self, compression_obj: CompressionData, sample_id: str = "") -> int:
        """
        Decompress SPRING into FASTQ by submitting sbatch script to SLURM

        """
        CrunchyAPI.create_pending_file(
            pending_path=compression_obj.pending_path, dry_run=self.dry_run
        )
        # Fetch the metadata information from a spring metadata file
        crunchy_metadata: CrunchyMetadata = files.get_crunchy_metadata(
            compression_obj.spring_metadata_path
        )
        files_info: Dict[str, CrunchyFile] = files.get_spring_archive_files(crunchy_metadata)
        log_dir = files.get_log_dir(compression_obj.spring_path)

        error_function = SPRING_TO_FASTQ_ERROR.format(
            fastq_first=compression_obj.fastq_first,
            fastq_second=compression_obj.fastq_second,
            pending_path=compression_obj.pending_path,
        )

        commands = SPRING_TO_FASTQ_COMMANDS.format(
            conda_env=self.crunchy_env,
            tmp_dir=files.get_tmp_dir(
                prefix="spring_", suffix="_decompress", base=compression_obj.analysis_dir.as_posix()
            ),
            fastq_first=compression_obj.fastq_first,
            fastq_second=compression_obj.fastq_second,
            spring_path=compression_obj.spring_path,
            pending_path=compression_obj.pending_path,
            checksum_first=files_info["fastq_first"].checksum,
            checksum_second=files_info["fastq_second"].checksum,
        )

        sbatch_info = {
            "job_name": "_".join([sample_id, compression_obj.run_name, "spring_to_fastq"]),
            "account": self.slurm_account,
            "number_tasks": 12,
            "memory": 50,
            "log_dir": log_dir.as_posix(),
            "email": self.mail_user,
            "hours": 24,
            "commands": commands,
            "error": error_function,
        }
        sbatch_content: str = self.slurm_api.generate_sbatch_content(Sbatch.parse_obj(sbatch_info))
        sbatch_path = files.get_spring_to_fastq_sbatch_path(
            log_dir=log_dir, run_name=compression_obj.run_name
        )
        sbatch_number: int = self.slurm_api.submit_sbatch(
            sbatch_content=sbatch_content, sbatch_path=sbatch_path
        )
        LOG.info("Spring decompression running as job %s", sbatch_number)
        return sbatch_number

    @staticmethod
    def check_if_update_spring(file_date: datetime.date) -> bool:
        """Check if date is older than FASTQ_DELTA (21 days)"""
        delta = file_date + datetime.timedelta(days=FASTQ_DELTA)
        now = datetime.datetime.now()
        if delta > now.date():
            LOG.info("FASTQ files are not old enough")
            return False
        return True
