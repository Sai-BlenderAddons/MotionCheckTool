import bpy
from bpy.types import Operator, Panel, PropertyGroup
from bpy.props import FloatProperty, PointerProperty
from bpy_extras import anim_utils


# ============================================================
# Update callback for real-time B-Bone scale adjustment
# ============================================================
def update_bbone_scale(self, context):
    """Callback function to update bbone_x and bbone_z in real-time"""
    if not context.active_object or context.active_object.type != 'ARMATURE':
        return
    
    armature = context.active_object
    scale_value = self.bbone_scale
    
    # Check if we're in pose mode or edit mode with selected bones
    selected_bones = []
    
    if context.mode == 'POSE':
        selected_bones = [bone.name for bone in context.selected_pose_bones] if context.selected_pose_bones else []
    elif context.mode == 'EDIT_ARMATURE':
        selected_bones = [bone.name for bone in context.selected_bones] if context.selected_bones else []
    
    # Access bones through armature data
    bones = armature.data.bones
    
    if selected_bones:
        # Only adjust selected bones
        for bone_name in selected_bones:
            if bone_name in bones:
                bone = bones[bone_name]
                bone.bbone_x = scale_value
                bone.bbone_z = scale_value
    else:
        # Adjust all bones
        for bone in bones:
            bone.bbone_x = scale_value
            bone.bbone_z = scale_value


# ============================================================
# Update callback for camera rotation speed
# ============================================================
def update_camera_rotation_speed(self, context):
    """Update the rotation speed variable for camera empty"""
    # Find camera target empties and update their custom property
    for obj in bpy.data.objects:
        if obj.type == 'EMPTY' and obj.name.endswith("_Camera_Target"):
            if "rotation_speed" in obj:
                obj["rotation_speed"] = self.camera_rotation_speed


# ============================================================
# Property Group
# ============================================================
class ARMATURE_TOOLS_Properties(PropertyGroup):
    bbone_scale: FloatProperty(
        name="B-Bone Scale",
        description="Scale value for bbone_x and bbone_z (updates in real-time)",
        default=0.1,
        min=0.001,
        max=10.0,
        step=1,
        precision=3,
        update=update_bbone_scale,
    )
    
    camera_rotation_speed: FloatProperty(
        name="Rotation Speed",
        description="Camera orbit rotation speed (degrees per frame). Negative = clockwise, Positive = counter-clockwise, 0 = stop",
        default=0.5,
        min=-2.0,
        max=2.0,
        step=1,
        precision=3,
        update=update_camera_rotation_speed,
    )


