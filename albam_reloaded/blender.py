import os

try:
    import bpy
except ImportError:
    from unittest.mock import Mock
    bpy = Mock()

from .registry import blender_registry

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


class CustomMaterialOptions(bpy.types.Panel):
    '''Custom Properies panel in the Material section'''
    bl_label = "Albam material"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "material"

    @staticmethod #? Guess outdated method to get active material and select its node
    def active_node_mat(mat):  # pragma: no cover
        '''mat: bpy.data.materials['Pl0200.mod_08']'''
        # taken from blender source
        if mat is not None:
            #mat_node = mat.active_node_material # deprecated TODO
            #mat_node = mat
            #if mat_node:
            #    return mat_node
            #else:
            #     return mat
            return mat

        return None

    def draw(self, context):  # pragma: no cover
        mat = self.active_node_mat(context.material)
        if not mat:
            return
        layout = self.layout
        for prop_name, _, _ in blender_registry.bpy_props.get('material', []):
            layout.prop(mat, prop_name)

    @classmethod
    def poll(cls, context):  # pragma: no cover
        return context.material


class CustomTextureOptions(bpy.types.Panel):
    "Custom Propertis panel for texures"
    bl_label = "Albam texture"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "texture"

    def draw(self, context):  # pragma: no cover
        tex = context.texture #bpy.data.textures['00pl0200_01Face_BM']
        layout = self.layout
            
        if not tex:
                return
        for prop_name, _, _ in blender_registry.bpy_props.get('texture', []): # prop_name :'unk_byte_1', _:1 -value
            layout.prop(tex, prop_name)

        @classmethod
        def poll(cls, context):  # pragma: no cover #function is optional, used to check if the operator can run.
            if not hasattr(context, "texture_slot"): # useless code detect Texture slot for textures in a Material datablock
                #print("material data has attribute")
                return False
            return context.texture


class CustomMeshOptions(bpy.types.Panel):
    "Custom Propertis panel for meshes"
    bl_label = "Albam mesh"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "data"

    def draw(self, context):  # pragma: no cover
        mesh = context.mesh
        layout = self.layout
        if not mesh:
            return
        for prop_name, _, _ in blender_registry.bpy_props.get('mesh', []):
            layout.prop(mesh, prop_name)

    @classmethod
    def poll(cls, context):  # pragma: no cover
        return bool(context.mesh)


class AlbamImportExportPanel(bpy.types.Panel):
    '''UI Panel in 3D view'''
    bl_idname = "Albam_UI_Panel" # my lines
    bl_label = "Albam"
    bl_category = "Albam" # my lines
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"

    def draw(self, context):  # pragma: no cover
        scn = context.scene
        layout = self.layout
        layout.operator('albam_import.item', text='Import')
        layout.prop_search(scn, 'albam_item_to_export', scn, 'albam_items_imported', text='select')
        layout.operator('albam_export.item', text='Export')


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
            #print('file path is {}'.format(file_path))
            self._import_file(file_path=file_path, context=context)

        return {'FINISHED'}

    def _import_file(self, **kwargs):
            parent = kwargs.get('parent') #?
            file_path = kwargs.get('file_path')
            context = kwargs['context']
            kwargs['unpack_dir'] = self.unpack_dir
            #print("unpack dir is{}" .format(kwargs['unpack_dir']))
            with open(file_path, 'rb') as f: #read file as a binary
                data = f.read() # store file to data var
            id_magic = data[:4] # get first 4 bytes(?)

            #print("data is {}".format(data))
            func = blender_registry.import_registry.get(id_magic) # find header in dictionary
            if not func:
                raise TypeError('File not supported for import. Id magic: {}'.format(id_magic))
            #print('id_magic:{}'.format(id_magic))

            name = os.path.basename(file_path) #name of the imported archive
            #print('name:{}'.format(name))
            obj = bpy.data.objects.new(name, None) # Create a new object with the arc archive name, data = None
            obj.parent = parent
            obj.albam_imported_item['data'] = data # error?
            #print("import data is {}".format(obj.albam_imported_item.data))
            obj.albam_imported_item.source_path = str(file_path)
            
            # TODO: proper logging/raising and rollback if failure

            results_dict = func(blender_object=obj, **kwargs)
            #results_dict = False
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
        wm = context.window_manager
        wm.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        object_name = context.scene.albam_item_to_export
        #print("object_name is {}".format(object_name))
        obj = bpy.data.objects[object_name]
        #print("export obj is {}".format(obj))
        #for objs in bpy.data.objects:
        #    print(objs.name)
        id_magic = obj.albam_imported_item['data'][:4]
        func = blender_registry.export_registry.get(id_magic)
        if not func:
            raise TypeError('File not supported for export. Id magic: {}'.format(id_magic))
        bpy.ops.object.mode_set(mode='OBJECT')
        func(obj, self.filepath)
        return {'FINISHED'}
