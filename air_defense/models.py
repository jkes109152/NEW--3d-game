"""共用程序模型工廠；商店、角色預覽與戰鬥使用同一造型。"""
from math import sqrt, sin, cos, pi
from .visual_catalog import RECIPES, PALETTE, ARMOR_PARTS
from .config import ASSETS
from collections import OrderedDict

_round_mesh=None
_sphere_mesh=None
_shaped_meshes={}
_weapon_templates=OrderedDict()
_thumbnail_cache=OrderedDict()
_asset_fallbacks=set()
def rounded_mesh():
    global _round_mesh
    from panda3d.core import NodePath
    def clone():
        node=_round_mesh.copyTo(NodePath("rounded-copy"));node.detachNode();return node
    if _round_mesh is not None:return clone()
    from ursina import Mesh
    verts=[];normals=[];uvs=[];triangles=[];steps=4;radius=.16;inner=.5-radius
    for axis in range(3):
        others=[i for i in range(3) if i!=axis]
        for sign in (-1,1):
            base=len(verts)
            for row in range(steps+1):
                for col in range(steps+1):
                    p=[0.,0.,0.];p[axis]=sign*.5;p[others[0]]=col/steps-.5;p[others[1]]=row/steps-.5
                    core=[max(-inner,min(inner,v)) for v in p];n=[a-b for a,b in zip(p,core)];length=sqrt(sum(v*v for v in n));n=[v/length for v in n]
                    verts.append(tuple(a+radius*b for a,b in zip(core,n)));normals.append(tuple(n));uvs.append((col/steps,row/steps))
            for row in range(steps):
                for col in range(steps):
                    a=base+row*(steps+1)+col;b=a+1;c=a+steps+1;d=c+1
                    ids=(a,b,d,c)
                    cross_sign=1 if axis in (0,2) else -1
                    if cross_sign==sign:ids=ids[::-1]
                    triangles.extend([(ids[0],ids[1],ids[2]),(ids[0],ids[2],ids[3])])
    shades=[max(.58,min(1,.77+.17*n[1]-.10*n[0]-.07*n[2])) for n in normals]
    _round_mesh=Mesh(vertices=verts,triangles=triangles,normals=normals,uvs=uvs,colors=[(v,v,v,1) for v in shades],static=True)
    # 每個 Entity 取得獨立節點，共享不可變幾何，避免 reparent 搬走前一商品。
    return clone()

def sphere_mesh():
    """單位直徑球；模板永不掛入場景，合併實例不會污染後續部件。"""
    global _sphere_mesh
    from panda3d.core import NodePath
    if _sphere_mesh is None:
        from ursina import Mesh
        vertices=[];normals=[];uvs=[];triangles=[];rows=12;columns=16
        for row in range(rows+1):
            latitude=pi*row/rows
            for column in range(columns+1):
                longitude=2*pi*column/columns
                normal=(sin(latitude)*cos(longitude),cos(latitude),sin(latitude)*sin(longitude))
                vertices.append(tuple(v*.5 for v in normal));normals.append(normal);uvs.append((column/columns,row/rows))
        for row in range(rows):
            for column in range(columns):
                a=row*(columns+1)+column;b=a+1;c=a+columns+1;d=c+1
                triangles.extend(((a,d,b),(a,c,d)))
        shades=[max(.58,min(1,.77+.17*n[1]-.10*n[0]-.07*n[2])) for n in normals]
        _sphere_mesh=Mesh(vertices=vertices,normals=normals,uvs=uvs,triangles=triangles,colors=[(v,v,v,1) for v in shades],static=True)
    node=_sphere_mesh.copyTo(NodePath('sphere-copy'));node.detachNode();return node


def part(parent,position,scale,tint,shape='round'):
    from ursina import Entity,color
    model=rounded_mesh() if shape=='round' else sphere_mesh() if shape=='sphere' else shaped_mesh(shape) if shape in ('ring','cylinder','cone','wedge') else shape
    return Entity(parent=parent,model=model,position=position,scale=scale,color=color.hex(tint),add_to_scene_entities=False)


