try:
    import bpy
    import bmesh
except ImportError:
    pass


def show_message_box(message = "", title = "Message Box", icon = 'INFO'):

    def draw(self, context):
        self.layout.label(text=message)

    bpy.context.window_manager.popup_menu(draw, title = title, icon = icon)


def split_seams(me):
    bm = bmesh.from_edit_mesh(me)
    bpy.context.scene.tool_settings.use_uv_select_sync = True
    # old seams
    old_seams = [e for e in bm.edges if e.seam]
    # unmark
    for e in old_seams:
        e.seam = False
    # mark seams from uv islands
    bpy.ops.uv.seams_from_islands()
    seams = [e for e in bm.edges if e.seam]
    # split on seams
    bmesh.ops.split_edges(bm, edges=seams)
    # re instate old seams.. could clear new seams.
    for e in old_seams:
        e.seam = True
    bmesh.update_edit_mesh(me)


def split_UV_seams_operator(selected_meshes):

    for mesh in selected_meshes:
        me = mesh.data
        # in order to select edges, you need to make sure that
        # previously you deselected everything in the Edit Mode
        # and set the select_mode to 'EDGE'
        bpy.ops.object.mode_set(mode = 'EDIT')
        bpy.ops.mesh.select_mode(type = 'EDGE')
        bpy.ops.mesh.select_all(action='SELECT')
        split_seams(me) 
        bpy.ops.mesh.select_all(action = 'DESELECT')
        
        # we need to return back to the OBJECT mode,
        # otherwise, the result won't be seen,
        # see https://blender.stackexchange.com/questions/43127 for info
        bpy.ops.object.mode_set(mode = 'OBJECT')
        show_message_box(message="The fix is complete")


def select_invalid_meshes_operator(scene_meshes):
    '''Select meshes with more than 32 bone influences
    works only with parented meshes to an armature so it exclude meshes that excludes grids that will not be exported

    Parameters:
    scene_meshes (bpy.context.scene.objects): blender objects filtered by mesh type
    '''
    bpy.ops.object.select_all(action='DESELECT')
    invalid_meshes = []
    invalid_vertex_groups = []
    visible_meshes = [ob for ob in scene_meshes if ob.visible_get()]
    for mesh in visible_meshes:
        armature = mesh.parent #
        if armature:
            vertex_group_mapping = {vg.index: armature.pose.bones.find(vg.name) for vg in mesh.vertex_groups}
            vertex_group_mapping = {k: v for k, v in vertex_group_mapping.items() if v != -1}
            try:
                bone_indices = {vertex_group_mapping[vgroup.group] for vertex in mesh.data.vertices for vgroup in vertex.groups}
            except:
                print(mesh.name)
                invalid_vertex_groups.append(mesh)
                bone_indices = {}

            if len(bone_indices)>32:
                invalid_meshes.append(mesh)
        else:
            continue     
    if invalid_meshes:
        for mesh in invalid_meshes:
            #mesh.hide_select = False
            mesh.select_set(True)
            #bpy.context.view_layer.objects.active = mesh
        show_message_box(message="Meshes with more than 32 bone influences selected")
    else:
        show_message_box(message="There is no invalid mesh among visible")


def transfer_normals(source_obj, target_objs):
    for obj in target_objs:
        if obj != source_obj:
            modifier = obj.modifiers.new(name="Transfer Normals", type='DATA_TRANSFER')
            modifier.use_loop_data = True
            modifier.data_types_loops = {'CUSTOM_NORMAL'}
            modifier.object = source_obj
            bpy.context.view_layer.objects.active  = obj
            bpy.ops.object.modifier_apply(modifier=modifier.name)