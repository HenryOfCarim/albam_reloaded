from collections import OrderedDict, namedtuple
import ctypes
from io import BytesIO
from itertools import chain
import ntpath
import os
import tempfile
import re
import struct
try:
    import bpy
except ImportError:
    pass

from ...registry import blender_registry
from ...exceptions import ExportError
from ...engines.mtframework.mod_156 import (
    Mesh156,
    WeightBound,
    MaterialData,
    BonePalette,
    CLASSES_TO_VERTEX_FORMATS,
    VERTEX_FORMATS_TO_CLASSES,
    )
from ...engines.mtframework import Arc , Mod156, Tex112
from ...engines.mtframework.utils import (
    vertices_export_locations,
    blender_texture_to_texture_code,
    get_texture_dirs,
    get_default_texture_dir,
    )
from ...lib.half_float import pack_half_float
from ...lib.structure import get_offset
from ...lib.geometry import z_up_to_y_up
from ...lib.misc import ntpath_to_os_path
from ...lib.blender import (
    triangles_list_to_triangles_strip,
    get_textures_from_the_material,
    get_textures_from_blender_objects,
    get_materials_from_blender_objects,
    get_vertex_count_from_blender_objects,
    get_bone_indices_and_weights_per_vertex,
    get_uvs_per_vertex,
    )


ExportedMeshes = namedtuple('ExportedMeshes', ('meshes_array', 'vertex_buffer', 'index_buffer', 'weight_bounds'))
ExportedMaterials = namedtuple('ExportedMaterials', ('textures_array', 'materials_data_array',
                                                     'materials_mapping', 'blender_textures',
                                                     'texture_dirs'))
ExportedMod = namedtuple('ExportedMod', ('mod', 'exported_materials'))


@blender_registry.register_function('export', b'ARC\x00')
def export_arc(blender_object, file_path):
    '''
        blender_object : bpy.data.objects['uPl02JillCos1.arc']
        file_path : full path to .ars
    '''
    saved_arc = Arc(file_path=BytesIO(blender_object.albam_imported_item.data)) # <albam_reloaded.engines.mtframework.arc.GenArc object

    mods = {}
    texture_dirs = {}
    textures_to_export = []

    for child in blender_object.children:
        exportable = hasattr(child, 'albam_imported_item')
        if not exportable:
            continue

        exported_mod = export_mod156(child) #run export_mod156 function
        mods[child.name] = exported_mod # {'Pl0200.mod': <ExportedMod, len() = 2>}
        texture_dirs.update(exported_mod.exported_materials.texture_dirs) # path inside arc 'pawn\\pl\\pl02\\model'
        textures_to_export.extend(exported_mod.exported_materials.blender_textures)

    with tempfile.TemporaryDirectory() as tmpdir:
        saved_arc.unpack(tmpdir)

        mod_files = [os.path.join(root, f) for root, _, files in os.walk(tmpdir)
                     for f in files if f.endswith('.mod')]

        # overwriting the original mod files with the exported ones
        for modf in mod_files:
            filename = os.path.basename(modf)
            try:
                # TODO: mods with the same name in different folders
                exported_mod = mods[filename]
            except KeyError:
                raise ExportError("Can't export to arc, a mod file is missing: {}. "
                                  "Was it deleted before exporting?. "
                                  "mods.items(): {}".format(filename, mods.items()))

            with open(modf, 'wb') as w:
                w.write(exported_mod.mod)

        for blender_texture in textures_to_export:
            texture_name = blender_texture.name
            #texture_name = blender_texture.image.name
            resolved_path = ntpath_to_os_path(texture_dirs[texture_name])
            tex_file_path = bpy.path.abspath(blender_texture.image.filepath)
            tex_filename_no_ext = os.path.splitext(os.path.basename(tex_file_path))[0]
            destination_path = os.path.join(tmpdir, resolved_path, tex_filename_no_ext + '.tex')
            tex = Tex112.from_dds(file_path=bpy.path.abspath(blender_texture.image.filepath))
            # metadata saved
            # TODO: use an util function
            for field in tex._fields_:
                attr_name = field[0]
                if not attr_name.startswith('unk_'):
                    continue
                setattr(tex, attr_name, getattr(blender_texture, attr_name))

            with open(destination_path, 'wb') as w:
                w.write(tex)

        # Once the textures and the mods have been replaced, repack.
        new_arc = Arc.from_dir(tmpdir)

    with open(file_path, 'wb') as w:
        w.write(new_arc)


