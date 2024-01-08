from ctypes import c_int, c_uint, c_char, c_short, c_float, c_ubyte, sizeof
import os

from ...exceptions import ExportError
from ...image_formats.dds import DDSHeader, DDS
from ...lib.structure import DynamicStructure
from ...registry import blender_registry
from ...engines.mtframework.defaults import DEFAULT_TEXTURE


COMPRESSED_FORMATS = (
    "DXT1",
    "DXT5",
    b"DXT1",
    b"DXT5",
)

UNCOMPRESSED_TAG = b"\x15"


@blender_registry.register_bpy_prop('texture', 'unk_')
class Tex112(DynamicStructure):

    ID_MAGIC = b'TEX'
    _defaults_ = DEFAULT_TEXTURE
    _fields_ = (('id_magic', c_char * 4),
                ('version', c_short),
                ('revision', c_short),  # TODO: This is probably contains flags, e.g. cubemap doesn't work with 34
                ('mipmap_count', c_ubyte),
                ('image_count', c_ubyte),
                ('unk_byte_1', c_ubyte),
                ('unk_byte_2', c_ubyte),
                ('width', c_short),
                ('height', c_short),
                ('reserved_1', c_int),
                ('compression_format', c_char * 4),
                ('unk_f_red', c_float),
                ('unk_f_green', c_float),
                ('unk_f_blue', c_float),
                ('unk_f_alpha', c_float),
                ("floats_unk", lambda s: c_float * 27 if s.image_count > 1 else c_ubyte * 0),
                ('mipmap_offsets', lambda s: c_uint * (s.mipmap_count * s.image_count)),
                ('dds_data', lambda s, f: c_ubyte * (os.path.getsize(f) - 40 -
                 sizeof(s.mipmap_offsets)) if f else c_ubyte * len(s.dds_data)),
                )

    def to_dds(self):
        if self.compression_format == UNCOMPRESSED_TAG:
            is_compressed = False
            pixel_fmt = b""
        else:
            is_compressed = True
            pixel_fmt = self.compression_format
        is_cubemap = self.image_count > 1
        header = DDSHeader(dwHeight=self.height, dwWidth=self.width,
                           dwMipMapCount=self.mipmap_count,
                           pixelfmt_dwFourCC=pixel_fmt)
        header.set_constants()
        header.set_variables(compressed=is_compressed, cubemap=is_cubemap)
        dds = DDS(header=header, data=self.dds_data)
        return dds

    @classmethod
    def from_dds(cls, file_path):
        with open(file_path, 'rb') as f:
            magic = f.read(4)
        if magic != b"DDS ":
            raise ExportError("Exported texture {} is not a .dds image".format(file_path))
        dds = DDS(file_path=file_path)
        mipmap_count = dds.header.dwMipMapCount
        width = dds.header.dwWidth
        height = dds.header.dwHeight
        dds_fmt = dds.header.pixelfmt_dwFourCC
        compression_format = dds_fmt or UNCOMPRESSED_TAG
        image_count = 6 if dds.header.is_proper_cubemap else 1
        fixed_size_of_header = 40
        start_offset = fixed_size_of_header + (mipmap_count * 4 * image_count)
        if image_count > 1:
            start_offset += (27 * 4)
        mipmap_offsets = cls.calculate_mipmap_offsets(mipmap_count, width, height, dds_fmt, start_offset, image_count)
        try:
            assert len(mipmap_offsets) // image_count == mipmap_count
        except:
            raise TypeError('There is no mipmap in {}'.format(file_path))
        mipmap_offsets = (c_uint * len(mipmap_offsets))(*mipmap_offsets)
        dds_data = (c_ubyte * len(dds.data)).from_buffer(dds.data)

        tex = cls(id_magic=cls.ID_MAGIC,
                  version=112,
                  revision=34 if not image_count > 1 else 3,  # TODO: proper flags
                  mipmap_count=mipmap_count,
                  image_count=image_count,
                  width=width,
                  height=height,
                  compression_format=compression_format,
                  mipmap_offsets=mipmap_offsets,
                  dds_data=dds_data)

        return tex

    @classmethod
    def from_multiple_dds(cls, version=112, *file_paths):
        return (cls.from_dds(file_path) for file_path in file_paths)

    @staticmethod
    def calculate_mipmap_offsets(mipmap_count, width, height, fmt, start_offset, image_count):
        offsets = [start_offset]
        current_offset = start_offset
        for im in range(image_count):
            for i in range(mipmap_count):
                # Don't calculate last offset since we already start with one extra
                if im == image_count - 1 and i == mipmap_count - 1:
                    break
                size = DDSHeader.calculate_mipmap_size(width, height, i, fmt)
                current_offset += size
                offsets.append(current_offset)
        return offsets
