import numpy as np
import sys
import copy
from numpy import sqrt,sin,cos,pi
from qcqp import *
import scipy
import cvxopt
import matplotlib.pyplot as plt
from cvxpy import *
from cvxopt import matrix, solvers
from util import PrintNumpy,inf

FILENAME = 'ddrive'
DYNAMICAL_SYTEM_NAME = 'non-holonomic differential drive (deform)'
system_name = DYNAMICAL_SYTEM_NAME

AM = 1
DEBUG = False
### car/sailboat
#amin = np.array((-AM,-AM,-AM,0))
#amax = np.array((AM,AM,AM,0))
amin = np.array((-AM,-AM,-0.5*AM))
amax = np.array((AM,AM,0.5*AM))

def ControlPerWaypoint(W, Ndim, Nwaypoints):
        assert(Ndim==4)
        Kdim = 3
        R = np.zeros((Ndim,Kdim,Nwaypoints))
        for i in range(0,Nwaypoints):
                if Nwaypoints>1:
                        t = W[3,i]
                else:
                        t = W[3]

                R[0,:,i] = np.array((cos(t),-sin(t),0.0))
                R[1,:,i] = np.array((sin(t),cos(t),0.0))
                R[2,:,i] = np.array((0.0,0.0,0.0))
                R[3,:,i] = np.array((0.0,0.0,1.0))

        return R
def GetControlMatrixAtWaypoint(p):
        return ControlPerWaypoint(p, p.shape[0], 1)[:,:,0]

### input: p -- waypoint on manifold
###     F -- force on manifold at p
###
### output: [A,b] such that A*qdd + b <= 0 

def GetControlConstraintMatrices(p, F):
        #Ndim = p.shape[0]
        #R = ControlPerWaypoint(p, Ndim, 1)[:,:,0]
        #return GetControlConstraintMatricesFromControl(R,F)
        return GetControlConstraintMatricesAdjust(p, F, epsilon=0)

def GetControlConstraintMatricesAdjust(p, F, epsilon=0.1):
        Ndim = p.shape[0]
        R = ControlPerWaypoint(p, Ndim, 1)[:,:,0]
        return GetControlConstraintMatricesFromControlAdjust(R,F,epsilon=epsilon)


def GetControlConstraintMatricesFromControl(R, F):
        return GetControlConstraintMatricesFromControlAdjust(R, F, epsilon=0)

def GetControlConstraintMatricesFromControlAdjust(R, F, epsilon=0):
        Adim = amin.shape[0]
        aminE = np.zeros((Adim))
        amaxE = np.zeros((Adim))
        for i in range(0,Adim):
                aminE[i]=amin[i]+epsilon
                amaxE[i]=amax[i]-epsilon
                if amaxE[i] < aminE[i]:
                        amid = amin[i]+0.5*(amax[i]-amin[i])
                        admin = np.linalg.norm(amid-amin[i])
                        admax = np.linalg.norm(amid-amax[i])
                        aminE[i] = amid-admin/10.0
                        amaxE[i] = amid+admax/10.0

        Ndim = R.shape[0]
        #Rmin = np.minimum(np.dot(R,aminE),np.dot(R,amaxE))
        #Rmax = np.maximum(np.dot(R,aminE),np.dot(R,amaxE))
        #H1 = F - Rmax
        #H2 = -F + Rmin

        Rinv = np.linalg.pinv(R)
        H1 = -np.dot(Rinv,F)-amaxE
        H2 = np.dot(Rinv,F)+aminE
        for j in range(Adim):
                if H2[j] > -H1[j]:
                        print H2[j],"<= q[",j,"]<=",-H1[j]
                        print "H1",H1,"H2",H2
                        print "amin",amin,"amax",amax
                        print "epsilon",epsilon,"->"
                        print "amin",aminE,"amax",amaxE
                        sys.exit(1)

        b = np.hstack((H1,H2)).flatten()
        RxI = np.dot(Rinv,np.identity(Ndim))
        A = np.vstack((RxI,-RxI))
        return [A,b]

