from . blender import *

try:
    import bpy
except ImportError:
    pass

from . engines.mtframework.blender_import import *
from . engines.mtframework.blender_export import *
#from . registry import blender_registry
from . registry import *
from . import auto_load
auto_load.init()

bl_info = {
    "name": "Albam Reloaded",
    "author": "Sebastian Brachi",
    "version": (0, 3, 1),
    "blender": (2, 80, 0),
    "location": "Properties Panel",
    "description": "Import-Export multiple video-game formats",
    #"wiki_url": "https://github.com/Brachi/albam",
    #"tracker_url": "https://github.com/Brachi/albam/issues",
    "category": "Import-Export"}


classes = ( AlbamImportedItemName,
            AlbamImportedItem,
            CustomMaterialOptions,
            CustomTextureOptions,
            CustomMeshOptions,
            AlbamImportExportPanel,
            AlbamImportOperator,
            AlbamExportOperator,
           )

def register():

    for prop_name, prop_cls_name, default in blender_registry.bpy_props.get('material', []):
        prop_cls = getattr(bpy.props, prop_cls_name)
        #print("test")
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
    
    #bpy.utils.register_module(__name__) #register modules # deprecated
    auto_load.register()
    ''' Classic blender 2.80 registration of classes
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)'''
    bpy.types.Scene.albam_item_to_export = bpy.props.StringProperty()
    bpy.types.Scene.albam_items_imported = bpy.props.CollectionProperty(type=blender.AlbamImportedItemName) # register name property for scene
    bpy.types.Object.albam_imported_item = bpy.props.PointerProperty(type=blender.AlbamImportedItem) # register new object properties

def unregister():
    ''' Classic blender 2.80 unregistration of classes
    from bpy.utils import unregister_class
    for cls in reversed(classes):
         unregister_class(cls)'''
    bpy.types.Scene.albam_item_to_export = bpy.props.StringProperty()
    bpy.types.Scene.albam_items_imported = bpy.props.CollectionProperty(type=blender.AlbamImportedItemName)
    bpy.types.Object.albam_imported_item = bpy.props.PointerProperty(type=blender.AlbamImportedItem)
    auto_load.unregister()

if __name__ == "__main__":
    register()