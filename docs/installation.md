# Installation

[日本語](#japanese) · [English](#english)

## English

### Requirements

- Python 3.11 or newer
- `ffmpeg` and `ffprobe`
- A current terminal; Windows Terminal is recommended on Windows

Run `archiveloom doctor` after installation. ArchiveLoom fails closed when a required dependency or external-only storage check cannot be verified.

### Install ArchiveLoom

Until the first PyPI release, install directly from GitHub:

```console
pipx install git+https://github.com/nematatu/archiveloom.git
```

or:

```console
uv tool install git+https://github.com/nematatu/archiveloom.git
```

Alpha releases also provide unsigned standalone executables for macOS, Windows, and Linux on [GitHub Releases](https://github.com/nematatu/archiveloom/releases). They do not bundle FFmpeg. Review the release notes and keep `ffmpeg`/`ffprobe` on `PATH`; Python tool installation remains the recommended alpha path.

For contributors:

```console
git clone https://github.com/nematatu/archiveloom.git
cd archiveloom
python -m venv .venv
```

Activate the environment, then:

```console
python -m pip install --upgrade pip
python -m pip install -e ".[dev,docs]"
archiveloom doctor
```

### macOS

Install FFmpeg with Homebrew:

```console
brew install ffmpeg pipx
pipx ensurepath
```

External-only detection uses `diskutil info -plist` and refuses the target when it cannot prove that the volume is external.

### Windows

Install Python and FFmpeg with winget:

```powershell
winget install Python.Python.3.13
winget install Gyan.FFmpeg
py -m pip install --user pipx
py -m pipx ensurepath
```

Open a new terminal after changing PATH. External-only detection uses PowerShell `Get-Partition | Get-Disk`. USB, SD, MMC, and IEEE 1394 disks are treated as external only when they are not boot or system disks.

### Linux

Debian/Ubuntu:

```console
sudo apt update
sudo apt install ffmpeg pipx python3-venv
pipx ensurepath
```

Fedora:

```console
sudo dnf install ffmpeg pipx python3
pipx ensurepath
```

Arch Linux:

```console
sudo pacman -S ffmpeg python-pipx
pipx ensurepath
```

External-only detection requires `findmnt` and `lsblk`, normally provided by util-linux.

### Verify

```console
archiveloom --version
archiveloom doctor --output /path/to/archive
archiveloom adapters list
```

<a id="japanese"></a>

## 日本語

### 必要なもの

- Python 3.11以上
- `ffmpeg`と`ffprobe`
- 現在のターミナル。WindowsではWindows Terminalを推奨

インストール後に`archiveloom --lang ja doctor`を実行してください。依存関係や外付け判定を確認できない場合、ArchiveLoomは安全側に停止します。

### ArchiveLoomのインストール

最初のPyPI公開まではGitHubからインストールします。

```console
pipx install git+https://github.com/nematatu/archiveloom.git
```

または:

```console
uv tool install git+https://github.com/nematatu/archiveloom.git
```

[GitHub Releases](https://github.com/nematatu/archiveloom/releases)では、macOS・Windows・Linux用の未署名アルファ版単体実行ファイルも配布します。FFmpegは同梱しないため、`ffmpeg`・`ffprobe`を別途`PATH`へ設定してください。アルファ期間はPythonツールとしての導入を推奨します。

FFmpegの導入は上記のmacOS・Windows・Linux別コマンドを参照してください。実際のパッケージ名はOSのバージョンやリポジトリにより異なる場合があります。
