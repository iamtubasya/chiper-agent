from pathlib import Path


def test_windows_native_install_path_docs_match_installer() -> None:
    doc = Path("website/docs/user-guide/windows-native.md").read_text()
    install = Path("scripts/install.ps1").read_text()

    assert "%LOCALAPPDATA%\\chiper\\chiper-agent\\venv\\Scripts" in doc
    assert "Get-Command chiper        # should print C:\\Users\\<you>\\AppData\\Local\\chiper\\chiper-agent\\venv\\Scripts\\chiper.exe" in doc
    assert '$chiperBin = "$InstallDir\\venv\\Scripts"' in install
