import bpy
from bpy.types import PropertyGroup
from bpy.props import FloatProperty


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
# Update callback for fake bone depth
# ============================================================
def update_fake_bone_depth(self, context):
    """Update the bevel depth for all fake bone curves in real-time"""
    if not context.active_object or context.active_object.type != 'ARMATURE':
        return
    
    armature = context.active_object
    collection_name = f"{armature.name}_FakeBones"
    
    if collection_name not in bpy.data.collections:
        return
    
    fake_bone_collection = bpy.data.collections[collection_name]
    depth_value = self.fake_bone_depth
    
    for obj in fake_bone_collection.objects:
        if obj.type == 'CURVE':
            obj.data.bevel_depth = depth_value


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
    
    fake_bone_depth: FloatProperty(
        name="Bevel Depth",
        description="Bevel depth for fake bone curves (updates in real-time)",
        default=1.0,
        min=0.01,
        max=10.0,
        step=10,
        precision=3,
        update=update_fake_bone_depth,
    )
    
    rotation_threshold_x: FloatProperty(
        name="X Threshold",
        description="Maximum allowed X-axis rotation per frame (degrees). Exceeding this marks R channel",
        default=8.0,
        min=1.0,
        max=180.0,
        step=100,
        precision=1,
    )
    
    rotation_threshold_y: FloatProperty(
        name="Y Threshold",
        description="Maximum allowed Y-axis rotation per frame (degrees). Exceeding this marks G channel",
        default=8.0,
        min=1.0,
        max=180.0,
        step=100,
        precision=1,
    )
    
    rotation_threshold_z: FloatProperty(
        name="Z Threshold",
        description="Maximum allowed Z-axis rotation per frame (degrees). Exceeding this marks B channel",
        default=8.0,
        min=1.0,
        max=180.0,
        step=100,
        precision=1,
    )
