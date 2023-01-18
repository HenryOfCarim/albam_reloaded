from . blender import *

try:
    import bpy
except ImportError:
    pass

from . engines.mtframework.blender_import import *
from . engines.mtframework.blender_export import *
from . registry import *


bl_info = {
    "name": "Albam Reloaded",
    "author": "Sebastian Brachi",
    "version": (0, 3, 6),
    "blender": (2, 80, 0),
    "location": "Properties Panel",
    "description": "Import-Export multiple video-game formats",
    "wiki_url": "https://github.com/HenryOfCarim/albam_reloaded/wiki",
    "tracker_url": "https://github.com/HenryOfCarim/albam_reloaded/issues",
    "category": "Import-Export"}


classes = ( AlbamImportedItem,
            AlbamImportedItemName,
            AlbamExportSettings,
            ALBAM_PT_CustomTextureOptions,
            AlbamExportOperator,
            ALBAM_PT_ImportExportPanel,
            ALBAM_PT_ToolsPanel,
            ALBAM_PT_CustomMaterialOptions,
            ALBAM_PT_CustomMeshOptions,
            AlbamImportOperator,
            AlbamFixLeakedTexuresOperator,
            AlbamSelectInvalidMeshesOperator,
            AlbamRemoveEmptyVertexGroupsOperator,
            AlbamTransferNormalsOperator,
           )

def register():

    for prop_name, prop_cls_name, default in blender_registry.bpy_props.get('material', []):
        prop_cls = getattr(bpy.props, prop_cls_name)
        kwargs = {}
        if default:
            kwargs['default'] = default
        prop_instance = prop_cls(**kwargs)
        setattr(bpy.types.Material, prop_name, prop_instance)

    # Setting custom texture properties
    for prop_name, prop_cls_name, default in blender_registry.bpy_props.get('texture', []):
        prop_cls = getattr(bpy.props, prop_cls_name)
        kwargs = {}
        if default:
            kwargs['default'] = default
        prop_instance = prop_cls(**kwargs)
        setattr(bpy.types.Texture, prop_name, prop_instance)

    # Setting custom mesh properties
    for prop_name, prop_cls_name, default in blender_registry.bpy_props.get('mesh', []):
        prop_cls = getattr(bpy.props, prop_cls_name)
        kwargs = {}
        if default:
            kwargs['default'] = default
        prop_instance = prop_cls(**kwargs)
        setattr(bpy.types.Mesh, prop_name, prop_instance)
    
    ''' Classic blender 2.80 registration of classes'''
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)
    bpy.types.Scene.albam_item_to_export = bpy.props.StringProperty()
    bpy.types.Scene.albam_items_imported = bpy.props.CollectionProperty(type=blender.AlbamImportedItemName) # register name property for scene
    bpy.types.Object.albam_imported_item = bpy.props.PointerProperty(type=blender.AlbamImportedItem) # register new object properties
    bpy.types.Scene.albam_export_settings = bpy.props.PointerProperty(type=blender.AlbamExportSettings)
    bpy.types.Scene.albam_scene_meshes = bpy.props.PointerProperty(type=bpy.types.Object)

def unregister():
    ''' Classic blender 2.80 unregistration of classes'''
    from bpy.utils import unregister_class
    for cls in reversed(classes):
         unregister_class(cls)
    
    del bpy.types.Scene.albam_item_to_export 
    del bpy.types.Scene.albam_items_imported
    del bpy.types.Object.albam_imported_item
    del bpy.types.Scene.albam_export_settings
    del bpy.types.Scene.albam_scene_meshes

if __name__ == "__main__":
    register()
