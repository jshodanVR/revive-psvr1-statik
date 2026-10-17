# Known issues and validation scope

The packaged player passed a user headset smoke test on 17 October 2026. Earlier testing also covered three levels after the loading-memory correction. These checks do not establish a complete playthrough or coverage of every device.

- Color-to-depth image-copy Vulkan validation errors (01548/10211) were observed
  in earlier builds. Their existence must not be described as a clean validation pass.
- Higher rendering scales increase GPU and memory requirements. Resolution and
  memory changes are enabled only for the recognized executable layout.
- Enhanced surfaces are optional and default off; not every puzzle/material
  combination has been verified. Disable them when comparing graphical problems.
- Runtime and controller coverage is incomplete. OpenXR compatibility is not a
  guarantee that every device profile has been tested.

For regression testing, check package preparation, both eyes, the PROJECT laser pointer,
level transitions, PC/VR input switching, all puzzle buttons, L3+R3 recentering,
and save preservation. Use consecutive frames/video to assess flicker.
