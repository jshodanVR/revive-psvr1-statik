# RevivePSVR1 — Statik

Play **Statik** on Windows through an OpenXR PCVR headset, using a modified
shadPS4 emulator derived from AstroQuest. Bring your own compatible game dump.
No game, extracted game assets, firmware or saves are included.

This is an independent Statik project. Updates from other projects are reviewed
and integrated manually. Other games and Quest/Android are not release targets.

## Current status

The inherited Statik implementation has positive headset reports and fixes for
loading memory, stereo stencil rendering and controller recentering. This new
repository is a fresh development snapshot and requires its own headset test.
It is not a claim of a complete, crash-free playthrough. Some Vulkan image-copy
validation issues remain; see [known issues](docs/KNOWN-ISSUES.md).

## Build and play

1. Follow [BUILD.md](BUILD.md) to compile and prepare the local player.
2. Put your Statik **CUSA06929** base PKG in `games`. The verified layout is
   APP_VER **01.00**, VERSION **01.01**; no separate update is required.
3. Start your headset and select its OpenXR runtime.
4. Open **Play Statik VR.bat**. The launcher prepares the game and shows settings.

The importer scans `games`, checks internal metadata and retains your PKG.
An encrypted store download is not an extractable game dump.
Use a writable folder; administrator access is not required to play.

## Features

- OpenXR headset tracking and stereo output, with the headset's field of view.
- PC DualShock/DualSense and tracked VR controllers, including Steam Frame bindings.
- Selectable left/right hand for the virtual gamepad, mixed PC/VR input and recentering.
- Verified executable layouts offer 100%, 125%, 150% and 200% game rendering scale.
- Optional Enhanced surfaces, disabled by default, generated using local game files.
- Automatic package preparation and local diagnostic collection.

Read [controls](docs/CONTROLS.md), [saves and upgrades](docs/SAVES.md), and
[package troubleshooting](docs/PKG-IMPORT-PCVR.txt).
Run **Collect PCVR Logs.bat** after a problem. Review logs before sharing: they
can contain local paths and device names. Nothing is uploaded automatically.

## Credits and source

Built on [AstroQuest](https://github.com/bigmak94/AstroQuest),
[shadPS4](https://github.com/shadps4-emu/shadPS4) and
[shadps4-arm64](https://github.com/zenithblue-oss/shadps4-arm64).
Selected inherited changes also originate from
[evertec82/Farpoint](https://github.com/evertec82/Farpoint).
Their authorship and license notices are retained. See [provenance](docs/PROVENANCE.md),
[LICENSE](LICENSE) and [third-party notices](THIRD-PARTY-NOTICES.md).

No affiliation with the original game's developers or Sony is implied.