#def GetBestControls( p, dp, pnext, ddq, FN, dt, speed):
def GetBestControlPathInvariant( p, dq, ddq, pnext, F, dt):
        #q = q + dt*dq + dt2*ddq + dt2*F
        Ndim = p.shape[0]
        dt2 = dt*dt/2

        if dt < 1e-100:
                ## cannot make progress in near zero time
                print "time step too small",dt
                sys.exit(0)
                return [q,ddq]

        boundary_distance = 0.0
        [Acontrol,bcontrol] = GetControlConstraintMatricesAdjust(p,F,epsilon=boundary_distance)
        A = np.zeros((Acontrol.shape))
        b = np.zeros((bcontrol.shape))

        #### adjust ddq to new conditions

        # minimize || M*ddq - R*u - F ||
        Rp = GetControlMatrixAtWaypoint(p)
        A = (2*Acontrol)/(dt*dt)
        b = bcontrol + np.dot(A,(-p - dt*dq))


        Adim = amin.shape[0]
        Id = np.eye(Ndim)
        u = Variable(Adim)
        objective = Minimize( norm(np.dot(Id,ddq) - (Rp*u + F)) )
        constraints = [ amin <= u, u <= amax]

        prob = Problem(objective, constraints)
        dnew = np.abs(prob.solve(solver=ECOS, max_iters=500, feastol=1e-10,abstol=1e-10,reltol=1e-10))
        if dnew < inf:
                print dnew
                u_adjusted =np.array(u.value).flatten()
        else:
                print "infeasible qp"
                sys.exit(0)

        ddq = np.dot(np.linalg.pinv(Id),(np.dot(Rp,u_adjusted)+F))

        #qnext = p + dt*dq + dt2*ddq
        #return [qnext, ddq]

        #### constraint on tangent acceleration
        Aq = np.vstack((ddq,-ddq))
        bq = np.hstack((-np.dot(ddq,ddq),np.dot(ddq,ddq)))

        #A = np.vstack((A,Aq))
        #b = np.hstack((b,bq))

        x = Variable(Ndim)
        objective = Minimize( norm(x - pnext) )
        constraints = [ A*x <= -b ]
                        #quad_form(x-p,Id) <= ds_next*ds_next]
        prob = Problem(objective, constraints)
        qcontrol = None
        try:
                #dnew = np.abs(prob.solve(solver=ECOS, verbose=False, max_iters=500, feastol_inacc=1e-20))
                ### default ECOS: max_iters=100, feastol=1e-7, abstol=1e-7, reltol = 1e-6
                dnew = np.abs(prob.solve(solver=ECOS, max_iters=500,
                        feastol=1e-10,abstol=1e-10,reltol=1e-10))
                #dnew = np.abs(prob.solve(solver=SCS, max_iters=5000, eps=1e-200))
                #dnew = np.abs(prob.solve(solver=CVXOPT))
                #dnew = np.abs(prob.solve(solver=ECOS_BB, mi_rel_eps=1e-100))
                if dnew < inf:
                        qcontrol =np.array(x.value).flatten()
                        qdd = 2*(qcontrol-p-dt*dq)/(dt*dt)
                        qdd[2] = 0
                        qdnext = dq + dt*qdd
                        qnext = p + dt*dq + dt2*qdd
                        #print "ECOS dt",dt,"dp2x",np.linalg.norm(p-qcontrol),"dx2pnext",np.linalg.norm(pnext-qcontrol),"qcontrol",qcontrol,"p",p,"pnext",pnext
                else:
                        qnext = None
                        qdnext = None
                        print "no solution found"
                        sys.exit(0)
        except Exception as e:
                print e
                PrintNumpy('pnext', pnext)
                PrintNumpy('p', p)
                PrintNumpy('dp', dq/np.linalg.norm(dq))
                PrintNumpy('force', F)
                print "speed:",np.linalg.norm(dq)
                print "dt:",dt
                sys.exit(0)

        return [qnext, qdd]



def GetNearestControlPoint(p, dp, pnext, F, dt, speed, Acontrol, bcontrol, returnControl=False):
        ds_next = np.linalg.norm(p-pnext)
        ds_next += ds_next/10.0
        dt2 = dt*dt/2
        Ndim = p.shape[0]

        if dt < 1e-100:
                ## cannot make progress in near zero time
                if returnControl:
                        return [p,dp,np.zeros(p.shape),ds_next]
                else:
                        return [p,dp,ds_next]


        A = np.zeros((Acontrol.shape))
        b = np.zeros((bcontrol.shape))

        A = (2*Acontrol)/(dt*dt)
        b = bcontrol + np.dot(A,(-p - dt*speed*dp))

###############################################################################
##### QCQP
###############################################################################
        Id = np.eye(Ndim)
        x = Variable(Ndim)
        #objective = Minimize( norm(x - pnext) + (dp)*x)
        objective = Minimize( norm(x - pnext))
        constraints = [ A*x <= -b,
                        quad_form(x-p,Id) <= ds_next*ds_next]
        prob = Problem(objective, constraints)
        qcontrol = None
        try:
                #dnew = np.abs(prob.solve(solver=ECOS, verbose=False, max_iters=500, feastol_inacc=1e-20))
                ### default ECOS: max_iters=100, feastol=1e-7, abstol=1e-7, reltol = 1e-6
                dnew = np.abs(prob.solve(solver=ECOS, max_iters=500,
                        feastol=1e-10,abstol=1e-10,reltol=1e-10))
                #dnew = np.abs(prob.solve(solver=SCS, max_iters=5000, eps=1e-200))
                #dnew = np.abs(prob.solve(solver=CVXOPT))
                #dnew = np.abs(prob.solve(solver=ECOS_BB, mi_rel_eps=1e-100))
                if dnew < inf:
                        qcontrol =np.array(x.value).flatten()
                        qdd = 2*(qcontrol-p-dt*speed*dp)/(dt*dt)
                        qdnext = speed*dp + dt*qdd
                        qnext = p + dt*speed*dp + dt2*qdd
                        #print "ECOS dt",dt,"dp2x",np.linalg.norm(p-qcontrol),"dx2pnext",np.linalg.norm(pnext-qcontrol),"qcontrol",qcontrol,"p",p,"pnext",pnext
                else:
                        qnext = None
                        qdnext = None
        except Exception as e:
                print e
                PrintNumpy('pnext', pnext)
                PrintNumpy('p', p)
                PrintNumpy('dp', dp)
                PrintNumpy('force', F)
                print "speed=",speed
                print "ds:",ds_next
                print "dt:",dt
                sys.exit(0)

        if returnControl:
                return [qnext, qdnext, qdd, dnew]
        else:
                return [qnext, qdnext, dnew]

