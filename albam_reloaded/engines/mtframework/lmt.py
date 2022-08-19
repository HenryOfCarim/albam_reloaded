from collections import defaultdict
from ctypes import Structure, sizeof, c_uint, c_float, c_ushort, c_ubyte, addressof, c_longlong

from ...lib.structure import DynamicStructure, get_offset


def get_block_info_array(structure):
    non_null_offsets = [o for o in structure.block_offset_array if o]
    return AnimBlockInfo * len(non_null_offsets)


def get_frames_buffer(structure, file_path):
    buff = open(file_path, 'rb')
    size = 0
    buff.seek(structure.block_info_array[0].offset)
    initial_pos = buff.tell()
    for i, block in enumerate(structure.block_info_array):
        frames_info = (AnimFrame * block.bone_count)()
        buff.readinto(frames_info)
        buffer_size = sum(f.buffer_size for f in frames_info)
        if frames_info[0].buffer_offset < buff.tell():
            buffer_size = 0
        if buffer_size:
            buff.seek(buffer_size, 1)
        tot_size = sizeof(frames_info) + buffer_size
        size += tot_size
        extra_1 = block.count_01 * 8
        extra_2 = block.count_02 * 8
        if extra_1:
            buff.read(extra_1)
        if extra_2:
            buff.read(extra_2)
        size += extra_1 + extra_2

    buff.seek(initial_pos)
    return c_ubyte * size


class LMTVec3Frame(Structure):
    _fields_ = (('x', c_float),
                ('y', c_float),
                ('z', c_float)
                )

    def decompress(self):
        return self.x, self.y, self.z


class LMTQuatFramev14(Structure):
    _fields_ = (('i_value', c_longlong),
                #('i_value_2', c_float),
                )

    def decompress(self):
        pow_14 = (2 ** 14) - 1
        src = self.i_value

        num = src & pow_14
        if num > 8191:
            num -= pow_14
        real = num / 4096

        num = (src >> 14) & pow_14
        if num > 8191:
            num -= pow_14
        k = num / 4096

        num = ((src >> 14) >> 14) & pow_14
        if num > 8191:
            num -= pow_14
        j = num / 4096

        num = (((src >> 14) >> 14) >> 14) & pow_14
        if num > 8191:
            num -= pow_14
        i = num / 4096

        return (real, i, j, k)


class AnimFrame(Structure):

    _fields_ = (('buffer_type', c_ubyte),
                ('usage', c_ubyte),
                ('joint_type', c_ubyte),
                ('bone_index', c_ubyte),
                ('unk_01', c_float),
                ('buffer_size', c_uint),
                ('buffer_offset', c_uint),
                ('reference_data', c_float * 4),
                )


class AnimBlockInfo(Structure):

    _fields_ = (('offset', c_uint),
                ('bone_count', c_uint),
                ('frame_count', c_uint),
                ('unk_01', c_uint * 25),
                ('count_01', c_uint),
                ('offset_01', c_uint),
                ('unk_02', c_uint * 16),
                ('count_02', c_uint),
                ('offset_02', c_uint),
                )


class LMT(DynamicStructure):
    ID_MAGIC = b'LMT'

    _fields_ = (('ID', c_uint,),
                ('version', c_ushort),
                ('block_count', c_ushort),
                ('block_offset_array', lambda s: (s.block_count) * c_uint),
                ('padding', lambda s: c_ubyte * ((16 - (sizeof(s) & 15)) & 15)),
                ('block_info_array', get_block_info_array),
                ('frames_buffer', get_frames_buffer),
                )

    def read_frame_buffer(self, block_index):
        final_frames = []
        block = self.block_info_array[block_index]
        base_address = addressof(self.frames_buffer)
        base_offset = get_offset(self, 'frames_buffer')

        """
        print('bloci index', block_index, 'bone_count', block.bone_count)
        print('block.unk_01', block.unk_01[:])
        print('block.unk_02', block.unk_02[:])
        print('count_01', block.count_01)
        print('count_02', block.count_02)
        print('offset_01', block.offset_01)
        print('offset_02', block.offset_02)
        print()
        print()
        """
        frames_info = (AnimFrame * block.bone_count).from_address(base_address)
        for frame_info in frames_info:
            buffer_relative_offset = frame_info.buffer_offset - base_offset
            buffer_address = base_address + buffer_relative_offset
            frame_cls = self._get_frame_class(frame_info.buffer_type)
            if not frame_cls:
                continue
            frame_count = frame_info.buffer_size // sizeof(frame_cls)
            # print('frame_count', frame_count, 'buffer_size', frame_info.buffer_size)
            if frame_info.buffer_type == 2:
                print('[frame_info]: bone_index:', frame_info.bone_index,
                      'buffer_type', frame_info.buffer_type,
                      'joint_type', frame_info.joint_type,
                      'usage', frame_info.usage)

            if frame_count > 200:
                print('error in frame')
                print('error in frame')
                print('error in frame')
                print('error in frame')
                print('error in frame')
                print('error in frame')
                print('error in frame')
                continue
            frame = (frame_cls * frame_count).from_address(buffer_address)
            final_frames.append((frame_info, frame))

        return final_frames

    def _get_frame_class(self, buffer_type):
        if buffer_type == 6:
            cls = LMTQuatFramev14
        elif buffer_type == 2:
            cls = LMTVec3Frame
        else:
            cls = None
            print('unsupported buffer_type: {}'.format(buffer_type))
        return cls

    def _get_track_type(self, frame_info):
        is_ik = False
        if frame_info.buffer_type == 6:
            data_type = 'rotation'
            is_ik = False
        elif frame_info.buffer_type == 2 and frame_info.bone_index != 0:
            data_type = 'location'
            is_ik = True
        elif frame_info.buffer_type == 2 and frame_info.bone_index == 0:
            data_type = 'location'
            is_ik = False
        else:
            data_type = None
        return data_type, is_ik

    def decompress(self):
        """
        Return a dict with bone ids as keys and a dict of tracks:
            {<bone_id>: {'rotation': [<frame_1>, <frame_2>, ...]
                         'location': [<frame_1>, <frame_2>, ...]
                         }
           }
           where a frame in rotation is a tuple of w,x,y,z values (quaternions)
           and a frame in location is ?
        """
        animations = []
        for i, _ in enumerate(self.block_info_array):
            tracks = defaultdict(lambda: {'rotation': [],
                                          'location': [],
                                          'is_ik': False,
                                          })

            frames = self.read_frame_buffer(i)
            for frame_info, frames in frames:
                track_type, is_ik = self._get_track_type(frame_info)
                frame_data = [f.decompress() for f in frames]
                tracks[frame_info.bone_index]['is_ik'] = is_ik
                tracks[frame_info.bone_index][track_type].extend(frame_data)
            animations.append(tracks)
        return animations