# ============================================================
# Operator: Quick Setup
# ============================================================
class ARMATURE_TOOLS_OT_quick_setup(Operator):
    """Quick setup: Hide non-armature objects, set B-Bone display with axes, set frame range, and create follow camera"""
    bl_idname = "armature_tools.quick_setup"
    bl_label = "Quick Setup"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        # Allow execution if there's any armature in the scene
        for obj in context.scene.objects:
            if obj.type == 'ARMATURE':
                return True
        return False

    def execute(self, context):
        props = context.scene.armature_tools_props
        
        # 1. Find armature - prefer active object if it's an armature, otherwise find first armature
        armature = None
        
        if context.active_object and context.active_object.type == 'ARMATURE':
            armature = context.active_object
        else:
            # Look for armature in selected objects first
            for obj in context.selected_objects:
                if obj.type == 'ARMATURE':
                    armature = obj
                    break
            
            # If no armature in selection, find any visible armature in scene
            if not armature:
                for obj in context.scene.objects:
                    if obj.type == 'ARMATURE' and obj.visible_get():
                        armature = obj
                        break
        
        if not armature:
            self.report({'ERROR'}, "No armature found in scene")
            return {'CANCELLED'}
        
        # 2. Hide and deselect all non-armature objects
        for obj in context.scene.objects:
            if obj.type != 'ARMATURE':
                obj.hide_set(True)
                obj.select_set(False)
        
        # Make sure armature is visible, selected and active
        armature.hide_set(False)
        armature.select_set(True)
        context.view_layer.objects.active = armature
        
        # 3. Set B-Bone display, show axes, and set B-Bone scale to 0.5
        armature.data.display_type = 'BBONE'
        armature.data.show_axes = True
        
        # Set B-Bone scale to 0.5 for all bones
        for bone in armature.data.bones:
            bone.bbone_x = 0.5
            bone.bbone_z = 0.5
        
        # Update the property to match
        props.bbone_scale = 0.5
        
        # 4. Set frame range from animation
        self.set_frame_range_from_animation(context, armature)
        
        # 5. Create follow camera
        self.create_follow_camera(context, armature, props)
        
        # Make sure armature is the active object at the end
        armature.select_set(True)
        context.view_layer.objects.active = armature
        
        # 6. Deselect all bones to improve timeline playback performance
        # Switch to pose mode temporarily to deselect bones
        current_mode = context.mode
        if current_mode != 'POSE':
            bpy.ops.object.mode_set(mode='POSE')
        
        # Deselect all pose bones
        bpy.ops.pose.select_all(action='DESELECT')
        
        # Return to object mode
        bpy.ops.object.mode_set(mode='OBJECT')
        
        self.report({'INFO'}, f"Quick setup completed for '{armature.name}'!")
        return {'FINISHED'}
    
    def set_frame_range_from_animation(self, context, armature):
        """Set frame range based on animation data"""
        from bpy_extras import anim_utils
        
        earliest_start = float('inf')
        latest_end = float('-inf')
        
        anim_data = armature.animation_data
        if anim_data and anim_data.action:
            action = anim_data.action
            action_slot = anim_data.action_slot
            
            try:
                channelbag = anim_utils.action_get_channelbag_for_slot(action, action_slot)
                if channelbag:
                    for fcurve in channelbag.fcurves:
                        if len(fcurve.keyframe_points) > 0:
                            fcurve_start = fcurve.keyframe_points[0].co[0]
                            fcurve_end = fcurve.keyframe_points[-1].co[0]
                            earliest_start = min(earliest_start, fcurve_start)
                            latest_end = max(latest_end, fcurve_end)
            except Exception:
                pass
        
        # Check NLA tracks
        if anim_data and anim_data.nla_tracks:
            for track in anim_data.nla_tracks:
                for strip in track.strips:
                    earliest_start = min(earliest_start, strip.frame_start)
                    latest_end = max(latest_end, strip.frame_end)
        
        if earliest_start != float('inf') and latest_end != float('-inf'):
            context.scene.frame_start = int(earliest_start)
            context.scene.frame_end = int(latest_end)
    
    def create_follow_camera(self, context, armature, props):
        """Create follow camera setup"""
        # Find the Hips bone
        hips_bone_name = None
        possible_names = ['Hips', 'hips', 'HIPS', 'hip', 'Hip', 'HIP', 
                          'pelvis', 'Pelvis', 'PELVIS', 'root', 'Root', 'ROOT',
                          'mixamorig:Hips', 'mixamorig_Hips']
        
        for name in possible_names:
            if name in armature.data.bones:
                hips_bone_name = name
                break
        
        if not hips_bone_name:
            for bone in armature.data.bones:
                if 'hip' in bone.name.lower():
                    hips_bone_name = bone.name
                    break
        
        if not hips_bone_name:
            return  # Skip camera creation if no hips bone found
        
        # Check if camera already exists
        camera_target_name = f"{armature.name}_Camera_Target"
        camera_name = f"{armature.name}_Follow_Camera"
        
        if camera_target_name in bpy.data.objects or camera_name in bpy.data.objects:
            return  # Camera already exists, skip creation
        
        # Create Empty
        bpy.ops.object.empty_add(type='PLAIN_AXES', location=(0, 0, 0))
        empty = context.active_object
        empty.name = camera_target_name
        empty.empty_display_size = 0.01
        
        # Add custom property for rotation speed
        empty["rotation_speed"] = props.camera_rotation_speed
        id_props = empty.id_properties_ui("rotation_speed")
        id_props.update(
            min=-2.0, max=2.0, soft_min=-2.0, soft_max=2.0, default=0.5,
            description="Camera orbit rotation speed (degrees per frame)"
        )
        
        # Add Copy Location constraint
        constraint = empty.constraints.new(type='COPY_LOCATION')
        constraint.target = armature
        constraint.subtarget = hips_bone_name
        constraint.name = "Follow_Hips"
        
        # Add driver for Z rotation
        driver = empty.driver_add("rotation_euler", 2).driver
        driver.type = 'SCRIPTED'
        
        var_frame = driver.variables.new()
        var_frame.name = "frame"
        var_frame.type = 'SINGLE_PROP'
        var_frame.targets[0].id_type = 'SCENE'
        var_frame.targets[0].id = context.scene
        var_frame.targets[0].data_path = "frame_current"
        
        var_speed = driver.variables.new()
        var_speed.name = "speed"
        var_speed.type = 'SINGLE_PROP'
        var_speed.targets[0].id_type = 'OBJECT'
        var_speed.targets[0].id = empty
        var_speed.targets[0].data_path = '["rotation_speed"]'
        
        driver.expression = "radians(frame * speed)"
        
        # Create Camera
        bpy.ops.object.camera_add(location=(0, -5, 2))
        camera = context.active_object
        camera.name = camera_name
        
        # Parent camera to empty
        camera.parent = empty
        camera.matrix_parent_inverse = empty.matrix_world.inverted()
        
        # Add Track To constraint
        constraint_track = camera.constraints.new(type='TRACK_TO')
        constraint_track.target = empty
        constraint_track.track_axis = 'TRACK_NEGATIVE_Z'
        constraint_track.up_axis = 'UP_Y'
        
        # Set as scene camera and switch to camera view
        context.scene.camera = camera
        
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        space.region_3d.view_perspective = 'CAMERA'
                        space.lock_camera = True
                        break
                break


