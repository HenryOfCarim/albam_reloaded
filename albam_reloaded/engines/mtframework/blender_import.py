from itertools import chain
import ntpath
import os

try:
    import bpy
    from mathutils import Matrix, Vector
except ImportError:
    pass

from ...exceptions import BuildMeshError, TextureError #my lines IDK where they originally imported

from ...engines.mtframework import Arc, Mod156, Tex112, KNOWN_ARC_BLENDER_CRASH, CORRUPTED_ARCS
from ...engines.mtframework.utils import (
    get_vertices_array,
    get_indices_array,
    get_non_deform_bone_indices,
    get_bone_parents_from_mod,
    transform_vertices_from_bbox,
    texture_code_to_blender_texture,

    )
from ...engines.mtframework.mappers import BONE_INDEX_TO_GROUP
from ...lib.misc import chunks
from ...lib.half_float import unpack_half_float
from ...lib.blender import strip_triangles_to_triangles_list, create_mesh_name
from ...registry import blender_registry


@blender_registry.register_function('import', identifier=b'ARC\x00')
def import_arc(blender_object, file_path, **kwargs):
    """Imports an arc file (Resident Evil 5 for only for now) into blender,
    extracting all files to a tmp dir and saving unknown/unused data
    to the armature (if any) for using in exporting
    """

    unpack_dir = kwargs.get('unpack_dir')
    if file_path.endswith(tuple(KNOWN_ARC_BLENDER_CRASH) + tuple(CORRUPTED_ARCS)):
        raise ValueError('The arc file provided is not supported yet, it might crash Blender')

    base_dir = os.path.basename(file_path).replace('.arc', '_arc_extracted')
    out = unpack_dir or os.path.join(os.path.expanduser('~'), '.albam', 're5', base_dir) #causing an error
    #out = os.path.join(os.path.expanduser('~'), '.albam', 're5', base_dir)
    if not os.path.isdir(out):
        os.makedirs(out)
    if not out.endswith(os.path.sep):
        out = out + os.path.sep

    arc = Arc(file_path=file_path)
    arc.unpack(out)

    mod_files = [os.path.join(root, f) for root, _, files in os.walk(out)
                 for f in files if f.endswith('.mod')]
    mod_folders = [os.path.dirname(mod_file.split(out)[-1]) for mod_file in mod_files]

    return {'files': mod_files,
            'kwargs': {'parent': blender_object,
                       'mod_folder': mod_folders[0],  # XXX will break if mods are in different folders
                       'base_dir': out,
                       },
            }


@blender_registry.register_function('import', identifier=b'MOD\x00')
def import_mod(blender_object, file_path, **kwargs):
    base_dir = kwargs.get('base_dir') # full path to _extracted folder

    mod = Mod156(file_path=file_path)
    textures = _create_blender_textures_from_mod(mod, base_dir)
    materials = _create_blender_materials_from_mod(mod, blender_object.name, textures)

    meshes = []
    for i, mesh in enumerate(mod.meshes_array):
        name = create_mesh_name(mesh, i, file_path)
        try:
            m = _build_blender_mesh_from_mod(mod, mesh, i, name, materials)
            meshes.append(m)
        except BuildMeshError as err:
            # TODO: logging
            print('Error building mesh {0} for mod {1}'.format(i, file_path))
            print('Details:', err)

    if mod.bone_count: # create  skeleton? 
        armature_name = 'skel_{}'.format(blender_object.name)
        root = _create_blender_armature_from_mod(blender_object, mod, armature_name)
        root.show_in_front = True # set x-ray view for bones
    else:
        root = blender_object

    for mesh in meshes: # skin mesh to bones? 
        #bpy.context.scene.objects.link(mesh)
        bpy.context.collection.objects.link(mesh)
        mesh.parent = root
        if mod.bone_count:
            modifier = mesh.modifiers.new(type="ARMATURE", name=blender_object.name)
            modifier.object = root
            modifier.use_vertex_groups = True


