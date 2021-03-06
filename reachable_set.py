from shapely.ops import cascaded_union, polygonize
import re
import os
from svglib.svglib import svg2rlg
from reportlab.graphics import renderPDF
from os.path import basename

import subprocess 
from matplotlib.collections import LineCollection
import matplotlib.ticker as mtick
import matplotlib
from scipy.spatial import ConvexHull
from shapely.geometry import Polygon
from scipy.spatial import Delaunay
import shapely.geometry as geometry
import pylab as plt
import numpy as np
import math
from util import *

class ReachableSet():

        pts = None
        poly = []
        rs_boundary_thickness = 15

        rs_color = np.array((0.8,0.8,1.0,1.0))
        rs_last_color = np.array((0.1,0.1,1.0,0.5))

        path_lw = 3

        force_color = np.array((1.0,0,0))
        tangent_color = np.array((0,0,0))
        orientation_color = np.array((0.9,0.0,0.5))
        fs = 28
        fs_label = 38
        fs_title = 46
        image = None

        def __init__(self, p, s, dp, force, R, amin, amax):
                
                self.pts = None
                self.poly = []
                self.fig = plt.figure(facecolor='white')
                self.image = self.fig.gca()


                plt.xlabel('X-Position [m]', fontsize=self.fs_label)
                plt.ylabel('Y-Position [m]', fontsize=self.fs_label)

                
                M = 10000
                tstart = 0.001
                tend = 0.01
                tsamples= 15

                Ndim = p.shape[0]
                poly = []
                
                for dt in self.expspace(tstart,tend,tsamples):
                        print dt
                        dt2 = dt*dt*0.5
                        q = np.zeros((Ndim,M))
                        for i in range(0,M):
                                ## sample random control
                                ar = np.random.uniform(amin, amax)
                                control = np.dot(R,ar)
                                q[:,i] = p + dt*s*dp + dt2 * force + dt2 * control

                        self.add_points( q[0:2,:].T )

                tstring = 'Reachable Set (<T='+str(dt)+')'
                self.filename = 'images/reachableset_ori'+str(np.around(p[3],decimals=2))
                self.filename = re.sub('[.]', '-', self.filename)
                self.filename += '.png'

                plt.title(tstring, fontsize=self.fs_title, y=1.05)
                self.arrow_head_size = np.linalg.norm(dt2*force)/5
                self.hw = 0.5*self.arrow_head_size
                self.lw = 0.2*self.arrow_head_size

                qnext = p+dt*s*dp+dt2*force

                self.image.plot(p[0], p[1], 'ok', markersize=10)
                self.image.plot(qnext[0],qnext[1], 'ok', markersize=10)

                dori = np.dot(Rz(p[3]),ex)[0:2]
                dori = 0.5*(dori/np.linalg.norm(dori))

                if s < 0.001:
                        dnf = np.linalg.norm(force)
                        nforce = force/dnf
                        si = np.linalg.norm(dt2*dnf/(dt*np.linalg.norm(dp)))
                        self.image.plot([p[0]+dt*1.5*si*dp[0],p[0]-0.2*dt*si*dp[0]],[p[1]+dt*1.5*si*dp[1],p[1]-0.2*dt*si*dp[1]],'-k',linewidth=self.path_lw)

                        arrow0 = self.PlotArrow(p, dt*si*dori, self.orientation_color)

                        arrow0 = self.PlotArrow(qnext, dt*si*dori, self.orientation_color)
                        arrow2 = self.PlotArrow(p, dt2*force, self.force_color)

                        plt.legend([arrow0,arrow2,],
                                        ['Orientation','Force',],fontsize=self.fs)
                else:
                        self.image.plot([p[0]+dt*1.5*s*dp[0],p[0]-0.2*dt*s*dp[0]],[p[1]+dt*1.5*s*dp[1],p[1]-0.2*dt*s*dp[1]],'-k',linewidth=self.path_lw)

                        arrow0 = self.PlotArrow(p, dt*s*dori, self.orientation_color)
                        arrow1 = self.PlotArrow(p, dt*s*dp, self.tangent_color)
                        arrow2 = self.PlotArrow(p, dt2*force, self.force_color)

                        arrow0 = self.PlotArrow(qnext, dt*s*dori, self.orientation_color)
                        arrow2 = self.PlotArrow(p+dt*s*dp, dt2*force, self.force_color)

                        plt.legend([arrow0,arrow1,arrow2,],
                                        ['Orientation','Velocity/Tangent Path','Force',],fontsize=self.fs)
                plt.tight_layout()
                plt.axis('equal')

        def PlotArrow(self, pos, direction, color):
                nd = np.linalg.norm(direction)

                new_length = nd-self.arrow_head_size
                norm_dir = direction/nd
                
                return self.image.arrow(pos[0],
                                pos[1],
                                new_length*norm_dir[0],
                                new_length*norm_dir[1],
                                head_width=self.hw,
                                width =self.lw,
                                head_length=self.arrow_head_size,
                                fc=color,
                                ec=color)

        def expspace(self, tstart, tend, tsamples):
                tlin = np.linspace(tstart, tend, tsamples)
                tpow = (tlin-tstart)**2
                dt = tpow[-1]-tpow[0]
                tscale = (tend-tstart)/dt
                texp = tscale * tpow + tstart
                return texp

        def add_points(self, q):
                hull = ConvexHull(q,qhull_options='QJ')    
                q = q[hull.vertices,:]

                self.poly.append( Polygon(q) )
                if self.pts is None:
                        self.pts = q
                else:
                        self.pts = np.vstack((self.pts,q))

        def Plot(self):
                #self.rs = cascaded_union(self.poly)

                for i in range(0,len(self.poly)):
                        x1,y1 = self.poly[i].exterior.xy

                        if i < len(self.poly)-1:
                                x2,y2 = self.poly[i+1].exterior.xy
                                x = np.hstack((x1,x2))
                                y = np.hstack((y1,y2))
                                q = np.vstack((x,y))
                                hull = ConvexHull(q.T,qhull_options='QJ')    
                                self.image.fill(q[0,hull.vertices], q[1,hull.vertices],
                                                facecolor=self.rs_color,
                                                edgecolor='None',
                                                zorder=0)

                q = np.vstack((x1,y1))
                hull = ConvexHull(q.T,qhull_options='QJ')    
                self.image.fill(q[0,hull.vertices], q[1,hull.vertices],
                                facecolor=self.rs_last_color,
                                edgecolor=self.rs_last_color,
                                linewidth=self.rs_boundary_thickness,
                                linestyle="dashed",
                                zorder=1)

                self.image.xaxis.get_major_formatter().set_powerlimits((0, 2))
                self.image.yaxis.get_major_formatter().set_powerlimits((0, 2))

                self.image.tick_params(axis='both', which='major', pad=15)
                self.image.tick_params(axis='both', which='minor', pad=15)

                self.image.yaxis.get_offset_text().set_size(self.fs)
                self.image.xaxis.get_offset_text().set_size(self.fs)

                for tick in self.image.xaxis.get_major_ticks():
                        tick.label.set_fontsize(self.fs) 

                for tick in self.image.yaxis.get_major_ticks():
                        tick.label.set_fontsize(self.fs) 

                self.fig.set_size_inches(18.5, 15.5, forward=True)
                plt.savefig(self.filename,format='svg', dpi=1200)


                svgname = self.filename
                pdfname = os.path.splitext(self.filename)[0]+'.pdf'

                syscmd = 'mogrify -format pdf -trim '+svgname
                os.system(syscmd)
                syscmd = 'pdfcrop '+pdfname+' '+pdfname
                os.system(syscmd)

                os.system('cp /home/`whoami`/git/openrave/sandbox/WPI/images/*.pdf /home/`whoami`/git/papers/images/simulation/')
                plt.show()

