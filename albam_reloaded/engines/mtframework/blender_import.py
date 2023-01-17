from itertools import chain
import ntpath
import os

try:
    import bpy
    import addon_utils
    from mathutils import Matrix, Vector
except ImportError:
    pass

from ...exceptions import BuildMeshError, TextureError #my lines IDK where they originally imported

from ...engines.mtframework import Arc, Mod156, SBC1, Tex112, KNOWN_ARC_BLENDER_CRASH, CORRUPTED_ARCS
from ...engines.mtframework.utils import (
    get_vertices_array,
    get_indices_array,
    get_non_deform_bone_indices,
    get_bone_parents_from_mod,
    transform_vertices_from_bbox,
    texture_code_to_blender_texture,

    )
from ...engines.mtframework.mappers import BONE_INDEX_TO_GROUP
from ...lib.misc import chunks
from ...lib.half_float import unpack_half_float
from ...lib.blender import strip_triangles_to_triangles_list
from ...registry import blender_registry


@blender_registry.register_function('import', identifier=b'ARC\x00')
def import_arc(blender_object, file_path, **kwargs):
    """Imports an arc file (Resident Evil 5 for only for now) into blender,
    extracting all files to a tmp dir and saving unknown/unused data
    to the armature (if any) for using in exporting
    """

    unpack_dir = kwargs.get('unpack_dir')
    if file_path.endswith(tuple(KNOWN_ARC_BLENDER_CRASH) + tuple(CORRUPTED_ARCS)):
        raise ValueError('The arc file provided is not supported yet, it might crash Blender')

    base_dir = os.path.basename(file_path).replace('.arc', '_arc_extracted')
    out = unpack_dir or os.path.join(os.path.expanduser('~'), '.albam', 're5', base_dir) #causing an error
    #out = os.path.join(os.path.expanduser('~'), '.albam', 're5', base_dir)
    if not os.path.isdir(out):
        os.makedirs(out)
    if not out.endswith(os.path.sep):
        out = out + os.path.sep

    arc = Arc(file_path=file_path)
    arc.unpack(out)

    mod_files = [os.path.join(root, f) for root, _, files in os.walk(out)
                 for f in files if f.endswith('.mod')]
   
    sbc_files = [os.path.join(root, f) for root, _, files in os.walk(out)
                 for f in files if f.endswith('.sbc')]

    mod_folders = [os.path.dirname(mod_file.split(out)[-1]) for mod_file in mod_files]
    mod_files.append(sbc_files[1]) # testing 

    return {'files': mod_files,
            'kwargs': {'parent': blender_object,
                       'mod_folder': mod_folders[0],  # XXX will break if mods are in different folders
                       'base_dir': out,
                       },
            }


@blender_registry.register_function('import', identifier=b'SBC1')
def import_sbc(blender_object, file_path, **kwargs):
    base_dir = kwargs.get('base_dir') # full path to _extracted folder

    sbc = SBC1(file_path=file_path)
    bbox = [f for f in sbc.bbox]
    boxes = [ b for b in sbc.boxes]
    groups = [g for g in sbc.groups]
    triangles = [t for t in sbc.triangles]
    vertices = [v for v in sbc.vertices ]
    print("it works somwhow")


@blender_registry.register_function('import', identifier=b'MOD\x00')
def import_mod(blender_object, file_path, **kwargs):
    base_dir = kwargs.get('base_dir') # full path to _extracted folder

    mod = Mod156(file_path=file_path)
    textures = _create_blender_textures_from_mod(mod, base_dir)
    materials = _create_blender_materials_from_mod(mod, blender_object.name, textures)

    # To simplify, import only main level of detail meshes
    LODS_TO_IMPORT = (1, 255)
    blender_meshes = []
    meshes = [m for m in mod.meshes_array if m.level_of_detail in LODS_TO_IMPORT]
    for i, mesh in enumerate(meshes):
        name = _create_mesh_name(i, file_path)
        try:
            m = _build_blender_mesh_from_mod(mod, mesh, i, name, materials)
            blender_meshes.append(m)
        except BuildMeshError as err:
            # TODO: logging
            print(f'Error building mesh {i} for mod {file_path}')
            print('Details:', err)

    if mod.bone_count:
        armature_name = 'skel_{}'.format(blender_object.name)
        root = _create_blender_armature_from_mod(blender_object, mod, armature_name)
        root.show_in_front = True # set x-ray view for bones
    else:
        root = blender_object

    for mesh in blender_meshes:
        bpy.context.collection.objects.link(mesh)
        mesh.parent = root
        if mod.bone_count:
            modifier = mesh.modifiers.new(type="ARMATURE", name=blender_object.name)
            modifier.object = root
            modifier.use_vertex_groups = True


