"""Embarque 3D: ônibus e boneco de blocos. Python/Pygame/OpenGL 3.3."""
import math
import ctypes
from pathlib import Path
import numpy as np
import pygame
from pygame.locals import DOUBLEBUF, OPENGL
from OpenGL.GL import *
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent
W, H = 1100, 700

def identity(): return np.eye(4, dtype=np.float32)
def translate(x=0,y=0,z=0):
    m=identity();m[:3,3]=[x,y,z];return m
def scale(x=1,y=1,z=1): return np.diag([x,y,z,1]).astype('f4')
def rotate_y(a):
    c,s=math.cos(a),math.sin(a);m=identity();m[0,0]=m[2,2]=c;m[0,2]=s;m[2,0]=-s;return m
def rotate_x(a):
    c,s=math.cos(a),math.sin(a);m=identity();m[1,1]=m[2,2]=c;m[1,2]=-s;m[2,1]=s;return m
def rotate_z(a):
    c,s=math.cos(a),math.sin(a);m=identity();m[0,0]=m[1,1]=c;m[0,1]=-s;m[1,0]=s;return m
def perspective(fov,aspect,near,far):
    f=1/math.tan(math.radians(fov)/2);m=np.zeros((4,4),dtype='f4');m[0,0]=f/aspect;m[1,1]=f;m[2,2]=(far+near)/(near-far);m[2,3]=2*far*near/(near-far);m[3,2]=-1;return m
def ortho(l,r,b,t,n,f):
    m=identity();m[0,0]=2/(r-l);m[1,1]=2/(t-b);m[2,2]=-2/(f-n);m[0,3]=-(r+l)/(r-l);m[1,3]=-(t+b)/(t-b);m[2,3]=-(f+n)/(f-n);return m
def look_at(eye,target,up=(0,1,0)):
    eye=np.array(eye,dtype='f4');target=np.array(target,dtype='f4');up=np.array(up,dtype='f4');f=target-eye;f/=np.linalg.norm(f);s=np.cross(f,up);s/=np.linalg.norm(s);u=np.cross(s,f);m=identity();m[0,:3]=s;m[1,:3]=u;m[2,:3]=-f;m[:3,3]=-m[:3,:3]@eye;return m

def shader_program(vs,fs):
    def compile_shader(path,kind):
        src=(ROOT/'shaders'/path).read_text(encoding='utf8');s=glCreateShader(kind);glShaderSource(s,src);glCompileShader(s)
        if not glGetShaderiv(s,GL_COMPILE_STATUS):raise RuntimeError(glGetShaderInfoLog(s).decode())
        return s
    v=compile_shader(vs,GL_VERTEX_SHADER);f=compile_shader(fs,GL_FRAGMENT_SHADER);p=glCreateProgram();glAttachShader(p,v);glAttachShader(p,f);glLinkProgram(p)
    if not glGetProgramiv(p,GL_LINK_STATUS):raise RuntimeError(glGetProgramInfoLog(p).decode())
    glDeleteShader(v);glDeleteShader(f);return p

def cube_mesh():
    # Seis faces com normais e coordenadas UV independentes; 36 vértices.
    faces=[((0,0,1),[(-.5,-.5,.5),(.5,-.5,.5),(.5,.5,.5),(-.5,.5,.5)]),((0,0,-1),[(.5,-.5,-.5),(-.5,-.5,-.5),(-.5,.5,-.5),(.5,.5,-.5)]),((1,0,0),[(.5,-.5,.5),(.5,-.5,-.5),(.5,.5,-.5),(.5,.5,.5)]),((-1,0,0),[(-.5,-.5,-.5),(-.5,-.5,.5),(-.5,.5,.5),(-.5,.5,-.5)]),((0,1,0),[(-.5,.5,.5),(.5,.5,.5),(.5,.5,-.5),(-.5,.5,-.5)]),((0,-1,0),[(-.5,-.5,-.5),(.5,-.5,-.5),(.5,-.5,.5),(-.5,-.5,.5)])]
    data=[];uv=[(0,0),(1,0),(1,1),(0,1)]
    for normal,points in faces:
        for i in [0,1,2,0,2,3]:data.extend([*points[i],*normal,*uv[i]])
    return np.array(data,dtype='f4')

