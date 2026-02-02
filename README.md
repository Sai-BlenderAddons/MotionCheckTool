# Armature Tools - Blender 5.0 Extension

A Blender 5.0 extension providing convenient tools for working with armatures, designed to streamline animation preview workflows.

## Project Structure

```
armature_tools/
├── __init__.py           # Main entry point, handles registration
├── properties.py         # PropertyGroup and update callbacks (Model)
├── operators.py          # All operators (Controller)
├── ui.py                 # Panel definitions (View)
├── blender_manifest.toml # Extension manifest
└── README.md             # This file
```

## Features

### Quick Setup
One-click setup that automatically:
- Hides all non-armature objects in the scene
- Sets bone display to B-Bone mode with axes visible
- Sets B-Bone scale to 0.5 for all bones
- Configures frame range based on animation data
- Creates a follow camera system
- Deselects all bones to improve timeline playback performance

### Display Mode
- **Set B-Bone Display + Axes** - Quick button to set display mode
- **Display As** - Dropdown to switch between display modes (Octahedral, Stick, B-Bone, Envelope, Wire)
- **Show Names** - Toggle bone name visibility
- **Show Axes** - Toggle bone axes visibility
- **Axes Position** - Adjust axes position along the bone (0 = head, 1 = tail)

### B-Bone Scale
- Real-time adjustment of `bbone_x` and `bbone_z` values
- Affects selected bones only (in Pose/Edit mode) or all bones if none selected
- Slider with range 0.001 - 10.0

### Camera Setup
- **Create Follow Camera** - Creates an Empty and Camera that follow the Hips bone
  - Empty uses Copy Location constraint to track Hips position
  - Camera is parented to Empty with Track To constraint
  - Empty rotates around Z-axis based on frame number (controllable speed)
  - Automatically switches to camera view and enables "Lock Camera to View"
- **Rotation Speed** - Adjust camera orbit speed (-2.0 to 2.0 degrees/frame)
  - Negative = clockwise, Positive = counter-clockwise, 0 = stop
- **Track To Target** - Toggle camera tracking on/off for free rotation
- **Lock Camera to View** - Toggle viewport camera lock

### Frame Range
- **Set Frame Range from Animation** - Automatically sets scene frame range based on:
  - Keyframe data from selected bones (if any selected in Pose mode)
  - All animation data if no bones selected
  - NLA strip ranges

## Installation

1. Download the `armature_tools-1.0.0.zip` file
2. In Blender 5.0, go to `Edit > Preferences > Get Extensions`
3. Click the dropdown menu in the top-right corner
4. Select `Install from Disk...`
5. Choose the downloaded zip file

## Usage

1. The panel appears in the 3D Viewport sidebar (press `N` to toggle)
2. Look for the **"Armature Tools"** tab
3. The panel is visible when:
   - An Armature is the active object (full panel)
   - Any Armature exists in the scene (Quick Setup only)

### Typical Workflow

1. Import or create an armature with animation
2. Click **Quick Setup** to automatically configure everything
3. Use the playback controls to preview the animation
4. Adjust camera rotation speed as needed
5. Toggle **Track To Target** off to manually adjust camera angle
6. Toggle **Lock Camera to View** to reposition the camera

## Supported Hips Bone Names

The follow camera automatically detects Hips bones with these names:
- Hips, hips, HIPS
- Hip, hip, HIP
- Pelvis, pelvis, PELVIS
- Root, root, ROOT
- mixamorig:Hips, mixamorig_Hips
- Any bone containing "hip" (case-insensitive)

## Requirements

- Blender 5.0.0 or later

## License

GPL-3.0-or-later

## Changelog

### v1.0.0
- Initial release
- Quick Setup feature
- Display Mode controls (B-Bone, Axes, Names)
- B-Bone Scale real-time adjustment
- Follow Camera with rotation driver
- Frame Range auto-detection
- Track To and Lock Camera toggles
- Refactored to MVC architecture (properties.py, operators.py, ui.py)