def _build_blender_mesh_from_mod(mod, mesh, mesh_index, name, materials):
    me_ob = bpy.data.meshes.new(name)
    ob = bpy.data.objects.new(name, me_ob)

    imported_vertices = _import_vertices(mod, mesh)
    vertex_locations = imported_vertices['locations']
    vertex_normals = imported_vertices['normals']
    uvs_per_vertex = imported_vertices['uvs']
    uvs_per_vertex_2 = imported_vertices['uvs2']
    uvs_per_vertex_3 = imported_vertices['uvs3']
    weights_per_bone = imported_vertices['weights_per_bone']
    indices = get_indices_array(mod, mesh)
    indices = strip_triangles_to_triangles_list(indices)
    faces = chunks(indices, 3)
    weights_per_bone = imported_vertices['weights_per_bone']

    assert min(indices) >= 0, "Bad face indices"  # Blender crashes if not
    me_ob.from_pydata(vertex_locations, [], faces)

    me_ob.create_normals_split()

    me_ob.validate(clean_customdata=False)
    me_ob.update(calc_edges=True)
    me_ob.polygons.foreach_set("use_smooth", [True] * len(me_ob.polygons))

    loop_normals = []
    for loop in me_ob.loops:
        loop_normals.append(vertex_normals[loop.vertex_index])

    me_ob.normals_split_custom_set_from_vertices(vertex_normals)
    me_ob.use_auto_smooth = True

    mesh_material = materials[mesh.material_index]
    '''Old code
    if not mesh.use_cast_shadows and mesh_material.use_cast_shadows:
        mesh_material.use_cast_shadows = False'''
    if not mesh.use_cast_shadows and mesh_material.shadow_method: # code gets .use_cast_shadows from mesh's custom props
        mesh_material.shadow_method = 'NONE' # if use_cast_shadows is false and a material shadows is enabled, set it to NONE
    me_ob.materials.append(mesh_material)

    for bone_index, data in weights_per_bone.items():
        vg = ob.vertex_groups.new(name=str(bone_index))
        for vertex_index, weight_value in data:
            vg.add((vertex_index,), weight_value, 'ADD')

    if uvs_per_vertex:
        uv_layer = me_ob.uv_layers.new(name=name)
        per_loop_list = []
        for loop in me_ob.loops:
            offset = loop.vertex_index * 2
            per_loop_list.extend((uvs_per_vertex[offset], uvs_per_vertex[offset + 1]))
        uv_layer.data.foreach_set('uv', per_loop_list)

    # Checking material until we find a better way. Taken from max script
    has_light_map = mod.materials_data_array[mesh.material_index].texture_indices[3] > 0
    has_normal_map = mod.materials_data_array[mesh.material_index].texture_indices[1] > 0
    if has_light_map:
        if has_normal_map:
            source_uvs = uvs_per_vertex_3
        else:
            source_uvs = uvs_per_vertex_2
        uv_layer = me_ob.uv_layers.new(name="lightmap")
        per_loop_list = []
        for loop in me_ob.loops:
            offset = loop.vertex_index * 2
            per_loop_list.extend((source_uvs[offset], source_uvs[offset + 1]))
        uv_layer.data.foreach_set('uv', per_loop_list)


    # Saving unknown metadata for export
    # TODO: use a util function
    for field_tuple in mesh._fields_:
        attr_name = field_tuple[0]
        if not attr_name.startswith('unk_'):
            continue
        attr_value = getattr(mesh, attr_name)
        setattr(me_ob, attr_name, attr_value)

    return ob


