from ctypes import (
    Structure,
    LittleEndianStructure,
    c_uint, c_uint8, c_uint16, c_float, c_char, c_short, c_ushort, c_byte, c_ubyte,
)

from ...engines.mtframework.defaults import DEFAULT_MATERIAL, DEFAULT_MESH
from ...lib.structure import DynamicStructure
from ...registry import blender_registry


def unk_data_depends_on_other_unk(tmp_struct):
    if tmp_struct.unk_08:
        return c_ubyte * (tmp_struct.bones_array_offset - 176)
    else:
        return c_ubyte * 0


class Mod156(DynamicStructure):
    _fields_ = (('id_magic', c_char * 4),
                ('version', c_ubyte),
                ('version_rev', c_byte),
                ('bone_count', c_ushort),
                ('mesh_count', c_short),
                ('material_count', c_ushort),
                ('vertex_count', c_uint),
                ('face_count', c_uint),
                ('edge_count', c_uint),
                ('vertex_buffer_size', c_uint),
                ('vertex_buffer_2_size', c_uint),
                ('texture_count', c_uint),
                ('group_count', c_uint),
                ('bone_palette_count', c_uint),
                ('bones_array_offset', c_uint),
                ('group_offset', c_uint),
                ('textures_array_offset', c_uint),
                ('meshes_array_offset', c_uint),
                ('vertex_buffer_offset', c_uint),
                ('vertex_buffer_2_offset', c_uint),
                ('index_buffer_offset', c_uint),
                ('reserved_01', c_uint),
                ('reserved_02', c_uint),
                ('sphere_x', c_float),
                ('sphere_y', c_float),
                ('sphere_z', c_float),
                ('sphere_w', c_float),
                ('box_min_x', c_float),
                ('box_min_y', c_float),
                ('box_min_z', c_float),
                ('box_min_w', c_float),
                ('box_max_x', c_float),
                ('box_max_y', c_float),
                ('box_max_z', c_float),
                ('box_max_w', c_float),
                ('unk_01', c_uint),
                ('unk_02', c_uint),
                ('unk_03', c_uint),
                ('unk_04', c_uint),
                ('unk_05', c_uint),
                ('unk_06', c_uint),
                ('unk_07', c_uint),
                ('unk_08', c_uint),
                ('unk_09', c_uint),
                ('unk_10', c_uint),
                ('unk_11', c_uint),
                ('reserved_03', c_uint),
                ('unk_vtx8_01', lambda s: Unk8Block01 * s.unk_10),
                ('unk_vtx8_02', lambda s: Unk8Block02 * s.unk_09),
                ('unk_vtx8_03', lambda s: Unk8Block03 * s.unk_08),
                ('bones_array', lambda s: Bone * s.bone_count),
                ('bones_unk_matrix_array', lambda s: (c_float * 16) * s.bone_count),
                ('bones_world_transform_matrix_array', lambda s: (c_float * 16) * s.bone_count),
                ('bones_animation_mapping', lambda s: (c_ubyte * 256) if s.bone_palette_count else c_ubyte * 0),
                ('bone_palette_array', lambda s: BonePalette * s.bone_palette_count),
                ('group_data_array', lambda s: GroupData * s.group_count),
                ('textures_array', lambda s: (c_char * 64) * s.texture_count),
                ('materials_data_array', lambda s: MaterialData * s.material_count),
                ('meshes_array', lambda s: Mesh156 * s.mesh_count),
                ('num_weight_bounds', c_uint),
                ('weight_bounds', lambda s: WeightBound * s.num_weight_bounds),
                ('vertex_buffer', lambda s: c_ubyte * s.vertex_buffer_size),
                ('vertex_buffer_2', lambda s: c_ubyte * s.vertex_buffer_2_size),
                # TODO: investigate the padding
                ('index_buffer', lambda s: c_ushort * (s.face_count - 1)),
                )

class Unk8Block01(Structure):
    _fields_ = (('unk_01', c_ushort),
                ('unk_02', c_ushort),
                )

