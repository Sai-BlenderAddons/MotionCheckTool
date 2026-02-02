import bpy
from bpy.props import PointerProperty

from . import properties
from . import operators
from . import ui


# ============================================================
# Registration
# ============================================================
def register():
    # Register property group
    bpy.utils.register_class(properties.ARMATURE_TOOLS_Properties)
    
    # Register operators
    for cls in operators.operator_classes:
        bpy.utils.register_class(cls)
    
    # Register panels
    for cls in ui.panel_classes:
        bpy.utils.register_class(cls)
    
    # Register scene property
    bpy.types.Scene.armature_tools_props = PointerProperty(type=properties.ARMATURE_TOOLS_Properties)


def unregister():
    # Unregister scene property
    del bpy.types.Scene.armature_tools_props
    
    # Unregister panels
    for cls in reversed(ui.panel_classes):
        bpy.utils.unregister_class(cls)
    
    # Unregister operators
    for cls in reversed(operators.operator_classes):
        bpy.utils.unregister_class(cls)
    
    # Unregister property group
    bpy.utils.unregister_class(properties.ARMATURE_TOOLS_Properties)


if __name__ == "__main__":
    register()
