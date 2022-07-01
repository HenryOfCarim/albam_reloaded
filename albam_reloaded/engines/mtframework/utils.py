from ast import Return
import ctypes
from collections import Counter
import ntpath

from albam_reloaded.engines.mtframework import tex

from ...exceptions import BuildMeshError
from ...engines.mtframework.mod_156 import (
    VERTEX_FORMATS_TO_CLASSES,
    )
from ...lib.structure import get_size


def get_vertices_array(mod, mesh):
    try:
        VF = VERTEX_FORMATS_TO_CLASSES[mesh.vertex_format]
    except KeyError:
        raise TypeError('Unrecognized vertex format: {}'.format(hex(mesh.vertex_format)))
    if mod.version == 156:
        position = max(mesh.vertex_index_start_1, mesh.vertex_index_start_2) * mesh.vertex_stride
        if mesh.vertex_index_start_2 > mesh.vertex_index_start_1:
            vertex_count = mesh.vertex_index_end - mesh.vertex_index_start_2 + 1
            # TODO: research the content of mesh.vertex_index_start_1 and what it means in this case
            # So far it looks it contains only garbage; all vertices have the same values.
            # It's unknown why they exist for, and why they count for mesh.vertex_count
            # The imported meshes here will have a different mesh count than the original.
        else:
            vertex_count = mesh.vertex_count
    elif mod.version == 210:
        position = mesh.vertex_index * ctypes.sizeof(VF)
        vertex_count = mesh.vertex_count
    else:
        raise TypeError('Unsupported mod version: {}'.format(mod.version))
    offset = ctypes.addressof(mod.vertex_buffer)
    offset += mesh.vertex_offset
    offset += position
    return (VF * vertex_count).from_address(offset)


def get_indices_array(mod, mesh):
    offset = ctypes.addressof(mod.index_buffer)
    position = mesh.face_offset * 2 + mesh.face_position * 2
    index_buffer_size = get_size(mod, 'index_buffer')
    if position > index_buffer_size:
        raise BuildMeshError('Error building mesh in get_indices_array (out of bounds reference)'
                             'Size of mod.indices_buffer: {} mesh.face_offset: {}, mesh.face_position: {}'
                             .format(index_buffer_size, mesh.face_offset, mesh.face_position))
    offset += position
    return (ctypes.c_ushort * mesh.face_count).from_address(offset)


def get_non_deform_bone_indices(mod):
    bone_indices = {i for i, _ in enumerate(mod.bones_array)}
    active_bone_indices = {mod.bone_palette_array[mod.meshes_array[mesh_index].bone_palette_index].values[bone_index]
                           for mesh_index, mesh in enumerate(mod.meshes_array)
                           for i, vert in enumerate(get_vertices_array(mod, mod.meshes_array[mesh_index]))
                           for bone_index in vert.bone_indices
                           }

    return bone_indices.difference(active_bone_indices)


def vertices_export_locations(xyz_tuple, model_bounding_box):
    x, y, z = xyz_tuple

    x -= model_bounding_box.min_x
    x /= (model_bounding_box.max_x -  model_bounding_box.min_x)
    x *= 32767

    y -= model_bounding_box.min_y
    y /= (model_bounding_box.max_y - model_bounding_box.min_y)
    y *= 32767

    z -= model_bounding_box.min_z
    z /= (model_bounding_box.max_z - model_bounding_box.min_z)
    z *= 32767

    return (round(x), round(y), round(z))


def transform_vertices_from_bbox(vertex_format, mod):
    x = vertex_format.position_x
    y = vertex_format.position_y
    z = vertex_format.position_z

    x  = x / 32767 * (mod.box_max_x - mod.box_min_x) + mod.box_min_x
    y  = y / 32767 * (mod.box_max_y - mod.box_min_y) + mod.box_min_y
    z  = z / 32767 * (mod.box_max_z - mod.box_min_z) + mod.box_min_z

    return (x, y, z)


def get_bone_parents_from_mod(bone, bones_array):
    parents = []
    parent_index = bone.parent_index
    child_bone = bone
    if parent_index != 255:
        parents.append(parent_index)
    while parent_index != 255:
        child_bone = bones_array[child_bone.parent_index]
        parent_index = child_bone.parent_index
        if parent_index != 255:
            parents.append(parent_index)
    return parents


