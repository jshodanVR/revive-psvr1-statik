# RevivePSVR1 - Statik

Play **Statik** on Windows with an OpenXR PCVR headset and either a PC gamepad
or tracked VR controllers. Bring your own compatible game dump.

## Download and play

Download **RevivePSVR1-Statik-v0.1.0-Windows-PCVR.zip** from
[Releases](https://github.com/jshodanVR/revive-psvr1-statik/releases).
The player and package importer are included. **You do not need to compile anything.**
GitHub's automatic "Source code" downloads are for developers, not players.

1. Extract the entire ZIP into a writable folder, for example `C:\VR\Statik`.
2. Put your Statik **CUSA06929** base PKG in `games`. The supported layout is
   APP_VER **01.00**, VERSION **01.01**; no separate update is required.
3. Start your headset and select its OpenXR runtime.
4. Open **Play Statik VR.bat**. The launcher prepares the game and shows settings.

Requirements: Windows x64, a Vulkan-capable GPU with current drivers, an OpenXR
PCVR runtime, and the [Microsoft Visual C++ x64 runtime](https://aka.ms/vs/17/release/vc_redist.x64.exe).
Package preparation uses Windows PowerShell and .NET Framework.
Administrator access is not required to play.

The importer scans `games`, checks internal metadata and retains your original PKG.
An encrypted store download is not an extractable game dump. No game, firmware,
extracted game files or saves are included in the download.

## Features

- OpenXR headset tracking and stereo output with the headset's field of view.
- PC DualShock/DualSense and tracked VR controllers, including Steam Frame bindings.
- Selectable left/right hand for the virtual gamepad, mixed PC/VR input and recentering.
- Recognized executable layouts offer 100%, 125%, 150% and 200% game rendering scale.
- Optional Enhanced surfaces, disabled by default, generated from local game files.
- Automatic package preparation and local diagnostic collection.

## Status and support

Version 0.1.0 is an initial pre-release. The packaged player passed the user's
headset smoke test on 17 October 2026. A complete playthrough and every headset
or controller combination have not been verified. See [known issues](docs/KNOWN-ISSUES.md).

Read [controls](docs/CONTROLS.md), [saves and upgrades](docs/SAVES.md), and
[package troubleshooting](docs/PKG-IMPORT-PCVR.txt).
After a problem, run **Collect PCVR Logs.bat**. Review logs before sharing:
they can contain local paths and device names. Nothing is uploaded automatically.

## Development and licenses

This is a standalone Windows PCVR Statik project. Developers can follow
[BUILD.md](BUILD.md). Source provenance, contributor attribution and dependency
licenses are documented in [PROVENANCE.md](docs/PROVENANCE.md),
[LICENSE](LICENSE) and [THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md).

No affiliation with the original game's developers or Sony is implied.
