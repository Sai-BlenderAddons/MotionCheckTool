import bpy
from bpy.types import Panel


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
        self.draw_quick_setup(layout)
        
        # If no armature is active, show a hint and stop here
        if not armature:
            layout.separator()
            layout.label(text="Select an Armature to see more options", icon='INFO')
            return

        layout.separator()

        # Display info
        layout.label(text=f"Armature: {armature.name}")
        layout.separator()

        # Draw all sections
        self.draw_display_mode(layout, armature)
        layout.separator()
        self.draw_bbone_scale(layout, context, props, armature)
        layout.separator()
        self.draw_camera_setup(layout, context, props, armature)
        layout.separator()
        self.draw_frame_range(layout, context)

    def draw_quick_setup(self, layout):
        """Draw Quick Setup section"""
        box = layout.box()
        box.label(text="Quick Setup", icon='PLAY')
        row = box.row()
        row.scale_y = 1.5
        row.operator("armature_tools.quick_setup", icon='AUTO')

    def draw_display_mode(self, layout, armature):
        """Draw Display Mode section"""
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

    def draw_bbone_scale(self, layout, context, props, armature):
        """Draw B-Bone Scale section"""
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

    def draw_camera_setup(self, layout, context, props, armature):
        """Draw Camera Setup section"""
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

    def draw_frame_range(self, layout, context):
        """Draw Frame Range section"""
        box = layout.box()
        box.label(text="Frame Range", icon='TIME')
        
        # Show current frame range
        row = box.row()
        row.label(text=f"Current: {context.scene.frame_start} - {context.scene.frame_end}")
        
        box.operator("armature_tools.set_frame_range", icon='PREVIEW_RANGE')


# ============================================================
# Fake Bone Panel
# ============================================================
class ARMATURE_TOOLS_PT_fake_bone_panel(Panel):
    """Fake Bone Panel"""
    bl_label = "Fake Bone"
    bl_idname = "ARMATURE_TOOLS_PT_fake_bone_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Armature Tools"

    def draw(self, context):
        layout = self.layout
        props = context.scene.armature_tools_props
        armature = context.active_object if context.active_object and context.active_object.type == 'ARMATURE' else None
        
        # Create Fake Bones button
        box = layout.box()
        box.label(text="Create", icon='BONE_DATA')
        row = box.row()
        row.enabled = armature is not None
        row.operator("armature_tools.create_fake_bones", icon='ADD')
        
        if not armature:
            box.label(text="Select an Armature to create", icon='INFO')
        
        # Find any fake bones collection
        fake_bone_collection = None
        related_armature = None
        
        # Check if active object is an armature
        if armature:
            collection_name = f"{armature.name}_FakeBones"
            if collection_name in bpy.data.collections:
                fake_bone_collection = bpy.data.collections[collection_name]
                related_armature = armature
        
        # Or check if active object is a curve in a fake bones collection
        if not fake_bone_collection and context.active_object and context.active_object.type == 'CURVE':
            for collection in context.active_object.users_collection:
                if collection.name.endswith("_FakeBones"):
                    fake_bone_collection = collection
                    armature_name = collection.name.replace("_FakeBones", "")
                    if armature_name in bpy.data.objects:
                        related_armature = bpy.data.objects[armature_name]
                    break
        
        # Fallback: find any fake bones collection in scene
        if not fake_bone_collection:
            for obj in context.scene.objects:
                if obj.type == 'ARMATURE':
                    collection_name = f"{obj.name}_FakeBones"
                    if collection_name in bpy.data.collections:
                        fake_bone_collection = bpy.data.collections[collection_name]
                        related_armature = obj
                        break
        
        layout.separator()
        
        # Settings section
        box = layout.box()
        box.label(text="Settings", icon='PREFERENCES')
        
        if fake_bone_collection:
            curve_count = sum(1 for obj in fake_bone_collection.objects if obj.type == 'CURVE')
            box.label(text=f"Collection: {fake_bone_collection.name}")
            box.label(text=f"Fake Bones: {curve_count}")
            
            # Bevel Depth slider (real-time update)
            box.prop(props, "fake_bone_depth", slider=True)
        else:
            box.label(text="No fake bones created yet", icon='INFO')
        
        layout.separator()
        
        # Rotation Anomaly Detection section
        box = layout.box()
        box.label(text="Rotation Anomaly Detection", icon='ERROR')
        
        # Threshold parameters for each axis
        col = box.column(align=True)
        col.label(text="Max Rotation/Frame (°):")
        row = col.row(align=True)
        row.prop(props, "rotation_threshold_x", text="X(R)")
        row.prop(props, "rotation_threshold_y", text="Y(G)")
        row.prop(props, "rotation_threshold_z", text="Z(B)")
        
        # Check if we can run the analysis
        can_analyze = fake_bone_collection is not None
        
        # Mark keyframes buttons
        col = box.column(align=True)
        
        # Button for selected curves only
        row = col.row()
        row.enabled = can_analyze
        op = row.operator("armature_tools.mark_acceleration_keyframes", text="Detect Selected", icon='RESTRICT_SELECT_OFF')
        op.selected_only = True
        
        # Button for all curves
        row = col.row()
        row.enabled = can_analyze
        op = row.operator("armature_tools.mark_acceleration_keyframes", text="Detect All", icon='GROUP_BONE')
        op.selected_only = False
        
        if not can_analyze:
            box.label(text="Create fake bones first", icon='INFO')


# ============================================================
# Panel classes list for registration
# ============================================================
panel_classes = (
    ARMATURE_TOOLS_PT_main_panel,
    ARMATURE_TOOLS_PT_fake_bone_panel,
)
