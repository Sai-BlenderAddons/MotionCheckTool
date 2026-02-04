import bpy
from bpy.types import Operator
from bpy_extras import anim_utils


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
# Operator: Create Fake Bones from Armature
# ============================================================
class ARMATURE_TOOLS_OT_create_fake_bones(Operator):
    """Create curve objects that mimic bones, constrained to follow the armature"""
    bl_idname = "armature_tools.create_fake_bones"
    bl_label = "Create Fake Bones"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.active_object and context.active_object.type == 'ARMATURE'

    def execute(self, context):
        armature = context.active_object
        props = context.scene.armature_tools_props
        
        # Create or get the collection for fake bones
        collection_name = f"{armature.name}_FakeBones"
        if collection_name in bpy.data.collections:
            fake_bone_collection = bpy.data.collections[collection_name]
            # Clear existing fake bones
            for obj in list(fake_bone_collection.objects):
                bpy.data.objects.remove(obj, do_unlink=True)
        else:
            fake_bone_collection = bpy.data.collections.new(collection_name)
            context.scene.collection.children.link(fake_bone_collection)
        
        # Store created curves for later reference
        created_curves = []
        
        # Iterate through all bones
        for bone in armature.data.bones:
            # Create curve data
            curve_data = bpy.data.curves.new(name=f"FakeBone_{bone.name}", type='CURVE')
            curve_data.dimensions = '3D'
            curve_data.bevel_depth = props.fake_bone_depth
            curve_data.bevel_resolution = 4
            curve_data.fill_mode = 'FULL'
            
            # Create a spline
            spline = curve_data.splines.new('POLY')
            spline.points.add(1)  # Add one more point (starts with 1)
            
            # Set point positions
            # First point at origin (0, 0, 0)
            spline.points[0].co = (0, 0, 0, 1)
            # Second point at (0, bone_length, 0) - along Y axis
            bone_length = bone.length
            spline.points[1].co = (0, bone_length, 0, 1)
            
            # Create curve object
            curve_obj = bpy.data.objects.new(f"FakeBone_{bone.name}", curve_data)
            
            # Link to collection
            fake_bone_collection.objects.link(curve_obj)
            
            # Add Child Of constraint
            constraint = curve_obj.constraints.new(type='CHILD_OF')
            constraint.target = armature
            constraint.subtarget = bone.name
            constraint.name = f"Follow_{bone.name}"
            
            # Set inverse matrix to align properly
            # We need to set the inverse so the curve follows the bone correctly
            constraint.set_inverse_pending = True
            
            created_curves.append(curve_obj)
        
        # Update view layer to apply constraints
        context.view_layer.update()
        
        # Clear inverse for all constraints (makes them follow bone transform directly)
        for curve_obj in created_curves:
            for constraint in curve_obj.constraints:
                if constraint.type == 'CHILD_OF':
                    # Calculate and set the inverse matrix
                    context.view_layer.objects.active = curve_obj
                    with context.temp_override(object=curve_obj, selected_objects=[curve_obj]):
                        bpy.ops.constraint.childof_clear_inverse(constraint=constraint.name, owner='OBJECT')
        
        # Restore active object to armature
        context.view_layer.objects.active = armature
        armature.select_set(True)
        
        self.report({'INFO'}, f"Created {len(created_curves)} fake bones in collection '{collection_name}'")
        return {'FINISHED'}


