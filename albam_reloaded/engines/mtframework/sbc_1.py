from ctypes import (
    Structure,
    LittleEndianStructure,
    c_int,
    c_uint, c_uint8, c_uint16, c_float, c_char, c_short, c_ushort, c_byte, c_ubyte,
)

from ...lib.structure import DynamicStructure
from ...registry import blender_registry

class RE5v4quad(Structure):
    _fields_ = (('a_min',c_float * 4),
                ('a_max',c_float * 4),
                ('b_min',c_float * 4),
                ('b_max',c_float * 4),
                ('id_a',c_ubyte),
                ('id_b',c_ubyte),
                ('id_c',c_ubyte),
                ('id_d',c_ubyte),
                ('id_e',c_ubyte),
                ('id_f',c_ubyte),
                ('id_g',c_ubyte),
                ('id_h',c_byte),
                ('id_s',c_byte * 8),
                )

class SBCgroup(Structure):
    _fields_ = (('base', c_uint),
                ('start_tris', c_uint),
                ('start_boxes', c_uint),
                ('start_vertices', c_uint),
                ('group_id', c_uint),
                ('box_a', c_float * 6),
                ('box_b', c_float* 6),
                ('box_c', c_float * 6),
                ('id_a', c_ushort),
                ('id_b', c_ushort),
                )

class RE5triangle(Structure):
    _fields_ = (('a', c_ushort),
                ('b', c_ushort),
                ('c', c_ushort),
                ('id_a', c_ushort),
                ('id_b', c_ushort),
                ('id_c', c_ushort),
                ('id_d', c_ushort),
                ('id_e', c_ushort),
                ('id_f', c_ushort),
                ('id_g', c_ushort),
                ('id_h', c_ushort),
                ('id_i', c_ushort),
                ('id_j', c_ushort),
                ('id_k', c_ushort),
                )

class RE5vertices(Structure):
    _fields_ = (('position_x', c_float),
                ('position_y', c_float),
                ('position_z', c_float),
                ('position_w', c_float),
                )

class SBC1(DynamicStructure):
    _fields_ = (('id_magic', c_char * 4),
                ('unk_num_01',c_ushort),
                ('boxcount', c_ushort),
                ('unk_num_02', c_ushort),
                ('unk_num_03', c_ushort),
                ('mvtc', c_uint),
                ('facecount', c_uint),
                ('ncount', c_uint),
                ('bbox', c_float * 6),
                ('boxes', lambda s: RE5v4quad * s.mvtc),
                ('groups', lambda s: SBCgroup * s.boxcount),
                ('triangles', lambda s: RE5triangle * s.facecount),
                ('vertices', lambda s: RE5vertices * s.ncount),
                )