def _build_blender_mesh_from_mod(mod, mesh, mesh_index, name, materials):
    me_ob = bpy.data.meshes.new(name)
    ob = bpy.data.objects.new(name, me_ob)

    imported_vertices = _import_vertices(mod, mesh)
    vertex_locations = imported_vertices['locations']
    vertex_normals = imported_vertices['normals']
    uvs_per_vertex = imported_vertices['uvs']
    weights_per_bone = imported_vertices['weights_per_bone']
    indices = get_indices_array(mod, mesh)
    indices = strip_triangles_to_triangles_list(indices)
    faces = chunks(indices, 3)
    uvs_per_vertex = imported_vertices['uvs']
    weights_per_bone = imported_vertices['weights_per_bone']

    assert min(indices) >= 0, "Bad face indices"  # Blender crashes if not
    me_ob.from_pydata(vertex_locations, [], faces)

    me_ob.create_normals_split()

    me_ob.validate(clean_customdata=False)
    me_ob.update(calc_edges=True)
    me_ob.polygons.foreach_set("use_smooth", [True] * len(me_ob.polygons))

    loop_normals = []
    for loop in me_ob.loops:
        loop_normals.append(vertex_normals[loop.vertex_index])

    me_ob.normals_split_custom_set_from_vertices(vertex_normals)
    me_ob.use_auto_smooth = True

    mesh_material = materials[mesh.material_index]
    '''Old code
    if not mesh.use_cast_shadows and mesh_material.use_cast_shadows:
        mesh_material.use_cast_shadows = False'''
    if not mesh.use_cast_shadows and mesh_material.shadow_method: # code gets .use_cast_shadows from mesh's custom props
        mesh_material.shadow_method = 'NONE' # if use_cast_shadows is false and a material shadows is enabled, set it to NONE
    me_ob.materials.append(mesh_material)

    for bone_index, data in weights_per_bone.items():
        vg = ob.vertex_groups.new(name=str(bone_index))
        for vertex_index, weight_value in data:
            vg.add((vertex_index,), weight_value, 'ADD')

    if uvs_per_vertex:
        #me_ob.uv_textures.new(name) # deprecated
        #print(dir(me_ob))
        me_ob.uv_layers.new(name=name)
        uv_layer = me_ob.uv_layers[-1].data
        per_loop_list = []
        for loop in me_ob.loops:
            offset = loop.vertex_index * 2
            per_loop_list.extend((uvs_per_vertex[offset], uvs_per_vertex[offset + 1]))
        uv_layer.foreach_set('uv', per_loop_list)
    # Hiding non main level of detail meshes if they have more than one.
    # For now, assuming that if the mesh has no bones, then it has only one level of detail
    if weights_per_bone and mesh.level_of_detail in (2, 252):
        #print(dir(ob))
        #ob.hide = True
        ob.hide_viewport  = True
        ob.hide_render = True

    # Saving unknown metadata for export
    # TODO: use a util function
    for field_tuple in mesh._fields_:
        attr_name = field_tuple[0]
        if not attr_name.startswith('unk_'):
            continue
        attr_value = getattr(mesh, attr_name)
        setattr(me_ob, attr_name, attr_value)

    return ob


def _import_vertices(mod, mesh):
    return _import_vertices_mod156(mod, mesh)


