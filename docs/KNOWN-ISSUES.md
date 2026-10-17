# Known issues and validation scope

This independent checkout has not yet been accepted in a physical headset.
Earlier Statik builds received positive headset reports, including three levels
after the loading-memory correction. That does not verify the whole game.

- Color-to-depth image-copy Vulkan validation errors (01548/10211) were observed
  in earlier builds. Their existence must not be described as a clean validation pass.
- Higher rendering scales increase GPU and memory requirements. Resolution and
  memory changes are enabled only for the recognized executable layout.
- Enhanced surfaces are optional and default off; not every puzzle/material
  combination has been verified. Disable them when comparing graphical problems.
- Runtime and controller coverage is incomplete. OpenXR compatibility is not a
  guarantee that every device profile has been tested.

Before release, check package preparation, both eyes, the PROJECT laser pointer,
level transitions, PC/VR input switching, all puzzle buttons, L3+R3 recentering,
and save preservation. Use consecutive frames/video to assess flicker.