def ForwardSimulate(p, dp, speed, ds, F, pnext=None):
        ### should best follow path!

        if pnext is None:
                pnext = p + ds*dp/np.linalg.norm(dp)
                if np.isnan(pnext).any():
                        print "there is no valid tangent information"
                        print "algorithm does not know to which point to go"
                        print "ds",ds
                        print "p",p
                        print "dp",dp
                        print "pnext",pnext
                        sys.exit(0)


        ### estimate tstep
        dds = speed*np.linalg.norm(dp)
        tv = ds / (dds)
        tf = np.sqrt(2*ds/np.linalg.norm(F))
        tc = np.sqrt(2*ds/np.linalg.norm(AM))
        if np.isnan(tf):
                tf = inf
        if np.isnan(tv):
                tv = inf
        if np.isnan(tc):
                tc = inf
        #print dds,2*ds,2*ds/np.linalg.norm(F)

        tall_predict = np.minimum(np.minimum(tv,tf),tc)
        tstep = tall_predict/10.0
        dt = 0.0
        #print "tv",tv,"tf",tf,"tc",tc,"tmin",tall_predict,"tstep",tstep
        if DEBUG:
                print "tv",tv,"tf",tf,"tc",tc,"tmin",tall_predict,"tstep",tstep


        ###### compute center of RS
        #dt = 0
        d = 0.0

        boundary_distance = 0.2

        ### slide along dynamical path until ds-ball is hit with some
        ### tolerance

        [Acontrol,bcontrol] = GetControlConstraintMatricesAdjust(p,F,epsilon=boundary_distance)
        Ndim = p.shape[0]
        dbest = 1e5
        dtbest = 0

        #tolerance=ds/30.0
        tolerance=ds/1e2
        ####################
        qcontrol = None

        ictr = 0
        
        ICTR_STOP = 20
        while True:
                #### Solve QCQP -> get new distance
                [qcontrol, qdcontrol, dcontrol_to_pnext] = GetNearestControlPoint(p, dp, pnext, F, dt, speed, Acontrol, bcontrol)

                if qcontrol is not None:
                        dp2qnext = np.linalg.norm(qcontrol-p)

                        if tstep < 1e-100:
                                [qcontrol, qdcontrol, ucontrol, dcontrol_to_pnext] = GetNearestControlPoint(p, dp, pnext, F, dt, speed, Acontrol, bcontrol, returnControl=True)
                                return [qcontrol, qdcontrol, ucontrol, dcontrol_to_pnext]
                        if np.abs(dp2qnext - ds)<tolerance:
                                dbest = dcontrol_to_pnext
                                dtbest = dt
                                if DEBUG:
                                        print "dtend:",dt,dbest
                                break
                        else:
                                if dp2qnext<ds:
                                        dt += tstep
                                        if DEBUG:
                                                print "time",dt,"d(qnext2pnext):",dcontrol_to_pnext
                                else:
                                        dt -= tstep
                                        tstep *= 0.5
                else:
                        dt -= tstep
                        tstep *= 0.5
                        
                if dt > 10:
                        break
                        
        [qcontrol, qdcontrol, ucontrol, dcontrol_to_pnext] = GetNearestControlPoint(p, dp, pnext, F, dtbest, speed, Acontrol, bcontrol, returnControl=True)
        #ictr = 0

        if dtbest < 1e-100:
                print "dtbest",dtbest
                PrintNumpy('p',p)
                PrintNumpy('dp',dp)
                PrintNumpy('F',F)
                print "ds=",ds
                print "s=",speed
                #sys.exit(0)


        if dtbest > 5:
                print "dtbest",dtbest
                PrintNumpy('p',p)
                PrintNumpy('dp',dp)
                PrintNumpy('F',F)
                print "ds=",ds
                print "s=",speed
                #VisualizeReachableSet3D(p,dp,dp,speed,ds,F)
                sys.exit(0)

        return [qcontrol,qdcontrol,ucontrol,dtbest]

def VisualizeReachableSet3D(p, dp, dwori, speed, ds, F):
        from reachable_set3d import ReachableSet3D
        Ndim = p.shape[0]
        R = ControlPerWaypoint(p, Ndim, 1)[:,:,0]
        reach = ReachableSet3D( ds, p, speed, dp, F, R, amin, amax)
        reach.Plot()
        reach.PlotShow()

