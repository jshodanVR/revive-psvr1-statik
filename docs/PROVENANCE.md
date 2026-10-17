# Source provenance and maintenance

Initial import: 17 October 2026, from the PSVR1-Revive development working tree.
This is a curated source snapshot, not a reconstruction of a previously released
binary. `import-provenance.json` records the base revision and explicitly notes
that working-tree changes were included. Local development history is not imported.

AstroQuest supplies the starting PSVR implementation on top of shadPS4 and its
ARM64 derivative. Original copyright and SPDX notices remain in the source.
Selected Farpoint fixes were inherited at revision
`de6d8df1165aac8e09d90febfb4fb6a30384f48c`; see third-party notices for attribution.


Statik-specific work includes executable-guarded resolution/memory changes,
PROJECT stencil stereo handling, complete controller mappings, mixed input,
box recentering, package preparation and locally generated optional overrides.
The shared emulator still contains code paths for other titles. They are not
launchable products of this repository; removing shared code blindly risks regressions.

Dependencies are vendored without their Git metadata, with revision/origin
records in `dependencies.json`. Test Statik before accepting changes.

Game-derived overrides are reconstructed from the user's local assets. Never
commit extracted game files, generated game PAKs, personal saves or diagnostic dumps.

The vendored FFmpeg build is adapted to use revision 94dde08 explicitly. Its
Windows x64 archive SHA256 is 5038087e7798a0b129dbb4ff4a0caf4b6995aff91f5bf424096f65840385661d.
The build verifies cached archives too; a parent repository commit cannot change this dependency.