def _import_vertices(mod, mesh):
    return _import_vertices_mod156(mod, mesh)


def _import_vertices_mod156(mod, mesh):
    vertices_array = get_vertices_array(mod, mesh)

    if mesh.vertex_format != 0:
        locations = (transform_vertices_from_bbox(vf, mod)
                     for vf in vertices_array)
    else:
        locations = ((vf.position_x, vf.position_y, vf.position_z) for vf in vertices_array)

    locations = map(lambda t: (t[0] / 100, t[2] / -100, t[1] / 100), locations)
    # from [0, 255] o [-1, 1]
    normals = map(lambda v: (((v.normal_x / 255) * 2) - 1,
                             ((v.normal_y / 255) * 2) - 1,
                             ((v.normal_z / 255) * 2) - 1), vertices_array)
    # y up to z up
    normals = map(lambda n: (n[0], n[2] * -1, n[1]), normals)

    uvs = [(unpack_half_float(v.uv_x), unpack_half_float(v.uv_y) * -1) for v in vertices_array]
    # XXX: normalmap has uvs as well? and then this should be uv3?
    if mesh.vertex_format == 0:
        uvs2 = [(unpack_half_float(v.uv2_x), unpack_half_float(v.uv2_y) * -1) for v in vertices_array]
        uvs3 = [(unpack_half_float(v.uv3_x), unpack_half_float(v.uv3_y) * -1) for v in vertices_array]
    else:
        uvs2 = []
        uvs3 = []


    return {'locations': list(locations),
            'normals': list(normals),
            # TODO: investigate why uvs don't appear above the image in the UV editor
            'uvs': list(chain.from_iterable(uvs)),
            'uvs2': list(chain.from_iterable(uvs2)),
            'uvs3': list(chain.from_iterable(uvs3)),
            'weights_per_bone': _get_weights_per_bone(mod, mesh, vertices_array)
            }


def _get_path_to_albam():
    for mod in addon_utils.modules():
        if mod.bl_info['name'] == "Albam Reloaded":
            filepath = mod.__file__
            path = os.path.split(filepath)[0]
            return (path)
        else:
            pass


def _create_blender_textures_from_mod(mod, base_dir):
    textures = [None]  # materials refer to textures in index-1
    # TODO: check why in Arc.header.file_entries[n].file_path it returns a bytes, and
    # here the whole array of chars

    for i, texture_path in enumerate(mod.textures_array):
        path = texture_path[:].decode('ascii').partition('\x00')[0] # relative path to a texture in the ARC archive without extension
        path = os.path.join(base_dir, *path.split(ntpath.sep))# full path to a texture
        path = '.'.join((path, 'tex')) # full path to a texture with .tex extension
        if not os.path.isfile(path):
            # TODO: log warnings, figure out 'rtex' format
            print('path {} does not exist'.format(path))
            # add a placeholder instead of the missing texure
            texture_name_no_extension = os.path.splitext(os.path.basename(path))[0]
            texture_name_no_extension = str(i).zfill(2) + texture_name_no_extension
            texture = bpy.data.textures.new(texture_name_no_extension, type='IMAGE')
            texture.use_fake_user = True

            image_path = _get_path_to_albam()
            image_path = os.path.join(image_path, "resourses", "missing texture.dds")
            dummy_image = bpy.data.images.load(image_path)

            texture.image = dummy_image
            texture_node_name = texture_name_no_extension + ".dds"
            texture.image.name = texture_node_name
            textures.append(texture) 
            continue
        tex = Tex112(path)
        try:
            dds = tex.to_dds()
        except TextureError as err:
            # TODO: log this instead of printing it
            print('Error converting "{}"to dds: {}'.format(path, err))
            textures.append(None)
            continue
        dds_path = path.replace('.tex', '.dds') # change extension in the full path
        with open(dds_path, 'wb') as w: #write bynary
            w.write(dds)
        image = bpy.data.images.load(dds_path, check_existing=True)
        texture_name_no_extension = os.path.splitext(os.path.basename(path))[0]
        texture_name_no_extension = str(i).zfill(2) + texture_name_no_extension
        texture = bpy.data.textures.get(texture_name_no_extension)
        # Create a texture data block if not exist
        if not texture:
            texture = bpy.data.textures.new(texture_name_no_extension, type='IMAGE') # bpy.data.textures['00pl0200_09AllHair_BM']
            texture.use_fake_user = True # Set fake user to prevent removing after saving to .blend
            texture.image = image 
        textures.append(texture) #create a list with bpy.data.textures

        # saving meta data for export
        # TODO: use a util function
        for field_tuple in tex._fields_:
            attr_name = field_tuple[0]
            if not attr_name.startswith('unk_'):
                continue
            attr_value = getattr(tex, attr_name)
            setattr(texture, attr_name, attr_value)

    return textures