# ============================================================
# Operator: Set Display Mode to B-Bone and Show Axes
# ============================================================
class ARMATURE_TOOLS_OT_set_bbone_display(Operator):
    """Set the selected Armature's display mode to B-Bone and show bone axes"""
    bl_idname = "armature_tools.set_bbone_display"
    bl_label = "Set B-Bone Display + Axes"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.active_object and context.active_object.type == 'ARMATURE'

    def execute(self, context):
        armature = context.active_object
        armature.data.display_type = 'BBONE'
        armature.data.show_axes = True
        self.report({'INFO'}, f"Set {armature.name} display to B-Bone with Axes")
        return {'FINISHED'}


# ============================================================
# Operator: Create Camera Following Hips
# ============================================================
class ARMATURE_TOOLS_OT_create_follow_camera(Operator):
    """Create an Empty and Camera that follow the Hips bone position"""
    bl_idname = "armature_tools.create_follow_camera"
    bl_label = "Create Follow Camera"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.active_object and context.active_object.type == 'ARMATURE'

    def execute(self, context):
        armature = context.active_object
        props = context.scene.armature_tools_props
        
        # Find the Hips bone (try common naming conventions)
        hips_bone_name = None
        possible_names = ['Hips', 'hips', 'HIPS', 'hip', 'Hip', 'HIP', 
                          'pelvis', 'Pelvis', 'PELVIS', 'root', 'Root', 'ROOT',
                          'mixamorig:Hips', 'mixamorig_Hips']
        
        for name in possible_names:
            if name in armature.data.bones:
                hips_bone_name = name
                break
        
        if not hips_bone_name:
            # If no standard name found, try to find any bone with 'hip' in name
            for bone in armature.data.bones:
                if 'hip' in bone.name.lower():
                    hips_bone_name = bone.name
                    break
        
        if not hips_bone_name:
            self.report({'ERROR'}, "Could not find Hips bone. Please ensure the armature has a bone named 'Hips' or similar")
            return {'CANCELLED'}

        # Create Empty
        bpy.ops.object.empty_add(type='PLAIN_AXES', location=(0, 0, 0))
        empty = context.active_object
        empty.name = f"{armature.name}_Camera_Target"
        empty.empty_display_size = 0.01
        
        # Add custom property for rotation speed with UI settings
        empty["rotation_speed"] = props.camera_rotation_speed
        
        # Set up the ID property UI limits
        id_props = empty.id_properties_ui("rotation_speed")
        id_props.update(
            min=-2.0,
            max=2.0,
            soft_min=-2.0,
            soft_max=2.0,
            default=0.5,
            description="Camera orbit rotation speed (degrees per frame). Negative = clockwise, Positive = counter-clockwise"
        )

        # Add Copy Location constraint to Empty
        constraint = empty.constraints.new(type='COPY_LOCATION')
        constraint.target = armature
        constraint.subtarget = hips_bone_name
        constraint.name = "Follow_Hips"
        
        # Add driver for Z rotation based on frame
        # Expression: radians(frame * rotation_speed)
        driver = empty.driver_add("rotation_euler", 2).driver
        driver.type = 'SCRIPTED'
        
        # Add frame variable
        var_frame = driver.variables.new()
        var_frame.name = "frame"
        var_frame.type = 'SINGLE_PROP'
        var_frame.targets[0].id_type = 'SCENE'
        var_frame.targets[0].id = context.scene
        var_frame.targets[0].data_path = "frame_current"
        
        # Add rotation_speed variable from custom property
        var_speed = driver.variables.new()
        var_speed.name = "speed"
        var_speed.type = 'SINGLE_PROP'
        var_speed.targets[0].id_type = 'OBJECT'
        var_speed.targets[0].id = empty
        var_speed.targets[0].data_path = '["rotation_speed"]'
        
        # Set expression: convert degrees to radians
        driver.expression = "radians(frame * speed)"

        # Create Camera
        bpy.ops.object.camera_add(location=(0, -5, 2))
        camera = context.active_object
        camera.name = f"{armature.name}_Follow_Camera"

        # Parent camera to empty
        camera.parent = empty
        camera.matrix_parent_inverse = empty.matrix_world.inverted()

        # Point camera towards the empty/hips
        constraint_track = camera.constraints.new(type='TRACK_TO')
        constraint_track.target = empty
        constraint_track.track_axis = 'TRACK_NEGATIVE_Z'
        constraint_track.up_axis = 'UP_Y'
        
        # Set the camera as the active scene camera
        context.scene.camera = camera
        
        # Switch view to camera and enable lock camera to view
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        # Switch to camera view
                        space.region_3d.view_perspective = 'CAMERA'
                        # Enable lock camera to view
                        space.lock_camera = True
                        break
                break

        self.report({'INFO'}, f"Created follow camera setup tracking '{hips_bone_name}' bone (Camera view enabled)")
        return {'FINISHED'}


