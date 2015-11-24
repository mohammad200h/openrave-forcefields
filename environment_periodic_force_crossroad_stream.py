from environment_periodic_force import *
import openravepy

class EnvironmentCrossroadStream(PeriodicForceEnvironment):
        def __init__(self):
                PeriodicForceEnvironment.__init__(self)
                xmlenv='environments/the_crossroad_stream.env.xml'
                xmlrobot='robots/pointrobot.robot.xml'
                self.setrobotenv(xmlrobot,xmlenv)

        def GetCells(self):
                C = self.GetCellsAll()
                ## do not use the first link, because it is a background
                self.cells = C[1:]
                return self.cells

        def GetForces(self):
                ##
                self.forces_max=[]
                self.forces_max.append(numpy.array((0.0,0.0,0.0)))
                self.forces_max.append(numpy.array((0.8,0.0,0.0)))
                self.forces_max.append(numpy.array((0.0,0.8,0.0)))
                self.forces_max.append(numpy.array((0.8,0.0,0.0)))
                self.forces_max.append(numpy.array((0.0,0.0,0.0)))
                self.forces_min=[]
                self.forces_min.append(numpy.array((0.0,0.0,0.0)))
                self.forces_min.append(numpy.array((0.8,0.0,0.0)))
                self.forces_min.append(numpy.array((0.0,0.4,0.0)))
                self.forces_min.append(numpy.array((0.8,0.0,0.0)))
                self.forces_min.append(numpy.array((0.0,0.0,0.0)))
                self.forces_period=[]
                self.forces_period.append(0.0)
                self.forces_period.append(1.0)
                self.forces_period.append(1.0)
                self.forces_period.append(1.0)
                self.forces_period.append(0.0)

        def RobotGetInitialPosition(self):
                return [-2.0,1.0]

        def RobotGetGoalPosition(self):
                return [2.0,1.0]

