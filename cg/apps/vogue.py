"""
    Module for vogue API
"""

import json
import logging
import subprocess
from subprocess import CalledProcessError

LOG = logging.getLogger(__name__)


class VogueAPI:

    """
        API for vogue
    """

    def __init__(self, config: dict):
        super(VogueAPI, self).__init__()
        self.vogue_binary = config["vogue"]["binary_path"]
        self.base_call = [self.vogue_binary]

    def load_genotype_data(self, genotype_dict: dict):
        """Load genotype data from a dict."""
        load_call = self.base_call[:]
        load_call.extend(["load", "genotype", "-s", json.dumps(genotype_dict)])

        # Execute command and print its stdout+stderr as it executes
        for line in execute_command(load_call):
            LOG.info("vogue output: %s", line)

    def load_apptags(self, apptag_list: list):
        """Add observations from a VCF."""
        load_call = self.base_call[:]
        load_call.extend(["load", "apptag", json.dumps(apptag_list)])

        # Execute command and print its stdout+stderr as it executes
        for line in execute_command(load_call):
            log_msg = f"vogue output: {line}"
            LOG.info(log_msg)


def check_process_status(process):
    """Checking process returncode to see if process failes or not."""

    return process.poll() != 0


def execute_command(cmd):
    """
        Prints stdout + stderr of command in real-time while being executed

        Args:
            cmd (list): command sequence

        Yields:
            line (str): line of output from command
    """
    process = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, bufsize=1
    )

    for line in process.stdout:
        yield line.decode("utf-8").strip()

    if check_process_status(process) and process.returncode:
        raise CalledProcessError(returncode=process.returncode, cmd=cmd)