class Unk8Block02(Structure):
    _fields_ = (('pos_x', c_ushort),
                ('pos_y', c_ushort),
                ('pos_z', c_ushort),
                ('pos_w', c_ushort),
                ('unk_00', c_uint),
                ('unk_01', c_uint),
                )

class Unk8Block03(Structure):
    _fields_ = (('unk_00', c_ushort),
                ('unk_01', c_ushort),
                ('unk_02', c_ushort),
                ('unk_03', c_ushort),
                )

class Unk8Block03(Structure):
    _fields_ = (('unk_01', c_uint),
                ('unk_02', c_uint),
                )

class Bone(Structure):
    _fields_ = (('anim_map_index', c_ubyte),
                ('parent_index', c_ubyte),  # 255: root
                ('mirror_index', c_ubyte),
                ('palette_index', c_ubyte),
                ('unk_01', c_float),
                ('parent_distance', c_float),
                # Relative to the parent bone
                ('location_x', c_float),
                ('location_y', c_float),
                ('location_z', c_float),
                )


class BonePalette(Structure):
    _fields_ = (('unk_01', c_uint),
                ('values', c_ubyte * 32),
                )

    _comments_ = {'unk_01': 'Seems to be the count of meaninful values out of the 32 bytes, needs verification'}


class GroupData(Structure):
    _fields_ = (('group_index', c_uint),
                ('unk_02', c_float),
                ('unk_03', c_float),
                ('unk_04', c_float),
                ('unk_05', c_float),
                ('unk_06', c_float),
                ('unk_07', c_float),
                ('unk_08', c_float),
                )
    _comments_ = {'group_index': "In ~25% of all RE5 mods, this value doesn't match the index"}