# ============================================================
# Operator: Mark Rotation Anomalies
# ============================================================
class ARMATURE_TOOLS_OT_mark_acceleration_keyframes(Operator):
    """Detect and mark frames where bone rotation exceeds threshold per axis (X=R, Y=G, Z=B)"""
    bl_idname = "armature_tools.mark_acceleration_keyframes"
    bl_label = "Detect Rotation Anomalies"
    bl_options = {'REGISTER', 'UNDO'}
    
    selected_only: bpy.props.BoolProperty(
        name="Selected Only",
        description="Only process selected curve objects",
        default=False,
    )

    @classmethod
    def poll(cls, context):
        # Check if there's an armature in scene and fake bones exist
        for obj in context.scene.objects:
            if obj.type == 'ARMATURE':
                collection_name = f"{obj.name}_FakeBones"
                if collection_name in bpy.data.collections:
                    return True
        return False

    def get_bone_euler_from_fcurves(self, armature, bone_name, frame):
        """Get bone rotation as Euler angles from FCurves at a specific frame"""
        from mathutils import Quaternion, Euler
        import math
        
        anim_data = armature.animation_data
        if not anim_data or not anim_data.action:
            return None
        
        action = anim_data.action
        action_slot = anim_data.action_slot
        
        try:
            from bpy_extras import anim_utils
            channelbag = anim_utils.action_get_channelbag_for_slot(action, action_slot)
            if not channelbag:
                return None
        except Exception:
            return None
        
        # Look for rotation fcurves for this bone
        quat_values = [None, None, None, None]
        euler_values = [None, None, None]
        
        base_path = f'pose.bones["{bone_name}"]'
        
        for fcurve in channelbag.fcurves:
            if base_path not in fcurve.data_path:
                continue
            
            if "rotation_quaternion" in fcurve.data_path:
                idx = fcurve.array_index
                if 0 <= idx <= 3:
                    quat_values[idx] = fcurve.evaluate(frame)
            
            elif "rotation_euler" in fcurve.data_path:
                idx = fcurve.array_index
                if 0 <= idx <= 2:
                    euler_values[idx] = fcurve.evaluate(frame)
        
        # Return euler directly if available
        if all(v is not None for v in euler_values):
            return Euler(euler_values)
        
        # Convert quaternion to euler if available
        if all(v is not None for v in quat_values):
            quat = Quaternion(quat_values)
            return quat.to_euler()
        
        return None

    def calculate_axis_rotation_diff(self, euler1, euler2):
        """Calculate the rotation difference per axis in degrees"""
        import math
        
        if euler1 is None or euler2 is None:
            return (0.0, 0.0, 0.0)
        
        # Calculate difference per axis (in radians), then convert to degrees
        diff_x = abs(math.degrees(euler2.x - euler1.x))
        diff_y = abs(math.degrees(euler2.y - euler1.y))
        diff_z = abs(math.degrees(euler2.z - euler1.z))
        
        # Handle angle wrapping (if difference > 180, take the shorter path)
        if diff_x > 180:
            diff_x = 360 - diff_x
        if diff_y > 180:
            diff_y = 360 - diff_y
        if diff_z > 180:
            diff_z = 360 - diff_z
        
        return (diff_x, diff_y, diff_z)

    def execute(self, context):
        props = context.scene.armature_tools_props
        threshold_x = props.rotation_threshold_x
        threshold_y = props.rotation_threshold_y
        threshold_z = props.rotation_threshold_z
        
        # Find armature and its fake bones collection
        armature = None
        fake_bone_collection = None
        
        # If active object is armature, use it
        if context.active_object and context.active_object.type == 'ARMATURE':
            armature = context.active_object
            collection_name = f"{armature.name}_FakeBones"
            if collection_name in bpy.data.collections:
                fake_bone_collection = bpy.data.collections[collection_name]
        
        # If active object is a curve in a fake bones collection
        if not armature and context.active_object and context.active_object.type == 'CURVE':
            for collection in context.active_object.users_collection:
                if collection.name.endswith("_FakeBones"):
                    fake_bone_collection = collection
                    armature_name = collection.name.replace("_FakeBones", "")
                    if armature_name in bpy.data.objects:
                        armature = bpy.data.objects[armature_name]
                    break
        
        # Fallback: find any armature with fake bones
        if not armature:
            for obj in context.scene.objects:
                if obj.type == 'ARMATURE':
                    collection_name = f"{obj.name}_FakeBones"
                    if collection_name in bpy.data.collections:
                        armature = obj
                        fake_bone_collection = bpy.data.collections[collection_name]
                        break
        
        if not armature or not fake_bone_collection:
            self.report({'ERROR'}, "No armature with fake bones found")
            return {'CANCELLED'}
        
        # Get frame range
        frame_start = context.scene.frame_start
        frame_end = context.scene.frame_end
        
        # Determine which curves to process
        curves_to_process = []
        
        if self.selected_only:
            # Only selected curves
            for obj in context.selected_objects:
                if obj.type == 'CURVE' and obj in fake_bone_collection.objects.values():
                    curves_to_process.append(obj)
        else:
            # All curves in the collection
            for obj in fake_bone_collection.objects:
                if obj.type == 'CURVE':
                    curves_to_process.append(obj)
        
        if not curves_to_process:
            self.report({'WARNING'}, "No curves to process")
            return {'CANCELLED'}
        
        total_anomalies = [0, 0, 0]  # X, Y, Z counts
        processed_count = 0
        
        for curve_obj in curves_to_process:
            # Find the associated bone name from constraint
            bone_name = None
            for constraint in curve_obj.constraints:
                if constraint.type == 'CHILD_OF' and constraint.target == armature:
                    bone_name = constraint.subtarget
                    break
            
            if not bone_name:
                continue
            
            # Get rotations from FCurves directly (fast!)
            # Separate anomaly frames for each axis
            anomaly_frames_x = []  # X axis -> R channel
            anomaly_frames_y = []  # Y axis -> G channel
            anomaly_frames_z = []  # Z axis -> B channel
            
            prev_euler = None
            
            for frame in range(frame_start, frame_end + 1):
                curr_euler = self.get_bone_euler_from_fcurves(armature, bone_name, frame)
                
                if prev_euler is not None and curr_euler is not None:
                    diff_x, diff_y, diff_z = self.calculate_axis_rotation_diff(prev_euler, curr_euler)
                    
                    if diff_x > threshold_x:
                        anomaly_frames_x.append(frame)
                    if diff_y > threshold_y:
                        anomaly_frames_y.append(frame)
                    if diff_z > threshold_z:
                        anomaly_frames_z.append(frame)
                
                prev_euler = curr_euler
            
            # Clear existing color keyframes on this curve BEFORE setting new ones
            if curve_obj.animation_data and curve_obj.animation_data.action:
                action = curve_obj.animation_data.action
                action_slot = curve_obj.animation_data.action_slot
                try:
                    from bpy_extras import anim_utils
                    channelbag = anim_utils.action_get_channelbag_for_slot(action, action_slot)
                    if channelbag:
                        # Remove all color fcurves (R, G, B, A)
                        fcurves_to_remove = []
                        for fcurve in channelbag.fcurves:
                            if fcurve.data_path == "color":
                                fcurves_to_remove.append(fcurve)
                        for fcurve in fcurves_to_remove:
                            channelbag.fcurves.remove(fcurve)
                except Exception:
                    pass
            
            # Ensure animation data exists for new keyframes
            if not curve_obj.animation_data:
                curve_obj.animation_data_create()
            
            # Set curve base color (all 0 is normal)
            curve_obj.color = (0.0, 0.0, 0.0, 1.0)
            
            # Process each axis/channel
            axis_data = [
                (anomaly_frames_x, 0),  # X -> R (index 0)
                (anomaly_frames_y, 1),  # Y -> G (index 1)
                (anomaly_frames_z, 2),  # Z -> B (index 2)
            ]
            
            for anomaly_frames, channel_index in axis_data:
                # Set initial keyframe at frame_start with value=0
                curve_obj.color[channel_index] = 0.0
                curve_obj.keyframe_insert(data_path="color", index=channel_index, frame=frame_start)
                
                if anomaly_frames:
                    # Build a dict of frames that need keyframes
                    frames_to_key = {}
                    
                    for frame in anomaly_frames:
                        # Set value=1 for anomaly frame
                        frames_to_key[frame] = 1.0
                        
                        # Set value=0 two frames before (if not already keyed and within range)
                        frame_before = frame - 2
                        if frame_before >= frame_start and frame_before not in frames_to_key:
                            frames_to_key[frame_before] = 0.0
                        
                        # Set value=0 two frames after (if not already keyed and within range)
                        frame_after = frame + 2
                        if frame_after <= frame_end and frame_after not in frames_to_key:
                            frames_to_key[frame_after] = 0.0
                    
                    # Insert keyframes for this channel
                    for frame, value in sorted(frames_to_key.items()):
                        curve_obj.color[channel_index] = value
                        curve_obj.keyframe_insert(data_path="color", index=channel_index, frame=frame)
                    
                    total_anomalies[channel_index] += len(anomaly_frames)
            
            # Set all color keyframes to CONSTANT interpolation
            if curve_obj.animation_data and curve_obj.animation_data.action:
                action = curve_obj.animation_data.action
                action_slot = curve_obj.animation_data.action_slot
                try:
                    from bpy_extras import anim_utils
                    channelbag = anim_utils.action_get_channelbag_for_slot(action, action_slot)
                    if channelbag:
                        for fcurve in channelbag.fcurves:
                            if fcurve.data_path == "color" and fcurve.array_index in (0, 1, 2):
                                for keyframe in fcurve.keyframe_points:
                                    keyframe.interpolation = 'CONSTANT'
                except Exception:
                    pass
            
            processed_count += 1
        
        self.report({'INFO'}, f"Processed {processed_count} curves. Anomalies - X(R):{total_anomalies[0]}, Y(G):{total_anomalies[1]}, Z(B):{total_anomalies[2]}")
        return {'FINISHED'}


# ============================================================
# Operator classes list for registration
# ============================================================
operator_classes = (
    ARMATURE_TOOLS_OT_quick_setup,
    ARMATURE_TOOLS_OT_set_bbone_display,
    ARMATURE_TOOLS_OT_create_follow_camera,
    ARMATURE_TOOLS_OT_set_frame_range,
    ARMATURE_TOOLS_OT_toggle_track_to,
    ARMATURE_TOOLS_OT_toggle_lock_camera,
    ARMATURE_TOOLS_OT_create_fake_bones,
    ARMATURE_TOOLS_OT_mark_acceleration_keyframes,
)
