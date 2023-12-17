from io import BytesIO
from ..engines.mtframework.mod_156 import Mod156

try:
    import bpy
except ImportError:
    pass

bone_mapping = {
                0:"root",
                1:"spine_lower",
                2:"spine_upper",
                3:"neck",
                4:"head",
                5:"clavicle_r",
                6:"upperarm_r",
                7:"lowerarm_r",
                8:"wrist_r",
                9:"hand_r",
                10:"clavicle_l",
                11:"upperarm_l",
                12:"lowerarm_l",
                13:"wrist_l",
                14:"hand_l",
                15:"pelvis",
                16:"thigh_r",
                17:"calf_r",
                18:"foot_r",
                19:"toe_r",
                20:"thigh_l",
                21:"calf_l",
                22:"foot_l",
                23:"toe_l",
                24:"thumb_01_r",
                25:"thumb_02_r",
                26:"thumb_03_r",
                27:"index_01_r",
                28:"index_02_r",
                29:"index_03_r",
                30:"middle_01_r",
                31:"middle_02_r",
                32:"middle_03_r",
                33:"palm_r",
                34:"ring_01_r",
                35:"ring_02_r",
                36:"ring_03_r",
                37:"pinky_01_r",
                38:"pinky_02_r",
                39:"pinky_03_r",
                40:"thumb_01_l",
                41:"thumb_02_l",
                42:"thumb_03_l",
                43:"index_01_l",
                44:"index_02_l",
                45:"index_03_l",
                46:"middle_01_l",
                47:"middle_02_l",
                48:"middle_03_l",
                49:"palm_l",
                50:"ring_01_l",
                51:"ring_02_l",
                52:"ring_03_l",
                53:"pinky_01_l",
                54:"pinky_02_l",
                55:"pinky_03_l",
                56:"eye_r",
                57:"eye_l",
                58:"eyelid_upper_r",
                59:"eyelid_upper_l",
                60:"jaw",
                62:"clavicle_deform_r",
                63:"elbow_r",
                64:"clavicle_deform_l",
                65:"elbow_l",
                66:"butt_cheek_r",
                67:"butt_cheek_l",
                68:"knee_r",
                69:"knee_l",
                70:"ctr_upperarm_deform_1_r",
                71:"upperarm_deform_1_r",
                72:"ctr_upperarm_deform_2_r",
                73:"upperarm_deform_2_r",
                74:"lowerarm_deform_1_r",
                75:"lowerarm_deform_2_r",
                76:"ctr_upperarm_deform_1_l",
                77:"upperarm_deform_1_l",
                78:"ctr_upperarm_deform_2_l",
                79:"upperarm_deform_2_l",
                80:"lowerarm_deform_1_l",
                81:"lowerarm_deform_2_l",
                #100:"thumb_r", # for chris
                #101:"thumb_l", # for chris
                #102:"lip_lower_2_r",
                #103:"lip_lower_1_r",
                #104:"lip_lower",
                #105:"lip_lower_2_l",
                #106:"lip_lower_1_l",
                #107:"lip_corner_l",
                #108:"ev_lip_below_lower",
                #109:"ev_chin",
                #110:"ev_lip_below_lower_r",
                #111:"ev_lip_below_lower_l",
                #112:"ev_tongue_tip",
                #113:"ev_tongue_base",
                #114:"ev_jaw_r",
                #115:"ev_double_chin",
                #116:"ev_jaw_l",
                #117:"ev_eye_r",
                #118:"ev_eye_l",
                #119:"ev_lip_upper_corner_r",
                120:"ctr_breast_r", # can be middle
                121:"breast_r", # can be middle
                122:"ctr_breast_l",
                123:"breast_l",
                #124:"ev_lip_upper_2_l",
                #125:"ev_lip_upper_corner_l",
                #126:"ev_lip_above_upper_r",
                #127:"ev_lip_above_upper",
                #128:"ev_lip_above_upper_l",
                #129:"ev_nostril_r",
                #130:"ev_nose_tip",
                #131:"ev_nostril_l",
                #142:"ev_nose_hump",
                #147:"ev_eyelash_lower_3_r",
                #148:"ev_eyelash_lower_2_r",
                #149:"ev_eyelash_lower_1_r",
                #165:"ev_eyebrow_3_r",
                #166:"ev_eyebrow_2_r",
                #167:"ev_eyebrow_1_r",
                #168:"ev_nose_bridge",
                #169:"ev_eyebrow_1_l",
                #170:"ev_eyebrow_2_l",
                #171:"ev_eyebrow_3_l",
                #172:"ev_forehead_r",
                #173:"ev_forehead",
                #174:"ev_forehead_l",
                #177:"ev_teeth_upper",
                #178:"ev_teeth_lower",
                180:"eyebrow_01_r",
                181:"eyebrow_02_r",
                182:"eyebrow_01_l",
                183:"eyebrow_02_l",
                184:"eyelid_lower_r",
                185:"eyelid_lower_l",
                186:"cheek_upper_r",
                187:"cheek_upper_l",
                188:"cheek_upper_outer_r",
                189:"cheek_upper_outer_l",
                190:"nose_r",
                191:"nose_l",
                192:"lip_corner_r",
                193:"lip_upper_r",
                194:"lip_upper",
                195:"lip_upper_l",
                196:"lip_corner_l",
                197:"lip_lower_r",
                198:"lip_lower",
                199:"lip_lower_l",
                200:"cheek_lower_r",
                201:"cheek_lower_l"
}