@blender_registry.register_bpy_prop('material', 'unk_')
class MaterialData(Structure):
    _defaults_ = DEFAULT_MATERIAL
    _fields_ = (('unk_01_flag_01', c_uint16, 1), # previously c_ushort
                ('unk_01_flag_02', c_uint16, 1),
                ('unk_01_flag_03', c_uint16, 1),# brige geometry
                ('unk_01_flag_04', c_uint16, 1),
                ('unk_01_flag_05', c_uint16, 1),
                ('unk_01_flag_06', c_uint16, 1), #alpha clip
                ('unk_01_no_alpha', c_uint16, 1),#opaque
                ('unk_01_flag_08', c_uint16, 1), #translusent
                ('unk_01_alpha_transparency', c_uint16, 1),#alpha transparency
                ('unk_01_flag_10', c_uint16, 1),
                ('unk_01_flag_11', c_uint16, 1),
                ('unk_01_flag_12', c_uint16, 1),
                ('unk_01_flag_13', c_uint16, 1),
                ('unk_01_flag_14', c_uint16, 1),
                ('unk_01_flag_15', c_uint16, 1),
                ('unk_01_flag_16', c_uint16, 1),
                ('unk_flag_01', c_uint16, 1),
                ('unk_flag_02', c_uint16, 1),
                ('unk_flag_03', c_uint16, 1),
                ('unk_flag_04', c_uint16, 1),
                ('unk_flag_05', c_uint16, 1),
                ('unk_flag_06', c_uint16, 1),
                ('unk_flag_07', c_uint16, 1),
                ('unk_flag_08', c_uint16, 1),
                ('unk_flag_09', c_uint16, 1),
                ('unk_flag_10', c_uint16, 1),
                ('unk_flag_11', c_uint16, 1),
                ('unk_flag_8_bones_vertex', c_uint16, 1),
                ('unk_flag_13', c_uint16, 1),
                ('unk_flag_14', c_uint16, 1),
                ('unk_flag_15', c_uint16, 1),
                ('unk_flag_16', c_uint16, 1),
                ('unk_02_flag_01',  c_uint16, 1),#'unk_02', c_short
                ('unk_02_flag_02',  c_uint16, 1),
                ('unk_02_flag_03',  c_uint16, 1),
                ('unk_02_flag_04',  c_uint16, 1),
                ('unk_02_flag_05',  c_uint16, 1),
                ('unk_02_flag_06',  c_uint16, 1),
                ('unk_02_flag_07',  c_uint16, 1),
                ('unk_02_do_not_use_AM_as_emmisive',  c_uint16, 1),
                ('unk_02_use_AM_as_emmisive',  c_uint16, 1),
                ('unk_02_flag_10',  c_uint16, 1),
                ('unk_02_do_not_use_detail_map',  c_uint16, 1),
                ('unk_02_use_detail_map',  c_uint16, 1),
                ('unk_02_flag_13',  c_uint16, 1),
                ('unk_02_flag_14',  c_uint16, 1),
                ('unk_02_flag_15',  c_uint16, 1),# env cubemap flag
                ('unk_02_flag_16',  c_uint16, 1),
                ('unk_03', c_short), 
                ('unk_04', c_ushort),
                ('unk_05', c_ushort),
                ('unk_06', c_ushort),
                ('unk_07', c_ushort),
                ('unk_08', c_ushort),
                ('unk_09', c_ushort),
                ('unk_10', c_ushort), # 0 or 65535
                ('unk_11', c_ushort), # 0 or 65535
                ('texture_indices', c_uint * 8),
                ('unk_f_01', c_float),
                ('unk_f_02', c_float),
                ('unk_f_03', c_float), # specular power ? 0.0 - 0.04
                ('unk_f_04', c_float), # glossnes level ?
                ('unk_f_05', c_float), # specular contrast ? 1.0 - 250
                ('unk_cubemap_roughness', c_float), # 7 for glasses
                ('unk_f_07', c_float),
                ('unk_f_08', c_float),
                ('unk_f_09', c_float),
                ('unk_f_10', c_float),
                ('unk_detail_power', c_float),
                ('unk_detail_factor', c_float),
                ('unk_f_13', c_float),
                ('unk_f_14', c_float),
                ('unk_f_15', c_float),
                ('unk_f_16', c_float),
                ('unk_f_17', c_float),
                ('unk_f_18', c_float),
                ('unk_f_19', c_float),
                ('unk_f_20', c_float),
                ('unk_normalmap_green_channel', c_float), # NormalMapFlip -1 or 1
                ('unk_f_22', c_float),
                ('unk_f_23', c_float),
                ('unk_f_24', c_float),
                ('unk_f_25', c_float),
                ('unk_f_26', c_float),)


class WeightBound(Structure):
    _fields_ = (
        ('bone_id', c_uint),
        ('unk_01', c_float * 3),
        ('bsphere', c_float * 4),
        ('bbox_min', c_float * 4),
        ('bbox_max', c_float * 4),
        ('oabb_matrix', c_float * 16),
        ('oabb_dimension', c_float * 4)
    )


@blender_registry.register_bpy_prop('mesh', 'unk_')
class Mesh156(LittleEndianStructure):
    _defaults_ = DEFAULT_MESH
    _fields_ = (('unk_render_group_index', c_ushort),
                ('material_index', c_ushort),
                ('constant', c_ubyte),  # always 1
                ('level_of_detail', c_ubyte),
                ('unk_z_order', c_ubyte),
                ('vertex_format', c_ubyte),
                ('vertex_stride', c_ubyte),
                ('unk_02', c_ubyte), # vertex_stride_2
                ('unk_03', c_ubyte),
                ('unk_flag_01', c_uint8, 1),
                ('unk_flag_02', c_uint8, 1),
                ('unk_flag_03', c_uint8, 1),
                ('unk_flag_04', c_uint8, 1),
                ('unk_flag_05', c_uint8, 1),
                ('use_cast_shadows', c_uint8, 1),
                ('unk_flag_06', c_uint8, 1),
                ('unk_flag_07', c_uint8, 1),
                ('vertex_count', c_ushort),
                ('vertex_index_end', c_ushort),
                ('vertex_index_start_1', c_uint), #vertex_position_2
                ('vertex_offset', c_uint),
                ('unk_05', c_uint), #vertex_offset
                ('face_position', c_uint),
                ('face_count', c_uint),
                ('face_offset', c_uint),
                ('unk_06', c_ubyte),
                ('unk_07', c_ubyte),
                ('vertex_index_start_2', c_ushort), #vertex_position
                ('vertex_group_count', c_ubyte),
                ('bone_palette_index', c_ubyte),
                ('unk_08', c_ubyte),
                ('unk_09', c_ubyte),
                ('unk_10', c_ushort),
                ('unk_11', c_ushort),
                )