class Renderer:
    def __init__(self):
        self.scene=shader_program('scene.vert','scene.frag');self.depth=shader_program('depth.vert','depth.frag')
        mesh=cube_mesh();self.vao=glGenVertexArrays(1);self.vbo=glGenBuffers(1);glBindVertexArray(self.vao);glBindBuffer(GL_ARRAY_BUFFER,self.vbo);glBufferData(GL_ARRAY_BUFFER,mesh.nbytes,mesh,GL_STATIC_DRAW)
        for index,size,offset in [(0,3,0),(1,3,12),(2,2,24)]:glEnableVertexAttribArray(index);glVertexAttribPointer(index,size,GL_FLOAT,GL_FALSE,32,ctypes.c_void_p(offset))
        glBindVertexArray(0)
        self.shadow=glGenTextures(1);glBindTexture(GL_TEXTURE_2D,self.shadow);glTexImage2D(GL_TEXTURE_2D,0,GL_DEPTH_COMPONENT24,2048,2048,0,GL_DEPTH_COMPONENT,GL_FLOAT,None)
        for key,value in [(GL_TEXTURE_MIN_FILTER,GL_NEAREST),(GL_TEXTURE_MAG_FILTER,GL_NEAREST),(GL_TEXTURE_WRAP_S,GL_CLAMP_TO_BORDER),(GL_TEXTURE_WRAP_T,GL_CLAMP_TO_BORDER)]:glTexParameteri(GL_TEXTURE_2D,key,value)
        glTexParameterfv(GL_TEXTURE_2D,GL_TEXTURE_BORDER_COLOR,np.array([1,1,1,1],dtype='f4'))
        self.fbo=glGenFramebuffers(1);glBindFramebuffer(GL_FRAMEBUFFER,self.fbo);glFramebufferTexture2D(GL_FRAMEBUFFER,GL_DEPTH_ATTACHMENT,GL_TEXTURE_2D,self.shadow,0);glDrawBuffer(GL_NONE);glReadBuffer(GL_NONE)
        if glCheckFramebufferStatus(GL_FRAMEBUFFER)!=GL_FRAMEBUFFER_COMPLETE:raise RuntimeError('Framebuffer de sombras incompleto')
        glBindFramebuffer(GL_FRAMEBUFFER,0)
        self.tex=self.make_texture();self.lightdir=np.array([-.55,-1,-.45],dtype='f4');self.lightspace=ortho(-17,17,-17,17,1,55)@look_at((12,22,12),(0,0,0))
        self.parts=[];glEnable(GL_DEPTH_TEST);glEnable(GL_CULL_FACE)
    def make_texture(self):
        path=ROOT/'assets'/'piso.png'
        if not path.exists():
            img=Image.new('RGB',(256,256),(155,160,153));d=ImageDraw.Draw(img)
            for k in range(0,256,32):d.line((k,0,k,255),fill=(120,126,120),width=2);d.line((0,k,255,k),fill=(120,126,120),width=2)
            img.save(path)
        im=Image.open(path).convert('RGB').transpose(Image.Transpose.FLIP_TOP_BOTTOM);tex=glGenTextures(1);glBindTexture(GL_TEXTURE_2D,tex);glTexImage2D(GL_TEXTURE_2D,0,GL_RGB,im.width,im.height,0,GL_RGB,GL_UNSIGNED_BYTE,im.tobytes());glGenerateMipmap(GL_TEXTURE_2D)
        glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_LINEAR_MIPMAP_LINEAR);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_LINEAR);return tex
    def box(self,parent,pos,size,color,rot=None,textured=False):
        m=parent@translate(*pos)@(rot if rot is not None else identity())@scale(*size)
        self.parts.append((m,color,1 if textured else 0))
    def uniform_mat(self,p,name,m):glUniformMatrix4fv(glGetUniformLocation(p,name),1,GL_TRUE,m)
    def render(self,view,proj):
        glBindVertexArray(self.vao);glUseProgram(self.depth);self.uniform_mat(self.depth,'lightSpace',self.lightspace)
        glViewport(0,0,2048,2048);glBindFramebuffer(GL_FRAMEBUFFER,self.fbo);glClear(GL_DEPTH_BUFFER_BIT);glCullFace(GL_FRONT)
        for m,_,_ in self.parts:self.uniform_mat(self.depth,'model',m);glDrawArrays(GL_TRIANGLES,0,36)
        glCullFace(GL_BACK);glBindFramebuffer(GL_FRAMEBUFFER,0);glViewport(0,0,W,H);glClearColor(.55,.76,.94,1);glClear(GL_COLOR_BUFFER_BIT|GL_DEPTH_BUFFER_BIT)
        glUseProgram(self.scene)
        for name,m in [('view',view),('projection',proj),('lightSpace',self.lightspace)]:self.uniform_mat(self.scene,name,m)
        glUniform3fv(glGetUniformLocation(self.scene,'lightDir'),1,self.lightdir)
        glActiveTexture(GL_TEXTURE0);glBindTexture(GL_TEXTURE_2D,self.tex);glUniform1i(glGetUniformLocation(self.scene,'diffuseTex'),0)
        glActiveTexture(GL_TEXTURE1);glBindTexture(GL_TEXTURE_2D,self.shadow);glUniform1i(glGetUniformLocation(self.scene,'shadowMap'),1)
        for m,color,texture in self.parts:
            self.uniform_mat(self.scene,'model',m);glUniform3f(glGetUniformLocation(self.scene,'color'),*color);glUniform1i(glGetUniformLocation(self.scene,'useTexture'),texture);glDrawArrays(GL_TRIANGLES,0,36)
        glBindVertexArray(0)