def _create_shader_node_group():
    '''Creates shader node group to hide all nodes from users under the hood'''

    shader_group = bpy.data.node_groups.new("MT Framework shader", 'ShaderNodeTree')
    group_inputs = shader_group.nodes.new('NodeGroupInput')
    group_inputs.location = (-2000,-200)

    # Create group inputs
    shader_group.inputs.new('NodeSocketColor',"Diffuse BM")
    shader_group.inputs.new('NodeSocketFloat', "Alpha BM")
    shader_group.inputs["Alpha BM"].default_value = 1
    shader_group.inputs.new('NodeSocketColor',"Normal NM")
    shader_group.inputs["Normal NM"].default_value = (1, 0.5, 1, 1)
    shader_group.inputs.new('NodeSocketFloat',"Alpha NM")
    shader_group.inputs["Alpha NM"].default_value = 0.5
    shader_group.inputs.new('NodeSocketColor',"Specular MM")
    #shader_group.inputs["Specular MM"].default_value = 1
    shader_group.inputs.new('NodeSocketColor',"Lightmap LM")
    shader_group.inputs.new('NodeSocketInt',"Use Lightmap")
    shader_group.inputs["Use Lightmap"].min_value = 0
    shader_group.inputs["Use Lightmap"].max_value = 1
    shader_group.inputs.new('NodeSocketColor',"Alpha Mask AM")
    shader_group.inputs.new('NodeSocketInt',"Use Alpha Mask")
    shader_group.inputs["Use Alpha Mask"].min_value = 0
    shader_group.inputs["Use Alpha Mask"].max_value = 1
    shader_group.inputs.new('NodeSocketColor',"Environment CM")
    shader_group.inputs.new('NodeSocketColor',"Detail DNM")
    shader_group.inputs["Detail DNM"].default_value = (1, 0.5, 1, 1)
    shader_group.inputs.new('NodeSocketFloat',"Alpha DNM")
    shader_group.inputs["Alpha DNM"].default_value = 0.5
    shader_group.inputs.new('NodeSocketInt',"Use Detail Map")
    shader_group.inputs["Use Detail Map"].min_value = 0
    shader_group.inputs["Use Detail Map"].max_value = 1

    # Create group outputs
    group_outputs = shader_group.nodes.new('NodeGroupOutput')
    group_outputs.location = (300,-90)
    shader_group.outputs.new('NodeSocketShader','Surface')

    # Shader node
    bsdf_shader = shader_group.nodes.new('ShaderNodeBsdfPrincipled')
    bsdf_shader.location = (0,-90)

    # Mix a diffuse map and a lightmap
    multiply_diff_light =  shader_group.nodes.new('ShaderNodeMixRGB')
    multiply_diff_light.name = "mult_diff_and_light"
    multiply_diff_light.label = "Multiply with Lightmap"
    multiply_diff_light.blend_type = 'MULTIPLY'
    multiply_diff_light.inputs[0].default_value = 0.8
    multiply_diff_light.location = (-450, -100)

    # RGB nodes
    normal_separate = shader_group.nodes.new('ShaderNodeSeparateRGB')
    normal_separate.name = "separate_normal"
    normal_separate.label = "Separate Normal"
    normal_separate.location =(-1700, -950)

    normal_combine = shader_group.nodes.new('ShaderNodeCombineRGB')
    normal_combine.name = "combine_normal"
    normal_combine.label = "Combine Normal"
    normal_combine.location = (-1500, -900)

    detail_separate = shader_group.nodes.new('ShaderNodeSeparateRGB')
    detail_separate.name = "separate_detail"
    detail_separate.label = "Separate Detail"
    detail_separate.location = (-1700,-1100)

    detail_combine = shader_group.nodes.new('ShaderNodeCombineRGB')
    detail_combine.name = "combine_detail"
    detail_combine.label = "Combine Detail"
    detail_combine.location = (-1500, -1050)

    separate_rgb_n = shader_group.nodes.new('ShaderNodeSeparateRGB')
    separate_rgb_n.name = "separate_rgb_n"
    separate_rgb_n.label = "Separate RGB N"
    separate_rgb_n.location = (-1250, -1050)

    separate_rgb_d = shader_group.nodes.new('ShaderNodeSeparateRGB')
    separate_rgb_d.name = "separate_rgb_d"
    separate_rgb_d.label = "Separate RGB D"
    separate_rgb_d.location = (-1250, -1250)

    combine_all_normals = shader_group.nodes.new('ShaderNodeCombineRGB')
    combine_all_normals.name = "combine_all_normals"
    combine_all_normals.label = "Combine All Normals"
    combine_all_normals.location = (-750, -1150)

    # Curve RGB for correct normal map display in blender
    invert_green = shader_group.nodes.new('ShaderNodeRGBCurve')
    invert_green.location = (-250, -1000)
    curve_g = invert_green.mapping.curves[1]
    curve_g.points[0].location = (1, 0)
    curve_g.points[1].location = (0, 1)
    invert_green.mapping.update()

    # Normalize normals nodes
    normalize_normals = shader_group.nodes.new('ShaderNodeVectorMath')
    normalize_normals.operation = 'NORMALIZE'
    normalize_normals.name = "normalize_normals"
    normalize_normals.label = "Normalize Normals"
    normalize_normals.location = (-590, -1050)

    # Add nodes
    add_normals_red = shader_group.nodes.new('ShaderNodeMixRGB')
    add_normals_red.blend_type = 'ADD'
    add_normals_red.name = "add_normals_red"
    add_normals_red.label = "Add Normals Red"
    add_normals_red.location = (-1000, -980)

    add_normals_green=  shader_group.nodes.new('ShaderNodeMixRGB')
    add_normals_green.blend_type = 'ADD'
    add_normals_green.name = "add_normals_green"
    add_normals_green.label = "Add Normals Green"
    add_normals_green.location = (-1000, -1200)

    add_normals_blue = shader_group.nodes.new('ShaderNodeMixRGB')
    add_normals_blue.blend_type = 'ADD'
    add_normals_blue.name = "add_normals_blue"
    add_normals_blue.label = "Add Normals Blue"
    add_normals_blue.location = (-1000, -1420)

    # Invert node
    invert_spec = shader_group.nodes.new('ShaderNodeInvert')
    invert_spec.location = (-200, -350)

    # Normal node
    normal_map =  shader_group.nodes.new('ShaderNodeNormalMap') # create normal map node
    normal_map.inputs[0].default_value = 1.5
    normal_map.location = (-200, -720)

    # Logic gates
    use_lightmap = shader_group.nodes.new('ShaderNodeMixRGB')
    use_lightmap.name = "switch_lightmap"
    use_lightmap.label = "Lightmap Switcher"
    use_lightmap.location = (-200, -150)

    use_alpha_mask = shader_group.nodes.new('ShaderNodeMixRGB')
    use_alpha_mask.name = "switch_alpha_mask"
    use_alpha_mask.label = "Alpha Mask Switcher"
    use_alpha_mask.location = (-200, -500)

    use_detail_map = shader_group.nodes.new('ShaderNodeMixRGB')
    use_detail_map.name ="switch_detail_map"
    use_detail_map.label = "Detail Mask Switcher"
    use_detail_map.location = (-440, -825)

    # Link nodes
    link = shader_group.links.new

    link(bsdf_shader.outputs[0], group_outputs.inputs[0])
    link(group_inputs.outputs[0], multiply_diff_light.inputs[1])
    link(multiply_diff_light.outputs[0], use_lightmap.inputs[2])
    link(group_inputs.outputs[0], use_lightmap.inputs[1])
    link(use_lightmap.outputs[0], bsdf_shader.inputs[0])
    link(group_inputs.outputs[1], use_alpha_mask.inputs[1])
    link(use_alpha_mask.outputs[0], bsdf_shader.inputs[21])
    link(group_inputs.outputs[2], normal_separate.inputs[0])
    link(normal_separate.outputs[1], normal_combine.inputs[1])
    link(normal_separate.outputs[2], normal_combine.inputs[2])
    link(group_inputs.outputs[3], normal_combine.inputs[0])
    link(normal_combine.outputs[0], use_detail_map.inputs[1])
    link(normal_combine.outputs[0], separate_rgb_n.inputs[0])

    link(group_inputs.outputs[4], invert_spec.inputs[1])
    link(invert_spec.outputs[0], bsdf_shader.inputs[9])
    link(group_inputs.outputs[5], multiply_diff_light.inputs[2])
    link(group_inputs.outputs[6], use_lightmap.inputs[0])
    link(group_inputs.outputs[7], use_alpha_mask.inputs[2]) # use alpha mask > color 2
    link(group_inputs.outputs[8], use_alpha_mask.inputs[0]) # use alpha mask int

    link(group_inputs.outputs[10], detail_separate.inputs[0])
    link(group_inputs.outputs[11], detail_combine.inputs[0])
    link(detail_separate.outputs[1], detail_combine.inputs[1])
    link(detail_separate.outputs[2], detail_combine.inputs[2])
    link(detail_combine.outputs[0], separate_rgb_d.inputs[0])

    link(separate_rgb_n.outputs[0], add_normals_red.inputs[1])
    link(separate_rgb_d.outputs[0], add_normals_red.inputs[2])
    link(separate_rgb_n.outputs[1], add_normals_green.inputs[1])
    link(separate_rgb_d.outputs[1], add_normals_green.inputs[2])
    link(separate_rgb_n.outputs[2], add_normals_blue.inputs[1])
    link(separate_rgb_d.outputs[2], add_normals_blue.inputs[2])
    link(add_normals_red.outputs[0], combine_all_normals.inputs[0])
    link(add_normals_green.outputs[0], combine_all_normals.inputs[1])
    link(add_normals_blue.outputs[0], combine_all_normals.inputs[2])

    link(combine_all_normals.outputs[0],normalize_normals.inputs[0])
    link(normalize_normals.outputs[0],use_detail_map.inputs[2])
    link(use_detail_map.outputs[0], invert_green.inputs[1])
    link(invert_green.outputs[0], normal_map.inputs[1])
    link(normal_map.outputs[0], bsdf_shader.inputs[22])
    link(group_inputs.outputs[12], use_detail_map.inputs[0])

    return shader_group