# ============================================================
# Operator: Set Frame Range from Animation
# ============================================================
class ARMATURE_TOOLS_OT_set_frame_range(Operator):
    """Set frame range to match the animation keyframes of selected object/bones"""
    bl_idname = "armature_tools.set_frame_range"
    bl_label = "Set Frame Range from Animation"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.active_object and context.active_object.type == 'ARMATURE'

    def execute(self, context):
        armature = context.active_object
        
        # Track the earliest start frame and latest end frame
        earliest_start = float('inf')
        latest_end = float('-inf')
        
        # Get selected bones if any
        selected_bone_names = []
        if context.mode == 'POSE' and context.selected_pose_bones:
            selected_bone_names = [bone.name for bone in context.selected_pose_bones]
        
        # Check if armature has animation data
        anim_data = armature.animation_data
        if anim_data and anim_data.action:
            action = anim_data.action
            action_slot = anim_data.action_slot
            
            # Blender 5.0: Use channelbag to access fcurves
            try:
                channelbag = anim_utils.action_get_channelbag_for_slot(action, action_slot)
                if channelbag:
                    for fcurve in channelbag.fcurves:
                        # If bones are selected, only consider their fcurves
                        if selected_bone_names:
                            # Check if this fcurve belongs to a selected bone
                            # FCurve data_path format: pose.bones["BoneName"].location/rotation/scale
                            bone_match = False
                            for bone_name in selected_bone_names:
                                if f'pose.bones["{bone_name}"]' in fcurve.data_path:
                                    bone_match = True
                                    break
                            if not bone_match:
                                continue
                        
                        # Get the frame range for this fcurve
                        if len(fcurve.keyframe_points) > 0:
                            # Get first and last keyframe of this fcurve
                            fcurve_start = fcurve.keyframe_points[0].co[0]
                            fcurve_end = fcurve.keyframe_points[-1].co[0]
                            
                            # Update earliest start and latest end
                            earliest_start = min(earliest_start, fcurve_start)
                            latest_end = max(latest_end, fcurve_end)
                            
            except Exception as e:
                self.report({'WARNING'}, f"Error accessing fcurves: {str(e)}")
        
        # Also check NLA tracks
        if anim_data and anim_data.nla_tracks:
            for track in anim_data.nla_tracks:
                for strip in track.strips:
                    earliest_start = min(earliest_start, strip.frame_start)
                    latest_end = max(latest_end, strip.frame_end)
        
        if earliest_start == float('inf') or latest_end == float('-inf'):
            self.report({'WARNING'}, "No animation keyframes found")
            return {'CANCELLED'}
        
        # Set frame range using the earliest start and latest end
        context.scene.frame_start = int(earliest_start)
        context.scene.frame_end = int(latest_end)
        
        if selected_bone_names:
            self.report({'INFO'}, f"Frame range set to {int(earliest_start)} - {int(latest_end)} (from selected bones)")
        else:
            self.report({'INFO'}, f"Frame range set to {int(earliest_start)} - {int(latest_end)}")
        
        return {'FINISHED'}