YELLOW=(.98,.69,.10);DARK=(.09,.15,.21);GLASS=(.18,.48,.65);WHITE=(.91,.93,.90);RED=(.82,.12,.10)
def bus(r,x,door,wheel):
    p=translate(x,0,0)
    r.box(p,(0,1.40,0),(4.5,2.25,1.8),YELLOW)
    r.box(p,(0,2.55,0),(4.5,.17,1.85),WHITE)
    r.box(p,(0,.43,0),(4.4,.3,1.72),DARK)
    # Frente na direção +X, portas na lateral +Z.
    for xx in [-1.65,-.9,-.15,.60,1.35]:
        r.box(p,(xx,1.85,-.913),(.57,.82,.04),GLASS)
        if xx<.6:r.box(p,(xx,1.85,.913),(.57,.82,.04),GLASS)
    r.box(p,(2.265,1.88,0),(.04,.85,1.55),GLASS)
    r.box(p,(-2.265,1.88,0),(.04,.85,1.55),GLASS)
    # Abertura visível simulada com painéis que deslizam para os lados.
    r.box(p,(1.12,1.37,.93),(.85,1.83,.06),DARK)
    r.box(p,(1.12-door*.22,1.38,.975),(.40,1.74,.05),GLASS)
    r.box(p,(1.12+door*.22,1.38,.975),(.40,1.74,.05),GLASS)
    for xx in [-1.45,1.55]:
        for zz in [-.94,.94]:
            r.box(p,(xx,.50,zz),(.67,.78,.23),DARK,rotate_z(wheel))
            r.box(p,(xx,.50,zz*1.15),(.25,.25,.04),(.65,.67,.70),rotate_z(wheel))
    for zz in [-.61,.61]:r.box(p,(2.29,.80,zz),(.06,.23,.28),WHITE)
    r.box(p,(-2.29,.78,0),(.06,.19,1.30),RED)
    r.box(p,(0,1.08,-.94),(3.9,.12,.05),DARK)

def character(r,x,z,walk=0,visible=True):
    if not visible:return
    p=translate(x,0,z);skin=(.92,.69,.48);shirt=(.17,.34,.85);pants=(.17,.20,.34)
    bob=.035*abs(math.sin(walk))
    r.box(p,(0,1.18+bob,0),(.48,.68,.30),shirt)
    r.box(p,(0,1.77+bob,0),(.43,.44,.42),skin)
    r.box(p,(0,2.02+bob,0),(.45,.12,.45),DARK)
    for side in [-1,1]:
        arm=translate(side*.34,1.43+bob,0)@rotate_z(side*.35*math.sin(walk))
        r.box(p@arm,(0,-.22,0),(.18,.55,.21),skin)
        leg=translate(side*.13,.83+bob,0)@rotate_z(side*.40*math.sin(walk))
        r.box(p@leg,(0,-.34,0),(.20,.70,.25),pants)
        r.box(p@leg,(.06,-.68,.07),(.29,.13,.39),DARK)
    r.box(p,(0,1.81+bob,.224),(.21,.045,.025),DARK)