def _import_vertices_mod156(mod, mesh):
    vertices_array = get_vertices_array(mod, mesh)

    if mesh.vertex_format != 0:
        locations = (transform_vertices_from_bbox(vf, mod)
                     for vf in vertices_array)
    else:
        locations = ((vf.position_x, vf.position_y, vf.position_z) for vf in vertices_array)

    locations = map(lambda t: (t[0] / 100, t[2] / -100, t[1] / 100), locations)
    # from [0, 255] o [-1, 1]
    normals = map(lambda v: (((v.normal_x / 255) * 2) - 1,
                             ((v.normal_y / 255) * 2) - 1,
                             ((v.normal_z / 255) * 2) - 1), vertices_array)
    # y up to z up
    normals = map(lambda n: (n[0], n[2] * -1, n[1]), normals)

    list_of_tuples = [(unpack_half_float(v.uv_x), unpack_half_float(v.uv_y) * -1) for v in vertices_array]
    return {'locations': list(locations),
            'normals': list(normals),
            # TODO: investigate why uvs don't appear above the image in the UV editor
            'uvs': list(chain.from_iterable(list_of_tuples)),
            'weights_per_bone': _get_weights_per_bone(mod, mesh, vertices_array)
            }


def _create_blender_textures_from_mod(mod, base_dir):
    textures = [None]  # materials refer to textures in index-1
    # TODO: check why in Arc.header.file_entries[n].file_path it returns a bytes, and
    # here the whole array of chars

    for i, texture_path in enumerate(mod.textures_array):
        path = texture_path[:].decode('ascii').partition('\x00')[0] # relative path to a texture in the ARC archive without extension
        path = os.path.join(base_dir, *path.split(ntpath.sep))# full path to a texture
        path = '.'.join((path, 'tex')) # full path to a texture with .tex extension
        if not os.path.isfile(path):
            # TODO: log warnings, figure out 'rtex' format
            print('path {} does not exist'.format(path))
            continue
        tex = Tex112(path)
        try:
            dds = tex.to_dds()
        except TextureError as err:
            # TODO: log this instead of printing it
            print('Error converting "{}"to dds: {}'.format(path, err))
            textures.append(None)
            continue
        dds_path = path.replace('.tex', '.dds') # change extension in the full path
        with open(dds_path, 'wb') as w: #write bynary
            w.write(dds)
        image = bpy.data.images.load(dds_path)
        texture_name_no_extension = os.path.splitext(os.path.basename(path))[0]
        texture_name_no_extension = str(i).zfill(2) + texture_name_no_extension
        texture = bpy.data.textures.new(texture_name_no_extension, type='IMAGE') # bpy.data.textures['00pl0200_09AllHair_BM']
        texture.use_fake_user = True # TEST
        texture.image = image 
        #print(dir(texture))
        #print(texure)
        textures.append(texture) #create a list with bpy.data.textures

        # saving meta data for export
        # TODO: use a util function
        for field_tuple in tex._fields_:
            attr_name = field_tuple[0]
            if not attr_name.startswith('unk_'):
                continue
            attr_value = getattr(tex, attr_name)
            setattr(texture, attr_name, attr_value)

    return textures


def _create_blender_materials_from_mod(mod, model_name, textures):
    '''textures: bpy.data.textures'''
    materials = []
    for i, material in enumerate(mod.materials_data_array):
        blender_material = bpy.data.materials.new('{}_{}'.format(model_name, str(i).zfill(2)))
        blender_material.use_nodes = True
        blender_material.blend_method = 'CLIP' # set transparency method 'OPAQUE', 'CLIP', 'HASHED', 'BLEND'

        principled_node = blender_material.node_tree.nodes.get("Principled BSDF")
        principled_node.inputs['Specular'].default_value = 0.2 # change specular

        ''' Old code
        #blender_material.use_transparency = True 
        #blender_material.alpha = 0.0
        #blender_material.specular_intensity = 0.2  # would be nice to get this info from the mod
        '''

        # unknown data for export, registered already
        # TODO: do this with a util function
        for field_tuple in material._fields_: # add custom properties to material
            attr_name = field_tuple[0]
            if not attr_name.startswith('unk_'):
                continue
            attr_value = getattr(material, attr_name)
            setattr(blender_material, attr_name, attr_value)
        materials.append(blender_material)

        for texture_code, tex_index in enumerate(material.texture_indices):
            if not tex_index:
                continue
            try:
                texture_target = textures[tex_index]
            except IndexError:
                # TODO
                print('tex_index {} not found. Texture len(): {}'.format(tex_index, len(textures)))
                continue
            if not texture_target:
                # This means the conversion failed before
                # TODO: logging
                continue
            if texture_code == 3 or texture_code == 4 or texture_code == 5 or texture_code == 6:
                print('texture_code not supported', texture_code)
                continue
            slot = blender_material.node_tree.nodes.new('ShaderNodeTexImage') 
            texture_code_to_blender_texture(texture_code, slot, blender_material)
            slot.image = texture_target.image # set bpy.data.textures[].image as a texures for ShaderNodeTexImage
            if  texture_code  == 1 or texture_code  == 7: # change color settings for normal and detail maps
                slot.image.colorspace_settings.name = 'Non-Color'

    return materials