def shaped_mesh(shape):
    """環形護架、管狀瞄具、三角槍托與火箭頭的共用低面數幾何。"""
    from panda3d.core import NodePath
    if shape not in _shaped_meshes:
        from ursina import Mesh
        vertices=[];normals=[];uvs=[];triangles=[]
        def face(points):
            a,b,c=points[:3];u=[b[i]-a[i] for i in range(3)];v=[c[i]-a[i] for i in range(3)]
            n=(u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]);length=sqrt(sum(x*x for x in n)) or 1
            base=len(vertices);vertices.extend(points);normals.extend([tuple(-x/length for x in n)]*len(points));uvs.extend([(i%2,i//2) for i in range(len(points))])
            triangles.extend((base,base+i,base+i+1) for i in range(1,len(points)-1))
        if shape=='ring':
            for i in range(24):
                for j in range(8):
                    theta=2*pi*i/24;phi=2*pi*j/8;r=.36+.14*cos(phi)
                    vertices.append((r*cos(theta),r*sin(theta),.5*sin(phi)));normals.append((cos(phi)*cos(theta),cos(phi)*sin(theta),sin(phi)));uvs.append((i/24,j/8))
                    a=i*8+j;b=((i+1)%24)*8+j;c=((i+1)%24)*8+(j+1)%8;d=i*8+(j+1)%8
                    triangles.extend(((a,c,b),(a,d,c)))
        elif shape in ('cylinder','cone'):
            for i in range(24):
                a=2*pi*i/24;b=2*pi*(i+1)/24;p=(.5*cos(a),.5*sin(a),-.5);q=(.5*cos(b),.5*sin(b),-.5)
                if shape=='cone':face((q,p,(0,0,.5)))
                else:
                    r=(p[0],p[1],.5);s=(q[0],q[1],.5);face((q,p,r,s));face(((0,0,.5),s,r))
                face(((0,0,-.5),p,q))
        else:
            a=(-.5,-.5,-.5);b=(-.5,.5,-.5);c=(-.5,.1,.5);d=(.5,-.5,-.5);e=(.5,.5,-.5);f=(.5,.1,.5)
            for points in ((a,b,c),(f,e,d),(d,e,b,a),(a,c,f,d),(b,e,f,c)):face(points)
        shades=[max(.58,min(1,.77+.17*n[1]-.10*n[0]-.07*n[2])) for n in normals]
        _shaped_meshes[shape]=Mesh(vertices=vertices,normals=normals,uvs=uvs,triangles=triangles,colors=[(v,v,v,1) for v in shades],static=True)
    node=_shaped_meshes[shape].copyTo(NodePath(shape+'-copy'));node.detachNode();return node

def _copy_geometry(template):
    from panda3d.core import NodePath
    node=template.copyTo(NodePath('model-copy'));node.detachNode()
    return node


def build_weapon(weapon_id,color_id='original',pattern_id='plain',attachments=(),parent=None,quality='medium'):
    """固定幾何合併並快取；槍機／供彈部件每個實例各自持有。"""
    from ursina import Entity
    key=(weapon_id,color_id,pattern_id,tuple(attachments),quality)
    if key not in _weapon_templates:
        from .scene import destroy_tree
        fixed=Entity(add_to_scene_entities=False);tint=PALETTE[color_id];moving=[]
        part(fixed,(0,0,.1),(.3,.3,.8),tint)
        part(fixed,(0,-.3,-.05),(.2,.42,.25),'#eed4b6')
        for index,(name,pos,size,shape) in enumerate(RECIPES[weapon_id]):
            shade=tint if index%2==0 else '#f8e4ac'
            if name in ('側槍機','泵動前護木'):
                moving.append((name,pos,size,shade,shape));continue
            node=part(fixed,pos,size,shade,shape);node.name=name
            if name=='弧形長匣':node.rotation_x=-12
            if name=='雙腳架':node.rotation_z=-12;part(fixed,(-pos[0],pos[1],pos[2]),size,shade,shape).rotation_z=12
            if pattern_id!='plain':
                texture=ASSETS/'textures'/f'{pattern_id}.png'
                if texture.is_file():node.texture=str(texture)
                else:_asset_fallbacks.add('textures/'+f'{pattern_id}.png')
        if weapon_id=='W02':
            for x in (-.27,.27):
                for y in (-.12,.24):part(fixed,(x,y,1.35),(.24,.24,.25),'#375875','sphere')
            part(fixed,(0,.5,-.1),(.18,.3,.2),'#eed4b6')
        if weapon_id=='W01':part(fixed,(0,.4,.1),(.12,.25,.13),'#eed4b6')
        if weapon_id in ('W06','W14','W18'):
            for x in (-.12,.12):part(fixed,(x,-.04,-.36),(.12,.15,.45),tint)
        if weapon_id=='W05':part(fixed,(0,-.3,-.08),(.29,.46,.32),'#eed4b6')
        if weapon_id in ('W08','W17'):
            height=.4 if weapon_id=='W08' else .32
            for z in (-.08,.42):part(fixed,(0,.15+height/2,z),(.1,height,.1),'#375875')
        if weapon_id=='W10':part(fixed,(0,.12,.6),(.13,.13,.7),tint)
        if weapon_id=='W12':part(fixed,(0,.21,.1),(.18,.2,.28),tint)
        if weapon_id=='W13':part(fixed,(-.19,.1,-.1),(.2,.18,.25),tint)
        if weapon_id=='W18':part(fixed,(0,-.04,-.65),(.42,.48,.7),'#eed4b6')
        if weapon_id=='W20':part(fixed,(0,.1,1.64),(.28,.28,.5),'#eed4b6','cone')
        if weapon_id in ('W06','W07','W10'):
            for z in (.4,.65,.9):part(fixed,(.21,.1,z),(.03,.12,.07),'#375875')
        if weapon_id=='W18':moving.append(('側槍機',(.26,.04,.12),(.22,.09,.09),'#375875','round'))
        if weapon_id not in ('W01','W02'):moving.append(('供彈部件',(0,-.24,.3),(.22,.3,.28),'#95d7c4','round'))
        for attachment in attachments:
            if 'scope' in attachment:
                height=.82 if weapon_id=='W08' else .53
                if weapon_id!='W17':part(fixed,(0,height,.2),(.22,.22,.6),'#83ddca','cylinder')
                else:part(fixed,(0,height,.7),(.28,.28,.12),'#83ddca','ring')
                for z in (0,.4):part(fixed,(0,(height+.15)/2,z),(.1,height-.15,.1),'#375875')
            elif attachment=='heavy_barrel':part(fixed,(0,.05,1.15),(.27,.27,.5),'#bb9ade')
            else:part(fixed,(0,-.3,.25),(.3,.3,.4),'#95d7c4')
        fixed.flattenStrong();mesh=_copy_geometry(fixed)
        for node in mesh.findAllMatches('**'):
            for tag in tuple(node.getPythonTagKeys()):node.clearPythonTag(tag)
        destroy_tree(fixed);_weapon_templates[key]=(mesh,tuple(moving))
        if len(_weapon_templates)>128:_weapon_templates.popitem(last=False)
    _weapon_templates.move_to_end(key)
    mesh,moving=_weapon_templates[key]
    root=Entity(parent=parent,model=_copy_geometry(mesh),add_to_scene_entities=False)
    for name,pos,size,shade,shape in moving:part(root,pos,size,shade,shape).name=name
    root.weapon_id=weapon_id;return root


def cache_metrics():
    return dict(rounded_templates=int(_round_mesh is not None),sphere_templates=int(_sphere_mesh is not None),shape_templates=len(_shaped_meshes),shape_template_limit=4,weapon_templates=len(_weapon_templates),weapon_template_limit=128,thumbnail_textures=len(_thumbnail_cache),thumbnail_limit=128,optional_asset_fallbacks=sorted(_asset_fallbacks))


def thumbnail_texture(kind,item_id,appearance=('original','plain',()),quality='medium'):
    """首次需要時由共用工廠離屏繪製；回傳靜態紋理，不保留更新攝影機。"""
    from ursina import Entity,application
    from panda3d.core import NodePath,Camera,OrthographicLens,Texture,Vec4,Vec3
    key=(kind,item_id,*appearance,quality)
    if key in _thumbnail_cache:
        _thumbnail_cache.move_to_end(key);return _thumbnail_cache[key]
    from .scene import destroy_tree
    engine=application.base;stage=NodePath('thumbnail-stage')
    pivot=Entity(parent=stage,rotation=(8,-110,-10),add_to_scene_entities=False)
    if kind=='weapon':build_weapon(item_id,*appearance,parent=pivot,quality=quality)
    elif kind=='armor':
        pivot.rotation=(5,150,0);pivot.y=-.75;build_character(item_id,parent=pivot)
    else:pivot.y=-.55;build_turret(item_id,parent=pivot)
    texture=Texture('thumbnail-'+item_id)
    buffer=engine.win.makeTextureBuffer('thumbnail-buffer',192,128,texture,True)
    if buffer is None:
        destroy_tree(pivot);stage.removeNode();raise RuntimeError('無法建立商品縮圖緩衝區')
    lens=OrthographicLens();lens.setFilmSize(3.5,2.3333);lens.setNearFar(.1,20)
    cam=stage.attachNewNode(Camera('thumbnail-camera'));cam.node().setLens(lens);cam.node().setScene(stage)
    cam.setPos(0,.1,-5);cam.lookAt(Vec3(0,.1,0),Vec3(0,1,0))
    region=buffer.makeDisplayRegion();region.setCamera(cam);buffer.setClearColor(Vec4(0,0,0,0));buffer.setClearColorActive(True)
    try:
        for _ in range(4):engine.graphicsEngine.renderFrame()
        engine.graphicsEngine.syncFrame()
        engine.graphicsEngine.extractTextureData(texture,engine.win.getGsg())
    finally:
        engine.graphicsEngine.removeWindow(buffer);cam.removeNode();destroy_tree(pivot);stage.removeNode()
    _thumbnail_cache[key]=texture
    if len(_thumbnail_cache)>128:_thumbnail_cache.popitem(last=False)
    return texture

def build_character(armor_id=None,parent=None,boss=False):
    from ursina import Entity
    root=Entity(parent=parent,add_to_scene_entities=False)
    tint='#b8a1e3' if boss else '#8bdbbf'
    part(root,(0,.98,0),(.7,1.1,.58),tint,'sphere')
    part(root,(0,1.53,.12),(.53,.45,.4),'#ffe6c8','sphere')
    for side in (-1,1):
        part(root,(side*.13,1.57,.31),(.065,.1,.04),'#314264','sphere')
        part(root,(side*.23,.2,.07),(.31,.4,.4),'#f4c8dc')
        part(root,(side*.42,.91,.08),(.23,.57,.25),tint,'sphere')
    if armor_id:
        name,pos,size=ARMOR_PARTS[armor_id];part(root,pos,size,'#f7d98a').name=name
    return root

def build_turret(turret_id,parent=None):
    from ursina import Entity
    root=Entity(parent=parent,add_to_scene_entities=False)
    part(root,(0,.23,0),(1.9,.46,1.9),'#b59cde');part(root,(0,.75,0),(.6,.85,.6),'#8bdbbf')
    weapon=build_weapon({'T01':'W06','T02':'W18','T03':'W02'}[turret_id],parent=root);weapon.position=(0,1.25,0);weapon.scale=.7
    return root