def texture_code_to_blender_texture(texture_code, blender_texture_slot, blender_material):
    ''' 
        Function for detecting texture type and map it to blender shader sockets
        texture_code : index for detecting type of a texture
        blender_texture_slot : image texture node
        blender_material : shader material
    '''
    #blender_texture_slot.use_map_alpha = True
    principled_node = blender_material.node_tree.nodes.get('Principled BSDF')
    link = blender_material.node_tree.links.new

    if texture_code == 0:
        # Diffuse
        link(blender_texture_slot.outputs['Color'], principled_node.inputs['Base Color'])
        link(blender_texture_slot.outputs['Alpha'], principled_node.inputs['Alpha'])
        blender_texture_slot.location =(-300, 350)
        #blender_texture_slot.use_map_color_diffuse = True
    elif texture_code == 1:
        # Normal
        # Since normal maps have offset channels, they need to be rearranged for Blender
        nm_separateRGB_n = blender_material.node_tree.nodes.new('ShaderNodeSeparateRGB')
        nm_separateRGB_n.location =(-860, -550)
        nm_combineRGB_n = blender_material.node_tree.nodes.new('ShaderNodeCombineRGB')
        nm_combineRGB_n.location = (-670, -500)

        blender_texture_slot.location = (-1150, -450)
        link(blender_texture_slot.outputs['Color'], nm_separateRGB_n.inputs['Image'])
        link(blender_texture_slot.outputs['Alpha'], nm_combineRGB_n.inputs['R']) # set normal node to shader socket
        link(nm_separateRGB_n.outputs['G'], nm_combineRGB_n.inputs['G'])
        link(nm_separateRGB_n.outputs['B'], nm_combineRGB_n.inputs['B'])

        dt_normal_n = blender_material.node_tree.nodes.get('Normal Map')
        #If a detail map was created before normal map
        if dt_normal_n:
            print("see normal node from a detail map(?) on the normal creation")
            dt_combineRGB_n = dt_normal_n.inputs['Color'].links[0].from_node
            dt_mixRGB = blender_material.node_tree.nodes.new('ShaderNodeMixRGB')
            dt_mixRGB.location = (-470, -250)
            link(dt_combineRGB_n.outputs['Image'],dt_mixRGB.inputs['Color1'])
            link(nm_combineRGB_n.outputs['Image'],dt_mixRGB.inputs['Color2'])
            link(dt_mixRGB.outputs['Color'],dt_normal_n.inputs['Color'])
        else:
            normal_map_node = blender_material.node_tree.nodes.new("ShaderNodeNormalMap")
            normal_map_node.location = (-200, -260)
            link(nm_combineRGB_n.outputs['Image'], normal_map_node.inputs['Color'])

        link(normal_map_node.outputs['Normal'], principled_node.inputs['Normal']) # set normal node to shader socket

    elif texture_code == 2:
        # Specular
        blender_texture_slot.location =(-600, 60)
        invert_spec_node = blender_material.node_tree.nodes.new('ShaderNodeInvert')
        invert_spec_node.location = (-330, 60)

        link(blender_texture_slot.outputs['Color'], invert_spec_node.inputs['Color'])
        link(invert_spec_node.outputs['Color'], principled_node.inputs['Roughness'])

    elif texture_code == 7:
        #Detail normal map
        blender_texture_slot.location =(-1150, -130)
        dt_tex_coord_n = blender_material.node_tree.nodes.new('ShaderNodeTexCoord') 
        dt_tex_coord_n.location = (-1550, -340)
        dt_mapping_n = blender_material.node_tree.nodes.new('ShaderNodeMapping')
        dt_mapping_n.location = (-1350, -340)

        # link detail map multiplier to the custom material property
        for x in range(3):
            d = dt_mapping_n.inputs[3].driver_add("default_value", x)
            var1 = d.driver.variables.new()
            var1.name = "detail_multiplier"
            var1.targets[0].id_type = 'MATERIAL'
            var1.targets[0].id = blender_material
            var1.targets[0].data_path = '["unk_detail_factor"]'
            d.driver.expression = var1.name

        
        dt_separateRGB_n = blender_material.node_tree.nodes.new('ShaderNodeSeparateRGB')
        dt_separateRGB_n.location = (-860, -260)
        dt_combineRGB_n = blender_material.node_tree.nodes.new('ShaderNodeCombineRGB')
        dt_combineRGB_n.location =(-670, -220)

        link(dt_tex_coord_n.outputs['UV'], dt_mapping_n.inputs['Vector'])
        link(dt_mapping_n.outputs['Vector'], blender_texture_slot.inputs['Vector'])
        
        link(blender_texture_slot.outputs['Color'], dt_separateRGB_n.inputs['Image'])
        link(blender_texture_slot.outputs['Alpha'], dt_combineRGB_n.inputs['R'])
        link(dt_separateRGB_n.outputs['G'], dt_combineRGB_n.inputs['G'])
        link(dt_separateRGB_n.outputs['B'], dt_combineRGB_n.inputs['B'])

        nm_normal_n = blender_material.node_tree.nodes.get('Normal Map') # check if normal node is already exist
        if nm_normal_n: # in case the normal map was created before a detail map
            dt_mixRGB = blender_material.node_tree.nodes.new('ShaderNodeMixRGB')
            dt_mixRGB.location = (-470, -250)
            link(dt_combineRGB_n.outputs['Image'],dt_mixRGB.inputs['Color1'])
            nm_combineRGB_n = nm_normal_n.inputs['Color'].links[0].from_node # get combine RGB link from the normal map inputs
            link(dt_mixRGB.outputs['Color'],nm_normal_n.inputs['Color'])
            link(nm_combineRGB_n.outputs['Image'], dt_mixRGB.inputs['Color2'])
        else: 
            dt_normal_n = blender_material.node_tree.nodes.new("ShaderNodeNormalMap") # create a new normal map node
            dt_normal_n.location = (-200, -130)
            link(dt_combineRGB_n.outputs['Image'], dt_normal_n.inputs['Color'])
            link(dt_normal_n.outputs['Normal'], principled_node.inputs['Normal'])
    else:
        print('texture_code not supported', texture_code)
        #blender_texture_slot.use_map_color_diffuse = False # deprecated
        # 5 - cubemap
        # TODO: 3, 4, 5, 6,