def export_mod156(parent_blender_object):
    saved_mod = Mod156(file_path=BytesIO(parent_blender_object.albam_imported_item.data))

    first_children = [child for child in parent_blender_object.children]
    blender_meshes = [c for c in first_children if c.type == 'MESH']
    # only going one level deeper
    if not blender_meshes:
        children_objects = list(chain.from_iterable(child.children for child in first_children))
        blender_meshes = [c for c in children_objects if c.type == 'MESH']

    if saved_mod.bone_count:
        bone_palettes = _create_bone_palettes(blender_meshes)
        bone_palette_array = (BonePalette * len(bone_palettes))()

        if saved_mod.unk_08:
            # Since unk_12 depends on the offset, calculate it early
            bones_array_offset = 176 + len(saved_mod.unk_12)
        else:
            bones_array_offset = 176
        for i, bp in enumerate(bone_palettes.values()):
            bone_palette_array[i].unk_01 = len(bp)
            if len(bp) != 32:
                padding = 32 - len(bp)
                bp = bp + [0] * padding
            bone_palette_array[i].values = (ctypes.c_ubyte * len(bp))(*bp)
    else:
        bones_array_offset = 0
        bone_palettes = {}
        bone_palette_array = (BonePalette * 0)()

    exported_materials = _export_textures_and_materials(blender_meshes, saved_mod)
    exported_meshes = _export_meshes(blender_meshes, bone_palettes, exported_materials, saved_mod)

    mod = Mod156(id_magic=b'MOD',
                 version=156,
                 version_rev=1,
                 bone_count=saved_mod.bone_count,
                 mesh_count=len(blender_meshes),
                 material_count=len(exported_materials.materials_data_array),
                 vertex_count=get_vertex_count_from_blender_objects(blender_meshes),
                 face_count=(ctypes.sizeof(exported_meshes.index_buffer) // 2) + 1,
                 edge_count=0,  # TODO: add edge_count
                 vertex_buffer_size=ctypes.sizeof(exported_meshes.vertex_buffer),
                 vertex_buffer_2_size=len(saved_mod.vertex_buffer_2),
                 texture_count=len(exported_materials.textures_array),
                 group_count=saved_mod.group_count,
                 group_data_array=saved_mod.group_data_array,
                 bone_palette_count=len(bone_palette_array),
                 bones_array_offset=bones_array_offset,
                 sphere_x=saved_mod.sphere_x,
                 sphere_y=saved_mod.sphere_y,
                 sphere_z=saved_mod.sphere_z,
                 sphere_w=saved_mod.sphere_w,
                 box_min_x=saved_mod.box_min_x,
                 box_min_y=saved_mod.box_min_y,
                 box_min_z=saved_mod.box_min_z,
                 box_min_w=saved_mod.box_min_w,
                 box_max_x=saved_mod.box_max_x,
                 box_max_y=saved_mod.box_max_y,
                 box_max_z=saved_mod.box_max_z,
                 box_max_w=saved_mod.box_max_w,
                 unk_01=saved_mod.unk_01,
                 unk_02=saved_mod.unk_02,
                 unk_03=saved_mod.unk_03,
                 unk_04=saved_mod.unk_04,
                 unk_05=saved_mod.unk_05,
                 unk_06=saved_mod.unk_06,
                 unk_07=saved_mod.unk_07,
                 unk_08=saved_mod.unk_08,
                 unk_09=saved_mod.unk_09,
                 unk_10=saved_mod.unk_10,
                 unk_11=saved_mod.unk_11,
                 unk_12=saved_mod.unk_12,
                 bones_array=saved_mod.bones_array,
                 bones_unk_matrix_array=saved_mod.bones_unk_matrix_array,
                 bones_world_transform_matrix_array=saved_mod.bones_world_transform_matrix_array,
                 bones_animation_mapping=saved_mod.bones_animation_mapping,
                 bone_palette_array=bone_palette_array,
                 textures_array=exported_materials.textures_array,
                 materials_data_array=exported_materials.materials_data_array,
                 meshes_array=exported_meshes.meshes_array,
                 num_weight_bounds=len(exported_meshes.weight_bounds),
                 weight_bounds=exported_meshes.weight_bounds,
                 vertex_buffer=exported_meshes.vertex_buffer,
                 vertex_buffer_2=saved_mod.vertex_buffer_2,
                 index_buffer=exported_meshes.index_buffer
                 )
    mod.group_offset = get_offset(mod, 'group_data_array')
    mod.textures_array_offset = get_offset(mod, 'textures_array')
    mod.meshes_array_offset = get_offset(mod, 'meshes_array')
    mod.vertex_buffer_offset = get_offset(mod, 'vertex_buffer')
    mod.vertex_buffer_2_offset = get_offset(mod, 'vertex_buffer_2')
    mod.index_buffer_offset = get_offset(mod, 'index_buffer')

    return ExportedMod(mod, exported_materials)


def _process_weights(weights_per_vertex, max_bones_per_vertex=4):
    """
    Given a dict `weights_per_vertex` with vertex_indices as keys and
    a list of tuples (bone_index, weight_value), iterate over values
    and process them to make them mtframework friendly:
    1) Limit bone weights: keep only up to `max_bones` elements, discarding the pairs that have the
       lowest influence. This is actually a limitation in albam for lack of
       understanding on how the engine treats vertices with more than 4 bone influencing it
    2) Normalize weights: make all weights sum up 1
    3) float to byte: convert the (-1.0, 1.0) to (0, 255)
    """
    # TODO: move to mtframework.utils
    new_weights_per_vertex = {}
    limit = max_bones_per_vertex
    for vertex_index, influence_list in weights_per_vertex.items():
        # limit max bones
        if len(influence_list) > limit:
            influence_list = sorted(influence_list, key=lambda t: t[1])[-limit:]

        # normalize
        weights = [t[1] for t in influence_list]
        bone_indices = [t[0] for t in influence_list]
        total_weight = sum(weights)
        if total_weight:
            weights = [(w / total_weight) for w in weights]

        # float to byte
        weights = [round(w * 255) or 1 for w in weights]  # can't have zero values
        # correct precision
        excess = sum(weights) - 255
        if excess:
            max_index, _ = max(enumerate(weights), key=lambda p: p[1])
            weights[max_index] -= excess

        new_weights_per_vertex[vertex_index] = list(zip(bone_indices, weights))

    return new_weights_per_vertex


def _get_normals_per_vertex(blender_mesh):
    normals = {}

    if blender_mesh.has_custom_normals:
        blender_mesh.calc_normals_split()
        for loop in blender_mesh.loops:
            normals.setdefault(loop.vertex_index, loop.normal)
    else:
        for vertex in blender_mesh.vertices:
            normals[vertex.index] = vertex.normal
    return normals


def _get_tangents_per_vertex(blender_mesh):
    tangents = {}
    try:
        uv_name = blender_mesh.uv_layers[0].name
    except IndexError:
        uv_name = ''
    blender_mesh.calc_tangents(uvmap=uv_name)
    for loop in blender_mesh.loops:
        tangents.setdefault(loop.vertex_index, loop.tangent)
    return tangents


def _export_vertices(blender_mesh_object, mesh_index, bone_palette, saved_mod):
    blender_mesh = blender_mesh_object.data
    vertex_count = len(blender_mesh.vertices)
    uvs_per_vertex = get_uvs_per_vertex(blender_mesh_object)
    weights_per_vertex = get_bone_indices_and_weights_per_vertex(blender_mesh_object)
    weights_per_vertex = _process_weights(weights_per_vertex)
    max_bones_per_vertex = max({len(data) for data in weights_per_vertex.values()}, default=0)
    normals = _get_normals_per_vertex(blender_mesh)
    tangents = _get_tangents_per_vertex(blender_mesh)

    VF = VERTEX_FORMATS_TO_CLASSES[max_bones_per_vertex]

    for vertex_index, (uv_x, uv_y) in uvs_per_vertex.items():
        # flipping for dds textures
        uv_y *= -1
        uv_x = pack_half_float(uv_x)
        uv_y = pack_half_float(uv_y)
        uvs_per_vertex[vertex_index] = (uv_x, uv_y)

    vertices_array = (VF * vertex_count)()
    has_bones = hasattr(VF, 'bone_indices')

    for vertex_index, vertex in enumerate(blender_mesh.vertices):
        vertex_struct = vertices_array[vertex_index]

        xyz = (vertex.co[0] * 100, vertex.co[1] * 100, vertex.co[2] * 100)
        xyz = z_up_to_y_up(xyz)
        if has_bones:
            # applying bounding box constraints
            xyz = vertices_export_locations(xyz, saved_mod)
            weights_data = weights_per_vertex.get(vertex_index, [])
            weight_values = [w for _, w in weights_data]
            bone_indices = [bone_palette.index(bone_index) for bone_index, _ in weights_data]
            array_size = ctypes.sizeof(vertex_struct.bone_indices)
            vertex_struct.bone_indices = (ctypes.c_ubyte * array_size)(*bone_indices)
            vertex_struct.weight_values = (ctypes.c_ubyte * array_size)(*weight_values)
        vertex_struct.position_x = xyz[0]
        vertex_struct.position_y = xyz[1]
        vertex_struct.position_z = xyz[2]
        vertex_struct.position_w = 32767
        try:
            # TODO: use a function with a good name (range conversion + y_up_to_z_up?)
            vertex_struct.normal_x = round(((normals[vertex_index][0] * 0.5) + 0.5) * 255)
            vertex_struct.normal_y = round(((normals[vertex_index][2] * 0.5) + 0.5) * 255)
            vertex_struct.normal_z = round(((normals[vertex_index][1] * -0.5) + 0.5) * 255)
            vertex_struct.normal_w = 255
            vertex_struct.tangent_x = round(((tangents[vertex_index][0] * 0.5) + 0.5) * 255)
            vertex_struct.tangent_y = round(((tangents[vertex_index][2] * 0.5) + 0.5) * 255)
            vertex_struct.tangent_z = round(((tangents[vertex_index][1] * -0.5) + 0.5) * 255)
            vertex_struct.tangent_w = 255
        except KeyError:
            # should not happen. TODO: investigate cases where it did happen
            print('Missing normal in vertex {}, mesh {}'.format(vertex_index, mesh_index))
        vertex_struct.uv_x = uvs_per_vertex.get(vertex_index, (0, 0))[0] if uvs_per_vertex else 0
        vertex_struct.uv_y = uvs_per_vertex.get(vertex_index, (0, 0))[1] if uvs_per_vertex else 0
    return vertices_array


def _create_bone_palettes(blender_mesh_objects):
    bone_palette_dicts = []
    MAX_BONE_PALETTE_SIZE = 32

    bone_palette = {'mesh_indices': set(), 'bone_indices': set()}
    for i, mesh in enumerate(blender_mesh_objects):
        # XXX case where bone names are not integers
        vertex_group_mapping = {vg.index: int(vg.name) for vg in mesh.vertex_groups}
        bone_indices = {vertex_group_mapping[vgroup.group] for vertex in mesh.data.vertices for vgroup in vertex.groups}

        msg = "Mesh {} is influenced by more than 32 bones, which is not supported".format(mesh.name)
        assert len(bone_indices) <= MAX_BONE_PALETTE_SIZE, msg

        current = bone_palette['bone_indices']
        potential = current.union(bone_indices)
        if len(potential) > MAX_BONE_PALETTE_SIZE:
            bone_palette_dicts.append(bone_palette)
            bone_palette = {'mesh_indices': {i}, 'bone_indices': set(bone_indices)}
        else:
            bone_palette['mesh_indices'].add(i)
            bone_palette['bone_indices'].update(bone_indices)

    bone_palette_dicts.append(bone_palette)

    final = OrderedDict([(frozenset(bp['mesh_indices']), sorted(bp['bone_indices']))
                        for bp in bone_palette_dicts])

    return final


def _infer_level_of_detail(name):
    LEVEL_OF_DETAIL_RE = re.compile(r'.*LOD_(?P<level_of_detail>\d+)$')
    match = LEVEL_OF_DETAIL_RE.match(name)
    if match:
        return int(match.group('level_of_detail'))
    return 1

def _get_shadow_method(blender_material):
    index = 0
    if blender_material:
        if not blender_material.shadow_method == 'NONE':
            index = 1
    return index

def _export_meshes(blender_meshes, bone_palettes, exported_materials, saved_mod):
    """
    No weird optimization or sharing of offsets in the vertex buffer.
    All the same offsets, different positions like pl0200.mod from
    uPl01ShebaCos1.arc
    No time to investigate why and how those are decided. I suspect it might have to
    do with location of the meshes
    """
    meshes_156 = (Mesh156 * len(blender_meshes))()
    vertex_buffer = bytearray()
    index_buffer = bytearray()
    materials_mapping = exported_materials.materials_mapping

    vertex_position = 0
    face_position = 0
    weight_bounds_list = []
    for mesh_index, blender_mesh_ob in enumerate(blender_meshes):
        level_of_detail = _infer_level_of_detail(blender_mesh_ob.name)
        bone_palette_index = 0
        bone_palette = []
        for bpi, (meshes_indices, bp) in enumerate(bone_palettes.items()):
            if mesh_index in meshes_indices:
                bone_palette_index = bpi
                bone_palette = bp
                break

        blender_mesh = blender_mesh_ob.data
        vertices_array = _export_vertices(blender_mesh_ob, mesh_index, bone_palette, saved_mod)
        vertex_buffer.extend(vertices_array)

        # TODO: is all this format conversion necessary?
        triangle_strips_python = triangles_list_to_triangles_strip(blender_mesh)
        # mod156 use global indices for verts, in case one only mesh is needed, probably
        triangle_strips_python = [e + vertex_position for e in triangle_strips_python]
        triangle_strips_ctypes = (ctypes.c_ushort * len(triangle_strips_python))(*triangle_strips_python)
        index_buffer.extend(triangle_strips_ctypes)

        vertex_count = len(blender_mesh.vertices)
        index_count = len(triangle_strips_python)

        m156 = meshes_156[mesh_index]
        try:
            blender_material = blender_mesh.materials[0]
            m156.material_index = materials_mapping[blender_material.name]
        except IndexError:
            # TODO: insert an empty generic material in this case
            raise ExportError('Mesh {} has no materials'.format(blender_mesh.name))
        m156.constant = 1
        m156.unk_render_group_index = blender_mesh.unk_render_group_index
        m156.level_of_detail = level_of_detail
        m156.vertex_format = CLASSES_TO_VERTEX_FORMATS[type(vertices_array[0])]
        m156.vertex_stride = 32
        m156.vertex_count = vertex_count
        m156.vertex_index_end = vertex_position + vertex_count - 1
        m156.vertex_index_start_1 = vertex_position
        m156.vertex_offset = 0
        m156.face_position = face_position
        m156.face_count = index_count
        m156.face_offset = 0
        m156.vertex_index_start_2 = vertex_position
        m156.vertex_group_count = len(blender_mesh_ob.vertex_groups)
        m156.bone_palette_index = bone_palette_index
        #m156.use_cast_shadows = int(blender_material.use_cast_shadows)
        m156.use_cast_shadows = int(_get_shadow_method(blender_material))
        vertex_position += vertex_count
        face_position += index_count

        for vg in sorted(blender_mesh_ob.vertex_groups, key=lambda vg: int(vg.name)):
            weight_bound = WeightBound(
                bone_id=int(vg.name),
                # TODO: will we ever figure this one out?
                unk_01=(ctypes.c_float * 3)(0, 0, 0),
                # TODO: calculate. Values seem in parent-bone space
                bsphere=(ctypes.c_float * 4)(0.1, 0.1, 0.1, 0.1),
                bbox_min=(ctypes.c_float * 4)(0.1, 0.1, 0.1, 0.1),
                bbox_max=(ctypes.c_float * 4)(0.2, 0.2, 0.2, 0.2),
                local_transform=(ctypes.c_float * 16)(1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1),
                # TODO: seems related to bbox_min/max
                unk_02=(ctypes.c_float * 4)(0, 0, 0, 0)
            )
            weight_bounds_list.append(weight_bound)

    weight_bounds = (WeightBound * len(weight_bounds_list))(*weight_bounds_list)
    vertex_buffer = (ctypes.c_ubyte * len(vertex_buffer)).from_buffer(vertex_buffer)
    index_buffer = (ctypes.c_ushort * (len(index_buffer) // 2)).from_buffer(index_buffer)
    return ExportedMeshes(meshes_156, vertex_buffer, index_buffer, weight_bounds)


def _export_textures_and_materials(blender_objects, saved_mod):
    '''blender_objects : bpy.data.objects['Pl0200.mod_0000_LOD_1']
       saved_mod : <albam_reloaded.engines.mtframework.mod_156.GenMod156 object>  
    '''
    textures = get_textures_from_blender_objects(blender_objects) # get a set of ShaderNodeTexImage
    blender_materials = get_materials_from_blender_objects(blender_objects) # get a set with blender_objects.data.materials

    textures_array = ((ctypes.c_char * 64) * len(textures))()
    materials_data_array = (MaterialData * len(blender_materials))()
    materials_mapping = {}  # blender_material.name: material_id
    texture_dirs = get_texture_dirs(saved_mod)
    default_texture_dir = get_default_texture_dir(saved_mod)

    for i, texture in enumerate(textures):
        #texture_dir = texture_dirs.get(texture.name)
        texture_dir = texture_dirs.get(texture.image.name)
        if not texture_dir:
            texture_dir = default_texture_dir
            texture_dirs[texture.name] = texture_dir
        # TODO: no default texture_dir means the original mod had no textures
        file_name = os.path.basename(bpy.path.abspath(texture.image.filepath))
        file_path = ntpath.join(texture_dir, file_name)
        try:
            file_path = file_path.encode('ascii')
        except UnicodeEncodeError:
            raise ExportError('Texture path {} is not in ascii'.format(file_path))
        if len(file_path) > 64:
            # TODO: what if relative path are used?
            raise ExportError('File path to texture {} is longer than 64 characters'
                              .format(file_path))

        file_path, _ = ntpath.splitext(file_path)
        textures_array[i] = (ctypes.c_char * 64)(*file_path)

    for mat_index, mat in enumerate(blender_materials):
        material_data = MaterialData() #get sructure with game data material fields
        # Setting uknown data
        # TODO: do this with a util function
        for field in material_data._fields_:
            attr_name = field[0]
            if not attr_name.startswith('unk_'):
                continue
            setattr(material_data, attr_name, getattr(mat, attr_name))

        ''' Old code    
        for texture_slot in mat.texture_slots:
            if not texture_slot or not texture_slot.texture:
                continue
            texture = texture_slot.texture
            # texture_indices expects index-1 based
            texture_index = textures.index(texture) + 1'''

        mat_tex = get_textures_from_the_material(mat) # get listh with imageTexturesnode of the material
        for texture_slot in mat_tex:
            if not texture_slot or not texture_slot.image:
                continue
            texture = texture_slot.image.name

            # texture_indices expects index-1 based
            mathes = [td for td in textures if td.image == texture_slot.image]
            #print(mathes[0])
            texture_index = textures.index(mathes[0]) + 1
            #texture_index = textures.index(texture_slot) + 1
            texture_code = blender_texture_to_texture_code(texture_slot)
            material_data.texture_indices[texture_code] = texture_index
        materials_data_array[mat_index] = material_data
        materials_mapping[mat.name] = mat_index

    return ExportedMaterials(textures_array, materials_data_array, materials_mapping, textures,
                             texture_dirs)
