import os
import json

try:
    import bpy
except ImportError:
    from unittest.mock import Mock
    bpy = Mock()

from .registry import blender_registry
from .tools.tools import *
from .tools.rename_bones import rename_bones
from .engines.mtframework.mod_156 import MaterialData, Mesh156

class AlbamImportedItemName(bpy.types.PropertyGroup): #
    '''Class for  bpy.types.Scene.albam_items_imported __init__.py registration
    All imported object names are saved here to then show them in the
    export list
    '''
    name : bpy.props.StringProperty(name="Imported Item", default="Unknown")


class AlbamImportedItem(bpy.types.PropertyGroup):
    '''Class for bpy.types.Object.albam_imported_item __init__.py registration'''
    name : bpy.props.StringProperty(options={'HIDDEN'})
    source_path : bpy.props.StringProperty(options={'HIDDEN'})
    folder : bpy.props.StringProperty(options={'HIDDEN'})  # Always in posix format
    data : bpy.props.StringProperty(options={'HIDDEN'}, subtype='BYTE_STRING')
    file_type : bpy.props.StringProperty(options={'HIDDEN'})


class AlbamSettings(bpy.types.PropertyGroup):
    '''Export option checkboxes for the Albam panel'''
    export_visible_bool : bpy.props.BoolProperty(
        name="AlbamSet only visible",
        description="Export visible meshes only",
        default = False
        )
    ignore_missing_mod_bool : bpy.props.BoolProperty(
        name="AlbamSet ignore missing",
        description="Ignore missing .mod error on during the export",
        default = False
        )
    clear_temp_foder_bool : bpy.props.BoolProperty(
        name="AlbamSet clear temp folder",
        description="Clear temporary folder before the import",
        default = False
        )
    transfer_normals_bool : bpy.props.BoolProperty(
        name="AlbamSet transfer normals",
        description="Automatically transfer normals from a temporary copy",
        default = True
        )


class CopyCustomPropertiesMat(bpy.types.Operator):
    """Copy Albam material properties from the active material"""
    bl_idname = "material.custom_property_copy"
    bl_label = "Copy Properties"
    
    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def execute(self, context):
      mat = bpy.context.active_object.active_material.name
      if mat:
          bpy.types.Scene.albam_copypaste_buffer = mat
          print(bpy.types.Scene.albam_copypaste_buffer )
      return {'FINISHED'}
    
class PasteCustomPropertiesMat(bpy.types.Operator):
    """Paste Albam material properties to the active material"""
    bl_idname = "material.custom_property_paste"
    bl_label = "Paste Properties"
    
    @classmethod
    def poll(cls, context):
        if not bpy.types.Scene.albam_copypaste_buffer:
            return False
        return True

    def execute(self, context):
        mat_name = bpy.types.Scene.albam_copypaste_buffer 
        try:
            copied_mat = bpy.data.materials.get(mat_name)
        except:
            bpy.types.Scene.albam_copypaste_buffer = ""
        active_mat = bpy.context.active_object.active_material
        material_data = MaterialData()
        for field in material_data._fields_:
            attr_name = field[0]
            if not attr_name.startswith('unk_'):
                continue 
            setattr(active_mat, attr_name, getattr(copied_mat, attr_name))
        return {'FINISHED'}

class StoreCustomPropertiesMat(bpy.types.Operator):
    """Copy Albam material properties from the active material"""
    bl_idname = "material.custom_property_store"
    bl_label = "Store to a file"

    filepath: bpy.props.StringProperty(subtype="DIR_PATH")
    filename = bpy.props.StringProperty(default="")
    
    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def execute(self, context):
        active_mat = bpy.context.active_object.active_material
        material_data = MaterialData()
        params ={}
        for field in material_data._fields_:
            attr_name = field[0]
            if not attr_name.startswith('unk_'):
                continue 
            params[attr_name] = getattr(active_mat, attr_name)
        with open(self.filepath, "w") as file:
            file.write(json.dumps(params, indent = 4))
            print("store mat params")
        return {'FINISHED'}

    def invoke(self, context, event):
        self.filepath = bpy.context.active_object.active_material.name + ".json"
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

