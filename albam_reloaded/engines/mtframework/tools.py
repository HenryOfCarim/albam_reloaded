import bpy
import bmesh

def ShowMessageBox(message = "", title = "Message Box", icon = 'INFO'):

    def draw(self, context):
        self.layout.label(text=message)

    bpy.context.window_manager.popup_menu(draw, title = title, icon = icon)


import bpy
import bmesh

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

        # now we check all the edges
        for edge in me.edges:
            if edge.use_seam: # if the edge uses seam
                edge.select = True # select it
            
        # as we did all selection in the OBJECT mode,
        # now we set to EDIT to see results
        bpy.ops.object.mode_set(mode = 'EDIT')
        ShowMessageBox(message="The fix is complete")
