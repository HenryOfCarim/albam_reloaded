import ctypes
from collections import Counter
import ntpath

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


def vertices_export_locations(xyz_tuple, bounding_box_width, bounding_box_height, bounding_box_length):
    x, y, z = xyz_tuple

    x += bounding_box_width / 2
    try:
        x /= bounding_box_width
    except ZeroDivisionError:
        pass
    if x > 1.0:
        x = 32767
    else:
        x *= 32767

    try:
        y /= bounding_box_height
    except ZeroDivisionError:
        pass
    if y > 1.0:
        y = 32767
    else:
        y *= 32767

    z += bounding_box_length / 2
    try:
        z /= bounding_box_length
    except ZeroDivisionError:
        pass
    if z > 1.0:
        z = 32767
    else:
        z *= 32767

    return (round(x), round(y), round(z))


def transform_vertices_from_bbox(vertex_format, bounding_box_width, bounding_box_height, bounding_box_length):
    x = vertex_format.position_x
    y = vertex_format.position_y
    z = vertex_format.position_z

    x *= bounding_box_width
    x /= 32767
    x -= bounding_box_width / 2

    y *= bounding_box_height
    y /= 32767

    z *= bounding_box_length
    z /= 32767
    z -= bounding_box_length / 2

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
    principled_node = blender_material.node_tree.nodes.get("Principled BSDF")
    link = blender_material.node_tree.links.new

    if texture_code == 0:
        # Diffuse
        link(blender_texture_slot.outputs['Color'], principled_node.inputs['Base Color'])
        link(blender_texture_slot.outputs['Alpha'], principled_node.inputs['Alpha'])
        blender_texture_slot.location =(-300, 300)
        #blender_texture_slot.use_map_color_diffuse = True
    elif texture_code == 1:
        # Normal
        # Since normal maps have offset channels, they need to be rearranged for Blender
        rgb_separate_node = blender_material.node_tree.nodes.new('ShaderNodeSeparateRGB')
        rgb_separate_node.location =(-600, -600)
        rgb_combine_node = blender_material.node_tree.nodes.new('ShaderNodeCombineRGB')
        rgb_combine_node.location = (-400, -500)

        normal_map_node = blender_material.node_tree.nodes.new("ShaderNodeNormalMap")
        normal_map_node.location = (-200, -400)
        blender_texture_slot.location = (-900, -500)
        
        link(blender_texture_slot.outputs['Color'], rgb_separate_node.inputs['Image'])
        link(blender_texture_slot.outputs['Alpha'], rgb_combine_node.inputs['R']) # set normal node to shader socket
        link(rgb_separate_node.outputs['G'], rgb_combine_node.inputs['G'])
        link(rgb_separate_node.outputs['B'], rgb_combine_node.inputs['B'])
        link(rgb_combine_node.outputs['Image'], normal_map_node.inputs['Color'])
        link(normal_map_node.outputs['Normal'], principled_node.inputs['Normal']) # set normal node to shader socket

        ''' Old code
        blender_texture_slot.use_map_color_diffuse = False
        blender_texture_slot.use_map_normal = True
        blender_texture_slot.normal_factor = 0.05'''
    elif texture_code == 2:
        # Specular
        # No sure should it have this Specular to Roughness conversion
        blender_texture_slot.location =(-500, -10)
        invert_spec_node = blender_material.node_tree.nodes.new('ShaderNodeInvert')
        invert_spec_node.location = (-200, -10)

        link(blender_texture_slot.outputs['Color'], invert_spec_node.inputs['Color'])
        link(invert_spec_node.outputs['Color'], principled_node.inputs['Roughness'])
        ''' Old code
        blender_texture_slot.use_map_color_diffuse = False
        blender_texture_slot.use_map_specular = True
        blender_material.specular_intensity = 0.0'''
    elif texture_code == 7:
        # cube map normal
        # maybe detail normal map
        detail_normal_map_node = blender_material.node_tree.nodes.new("ShaderNodeNormalMap")
        detail_normal_map_node.space = ('WORLD')
        detail_normal_map_node.location = (-200, -200)
        blender_texture_slot.projection = 'BOX'
        blender_texture_slot.location =(-900, -200)
        #link(detail_normal_map_node.outputs['Normal'], principled_node.inputs['Normal']) # set normal node to shader socket
        link(blender_texture_slot.outputs['Color'], detail_normal_map_node.inputs['Color'])
        ''' Old code
        blender_texture_slot.use_map_color_diffuse = False
        blender_texture_slot.use_map_normal = True
        blender_texture_slot.normal_factor = 0.05
        blender_texture_slot.texture_coords = 'GLOBAL'
        blender_texture_slot.mapping = 'CUBE'''
    else:
        print('texture_code not supported', texture_code)
        #blender_texture_slot.use_map_color_diffuse = False # deprecated
        # TODO: 3, 4, 5, 6,


def blender_texture_to_texture_code(blender_texture_slot):
    '''This function return a type ID of the image texture node dependind of node connetion
        blender_texture_slot : bpy.types.ShaderNodeTexImage
    '''
    texture_code = 0
    color_out = blender_texture_slot.outputs['Color'] 
    alpha_out = blender_texture_slot.outputs['Alpha']

    color_socket = (color_out.links[0].to_node.name)
    alpha_socket = None
    if alpha_out.links:
        alpha_socket = (alpha_out.links[0].to_node.name)

    # Diffuse
    #if blender_texture_slot.use_map_color_diffuse:
    if color_socket and alpha_socket == "Principled BSDF":
        texture_code = 0

    # Normal
    #elif blender_texture_slot.projection and blender_texture_slot.texture_coords == 'UV':
    elif (blender_texture_slot.projection == 'FLAT' and
         alpha_socket == "Combine RGB"):
        texture_code = 1

    # Specular
    #elif blender_texture_slot.use_map_specular:
    elif color_socket == "Invert":
        texture_code = 2

    # Cube normal # Detail map
    #elif (blender_texture_slot.use_map_normal and
    #      blender_texture_slot.texture_coords == 'GLOBAL' and
    #      blender_texture_slot.mapping == 'CUBE'):
    elif (blender_texture_slot.projection == 'BOX' and
          alpha_socket == None):
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