class LoadCustomPropertiesMat(bpy.types.Operator):
    """Load Albam material properties from a file to the active material"""
    bl_idname = "material.custom_property_load"
    bl_label = "Load from a file"

    filepath: bpy.props.StringProperty(subtype="DIR_PATH")
    filename = bpy.props.StringProperty(default="")
    filter_glob: bpy.props.StringProperty(
        default="*.json",
        options={'HIDDEN'},
    )

    @classmethod
    def poll(cls, context):
        return context.active_object is not None
    
    def execute(self, context):
        active_mat = bpy.context.active_object.active_material
        material_data = MaterialData()
        params ={}
        with open(self.filepath) as file:
            loaded_param = json.load(file)
        for field in material_data._fields_:
            attr_name = field[0]
            if not attr_name.startswith('unk_'):
                continue 
            if loaded_param.get(attr_name):
                setattr(active_mat, attr_name, loaded_param[attr_name])
        print("It works!")
        return{'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

class CopyCustomPropertiesMesh(bpy.types.Operator):
    """Copy Albam mesh properties from the active mesh"""
    bl_idname = "mesh.custom_property_copy"
    bl_label = "Copy Properties"

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def execute(self, context):
      obj = bpy.context.active_object.name
      if obj:
          bpy.types.Scene.albam_copypaste_buffer_mesh = obj
          print(bpy.types.Scene.albam_copypaste_buffer_mesh )
      return {'FINISHED'}

class PasteCustomPropertiesMesh(bpy.types.Operator):
    """Paste Albam mesh properties to the active material"""
    bl_idname = "mesh.custom_property_paste"
    bl_label = "Paste Properties"
    
    @classmethod
    def poll(cls, context):
        if not bpy.types.Scene.albam_copypaste_buffer_mesh:
            return False
        return True

    def execute(self, context):
        mesh_name = bpy.types.Scene.albam_copypaste_buffer_mesh 
        try:
            copied_mesh = bpy.data.objects.get(mesh_name)
        except:
            bpy.types.Scene.albam_copypaste_buffer = ""
        active_mesh = bpy.context.active_object
        mesh_data = Mesh156()
        for field in mesh_data._fields_:
            attr_name = field[0]
            if not attr_name.startswith('unk_'):
                continue 
            setattr(active_mesh.data, attr_name, getattr(copied_mesh.data, attr_name))

        return {'FINISHED'}

class ALBAM_PT_CustomMaterialOptions(bpy.types.Panel):
    '''Custom Properies panel in the Material section'''
    bl_label = "Albam material"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "material"

    @staticmethod #? Guess outdated method to get active material and select its node
    def active_node_mat(mat):  # pragma: no cover
        '''mat: bpy.data.materials'''
        # taken from blender source
        if mat is not None:
            return mat
        return None

    def draw(self, context):  # pragma: no cover
        mat = self.active_node_mat(context.material) #check if current material is valid
        if not mat:
            return
        layout = self.layout # add layout for Albam material panel
        row = layout.row()
        row.operator("material.custom_property_copy")
        row.operator("material.custom_property_paste")
        row = layout.row()
        row.operator("material.custom_property_store")
        row.operator("material.custom_property_load")
        for prop_name, _, _ in blender_registry.bpy_props.get('material', []): # get unk_ properties for a material:'unk_01' 32835
            layout.prop(mat, prop_name) # add property for panel

    @classmethod
    def poll(cls, context):  # pragma: no cover
        return context.material
    

class ALBAM_PT_CustomTextureOptions(bpy.types.Panel):
    '''Custom Propertis panel for texures'''
    bl_label = "Albam texture"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "texture"

    def draw(self, context):
        tex = context.texture
        layout = self.layout
        if not tex:
                return
        for prop_name, _, _ in blender_registry.bpy_props.get('texture', []): # prop_name :'unk_byte_1', _:1 -value
            layout.prop(tex, prop_name)

    @classmethod
    def poll(cls, context):  # pragma: no cover #function is optional, used to check if the operator can run.
        return bool(context.texture)


class ALBAM_PT_CustomMeshOptions(bpy.types.Panel):
    '''Custom Propertis panel for meshes'''
    bl_label = "[Albam] MTFramework Mesh Options"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "data"

    def draw(self, context):  # pragma: no cover
        mesh = context.mesh
        layout = self.layout
        row = layout.row()
        row.operator("mesh.custom_property_copy")
        row.operator("mesh.custom_property_paste")
        if not mesh:
            return
        for prop_name, _, _ in blender_registry.bpy_props.get('mesh', []):
            layout.prop(mesh, prop_name)

    @classmethod
    def poll(cls, context):  # pragma: no cover
        return bool(context.mesh)


class ALBAM_PT_ImportExportPanel(bpy.types.Panel):
    '''UI Albam subpanel in 3D view'''
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Albam"
    bl_idname = "ALBAM_PT_UI_Panel"
    bl_label = "Albam"

    def draw(self, context):  # pragma: no cover
        scn = context.scene
        layout = self.layout
        export_settings = scn.albam_export_settings

        layout.operator('albam_import.item', text='Import')
        layout.prop_search(scn, 'albam_item_to_export', scn, 'albam_items_imported', text='select')
        layout.operator('albam_export.item', text='Export')
        layout.prop(export_settings, "export_visible_bool", text="Export visible meshes only")
        layout.prop(export_settings, "ignore_missing_mod_bool", text="Ignore missing .mod files")
        layout.prop(export_settings, "clear_temp_foder_bool", text="Clear temporary folder")


class ALBAM_PT_ToolsPanel(bpy.types.Panel):
    '''UI Tool subpanel in 3D view'''
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Albam"
    bl_idname = "ALBAM_PT_TOOLS_Panel"
    bl_label = "Tools"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        scn = context.scene
        export_settings = scn.albam_export_settings
        layout = self.layout
        row = layout.row()
        row.operator('albam_tools.fix_leaked_texures', text="Fix leaked textures")
        row.prop(export_settings, "transfer_normals_bool", text="")
        layout.operator('albam_tools.select_invalid_meshes', text="Select invalid meshes")
        layout.operator('albam_tools.remove_empty_vertex_groups', text="Remove empty vertex groups")
        layout.operator('albam_tools.rename_bones', text="Auto-rename bones")
        layout.operator('albam_tools.transfer_normals', text="Transfer normals")
        layout.prop(scn, "albam_scene_meshes", text="from")
        #layout.prop_search(scn, 'albam_scene_meshes', bpy.data, 'meshes', text='from')

class AlbamImportOperator(bpy.types.Operator):
    '''Import button operator'''
    bl_idname = "albam_import.item"
    bl_label = "import item"
    directory : bpy.props.StringProperty(subtype='DIR_PATH') #fileselect_add properies here
    files : bpy.props.CollectionProperty(name='adf', type=bpy.types.OperatorFileListElement) #fileselect_add properies here
    filter_glob : bpy.props.StringProperty(default="*.arc", options={'HIDDEN'})
    unpack_dir : bpy.props.StringProperty(options={'HIDDEN'})

    def invoke(self, context, event):  # pragma: no cover
        wm = context.window_manager
        wm.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        to_import = [os.path.join(self.directory, f.name) for f in self.files] # combine path to file and file name list to a new list
        for file_path in to_import:
            self._import_file(file_path=file_path, context=context)

        return {'FINISHED'}

    def _import_file(self, **kwargs):
            parent = kwargs.get('parent') #?
            file_path = kwargs.get('file_path')
            context = kwargs['context']
            kwargs['unpack_dir'] = self.unpack_dir
            with open(file_path, 'rb') as f: #read file as a binary
                data = f.read() # store file to data var
            id_magic = data[:4] # get first 4 bytes(?)

            func = blender_registry.import_registry.get(id_magic) # find header in dictionary
            if not func:
                raise TypeError('File not supported for import. Id magic: {}'.format(id_magic))

            name = os.path.basename(file_path) #name of the imported archive
            obj = bpy.data.objects.new(name, None) # Create a new object with the arc archive name, data = None
            obj.parent = parent
            obj.albam_imported_item['data'] = data
            obj.albam_imported_item.source_path = str(file_path)
            
            # TODO: proper logging/raising and rollback if failure
            results_dict = func(blender_object=obj, **kwargs)
            #bpy.context.scene.objects.link(obj) #old
            bpy.context.collection.objects.link(obj)

            is_exportable = bool(blender_registry.export_registry.get(id_magic))
            if is_exportable:
                new_albam_imported_item = context.scene.albam_items_imported.add()
                new_albam_imported_item.name = name
            if results_dict:
                files = results_dict.get('files', [])
                kwargs = results_dict.get('kwargs', {})
                for f in files:
                    self._import_file(file_path=f, context=context, **kwargs)


class AlbamExportOperator(bpy.types.Operator):
    '''Export button operator'''
    bl_idname = "albam_export.item"
    bl_label = "export item"
    filepath : bpy.props.StringProperty()

    @classmethod
    def poll(self, context):  # pragma: no cover
        if not bpy.context.scene.albam_item_to_export:
            return False
        return True

    def invoke(self, context, event):  # pragma: no cover
        self.filepath = context.scene.albam_item_to_export # set a name to arc file
        wm = context.window_manager
        wm.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        object_name = context.scene.albam_item_to_export # '_exported_archive_name_.arc'
        obj = bpy.data.objects[object_name] 
        id_magic = obj.albam_imported_item['data'][:4]
        func = blender_registry.export_registry.get(id_magic)
        if not func:
            raise TypeError('File not supported for export. Id magic: {}'.format(id_magic))
        #bpy.ops.object.mode_set(mode='OBJECT')
        func(obj, self.filepath)
        show_message_box(message="Export is finished")
        return {'FINISHED'}


class AlbamFixLeakedTexuresOperator(bpy.types.Operator):
    '''Fix leaked texures button operator'''
    bl_idname = "albam_tools.fix_leaked_texures"
    bl_label = "fix leaked textures"

    @classmethod
    def poll(self, context):  # pragma: no cover
        if not bpy.context.selected_objects:
            return False
        return True

    def execute(self, context):
        selection = bpy.context.selected_objects
        selected_meshes = [obj for obj in selection if obj.type == 'MESH']
        if selected_meshes:
            split_UV_seams_operator(selected_meshes)
        else:
            show_message_box(message="There is no mesh in the selection")
        return {'FINISHED'}


class AlbamSelectInvalidMeshesOperator(bpy.types.Operator):
    '''Select meshes with more than 32 influences'''
    bl_idname = "albam_tools.select_invalid_meshes"
    bl_label = "select invalid meshes"

    def execute(self, context):
        try:
            bpy.ops.object.mode_set(mode='OBJECT')
        except:
            pass
        selection = bpy.context.scene.objects
        scene_meshes = [obj for obj in selection if obj.type == 'MESH']
        if scene_meshes:
            select_invalid_meshes_operator(scene_meshes)
        else:
            show_message_box(message="There is no mesh in the scene")
        return {'FINISHED'}
        
        
class AlbamRemoveEmptyVertexGroupsOperator(bpy.types.Operator):
    '''Remove vertex groups with 0 skin weighs'''
    bl_idname = "albam_tools.remove_empty_vertex_groups"
    bl_label = "remove empty vertex groups"
    
    def execute(self, context):
        try:
            bpy.ops.object.mode_set(mode='OBJECT')
        except:
            pass
        selection = bpy.context.scene.objects
        scene_meshes = [obj for obj in selection if obj.type == 'MESH']

        for ob in scene_meshes:
            ob.update_from_editmode()
            
            vgroup_used = {i: False for i, k in enumerate(ob.vertex_groups)}
            
            for v in ob.data.vertices:
                for g in v.groups:
                    if g.weight > 0.0:
                        vgroup_used[g.group] = True
            
            for i, used in sorted(vgroup_used.items(), reverse=True):
                if not used:
                    ob.vertex_groups.remove(ob.vertex_groups[i])
        show_message_box(message="Removing complete")
        return {'FINISHED'}


class AlbamRenameBonesOperator(bpy.types.Operator):
    '''Rename bones in the characters armature'''
    bl_idname = "albam_tools.rename_bones"
    bl_label = "rename character bones"

    @classmethod
    def poll(self, context):
        selection = bpy.context.selected_objects
        armature = [obj for obj in selection if obj.type == 'ARMATURE']
        if not armature:
            return False
        return True
    
    def execute(self, context):
        selection = bpy.context.selected_objects
        armature = [obj for obj in selection if obj.type == 'ARMATURE']
        #bones = armature[0].data.bones
        #print(bones)
        rename_bones(armature[0])
        return{'FINISHED'}


class AlbamTransferNormalsOperator(bpy.types.Operator):
    '''Transfer normals from a unified mesh to its parts'''
    bl_idname = "albam_tools.transfer_normals"
    bl_label = "transfer normals"

    @classmethod
    def poll(self, context):  # pragma: no cover
        source_obj = context.scene.albam_scene_meshes
        #if not bpy.context.selected_objects or source_obj.type == 'MESH':
        if source_obj == None or not bpy.context.selected_objects:
            return False
        if source_obj.type != 'MESH':
            return False
        return True
    
    def execute(self, context):
        selection = bpy.context.selected_objects
        source_obj = context.scene.albam_scene_meshes
        #for obj in bpy.data.objects:
        #     if obj.type == 'MESH':
        #        if obj.data == source_obj:
        #            source_obj = obj

        target_objs = [obj for obj in selection if obj.type == 'MESH']
        if target_objs  and source_obj:
            transfer_normals(source_obj, target_objs)
        else:
            show_message_box(message="There is no mesh in selection")
        return {'FINISHED'}
        