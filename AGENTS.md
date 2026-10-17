# Repository instructions

This is the independent Windows PCVR/OpenXR Statik project.
Use English for documentation, comments and user-facing messages.
Keep changes focused on Statik; other games are independent projects.
Do not modify the neighboring development checkout or another title's player.
Do not import upstream changes automatically. Preserve licenses and attribution.
Use the repository-local Git identity and dedicated deploy-key configuration;
never use a global account identity or unrelated authentication credentials.
Never commit game dumps, extracted game files, saves, private keys, local logs,
shader dumps, build output or machine-specific settings.
Build with tools/build-statik.ps1. Do not start a headset test while the user is
using another game. Document exact test coverage; a timed stop is not a crash,
and isolated screenshots do not establish the absence of flicker.
Accepted release tags and ZIPs are immutable. Prepare a new version for changes.
