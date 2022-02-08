# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTIBILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

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
    "name": "Albam",
    "author": "Sebastian Brachi",
    "version": (0, 3, 0),
    "blender": (2, 80, 0),
    "location": "Properties Panel",
    "description": "Import-Export multiple video-bame formats",
    #"wiki_url": "https://github.com/Brachi/albam",
    #"tracker_url": "https://github.com/Brachi/albam/issues",
    "category": "Import-Export"}

#import pkgutil

#search_path = ['.'] # Используйте None, чтобы увидеть все модули, импортируемые из sys.path
#all_modules = [x[1] for x in pkgutil.iter_modules(path=search_path)]
#print(all_modules)

classes = ( AlbamImportedItemName,
            AlbamImportedItem,
            CustomMaterialOptions,
            CustomTextureOptions,
            CustomMeshOptions,
            AlbamImportExportPanel,
            AlbamImportOperator,
            AlbamExportOperator,
            #BlenderRegistry,
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
    
    #bpy.utils.register_module(__name__) #register modules
    auto_load.register()
    #from bpy.utils import register_class
    #for cls in classes:
    #    register_class(cls)

    bpy.types.Scene.albam_item_to_export = bpy.props.StringProperty()
    #print(str(bpy.types.Scene.albam_item_to_export))
    bpy.types.Scene.albam_items_imported = bpy.props.CollectionProperty(type=blender.AlbamImportedItemName)

    bpy.types.Object.albam_imported_item = bpy.props.PointerProperty(type=blender.AlbamImportedItem)

def unregister():
    #from bpy.utils import unregister_class
    #for cls in reversed(classes):
    #     unregister_class(cls)
    #print("unregister module")
    auto_load.unregister()

if __name__ == "__main__":
    register()