def _create_blender_materials_from_mod(mod, model_name, textures):
    '''textures: bpy.data.textures'''
    materials = []
    existed_textures = []
    if not bpy.data.node_groups.get("MT Framework shader"):
        shader_node = _create_shader_node_group()

    for i, material in enumerate(mod.materials_data_array):
        blender_material = bpy.data.materials.new('{}_{}'.format(model_name, str(i).zfill(2)))
        blender_material.use_nodes = True
        blender_material.blend_method = 'CLIP' # set transparency method 'OPAQUE', 'CLIP', 'HASHED', 'BLEND'
        #blender_material.alpha_treshhold = 0.33

        node_to_delete = blender_material.node_tree.nodes.get("Principled BSDF")
        blender_material.node_tree.nodes.remove( node_to_delete )
        #principled_node.inputs['Specular'].default_value = 0.2 # change specular
        shader_node_group = blender_material.node_tree.nodes.new('ShaderNodeGroup')
        shader_node_group.node_tree = bpy.data.node_groups["MT Framework shader"]
        shader_node_group.name = "MTFrameworkGroup"
        shader_node_group.width = 300
        material_output = blender_material.node_tree.nodes.get("Material Output")
        material_output.location = (400, 0)

        link = blender_material.node_tree.links.new
        link(shader_node_group.outputs[0], material_output.inputs[0])

        # unknown data for export, registered already
        # TODO: do this with a util function
        for field_tuple in material._fields_: # add custom properties to material
            attr_name = field_tuple[0]
            if not attr_name.startswith('unk_'):
                continue
            attr_value = getattr(material, attr_name)
            setattr(blender_material, attr_name, attr_value)
        materials.append(blender_material)

        for texture_code, tex_index in enumerate(material.texture_indices):
            if not tex_index:
                continue
            try:
                texture_target = textures[tex_index]
            except IndexError:
                # TODO
                print('tex_index {} not found. Texture len(): {}'.format(tex_index, len(textures)))
                continue
            if not texture_target:
                # This means the conversion failed before
                # TODO: logging
                continue
            if texture_code == 6:
                print('texture_code not supported', texture_code)
                continue
            texture_node = blender_material.node_tree.nodes.new('ShaderNodeTexImage') 
            texture_code_to_blender_texture(texture_code, texture_node, blender_material)
            texture_node.image = texture_target.image # set bpy.data.textures[].image as a texures for ShaderNodeTexImage
            if  texture_code  == 1 or texture_code  == 7: # change color settings for normal and detail maps
                texture_node.image.colorspace_settings.name = 'Non-Color'

    return materials


