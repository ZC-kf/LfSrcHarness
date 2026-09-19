import os
import subprocess
from pathlib import Path

import pytest
from PIL import Image

ROOT = Path(__file__).parents[1]


def test_windows_installer_checks_runtime_before_copying_files() -> None:
    script = (ROOT / "deploy" / "windows" / "LfSrcHarness.iss").read_text(encoding="utf-8")

    assert "ArchitecturesAllowed=x64compatible" in script
    assert "function HasWebView2: Boolean;" in script
    assert "function HasDotNet: Boolean;" in script
    assert "function PrepareToInstall(var NeedsRestart: Boolean): String;" in script
    assert "MicrosoftEdgeWebview2Setup.exe" in script
    assert "NDP48-web.exe" in script
    assert "if HasWebView2 then" in script
    assert 'Name: "{userdesktop}\\LfSrcHarness"' in script


def test_windows_installer_fetches_prerequisites_from_microsoft() -> None:
    script = (ROOT / "deploy" / "windows" / "LfSrcHarness.iss").read_text(encoding="utf-8")

    assert "https://go.microsoft.com/fwlink/?LinkId=2085155" in script
    assert "https://go.microsoft.com/fwlink/p/?LinkId=2124703" in script
    assert "DownloadTemporaryFile" in script
    assert "VerifyMicrosoftSignature" in script
    assert 'Source: "..\\..\\package\\prereqs\\' not in script


def test_windows_installer_validates_embedded_payload_and_installed_app() -> None:
    script = (ROOT / "deploy" / "windows" / "LfSrcHarness.iss").read_text(encoding="utf-8")

    assert 'FileExists("..\\..\\package\\LfSrcHarness-Desktop-Preview\\LfSrcHarness.exe")' in script
    assert (
        'FileExists("..\\..\\package\\LfSrcHarness-Desktop-Preview\\_internal\\'
        'web\\dist\\index.html")'
        in script
    )
    assert "procedure CurStepChanged(CurStep: TSetupStep);" in script
    assert "--self-test" in script
    assert "RaiseException" in script


def test_desktop_icon_is_embedded_in_exe_and_installer() -> None:
    icon = ROOT / "assets" / "LfSrcHarness-icon.ico"
    with Image.open(icon) as image:
        assert image.size == (256, 256)
        assert len(image.info["sizes"]) >= 5
    spec = (ROOT / "build" / "lfsrc-desktop.spec").read_text(encoding="utf-8")
    installer = (ROOT / "deploy" / "windows" / "LfSrcHarness.iss").read_text(encoding="utf-8")
    assert 'icon=str(root / "assets" / "LfSrcHarness-icon.ico")' in spec
    assert "SetupIconFile=..\\..\\assets\\LfSrcHarness-icon.ico" in installer


@pytest.mark.skipif(os.name != "nt", reason="PowerShell source-copy test runs on Windows")
def test_windows_source_install_excludes_local_bundle_and_runtime_data(tmp_path: Path) -> None:
    source = tmp_path / "source"
    destination = tmp_path / "destination"
    for directory in ("deploy", "src", "web", "agent_bundle", "runs", "package"):
        (source / directory).mkdir(parents=True)
    (source / "deploy" / "install.ps1").write_text(
        (ROOT / "deploy" / "install.ps1").read_text(encoding="utf-8"), encoding="utf-8"
    )
    (source / "deploy" / ".env").write_text("private=1", encoding="utf-8")
    (source / "src" / "own.py").write_text("pass", encoding="utf-8")
    (source / "agent_bundle" / "private.txt").write_text("private", encoding="utf-8")
    (source / "runs" / "evidence.txt").write_text("private", encoding="utf-8")
    (source / "package" / "tool.exe").write_text("private", encoding="utf-8")

    result = subprocess.run(
        ["powershell", "-NoProfile", "-File", str(source / "deploy" / "install.ps1"),
         "-Root", str(destination), "-CopyOnly"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert (destination / "src" / "own.py").exists()
    for relative in ("agent_bundle", "runs", "package", "deploy/.env"):
        assert not (destination / relative).exists()


@pytest.mark.skipif(os.name != "posix", reason="Linux installer runs on POSIX")
def test_linux_installer_reports_missing_python_before_installing(tmp_path: Path) -> None:
    result = subprocess.run(
        ["bash", str(ROOT / "deploy" / "install.sh"), "--check"],
        env={**os.environ, "LFSRC_PYTHON_BIN": str(tmp_path / "missing-python")},
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "Python 3.12" in result.stdout
    assert "--install-deps" in result.stdout


@pytest.mark.skipif(os.name != "posix", reason="Linux installer runs on POSIX")
def test_linux_source_copy_excludes_local_bundle_and_runtime_data(tmp_path: Path) -> None:
    source = tmp_path / "source"
    destination = tmp_path / "destination"
    for directory in ("deploy", "src", "web", "agent_bundle", "runs", "package"):
        (source / directory).mkdir(parents=True)
    (source / "deploy" / "install.sh").write_text(
        (ROOT / "deploy" / "install.sh").read_text(encoding="utf-8"), encoding="utf-8"
    )
    (source / "deploy" / ".env").write_text("private=1", encoding="utf-8")
    (source / "src" / "own.py").write_text("pass", encoding="utf-8")
    (source / "agent_bundle" / "private.txt").write_text("private", encoding="utf-8")
    (source / "runs" / "evidence.txt").write_text("private", encoding="utf-8")
    (source / "package" / "tool.exe").write_text("private", encoding="utf-8")

    result = subprocess.run(
        ["bash", str(source / "deploy" / "install.sh"), "--root", str(destination),
         "--copy-only"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert (destination / "src" / "own.py").exists()
    for relative in ("agent_bundle", "runs", "package", "deploy/.env"):
        assert not (destination / relative).exists()