def _create_blender_armature_from_mod(blender_object, mod, armature_name):
    armature = bpy.data.armatures.new(armature_name)
    armature_ob = bpy.data.objects.new(armature_name, armature)
    armature_ob.parent = blender_object

    #set to Object mode
    if bpy.context.mode != 'OBJECT': 
        bpy.ops.object.mode_set(mode='OBJECT')
    # deselect all objects
    for i in bpy.context.scene.objects:
    #    i.select = False #deprecated
        i.select_set(False) # my change
    #bpy.context.scene.objects.link(armature_ob) # deprecated
    bpy.context.collection.objects.link(armature_ob)
    #bpy.context.scene.objects.active = armature_ob # deprecated 
    bpy.context.view_layer.objects.active = armature_ob
    #armature_ob.select = True # deprecated
    armature_ob.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')

    blender_bones = []
    for i, bone in enumerate(mod.bones_array): # add counter to the array
        blender_bone = armature.edit_bones.new(str(i))
        blender_bones.append(blender_bone)
        parents = get_bone_parents_from_mod(bone, mod.bones_array)
        if not parents:
            blender_bone.head = Vector((bone.location_x / 100,
                                        bone.location_z * -1 / 100,
                                        bone.location_y / 100))
            continue
        chain = [i] + parents
        wtm = Matrix.Translation((0, 0, 0))
        for bi in reversed(chain):
            b = mod.bones_array[bi]
            wtm = wtm @ Matrix.Translation((b.location_x / 100, b.location_z / 100 * -1, b.location_y / 100))
            #wtm = wtm * Matrix.Translation((b.location_x / 100, b.location_z / 100 * -1, b.location_y / 100)) # deprecated * was replaced with @
        blender_bone.head = wtm.to_translation()
        blender_bone.parent = blender_bones[bone.parent_index]

    assert len(blender_bones) == len(mod.bones_array)

    non_deform_bone_indices = get_non_deform_bone_indices(mod)
    # set tails of bone to their children or make them small if they have none
    for i, bone in enumerate(blender_bones):
        if i in non_deform_bone_indices:
            bone.use_deform = False
        children = bone.children_recursive
        non_mirror_children = [b for b in children
                               if mod.bones_array[int(b.name)].mirror_index == int(b.name)]
        mirror_children = [b for b in children
                           if mod.bones_array[int(b.name)].mirror_index != int(b.name)]
        if mod.bones_array[i].mirror_index == i and non_mirror_children:
            bone.tail = non_mirror_children[0].head
        elif mod.bones_array[i].mirror_index != i and mirror_children:
            bone.tail = mirror_children[0].head
        else:
            bone.length = 0.01
        # Some very small numbers won't be equal without rounding, but blender will
        # later treat them as equal, so using rounding here
        if round(bone.tail[0], 10) == round(bone.head[0], 10):
            bone.tail[0] += 0.01
        if round(bone.tail[1], 10) == round(bone.head[1], 10):
            bone.tail[1] += 0.01
        if round(bone.tail[2], 10) == round(bone.head[2], 10):
            bone.tail[2] += 0.01

    bpy.ops.object.mode_set(mode='OBJECT')
    assert len(armature.bones) == len(mod.bones_array)

    _create_bone_groups(armature_ob, mod)
    return armature_ob