def _create_blender_armature_from_mod(blender_object, mod, armature_name):
    armature = bpy.data.armatures.new(armature_name)
    armature_ob = bpy.data.objects.new(armature_name, armature)
    armature_ob.parent = blender_object

    #set to Object mode
    if bpy.context.mode != 'OBJECT': 
        bpy.ops.object.mode_set(mode='OBJECT')
    # deselect all objects
    for i in bpy.context.scene.objects:
        i.select_set(False) # my change
    bpy.context.collection.objects.link(armature_ob)
    bpy.context.view_layer.objects.active = armature_ob
    armature_ob.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')

    blender_bones = []
    non_deform_bone_indices = get_non_deform_bone_indices(mod)

    for i, bone in enumerate(mod.bones_array): # add counter to the array
        blender_bone = armature.edit_bones.new(str(i))

        if i in non_deform_bone_indices:
            blender_bone.use_deform = False
        parents = get_bone_parents_from_mod(bone, mod.bones_array)
        if not parents:
            blender_bone.head = Vector((bone.location_x / 100,
                                        bone.location_z * -1 / 100,
                                        bone.location_y / 100))
            blender_bone.tail = Vector((blender_bone.head[0], blender_bone.head[1], blender_bone.head[2] + 0.01))
        else:
            chain = [i] + parents
            wtm = Matrix.Translation((0, 0, 0))
            for bi in reversed(chain):
                b = mod.bones_array[bi]
                wtm = wtm @ Matrix.Translation((b.location_x / 100, b.location_z / 100 * -1, b.location_y / 100))
            blender_bone.head = wtm.to_translation()
            blender_bone.parent = blender_bones[bone.parent_index]

        blender_bone.tail = Vector((blender_bone.head[0], blender_bone.head[1], blender_bone.head[2] + 0.01))
        blender_bones.append(blender_bone)


    assert len(blender_bones) == len(mod.bones_array)


    bpy.ops.object.mode_set(mode='OBJECT')
    assert len(armature.bones) == len(mod.bones_array)

    _create_bone_groups(armature_ob, mod)
    return armature_ob


