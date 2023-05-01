from io import BytesIO
from ..engines.mtframework.mod_156 import Mod156

try:
    import bpy
except ImportError:
    pass
                
bone_names_spine = {
                    0:"root_ground",
                    1:"root",
                    2:"pelvis",
                    3:"spine_1",
                    4:"spine_2",
                    5:"neck",
                    6:"head"
                    }

bone_names_leg = {
                    0:"thigh",
                    1:"calf",
                    2:"foot",
                    3:"ball"
                    }
                
bone_names_leg_twist = { 
                        0: "thigh_twist",
                        1: "knee"
                        }
                
bone_names_arm = {
                    0:"clavicle",
                    1:"ctr_arm",
                    2:"loweram",
                    3:"ik_hand",
                    4:"hand"
                    }
                    
bone_names_arm_twist = {
                        0:"ctr_clavicle_twist",
                        1:"clavicle_twist",
                        2:"ctr_upperarm_twist",
                        3:"upperarm_twist",
                        4:"ctr_upperarm",
                        5:"upperarm",
                        6:"elbow",
                        7:"lowearm_twist",
                        8:"hand_twist"
                        }

bone_names_fingers = {
                        0:"hand_end",
                        1:"pinky",
                        2:"ring",
                        3:"middle",
                        4:"index",
                        5:"thumb"
                        }

bone_names_facial_base = {
                            0:"jaw",
                            1:"eye",
                            2:"eyelashes_upper"
                        }

bone_names_facial = {
                    0:"jaw",
                    1:"lip",
                    2:"nose",
                    3:"cheek",
                    4:"eye",
                    5:"eyelash",
                    6:"eyebrow"
}

bone_suffix = {
                0:"l",
                1:"r",
                2:"up",
                3:"low",
                4:"end"
}

bone_mapping = {
                0:"root",
                1:"lower_spine",
                2:"upper_spine",
                3:"neck",
                4:"head",
                5:"clavicle_r",
                6:"upper_arm_r",
                7:"arm_r",
                8:"wrist_r",
                9:"hand_r",
                10:"clavicle_l",
                11:"upper_arm_l",
                12:"arm_l",
                13:"wrist_l",
                14:"hand_l",
                15:"hips",
                16:"upper_leg_r",
                17:"leg_r",
                18:"foot_r",
                19:"toe_r",
                20:"upper_leg_l",
                21:"leg_l",
                22:"foot_l",
                23:"toe_l",
                24:"upper_thumb_r",
                25:"middle_thumb_r",
                26:"lower_thumb_r",
                27:"upper_index_r",
                28:"middle_index_r",
                29:"lower_index_r",
                30:"upper_middle_r",
                31:"middle_middle_r",
                32:"lower_middle_r",
                33:"palm_r",
                34:"upper_ring_r",
                35:"middle_ring_r",
                36:"lower_ring_r",
                37:"upper_pinky_r",
                38:"middle_pinky_r",
                39:"lower_pinly_r",
                40:"upper_thumb_l",
                41:"middle_thumb_l",
                42:"lower_thumb_l",
                43:"upper_index_l",
                44:"middle_index_l",
                45:"lower_index_l",
                46:"upper_middle_l",
                47:"middle_middle_l",
                48:"lower_middle_l",
                49:"palm_l",
                50:"upper_ring_l",
                51:"middle_ring",
                52:"lower_ring_l",
                53:"upper_pinky_l",
                54:"middle_pinky_l",
                55:"lower_pinky_l",
                56:"eye_r",
                57:"eye_l",
                58:"eyelid_r",
                59:"eyelid_l",
                60:"jaw",
                62:"shoulder_deform_r",
                63:"elbow_defom_r",
                64:"shoulder_deform_l",
                65:"elbow_deform_l",
                66:"butt_cheek_r",
                67:"butt_cheel_l",
                68:"knee_r",
                69:"knee_l",
                70:"upper_arm_deform_1_r",
                71:"upper_arm_deform_2_r",
                72:"upper_arm_deform_3_r",
                73:"upper_arm_deform_4_r",
                74:"arm_deform_1_r",
                75:"arm_deform_2_r",
                76:"upper_arm_deform_1_l",
                77:"upper_arm_deform_2_l",
                78:"upper_arm_deform_3_l",
                79:"upper_arm_deform_4_l",
                80:"arm_deform_1_l",
                81:"arm_deform_2_l",
                100:"thumb_r",
                101:"thumb_l",
                180:"inner_eyebrow_r",
                181:"outer_eyebrow_r",
                182:"inner_eyebrow_l",
                183:"outer_eyebrow_l",
                184:"lower_eyelid_r",
                185:"lower_eyelid_l",
                186:"upper_cheek_r",
                187:"upper_cheek_l",
                188:"upper_outer_cheek_r",
                189:"upper_outer_cheek_l",
                190:"nose_r",
                191:"nose_l",
                192:"outer_lip_r",
                193:"upper_lip_r",
                194:"upper_lip",
                195:"upper_lip_l",
                196:"outer_lip_l",
                197:"outer_lower_lip_l",
                198:"lower_lip",
                199:"lower_lip_l",
                200:"lower_cheek_r",
                201:"lower_cheek_l"
}

def rename_bones(armature):
    pose_bones = armature.pose.bones
    parent_blender_object = armature.parent
    saved_mod = Mod156(file_path=BytesIO(parent_blender_object.albam_imported_item.data))
    bones_array = saved_mod.bones_array
    i = 0
    for b in bones_array:
        if bone_mapping.get(b.anim_map_index):
            if i==0:
                x, y, z = pose_bones[i].head
                if (x, y, z) == (0, 0, 0):#if exist ground root bone
                    pose_bones[i].name = "root_ground"
            else:
                name = (bone_mapping.get(b.anim_map_index))
                pose_bones[i].name = name
        i += 1