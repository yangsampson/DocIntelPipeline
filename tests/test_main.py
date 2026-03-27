import pytest
import subprocess

# A simple test to see if the API can be imported
def test_read_main():
    from main import app
    assert app is not None

# A critical test for your specific project: Check if LibreOffice is actually there
def test_libreoffice_installed():
    result = subprocess.run(["soffice", "--version"], capture_output=True, text=True)
    assert result.returncode == 0
    assert "LibreOffice" in result.stdout
