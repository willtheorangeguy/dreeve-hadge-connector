import sys

import pytest

from tests.integration.run import command


def test_successful_cli_diagnostics_on_stderr_are_available():
    output = command(sys.executable, "-c", "import sys; print('delivered=6', file=sys.stderr)",
                     include_stderr=True)
    assert "delivered=6" in output


def test_json_stdout_stays_separate_from_diagnostics():
    output = command(sys.executable, "-c",
                     "import sys; print('{}'); print('diagnostic', file=sys.stderr)")
    assert output.strip() == "{}"


def test_failed_subprocess_keeps_diagnostics():
    with pytest.raises(RuntimeError, match="synthetic failure"):
        command(sys.executable, "-c", "import sys; print('synthetic failure', file=sys.stderr); sys.exit(1)")
