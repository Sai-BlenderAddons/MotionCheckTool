# Armature Tools - Blender 5.0 Extension

A Blender 5.0 extension providing convenient tools for working with armatures, designed to streamline animation preview workflows and detect motion capture errors with per-axis precision.

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

### Armature Tools Panel

#### Quick Setup
One-click setup that automatically:
- Finds and activates an armature in the scene
- Hides all non-armature objects
- Sets bone display to B-Bone mode with axes visible
- Sets B-Bone scale to 0.5 for all bones
- Configures frame range based on animation data
- Creates a follow camera system
- Deselects all bones to improve timeline playback performance

#### Display Mode
- **Set B-Bone Display + Axes** - Quick button to set display mode
- **Display As** - Dropdown to switch between display modes (Octahedral, Stick, B-Bone, Envelope, Wire)
- **Show Names** - Toggle bone name visibility
- **Show Axes** - Toggle bone axes visibility
- **Axes Position** - Adjust axes position along the bone (0 = head, 1 = tail)

#### B-Bone Scale
- Real-time adjustment of `bbone_x` and `bbone_z` values
- Affects selected bones only (in Pose/Edit mode) or all bones if none selected
- Slider with range 0.001 - 10.0

#### Camera Setup
- **Create Follow Camera** - Creates an Empty and Camera that follow the Hips bone
  - Empty uses Copy Location constraint to track Hips position
  - Camera is parented to Empty with Track To constraint
  - Empty rotates around Z-axis based on frame number (controllable speed)
  - Automatically switches to camera view and enables "Lock Camera to View"
- **Rotation Speed** - Adjust camera orbit speed (-2.0 to 2.0 degrees/frame)
- **Track To Target** - Toggle camera tracking on/off for free rotation
- **Lock Camera to View** - Toggle viewport camera lock

#### Frame Range
- **Set Frame Range from Animation** - Automatically sets scene frame range based on animation data

---

### Fake Bone Panel

A separate panel for creating curve-based bone visualizations and detecting motion capture errors.

#### Create
- **Create Fake Bones** - Generates curve objects that follow the armature's bone structure
  - Creates one curve per bone with matching names (`FakeBone_{bone_name}`)
  - Curves have two vertices: origin at (0,0,0) and end at (0, bone_length, 0)
  - Uses Child Of constraint to follow bone transforms
  - Organizes all curves in a dedicated collection (`{Armature}_FakeBones`)
  - Re-running clears existing fake bones and recreates them

#### Settings
- **Bevel Depth** - Real-time adjustment of curve thickness (0.01 - 10.0, default: 1.0)
- Shows the number of fake bones in the collection

#### Rotation Anomaly Detection
Designed to detect motion capture errors such as sudden flips or solver failures, with per-axis precision.

**Threshold Settings:**
- **X(R)** - X-axis rotation threshold (default: 8°) → Red channel
- **Y(G)** - Y-axis rotation threshold (default: 8°) → Green channel  
- **Z(B)** - Z-axis rotation threshold (default: 8°) → Blue channel

**Detection Buttons:**
- **Detect Selected** - Analyze only selected curve objects
- **Detect All** - Analyze all curves in the fake bones collection

**How it works:**
1. Reads bone rotation data (Euler or Quaternion) directly from FCurves
2. Calculates rotation difference per axis between consecutive frames
3. Handles angle wrapping (takes shorter path if difference > 180°)
4. Marks frames where rotation exceeds the threshold for each axis independently
5. Clears existing color keyframes before setting new ones

**Color Marking System (XYZ → RGB):**

| Axis Anomaly | Color Channel | Result Color |
|--------------|---------------|--------------|
| X only | R=1, G=0, B=0 | Red |
| Y only | R=0, G=1, B=0 | Green |
| Z only | R=0, G=0, B=1 | Blue |
| X + Y | R=1, G=1, B=0 | Yellow |
| X + Z | R=1, G=0, B=1 | Magenta |
| Y + Z | R=0, G=1, B=1 | Cyan |
| X + Y + Z | R=1, G=1, B=1 | White |
| None | R=0, G=0, B=0 | Black |

**Keyframe Details:**
- Uses CONSTANT interpolation for instant color switching
- Sets initial keyframe at animation start (all channels = 0)
- For each anomaly: sets value=1 at anomaly frame
- Sets value=0 two frames before and after anomalies for clean transitions
- Existing color keyframes are cleared before each detection run

---

## Installation

1. Download the `armature_tools-1.1.0.zip` file
2. In Blender 5.0, go to `Edit > Preferences > Get Extensions`
3. Click the dropdown menu in the top-right corner
4. Select `Install from Disk...`
5. Choose the downloaded zip file

## Usage

### Panel Location
Both panels appear in the 3D Viewport sidebar (press `N` to toggle), under the **"Armature Tools"** tab.

### Typical Animation Preview Workflow

1. Import or create an armature with animation
2. Click **Quick Setup** to automatically configure everything
3. Use the playback controls to preview the animation
4. Adjust camera rotation speed as needed
5. Toggle **Track To Target** off to manually adjust camera angle

### Mocap Error Detection Workflow

1. Import a motion capture armature with animation
2. Select the armature and click **Create Fake Bones**
3. Adjust **Bevel Depth** for better visibility
4. Set appropriate thresholds for each axis:
   - Lower values (e.g., 5°) = more sensitive, catches subtle issues
   - Higher values (e.g., 15°) = less sensitive, only catches major errors
   - Default 8° is a good starting point
5. Click **Detect All** to analyze all bones
6. Scrub through the timeline:
   - **Red** curves = X-axis rotation issues
   - **Green** curves = Y-axis rotation issues
   - **Blue** curves = Z-axis rotation issues
   - **Mixed colors** = multiple axis issues
7. Use **Detect Selected** to re-analyze specific bones with different thresholds

---

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

### v1.1.0
- Added **Fake Bone** panel (separate from Armature Tools)
- Added **Create Fake Bones** feature - generates curve objects following bone structure
- Added **Bevel Depth** real-time adjustment (range: 0.01 - 10.0, default: 1.0)
- Added **Rotation Anomaly Detection** for mocap error detection
  - **Per-axis detection**: X, Y, Z axes detected independently
  - **RGB color mapping**: X→Red, Y→Green, Z→Blue
  - Separate threshold for each axis (default: 8°)
  - Uses Euler angle difference calculation with angle wrapping
  - Reads directly from FCurves (fast, no scene updates)
  - CONSTANT interpolation for instant color switching
  - Clears existing color keyframes before each run
  - Support for selected curves or entire collection
- Refactored panel structure - Fake Bone is now a standalone panel

### v1.0.0
- Initial release
- Quick Setup feature
- Display Mode controls (B-Bone, Axes, Names)
- B-Bone Scale real-time adjustment
- Follow Camera with rotation driver
- Frame Range auto-detection
- Track To and Lock Camera toggles
- MVC architecture (properties.py, operators.py, ui.py)
