"""Behavioral checks for the Windows install-time component preflight."""

import json
import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "deploy" / "windows" / "OfficialComponents.ps1"


def run_check(install_root: Path, nmap: Path, metasploit: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            "powershell", "-NoProfile", "-NonInteractive", "-File", str(SCRIPT),
            "-Mode", "Check", "-InstallRoot", str(install_root),
            "-NmapExecutable", str(nmap), "-MetasploitExecutable", str(metasploit),
        ],
        capture_output=True,
        text=True,
        check=False,
    )


def run_install(
    install_root: Path, nmap: Path, metasploit: Path, *, offline: bool = False
) -> subprocess.CompletedProcess[str]:
    args = [
        "powershell", "-NoProfile", "-NonInteractive", "-File", str(SCRIPT),
        "-Mode", "Install", "-InstallRoot", str(install_root),
        "-NmapExecutable", str(nmap), "-MetasploitExecutable", str(metasploit),
    ]
    if offline:
        args.append("-Offline")
    return subprocess.run(args, capture_output=True, text=True, check=False)


@pytest.mark.skipif(os.name != "nt", reason="PowerShell installer check runs on Windows")
def test_preflight_reuses_existing_components_without_creating_downloads(tmp_path: Path) -> None:
    install_root = tmp_path / "LfSrc Harness"
    nmap = tmp_path / "existing" / "nmap.exe"
    metasploit = tmp_path / "existing" / "msfconsole.bat"
    nmap.parent.mkdir()
    nmap.write_bytes(b"present")
    metasploit.write_bytes(b"present")

    result = run_check(install_root, nmap, metasploit)

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {
        "metasploit": {"ready": True, "path": str(metasploit)},
        "nmap": {"ready": True, "path": str(nmap)},
    }
    assert not (install_root / "tools" / "downloads").exists()


@pytest.mark.skipif(os.name != "nt", reason="PowerShell installer check runs on Windows")
def test_preflight_reports_each_missing_component_without_network(tmp_path: Path) -> None:
    result = run_check(
        tmp_path / "LfSrc Harness",
        tmp_path / "absent-nmap.exe",
        tmp_path / "absent-msfconsole.bat",
    )

    assert result.returncode == 20, result.stderr
    status = json.loads(result.stdout)
    assert status["nmap"] == {"ready": False, "path": None}
    assert status["metasploit"] == {"ready": False, "path": None}
    assert not (tmp_path / "LfSrc Harness").exists()


@pytest.mark.skipif(os.name != "nt", reason="PowerShell installer check runs on Windows")
def test_install_reuses_present_components_without_download(tmp_path: Path) -> None:
    nmap = tmp_path / "nmap.exe"
    metasploit = tmp_path / "msfconsole.bat"
    nmap.write_bytes(b"present")
    metasploit.write_bytes(b"present")

    result = run_install(tmp_path / "LfSrc Harness", nmap, metasploit)

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["nmap"]["ready"] is True
    assert not (tmp_path / "LfSrc Harness" / "tools" / "downloads").exists()


@pytest.mark.skipif(os.name != "nt", reason="PowerShell installer check runs on Windows")
def test_install_offline_reports_missing_without_changing_system(tmp_path: Path) -> None:
    install_root = tmp_path / "LfSrc Harness"

    result = run_install(
        install_root, tmp_path / "missing-nmap.exe", tmp_path / "missing-msf.bat", offline=True
    )

    assert result.returncode == 21
    assert "nmap" in result.stderr.lower()
    assert "metasploit" in result.stderr.lower()
    assert not install_root.exists()
