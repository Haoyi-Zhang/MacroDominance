"""Vector drawing primitives; copied into each independent project generator."""
import argparse
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Polygon, Circle, FancyArrowPatch

plt.rcParams.update({'font.family':'STIXGeneral', 'mathtext.fontset':'stix',
                     'font.size':9, 'pdf.fonttype':42, 'ps.fonttype':42,
                     'text.usetex':False, 'axes.unicode_minus':False})
CM = 1 / 2.54

class Drawing:
    def __init__(self, bounds):
        x0,y0,x1,y1 = bounds
        self.fig = plt.figure(figsize=((x1-x0)*CM,(y1-y0)*CM))
        self.ax = self.fig.add_axes([0,0,1,1], xlim=(x0,x1), ylim=(y0,y1))
        self.ax.set_aspect('equal'); self.ax.axis('off')
        self.nodes = {}
        self.labels = []

    def text(self,x,y,label,size=9,ha='center',va='center'):
        artist=self.ax.text(x,y,label,fontsize=size,ha=ha,va=va,
                            linespacing=1.15,clip_on=False,zorder=4)
        self.labels.append([artist,None])
        return artist

    def box(self,name,x,y,w,h,label,dashed=False,shape='rect',size=9):
        style = {'edgecolor':'black','facecolor':'white','linewidth':.55,
                 'linestyle':(0,(4,3)) if dashed else 'solid', 'zorder':2}
        if shape == 'diamond':
            obj = Polygon([(x-w/2,y),(x,y+h/2),(x+w/2,y),(x,y-h/2)],**style)
        elif shape == 'circle': obj = Circle((x,y),w/2,**style)
        else: obj = Rectangle((x-w/2,y-h/2),w,h,**style)
        self.ax.add_patch(obj); self.text(x,y,label,size)
        self.labels[-1][1]=(x-w/2,y-h/2,x+w/2,y+h/2)
        self.nodes[name] = (x,y,w,h,shape)

    def point(self,name,side):
        x,y,w,h,_ = self.nodes[name]
        return {'n':(x,y+h/2),'s':(x,y-h/2),'e':(x+w/2,y),
                'w':(x-w/2,y),'nw':(x-w/2,y+h/2),
                'ne':(x+w/2,y+h/2),'c':(x,y)}[side]

    def line(self,points,dashed=False):
        xs,ys=zip(*points)
        self.ax.plot(xs,ys,color='black',linewidth=.55,
                     linestyle=(0,(4,3)) if dashed else 'solid',zorder=1)

    def arrow(self,p,q,dashed=False,via=()):
        points=[p,*via,q]
        if via:self.line(points[:-1],dashed)
        self.ax.add_patch(FancyArrowPatch(points[-2],points[-1],
                         arrowstyle='-|>',mutation_scale=7.5,linewidth=.55,
                         color='black',shrinkA=0,shrinkB=0,
                         linestyle=(0,(4,3)) if dashed else 'solid',zorder=1))

    def edge(self,a,b,sa='s',sb='n',**kwargs):
        self.arrow(self.point(a,sa),self.point(b,sb),**kwargs)

    def frame(self,x,y,w,h):
        self.ax.add_patch(Rectangle((x,y),w,h,fill=False,edgecolor='black',
                                   linewidth=.55,linestyle=(0,(4,3)),zorder=0))

    def save(self,out,name):
        # Fixed physical canvas: do not enlarge or rasterize the scientific figure.
        self.fig.canvas.draw()
        renderer=self.fig.canvas.get_renderer()
        x0,x1=self.ax.get_xlim();y0,y1=self.ax.get_ylim()
        for artist,node in self.labels:
            b=artist.get_window_extent(renderer).transformed(self.ax.transData.inverted())
            if b.x0<x0-.02 or b.x1>x1+.02 or b.y0<y0-.02 or b.y1>y1+.02:
                raise ValueError(name+': clipped label '+repr(artist.get_text()))
            if node and (b.x0<node[0]-.02 or b.x1>node[2]+.02 or b.y0<node[1]-.02 or b.y1>node[3]+.02):
                raise ValueError(name+': label exceeds node '+repr(artist.get_text()))
        self.fig.savefig(out/(name+'.pdf'),format='pdf',
                         metadata={'Creator':'Python Matplotlib','Producer':None,
                                   'CreationDate':None,'ModDate':None})
        plt.close(self.fig)

def render(out):
    d=Drawing((0,-1.8,8.8,2.4))
    d.arrow((.3,0),(8.25,0)); d.text(8.5,0,'$x$')
    tx=lambda x:.8*x
    for x in [1,3,4,6,7,9]:
        d.line([(tx(x),-.08),(tx(x),.08)])
        d.text(tx(x),-.28,str(x))
    for lo,hi in [(1,3),(7,9)]:
        d.line([(tx(lo),1.25),(tx(hi),1.25)])
        for x in [lo,hi]: d.line([(tx(x),1.13),(tx(x),1.37)])
    d.text(tx(2),1.75,r'$A=[a_-,a_+]$')
    d.text(tx(8),1.75,r'$B=[b_-,b_+]$')
    d.line([(tx(4),.63),(tx(6),.63)])
    d.ax.plot([tx(4),tx(6)],[.63,.63],'ko',markersize=2)
    d.text(tx(5),1.02,r'actual $[l,u]$')
    d.line([(tx(3),-.9),(tx(7),-.9)],dashed=True)
    for x in [3,7]: d.line([(tx(x),-1.02),(tx(x),-.78)])
    d.arrow((tx(4),.48),(tx(3),-.72),dashed=True)
    d.arrow((tx(6),.48),(tx(7),-.72),dashed=True)
    d.text(tx(5),-1.4,r'canonical $[l^*,u^*]=[3,7]$, $\delta=0$')
    clip=lambda x,a,b:min(b,max(a,x))
    if (clip(4,1,3),clip(6,7,9))!=(3,7):
        raise ValueError('Normalization example changed')
    for a in range(1,4):
        for b in range(7,10):
            if max(6,b)-min(4,a)!=max(7,b)-min(3,a):
                raise ValueError('Response-preserving example changed')
    d.save(out,'extrema')

def main():
    import tempfile
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',type=Path,default=Path(__file__).resolve().parent)
    parser.add_argument('--check',action='store_true')
    a=parser.parse_args();a.output_dir.mkdir(parents=True,exist_ok=True)
    render(a.output_dir)
    if a.check:
        with tempfile.TemporaryDirectory() as one,tempfile.TemporaryDirectory() as two:
            render(Path(one));render(Path(two))
            if (Path(one)/'extrema.pdf').read_bytes()!=(Path(two)/'extrema.pdf').read_bytes():
                raise ValueError('Fresh vector exports differ')
    print('Exterior interval vector figure and exact normalization checks passed.')

if __name__=='__main__':main()