head_bone_mapping = {
                    0:"root",
                    1:"spine_lower",
                    2:"spine_upper",
                    3:"neck",
                    4:"head",
                    5:"clavicle_r",
                    6:"upperarm_r",
                    7:"lowerarm_r",
                    8:"wrist_r",
                    9:"hand_r",
                    10:"clavicle_l",
                    11:"upperarm_l",
                    12:"lowerarm_l",
                    13:"wrist_l",
                    14:"hand_l",
                    15:"pelvis",
                    16:"thigh_r",
                    17:"calf_r",
                    18:"foot_r",
                    19:"toe_r",
                    20:"thigh_l",
                    21:"calf_l",
                    22:"foot_l",
                    23:"toe_l",
                    24:"thumb_01_r",
                    25:"thumb_02_r",
                    26:"thumb_03_r",
                    27:"index_01_r",
                    28:"index_02_r",
                    29:"index_03_r",
                    30:"middle_01_r",
                    31:"middle_02_r",
                    32:"middle_03_r",
                    33:"palm_r",
                    34:"ring_01_r",
                    35:"ring_02_r",
                    36:"ring_03_r",
                    37:"pinky_01_r",
                    38:"pinky_02_r",
                    39:"pinky_03_r",
                    40:"thumb_01_l",
                    41:"thumb_02_l",
                    42:"thumb_03_l",
                    43:"index_01_l",
                    44:"index_02_l",
                    45:"index_03_l",
                    46:"middle_01_l",
                    47:"middle_02_l",
                    48:"middle_03_l",
                    49:"palm_l",
                    50:"ring_01_l",
                    51:"ring_02_l",
                    52:"ring_03_l",
                    53:"pinky_01_l",
                    54:"pinky_02_l",
                    55:"pinky_03_l",
                    56:"pl_eye_r",
                    57:"pl_eye_l",
                    58:"eyelid_upper_r",
                    59:"eyelid_upper_l",
                    60:"jaw",
                    62:"clavicle_deform_r",
                    63:"elbow_r",
                    64:"clavicle_deform_l",
                    65:"elbow_l",
                    66:"butt_cheek_r",
                    67:"butt_cheek_l",
                    68:"knee_r",
                    69:"knee_l",
                    70:"ctr_upperarm_deform_1_r",
                    71:"upperarm_deform_1_r",
                    72:"ctr_upperarm_deform_2_r",
                    73:"upperarm_deform_2_r",
                    74:"lowerarm_deform_1_r",
                    75:"lowerarm_deform_2_r",
                    76:"ctr_upperarm_deform_1_l",
                    77:"upperarm_deform_1_l",
                    78:"ctr_upperarm_deform_2_l",
                    79:"upperarm_deform_2_l",
                    80:"lowerarm_deform_1_l",
                    81:"lowerarm_deform_2_l",
                    100:"jaw", 
                    101:"lip_lower_3_r", 
                    102:"lip_lower_2_r",
                    103:"lip_lower_1_r",
                    104:"lip_lower",
                    105:"lip_lower_1_l",
                    106:"lip_lower_2_l",
                    107:"lip_lower_3_l",
                    108:"lip_below_lower",
                    109:"chin",
                    110:"lip_below_lower_r",
                    111:"lip_below_lower_l",
                    112:"tongue_base",
                    113:"tongue_tip",
                    114:"jaw_r",
                    115:"double_chin",
                    116:"jaw_l",
                    117:"eye_l",
                    118:"eye_r",
                    119:"lip_upper_3_r",
                    120:"lip_upper_2_r",
                    121:"lip_upper_1_r",
                    122:"lip_upper",
                    123:"lip_upper_1_l",
                    124:"lip_upper_2_l",
                    125:"lip_upper_3_l",
                    126:"lip_above_upper_r",
                    127:"lip_above_upper",
                    128:"lip_above_upper_l",
                    129:"nostril_r",
                    130:"nose_tip",
                    131:"nostril_l",
                    132:"lip_hump_r",
                    133:"nose_wrinkle_lower_02_r",
                    134:"nose_wrinkle_lower_01_r",
                    135:"nose_wrinkle_lower_01_l",
                    136:"nose_wrinkle_lower_02_l",
                    137:"lip_hump_l",
                    138:"cheek_r",
                    139:"cheekbone_upper_r",
                    140:"cheekbone_lower_r",
                    141:"nose_wrinkle_upper_r",
                    142:"nose_hump",
                    143:"nose_wrinkle_upper_l",
                    144:"cheekbone_lower_l",
                    145:"cheekbone_upper_l",
                    146:"cheek_l",
                    147:"eyelid_lower_3_r",
                    148:"eyelid_lower_2_r",
                    149:"eyelid_lower_1_r",
                    150:"eyelid_lower_1_l",
                    151:"eyelid_lower_2_l",
                    152:"eyelid_lower_3_l",
                    153:"eyelid_upper_3_r",
                    154:"eyelid_upper_2_r",
                    155:"eyelid_upper_1_r",
                    156:"eyelid_upper_1_l",
                    157:"eyelid_upper_2_l",
                    158:"eyelid_upper_3_l",
                    159:"eyelash_upper_3_r",
                    160:"eyelash_upper_2_r",
                    161:"eyelash_upper_1_r",
                    162:"eyelash_upper_1_l",
                    163:"eyelash_upper_2_l",
                    164:"eyelash_upper_3_l",
                    165:"eyebrow_3_r",
                    166:"eyebrow_2_r",
                    167:"eyebrow_1_r",
                    168:"nose_bridge",
                    169:"eyebrow_1_l",
                    170:"eyebrow_2_l",
                    171:"eyebrow_3_l",
                    172:"forehead_r",
                    173:"forehead",
                    174:"forehead_l",
                    175:"eye_side_r",
                    176:"eye_side_l",
                    177:"teeth_upper",
                    178:"teeth_lower",
                    180:"eyebrow_01_r",
                    181:"eyebrow_02_r",
                    182:"eyebrow_01_l",
                    183:"eyebrow_02_l",
                    184:"eyelid_lower_r",
                    185:"eyelid_lower_l",
                    186:"pl_cheek_upper_r",
                    187:"pl_cheek_upper_l",
                    188:"pl_cheek_upper_outer_r",
                    189:"pl_cheek_upper_outer_l",
                    190:"pl_nose_r",
                    191:"pl_nose_l",
                    192:"pl_lip_corner_lower_r",
                    193:"pl_lip_upper_r",
                    194:"pl_lip_upper",
                    195:"pl_lip_upper_l",
                    196:"pl_lip_corner_lower_l",
                    197:"pl_lip_outer_lower_l",
                    198:"pl_lip_lower",
                    199:"pl_lip_lower_l",
                    200:"pl_cheek_lower_r",
                    201:"pl_cheek_lower_l"
}


def rename_bones(armature):
    pose_bones = armature.pose.bones
    armature_name = armature.name
    parent_blender_object = armature.parent 
    saved_mod = Mod156(file_path=BytesIO(parent_blender_object.albam_imported_item.data))
    bones_array = saved_mod.bones_array
    bone_map_array = bone_mapping 
    if not armature_name.find("evf") == -1:
        bone_map_array = head_bone_mapping
    if len(pose_bones) == len(saved_mod.bones_array):
        i = 0
        for b in bones_array:
            if bone_map_array.get(b.anim_map_index):
                name = (bone_map_array.get(b.anim_map_index))
                if i == 0:
                    x, y, z = pose_bones[i].head
                    if (x, y, z) == (0, 0, 0):#if exist ground root bone
                        name = "root_ground"
                pose_bones[i].name = name
            i += 1
    else:
        raise TypeError("Can't perform renaming because imported and current armature doesn't match")