def _create_bone_groups(armature_ob, mod):
    bone_groups_cache = {
        'BONE_GROUP_MAIN': {
            'color_set': 'THEME03',
            'name': 'Main',
            'layer': 1,
            },
        'BONE_GROUP_ARMS': {
            'color_set': 'THEME02',
            'name': 'Arms',
            'layer': 2,
            },
        'BONE_GROUP_LEGS': {
            'color_set': 'THEME05',
            'name': 'Legs',
            'layer': 3,
            },
        'BONE_GROUP_HANDS': {
            'color_set': 'THEME06',
            'name': 'Hands',
            'layer': 4,
            },
        'BONE_GROUP_HAIR': {
            'color_set': 'THEME07',
            'name': 'Hair',
            'layer': 5,
            },
        'BONE_GROUP_FACIAL_BASIC': {
            'color_set': 'THEME02',
            'name': 'Facial Basic',
            'layer': 6,
            },
        'BONE_GROUP_FACIAL': {
            'color_set': 'THEME01',
            'name': 'Facial',
            'layer': 7,
            },
        'BONE_GROUP_ACCESORIES': {
            'color_set': 'THEME14',
            'name': 'Accessories',
            'layer': 8,
            },
        'OTHER': {
            'color_set': 'THEME20',
            'name': 'Other',
            'layer': 9,
            },
    }

    bpy.ops.object.mode_set(mode='POSE')
    for i, bone in enumerate(armature_ob.pose.bones):
        source_bone = mod.bones_array[i]
        anim_index = source_bone.anim_map_index
        bone.bone_group = _get_or_create_bone_group(anim_index, armature_ob, i, bone_groups_cache)
    bpy.ops.object.mode_set(mode='OBJECT')