# ============================================================
# Operator: Toggle Track To Constraint
# ============================================================
class ARMATURE_TOOLS_OT_toggle_track_to(Operator):
    """Toggle Track To constraint influence between 0 and 1"""
    bl_idname = "armature_tools.toggle_track_to"
    bl_label = "Toggle Track To"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        if not context.active_object or context.active_object.type != 'ARMATURE':
            return False
        armature = context.active_object
        camera_name = f"{armature.name}_Follow_Camera"
        return camera_name in bpy.data.objects

    def execute(self, context):
        armature = context.active_object
        camera_name = f"{armature.name}_Follow_Camera"
        camera_obj = bpy.data.objects[camera_name]
        
        # Find the Track To constraint
        for constraint in camera_obj.constraints:
            if constraint.type == 'TRACK_TO':
                # Toggle influence between 0 and 1
                if constraint.influence > 0.5:
                    constraint.influence = 0.0
                    self.report({'INFO'}, "Track To disabled - Camera can be rotated freely")
                else:
                    constraint.influence = 1.0
                    self.report({'INFO'}, "Track To enabled - Camera tracks target")
                return {'FINISHED'}
        
        self.report({'WARNING'}, "Track To constraint not found")
        return {'CANCELLED'}


# ============================================================
# Operator: Toggle Lock Camera to View
# ============================================================
class ARMATURE_TOOLS_OT_toggle_lock_camera(Operator):
    """Toggle Lock Camera to View"""
    bl_idname = "armature_tools.toggle_lock_camera"
    bl_label = "Toggle Lock Camera to View"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        space.lock_camera = not space.lock_camera
                        status = "enabled" if space.lock_camera else "disabled"
                        self.report({'INFO'}, f"Lock Camera to View {status}")
                        return {'FINISHED'}
        
        self.report({'WARNING'}, "Could not find 3D View")
        return {'CANCELLED'}