class VertexFormat0(Structure):
    _fields_ = (('position_x', c_float),
                ('position_y', c_float),
                ('position_z', c_float),
                ('normal_x', c_ubyte),
                ('normal_y', c_ubyte),
                ('normal_z', c_ubyte),
                ('normal_w', c_ubyte),
                ('tangent_x', c_ubyte),
                ('tangent_y', c_ubyte),
                ('tangent_z', c_ubyte),
                ('tangent_w', c_ubyte),
                ('uv_x', c_ushort),  # half float
                ('uv_y', c_ushort),  # half float
                ('uv2_x', c_ushort),  # half float
                ('uv2_y', c_ushort),  # half float
                ('uv3_x', c_ushort),  # half float argb vertex color for static meshes
                ('uv3_y', c_ushort),  # half float argb vertex color for static meshes
                #('vertex_color_r', c_ubyte),
                #('vertex_color_g', c_ubyte),
                #('vertex_color_b', c_ubyte),
                #('vertex_color_a', c_ubyte),
                )


class VertexFormat(Structure):
    # http://forum.xentax.com/viewtopic.php?f=10&t=3057&start=165
    _fields_ = (('position_x', c_short),
                ('position_y', c_short),
                ('position_z', c_short),
                ('position_w', c_short),
                ('bone_indices', c_ubyte * 4),
                ('weight_values', c_ubyte * 4),
                ('normal_x', c_ubyte),
                ('normal_y', c_ubyte),
                ('normal_z', c_ubyte),
                ('normal_w', c_ubyte),
                ('tangent_x', c_ubyte),
                ('tangent_y', c_ubyte),
                ('tangent_z', c_ubyte),
                ('tangent_w', c_ubyte),
                ('uv_x', c_ushort),  # half float
                ('uv_y', c_ushort),  # half float
                ('uv2_x', c_ushort),  # half float
                ('uv2_y', c_ushort),  # half float
                )


class VertexFormat2(VertexFormat):
    pass


class VertexFormat3(VertexFormat):
    pass


class VertexFormat4(VertexFormat):
    pass


class VertexFormat5(Structure):
    _fields_ = (('position_x', c_short),
                ('position_y', c_short),
                ('position_z', c_short),
                ('position_w', c_short),
                ('bone_indices', c_ubyte * 8),
                ('weight_values', c_ubyte * 8),
                ('normal_x', c_ubyte),
                ('normal_y', c_ubyte),
                ('normal_z', c_ubyte),
                ('normal_w', c_ubyte),
                ('uv_x', c_ushort),  # half float
                ('uv_y', c_ushort),  # half float
                )


class VertexFormat6(VertexFormat5):
    pass


class VertexFormat7(VertexFormat5):
    pass


class VertexFormat8(VertexFormat5):
    pass


VERTEX_FORMATS_TO_CLASSES = {0: VertexFormat0,
                             1: VertexFormat,
                             2: VertexFormat2,
                             3: VertexFormat3,
                             4: VertexFormat4,
                             5: VertexFormat5,
                             6: VertexFormat6,
                             7: VertexFormat7,
                             8: VertexFormat8,
                             }


CLASSES_TO_VERTEX_FORMATS = {v: k for k, v in VERTEX_FORMATS_TO_CLASSES.items()}