def blender_texture_to_texture_code(blender_texture_image_node):
    '''This function return a type ID of the image texture node dependind of node connetion
        blender_texture_image_node : bpy.types.ShaderNodeTexImage
    '''
    texture_code = 0
    color_out = blender_texture_image_node.outputs['Color'] 
    alpha_out = blender_texture_image_node.outputs['Alpha']
    vector_in = blender_texture_image_node.inputs['Vector']

    color_socket = None
    alpha_socket = None
    vector_socket = None

    if color_out.links:
        color_socket = (color_out.links[0].to_node.name)

    if alpha_out.links:
        alpha_socket = (alpha_out.links[0].to_node.name)

    if vector_in.links:
        vector_socket =(vector_in.links[0].from_node.name)

    # Diffuse
    if color_socket and alpha_socket == "Principled BSDF":
        texture_code = 0

    # Normal
    elif (not vector_socket and
         alpha_socket == "Combine RGB"):
        texture_code = 1

    # Specular
    elif color_socket == "Invert":
        texture_code = 2

    # Detail normal map
    elif (vector_socket == 'Mapping'):
        texture_code = 7

    return texture_code


def get_texture_dirs(mod):
    """Returns a dict of <texture_name>: <texture_dir>"""
    texture_dirs = {}
    for texture_path in mod.textures_array:
        texture_path = texture_path[:].decode('ascii').partition('\x00')[0]
        texture_dir, texture_name_no_ext = ntpath.split(texture_path)
        texture_dirs[texture_name_no_ext] = texture_dir
    return texture_dirs


def get_default_texture_dir(mod):
    if not mod.textures_array:
        return None
    texture_dirs = []
    for texture_path in mod.textures_array:
        texture_path = texture_path[:].decode('ascii').partition('\x00')[0]
        texture_dir = ntpath.split(texture_path)[0]
        texture_dirs.append(texture_dir)

    return Counter(texture_dirs).most_common(1)[0][0]
