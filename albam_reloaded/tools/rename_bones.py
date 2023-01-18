from io import BytesIO
from ..engines.mtframework.mod_156 import Mod156

try:
    import bpy
except ImportError:
    pass



left_bones = []
middle_bones = []

spine = None
left_thigh = None
hand = None
                
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

def _get_bones_from_group(group_name, bones):
    group_bones = []
    for bone in bones:
        if bone.bone_group.name == group_name:
            group_bones.append(bone)
    return group_bones
                
def _get_group_bones_from_chain(bones_in_group, chain):
    bones = []
    for element in chain:
        if element in bones_in_group:
            bones.append(element)
    return bones

def _round_values(values):
    list = []
    for v in values:
        v = round(v,3)
        list.append(v)
    return list

def _side_filter(bone_group, *side):
    bones = []
    if not side:
        for b in bone_group:
            x, y, x = b.head 
            if round(b.head[0], 3) == 0:
                bones.append(b)
            #print("middle bones {}".format(mb.name))
    if "left" in side:
        for b in bone_group:
            x, y, x = b.head 
            if round(b.head[0], 3) > 0:
                bones.append(b)        
    return bones

def rename_bones(armature):
    pose_bones = armature.pose.bones
    parent_blender_object = armature.parent
    saved_mod = Mod156(file_path=BytesIO(parent_blender_object.albam_imported_item.data))
    bones_array = saved_mod.bones_array
    for b in bones_array:
        print("index is {} mirror index is {}".format(b.anim_map_index, b.mirror_index))

    group_bones = _get_bones_from_group('Main', pose_bones)
    left_bones = _side_filter(group_bones, 'left')
    middle_bones = _side_filter(group_bones)

    #get spine and left thigh bones
    skip = 0
    x, y, z = middle_bones[0].head
    if (x, y, z) == (0, 0, 0):#if exist ground root bone
        middle_bones[0].name = bone_names_spine[0]
        skip = 1

    middle_bones[0+skip].name = bone_names_spine[1]    
    childrens = middle_bones[0+skip].children
    for ch in childrens:
        gch = ch.children
        for g in gch:
            if g in left_bones:
                #print("grandchildren{}".format(g))
                ch.name = bone_names_spine[2]
                left_thigh  = g
                g.name = bone_names_leg[0]
            if g in middle_bones:
                ch.name = bone_names_spine[3] #"Spine_1"
                spine = ch

    #rename leg chain
    leg_chain = left_thigh.children_recursive
    bones_in_group = _get_group_bones_from_chain(left_bones, leg_chain)
    bone = left_thigh
    for i in range(len(bones_in_group)):
        ch = bone.children
        for c in ch:
            if c in left_bones:
                c.name = bone_names_leg[i+1]
                bone = c

    #rename spine chain
    spine_chain = spine.children_recursive
    bones_in_group = _get_group_bones_from_chain(middle_bones,spine_chain)
    bone = None
    for i in range(len(bones_in_group)):
        if i == 0:
            bone = spine
        ch = bone.children
        for c in ch:
            if c in middle_bones:
                c.name = bone_names_spine[i+4]
                bone = c
                if c.name == bone_names_spine[4]:
                    spine_1 = c

    #rename arm chain
    arm_chain = spine_1.children_recursive
    bones_in_group = _get_group_bones_from_chain(left_bones,arm_chain)
    bone = None
    for i in range(len(bones_in_group)):
        if i == 0:
            bone = spine_1
        ch = bone.children
        for c in ch:
            if c in left_bones:
                if i == 4:
                    hand = c
                c.name = bone_names_arm[i]
                bone = c

    #rename arm twist       
    bone_group = _get_bones_from_group('Arms', pose_bones)
    left_bones = _side_filter(bone_group, 'left')
    middle_bones = _side_filter(bone_group)

    for b in left_bones:
        parent = b.parent
        child = b.children
        offset = round(b.head[0], 3)
        children = b.children_recursive
        if parent.name == bone_names_arm[0]:  #clavicle_twist
            b.name = bone_names_arm_twist[1]
        elif parent.name == bone_names_arm[1]:
            if child:
                if round(parent.head[0], 3) == offset: # uppearm_twist
                    b.name = bone_names_arm_twist[2]
                    child[0].name = bone_names_arm_twist[3]
                else:
                    b.name = bone_names_arm_twist[4] #upperarm
                    child[0].name = bone_names_arm_twist[5]
            else:
                b.name =  bone_names_arm_twist[6]
        elif parent.name == bone_names_arm[2]:
            if round(parent.head[0], 3) == offset: #lowearm_twist
                print("lowerarm")
                b.name = bone_names_arm_twist[7] 
            else:
                b.name = bone_names_arm_twist[8] # hand_twist

    #rename leg twist            
    bone_group = _get_bones_from_group('Legs', pose_bones)
    left_bones = _side_filter(bone_group, "left")
    middle_bones = _side_filter(bone_group)

    for b in left_bones:
        parent = b.parent
        child = b.children
        offset = round(b.head[0], 3)
        if parent.name == bone_names_spine[2]:
            b.name = bone_names_leg_twist[0]
        elif parent.name == bone_names_leg[0]:
            b.name = bone_names_leg_twist[1]

    #rename fingers        
    bone_group = _get_bones_from_group('Hands', pose_bones)
    left_bones = _side_filter(bone_group, 'left')
    finger_bones = []
    finger_bones = [b for b in hand.children]

    for b in finger_bones:
        chain = b.children_recursive
        if len(chain)>3: # pinky and ring
            b.name = bone_names_fingers[0]
            childredn = b.children
            y_pos =[]
            bones = {}
            finger_bones.remove(b)
            print("there is {}".format(len(finger_bones)))
            for c in childredn:
                y_pos.append(c.head[0])
                bones[c.head[0]] = c
                print("child is {}".format(c))
            y_pos.sort()
            for i in range(len(y_pos)):
                parent_bone = bones[y_pos[i]]
                print("parent_bone {}".format(parent_bone))
                parent_bone.name = bone_names_fingers[i+1] + "_01" # name paretn pinky and ring
                parent_bone_children = parent_bone.children_recursive
                j = 2
                for ch in parent_bone_children:
                    ch.name = bone_names_fingers[i+1] + "_0" + str(j)
                    j += 1
        if len(finger_bones)==3: # thumb_chain
            x_pos = []
            bones = {}
            for c in finger_bones:
                x_pos.append(c.head[0])
                bones[c.head[0]] = c
            x_pos.sort()
            thumb_bone = bones[x_pos[0]]
            finger_bones.remove(thumb_bone)
            thumb_bone.name = bone_names_fingers[5] + "_01"
            thumb_bone_children = thumb_bone.children_recursive
            j = 2
            for ch in thumb_bone_children:
                ch.name = bone_names_fingers[5] + "_0" + str(j)
                j += 1
        if len(finger_bones) < 3: # middle chain
            print("start 1")
            y_pos = []
            bones = {}
            for c in finger_bones:
                y_pos.append(c.head[1])
                bones[c.head[1]] = c
            y_pos.sort()
            print(y_pos[0])
            index_bone = bones[y_pos[0]]
            finger_bones.remove(index_bone)
            index_bone.name = bone_names_fingers[4] + "_01"
            index_bones_children = index_bone.children_recursive
            j = 2
            for ch in index_bones_children:
                ch.name = bone_names_fingers[4] + "_0" + str(j)
                j += 1
                
            middle_bone = bones[y_pos[1]]
            finger_bones.remove(middle_bone)
            middle_bone.name = bone_names_fingers[3] + "_01"
            middle_bones_children = middle_bone.children_recursive
            j = 2
            for ch in middle_bones_children:
                ch.name = bone_names_fingers[3] + "_0" + str(j)
                j += 1

    # rename basic facial
    bone_group = _get_bones_from_group('Facial Basic', pose_bones)
    left_bones = _side_filter(bone_group, 'left')
    middle_bones = _side_filter(bone_group)

    middle_bones[0].name = bone_names_facial[0]
    y_pos = []
    bones = {}

    for b in left_bones:
        print(b)
        y_pos.append(b.head[1])
        bones [b.head[1]] = b
    y_pos.sort()
    bones [y_pos[0]].name = bone_names_facial[5]
    bones [y_pos[1]].name = bone_names_facial[4]+"_"+bone_suffix[2]


def _rename_mirrored_bones(): # find and rename mirrored bones
    for bone in left_bones:
        x, y, z = bone.head
        cur_name = bone.name
        location_x_plus = (-x, y, z)    
        for bone_1 in group_bones:
            i, j, k = (bone_1.head)
            location_x_minus = (i, j, k)
            if location_x_plus == location_x_minus and not bone in visited:
                bone_1.name = bone.name  + "_r"
                bone.name = cur_name + "_l"
                #print("mirrored {}".format(bone_1.name))r