# ============================================================
# Panel
# ============================================================
class ARMATURE_TOOLS_PT_main_panel(Panel):
    """Armature Tools Panel"""
    bl_label = "Armature Tools"
    bl_idname = "ARMATURE_TOOLS_PT_main_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Armature Tools"

    @classmethod
    def poll(cls, context):
        # Show panel if active object is armature OR if there's any armature in scene
        if context.active_object and context.active_object.type == 'ARMATURE':
            return True
        for obj in context.scene.objects:
            if obj.type == 'ARMATURE':
                return True
        return False

    def draw(self, context):
        layout = self.layout
        props = context.scene.armature_tools_props
        armature = context.active_object if context.active_object and context.active_object.type == 'ARMATURE' else None

        # Quick Setup Section (always shown at the top)
        box = layout.box()
        box.label(text="Quick Setup", icon='PLAY')
        row = box.row()
        row.scale_y = 1.5
        row.operator("armature_tools.quick_setup", icon='AUTO')
        
        # If no armature is active, show a hint and stop here
        if not armature:
            layout.separator()
            layout.label(text="Select an Armature to see more options", icon='INFO')
            return

        layout.separator()

        # Display info
        layout.label(text=f"Armature: {armature.name}")
        layout.separator()

        # Display Mode Section
        box = layout.box()
        box.label(text="Display Mode", icon='BONE_DATA')
        
        # Quick set B-Bone + Axes button
        row = box.row()
        row.operator("armature_tools.set_bbone_display", icon='IPO_BEZIER')
        
        # Display As dropdown
        row = box.row()
        row.prop(armature.data, "display_type", text="Display As")
        
        # Show Names checkbox
        row = box.row()
        row.prop(armature.data, "show_names", text="Show Names")
        
        # Show Axes checkbox
        row = box.row()
        row.prop(armature.data, "show_axes", text="Show Axes")
        
        # Axes Position (only show if axes are enabled)
        if armature.data.show_axes:
            row = box.row()
            row.prop(armature.data, "axes_position", text="Axes Position", slider=True)

        layout.separator()

        # B-Bone Scale Section
        box = layout.box()
        box.label(text="B-Bone Scale (Real-time)", icon='CON_SIZELIMIT')
        box.prop(props, "bbone_scale", slider=True)
        
        # Show info about what will be affected
        selected_count = 0
        if context.mode == 'POSE' and context.selected_pose_bones:
            selected_count = len(context.selected_pose_bones)
        elif context.mode == 'EDIT_ARMATURE' and context.selected_bones:
            selected_count = len(context.selected_bones)
        
        if selected_count > 0:
            box.label(text=f"Affecting: {selected_count} selected bone(s)")
        else:
            box.label(text=f"Affecting: All {len(armature.data.bones)} bones")

        layout.separator()

        # Camera Follow Section
        box = layout.box()
        box.label(text="Camera Setup", icon='CAMERA_DATA')
        box.operator("armature_tools.create_follow_camera", icon='CON_LOCLIKE')
        
        # Find existing camera target empty and show its rotation speed
        camera_target_name = f"{armature.name}_Camera_Target"
        camera_name = f"{armature.name}_Follow_Camera"
        
        if camera_target_name in bpy.data.objects:
            camera_target = bpy.data.objects[camera_target_name]
            if "rotation_speed" in camera_target:
                box.prop(camera_target, '["rotation_speed"]', text="Rotation Speed", slider=True)
        else:
            # Show the property for setting default value before creating
            box.prop(props, "camera_rotation_speed", text="Rotation Speed (default)", slider=True)
        
        # Track To influence toggle
        if camera_name in bpy.data.objects:
            camera_obj = bpy.data.objects[camera_name]
            # Find the Track To constraint
            for constraint in camera_obj.constraints:
                if constraint.type == 'TRACK_TO':
                    row = box.row()
                    # Create a toggle that sets influence to 0 or 1
                    icon = 'CHECKBOX_HLT' if constraint.influence > 0.5 else 'CHECKBOX_DEHLT'
                    row.operator("armature_tools.toggle_track_to", text="Track To Target", icon=icon)
                    break
        
        # Lock Camera to View toggle button
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        row = box.row()
                        icon = 'CHECKBOX_HLT' if space.lock_camera else 'CHECKBOX_DEHLT'
                        row.operator("armature_tools.toggle_lock_camera", text="Lock Camera to View", icon=icon)
                        break
                break

        layout.separator()

        # Frame Range Section
        box = layout.box()
        box.label(text="Frame Range", icon='TIME')
        
        # Show current frame range
        row = box.row()
        row.label(text=f"Current: {context.scene.frame_start} - {context.scene.frame_end}")
        
        box.operator("armature_tools.set_frame_range", icon='PREVIEW_RANGE')


# ============================================================
# Registration
# ============================================================
classes = (
    ARMATURE_TOOLS_Properties,
    ARMATURE_TOOLS_OT_quick_setup,
    ARMATURE_TOOLS_OT_set_bbone_display,
    ARMATURE_TOOLS_OT_create_follow_camera,
    ARMATURE_TOOLS_OT_toggle_track_to,
    ARMATURE_TOOLS_OT_toggle_lock_camera,
    ARMATURE_TOOLS_OT_set_frame_range,
    ARMATURE_TOOLS_PT_main_panel,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.armature_tools_props = PointerProperty(type=ARMATURE_TOOLS_Properties)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.armature_tools_props


if __name__ == "__main__":
    register()
