"""Tests for the deliver base command"""
import logging

from cg.meta.deliver_ticket import DeliverTicketAPI
from cg.cli.deliver.base import deliver as deliver_cmd
from cg.constants import EXIT_SUCCESS
from cg.models.cg_config import CGConfig
from click.testing import CliRunner
from cgmodels.cg.constants import Pipeline


def test_run_base_help():
    """Test to run the deliver base command with --help"""
    # GIVEN a cli runner
    runner = CliRunner()

    # WHEN running cg deliver help
    result = runner.invoke(deliver_cmd, ["--help"])

    # THEN assert the command exists without problems
    assert result.exit_code == EXIT_SUCCESS
    # THEN assert the information is printed
    assert "Deliver files with CG" in result.output


def test_run_deliver_analysis_help(base_context: CGConfig):
    """Test to run the deliver base command with --help"""
    # GIVEN a cli runner
    runner = CliRunner()
    # GIVEN a context with store and housekeeper information

    # WHEN running cg deliver help
    result = runner.invoke(deliver_cmd, ["analysis", "--help"], obj=base_context)

    # THEN assert the command exists without problems
    assert result.exit_code == EXIT_SUCCESS
    # THEN assert the information is printed
    assert "Deliver analysis files to customer inbox" in result.output


def test_run_deliver_ticket_help(base_context: CGConfig):
    """Test to run the deliver base command with --help"""
    # GIVEN a cli runner
    runner = CliRunner()
    # GIVEN a context with store and housekeeper information

    # WHEN running cg deliver help
    result = runner.invoke(deliver_cmd, ["ticket", "--help"], obj=base_context)

    # THEN assert the command exists without problems
    assert result.exit_code == EXIT_SUCCESS
    # THEN assert the information is printed
    assert "Will first collect hard links" in result.output


def test_run_deliver_delivered_ticket(cg_context: CGConfig, mocker, caplog, helpers):
    """Test for when files are already delivered to customer inbox on hasta"""
    caplog.set_level(logging.INFO)

    # GIVEN a cli runner
    runner = CliRunner()

    # GIVEN uploading data to caesar is not needed
    mocker.patch.object(DeliverTicketAPI, "check_if_upload_is_needed")
    DeliverTicketAPI.check_if_upload_is_needed.return_value = False

    # WHEN running cg deliver ticket
    result = runner.invoke(
        deliver_cmd,
        ["ticket", "--dry-run", "--ticket-id", "123456", "--delivery-type", "fastq"],
        obj=cg_context,
    )

    # THEN assert the command exists without problems
    assert result.exit_code == EXIT_SUCCESS

    # THEN assert that files are already delivered to the customer inbox on hasta
    assert "Files already delivered to customer inbox on hasta" in caplog.text


def test_run_deliver_ticket(cg_context: CGConfig, mocker, caplog, helpers):
    """Test for delivering tu customer inbox"""
    caplog.set_level(logging.INFO)

    # GIVEN a cli runner
    runner = CliRunner()

    # GIVEN uploading data to caesar is needed
    mocker.patch.object(DeliverTicketAPI, "check_if_upload_is_needed")
    DeliverTicketAPI.check_if_upload_is_needed.return_value = True

    # GIVEN data needs to be concatenated
    mocker.patch.object(DeliverTicketAPI, "check_if_concatenation_is_needed")
    DeliverTicketAPI.check_if_concatenation_is_needed.return_value = True

    # WHEN running cg deliver ticket
    result = runner.invoke(
        deliver_cmd,
        ["ticket", "--dry-run", "--ticket-id", "123456", "--delivery-type", "fastq"],
        obj=cg_context,
    )

    # THEN assert that files are delivered
    assert "Delivering files to customer inbox on hasta" in caplog.text