def environment(r):
    I=identity();r.box(I,(0,-.12,0),(38,.20,25),(.45,.61,.39),textured=True)
    r.box(I,(0,-.005,-1.65),(38,.025,4.9),(.22,.24,.27))
    r.box(I,(0,.02,2.35),(38,.12,2.8),(.69,.69,.67),textured=True)
    for x in range(-16,17,4):r.box(I,(x,.016,-1.65),(1.8,.025,.10),WHITE)
    # Abrigo e sinalização do ponto.
    for x in [3.8,7.5]:r.box(I,(x,1.45,4.10),(.12,2.9,.12),DARK)
    r.box(I,(5.65,2.95,4.10),(4.15,.16,1.50),(.17,.43,.59))
    r.box(I,(5.65,1.30,4.80),(3.6,.12,.55),(.35,.23,.15))
    r.box(I,(8.35,1.6,3.9),(.10,3.2,.10),DARK)
    r.box(I,(8.35,3.20,3.9),(.85,.63,.10),(.14,.38,.80))
    for x in [-13,-8,-3,11,15]:
        r.box(I,(x,1.0,7.4),(.28,2.0,.28),(.42,.29,.17))
        r.box(I,(x,2.45,7.4),(1.65,1.65,1.65),(.13,.42,.19))

def smooth(t):t=max(0,min(1,t));return t*t*(3-2*t)
def phase(t):
    # Ciclo de 18 s: aproximação, parada, abertura, embarque, fechamento, partida.
    if t<4:return -10+10*smooth(t/4),0,0,5.5,False,'ONIBUS SE APROXIMANDO'
    if t<5:return 0,0,0,5.5,False,'ONIBUS PAROU NO PONTO'
    if t<6.5:return 0,smooth((t-5)/1.5),0,5.5,False,'ABRINDO A PORTA'
    if t<10.5:
        k=smooth((t-6.5)/4);return 0,1,1.12,5.5-4.5*k,False,'BONECO CAMINHANDO PARA EMBARQUE'
    if t<12:return 0,1,1.12,1.0,True,'EMBARQUE CONCLUIDO'
    if t<13.5:return 0,1-smooth((t-12)/1.5),1.12,1.0,True,'FECHANDO A PORTA'
    return 10*smooth((t-13.5)/4.5),0,1.12,1.0,True,'ONIBUS PARTINDO'

def main():
    pygame.init();pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MAJOR_VERSION,3);pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MINOR_VERSION,3);pygame.display.gl_set_attribute(pygame.GL_CONTEXT_PROFILE_MASK,pygame.GL_CONTEXT_PROFILE_CORE)
    pygame.display.set_mode((W,H),DOUBLEBUF|OPENGL);pygame.display.set_caption('Embarque 3D | Onibus + Boneco de Blocos')
    r=Renderer();clock=pygame.time.Clock();time=0.;paused=False;cam_angle=.9;cam_height=10.;cam_dist=19.;speed=1.;running=True
    while running:
        dt=min(clock.tick(60)/1000,.05)
        for event in pygame.event.get():
            if event.type==pygame.QUIT:running=False
            if event.type==pygame.KEYDOWN:
                if event.key==pygame.K_ESCAPE:running=False
                if event.key==pygame.K_SPACE:paused=not paused
                if event.key==pygame.K_r:time=0
                if event.key==pygame.K_EQUALS or event.key==pygame.K_KP_PLUS:speed=min(3,speed+.25)
                if event.key==pygame.K_MINUS or event.key==pygame.K_KP_MINUS:speed=max(.25,speed-.25)
        keys=pygame.key.get_pressed()
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:cam_angle-=dt*1.2
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:cam_angle+=dt*1.2
        if keys[pygame.K_UP] or keys[pygame.K_w]:cam_height=min(22,cam_height+dt*7)
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:cam_height=max(2,cam_height-dt*7)
        if keys[pygame.K_q]:cam_dist=max(8,cam_dist-dt*8)
        if keys[pygame.K_e]:cam_dist=min(35,cam_dist+dt*8)
        if not paused:time=(time+dt*speed)%18
        x,door,cx,cz,hidden,status=phase(time)
        r.parts=[];environment(r);bus(r,x,door,time*2.7 if (time<4 or time>=13.5) else 0)
        character(r,cx,cz,walk=time*9 if 6.5<=time<10.5 else 0,visible=not hidden)
        eye=(math.sin(cam_angle)*cam_dist,cam_height,math.cos(cam_angle)*cam_dist)
        view=look_at(eye,(0,1,1));proj=perspective(55,W/H,.1,100)
        r.render(view,proj);pygame.display.set_caption(f'Embarque 3D | {status} | {"PAUSADO" if paused else "RODANDO"} | Velocidade {speed:.2f}x')
        pygame.display.flip()
    pygame.quit()
if __name__=='__main__':main()