def _get_or_create_bone_group(bone_anim_index, armature_ob, bone_index, bone_groups_cache):
    bone_group_name = BONE_INDEX_TO_GROUP.get(bone_anim_index, 'OTHER')

    bone_group_cache = bone_groups_cache.get(bone_group_name) or bone_groups_cache['OTHER']
    layer_index = bone_group_cache['layer']
    _move_bone_to_layers(armature_ob, bone_index, 0, layer_index)

    if bone_group_cache.get('bl_group'):
        return bone_group_cache['bl_group']

    bl_bone_group = armature_ob.pose.bone_groups.new(name=bone_group_cache['name'])
    bl_bone_group.color_set = bone_group_cache['color_set']
    bone_group_cache['bl_group'] = bl_bone_group

    return bl_bone_group


def _move_bone_to_layers(armature_ob, bone_index, *layer_indices):
    layers = [False] * 32
    for layer_index in layer_indices:
        layers[layer_index] = True
    armature_ob.data.bones[bone_index].select = True
    bpy.ops.pose.bone_layers(layers=layers)
    armature_ob.data.bones[bone_index].select = False


def _get_weights_per_bone(mod, mesh, vertices_array):
    weights_per_bone = {}
    if not mod.bone_count or not hasattr(vertices_array[0], 'bone_indices'):
        return weights_per_bone
    bone_palette = mod.bone_palette_array[mesh.bone_palette_index]
    for vertex_index, vertex in enumerate(vertices_array):
        for bi, bone_index in enumerate(vertex.bone_indices):
            if bone_index >= bone_palette.unk_01:
                real_bone_index = mod.bones_animation_mapping[bone_index]
            else:
                try:
                    real_bone_index = bone_palette.values[bone_index]
                except IndexError:
                    # Behaviour not observed in original files so far
                    real_bone_index = bone_index
            if bone_index + vertex.weight_values[bi] == 0:
                continue
            bone_data = weights_per_bone.setdefault(real_bone_index, [])
            bone_data.append((vertex_index, vertex.weight_values[bi] / 255))
    return weights_per_bone


def _create_mesh_name(index, file_path):
    mesh_name = os.path.basename(file_path)
    mesh_index = str(index).zfill(4)

    return f'{mesh_name}_{mesh_index}'