def _create_bone_groups(armature_ob, mod):
    bone_groups_cache = {
        'BONE_GROUP_MAIN': {
            'color_set': 'THEME03',
            'name': 'Main',
            'layer': 1,
            },
        'BONE_GROUP_ARMS': {
            'color_set': 'THEME02',
            'name': 'Arms',
            'layer': 2,
            },
        'BONE_GROUP_LEGS': {
            'color_set': 'THEME05',
            'name': 'Legs',
            'layer': 3,
            },
        'BONE_GROUP_HANDS': {
            'color_set': 'THEME06',
            'name': 'Hands',
            'layer': 4,
            },
        'BONE_GROUP_HAIR': {
            'color_set': 'THEME07',
            'name': 'Hair',
            'layer': 5,
            },
        'BONE_GROUP_FACIAL_BASIC': {
            'color_set': 'THEME02',
            'name': 'Facial Basic',
            'layer': 6,
            },
        'BONE_GROUP_FACIAL': {
            'color_set': 'THEME01',
            'name': 'Facial',
            'layer': 7,
            },
        'BONE_GROUP_ACCESORIES': {
            'color_set': 'THEME14',
            'name': 'Accessories',
            'layer': 8,
            },
        'OTHER': {
            'color_set': 'THEME20',
            'name': 'Other',
            'layer': 9,
            },
    }

    bpy.ops.object.mode_set(mode='POSE')
    for i, bone in enumerate(armature_ob.pose.bones):
        source_bone = mod.bones_array[i]
        anim_index = source_bone.anim_map_index
        bone.bone_group = _get_or_create_bone_group(anim_index, armature_ob, i, bone_groups_cache)
    bpy.ops.object.mode_set(mode='OBJECT')


def _get_or_create_bone_group(bone_anim_index, armature_ob, bone_index, bone_groups_cache):
    bone_group_name = BONE_INDEX_TO_GROUP.get(bone_anim_index, 'OTHER')

    bone_group_cache = bone_groups_cache.get(bone_group_name) or bone_groups_cache['OTHER']
    layer_index = bone_group_cache['layer']
    _move_bone_to_layers(armature_ob, bone_index, 0, layer_index)

    if bone_group_cache.get('bl_group'):
        return bone_group_cache['bl_group']

    bl_bone_group = armature_ob.pose.bone_groups.new(name=bone_group_cache['name'])
    bl_bone_group.color_set = bone_group_cache['color_set']
    bone_group_cache['bl_group'] = bl_bone_group

    return bl_bone_group


def _move_bone_to_layers(armature_ob, bone_index, *layer_indices):
    layers = [False] * 32
    for layer_index in layer_indices:
        layers[layer_index] = True
    armature_ob.data.bones[bone_index].select = True
    bpy.ops.pose.bone_layers(layers=layers)
    armature_ob.data.bones[bone_index].select = False


def _get_weights_per_bone(mod, mesh, vertices_array):
    weights_per_bone = {}
    if not mod.bone_count or not hasattr(vertices_array[0], 'bone_indices'):
        return weights_per_bone
    bone_palette = mod.bone_palette_array[mesh.bone_palette_index]
    for vertex_index, vertex in enumerate(vertices_array):
        for bi, bone_index in enumerate(vertex.bone_indices):
            if bone_index >= bone_palette.unk_01:
                real_bone_index = mod.bones_animation_mapping[bone_index]
            else:
                real_bone_index = bone_palette.values[bone_index]
            if bone_index + vertex.weight_values[bi] == 0:
                continue
            bone_data = weights_per_bone.setdefault(real_bone_index, [])
            bone_data.append((vertex_index, vertex.weight_values[bi] / 255))
    return weights_per_bone
