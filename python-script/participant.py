import os
import sys
import numpy as np

# include these few lines before importing SCP library
if sys.platform.startswith("win"):
    for p in os.environ["PYTHON_DLL_PATH"].split(os.pathsep):
        if p: os.add_dll_directory(p)

from pyExt import SystemCouplingParticipant as scp

import argparse

nodeIds = np.array([1])
nodeCoords = np.array([[0.0,0.0,0.0]])
solutionData = {"point-cloud" : {"vin" : np.array([0.0]), "vout" : np.array([1.0])}}
coordinatesStamp = 0

def getPointCloud(regionName):
    pc = scp.PointCloud(scp.OutputIntegerData(nodeIds), scp.OutputVectorData(nodeCoords))
    pc.coordinatesStemp = coordinatesStamp
    return pc

def getInputScalar(regionName, variableName):
    return scp.InputScalarData(solutionData[regionName][variableName])

def getOutputScalar(regionName, variableName):
    return scp.OutputScalarData(solutionData[regionName][variableName])

parser = argparse.ArgumentParser()
parser.add_argument("--schost", type=str, default="")
parser.add_argument("--scport", type=int, default=0)
parser.add_argument("--scname", type=str, default="")
args, unknown = parser.parse_known_args()

sc = scp.SystemCoupling(args.schost, args.scport, args.scname, "test")

sc.registerPointCloudAccess(getPointCloud)
sc.registerInputScalarDataAccess(getInputScalar)
sc.registerOutputScalarDataAccess(getOutputScalar)

sc.initializeAnalysis()

while sc.doTimeStep():
    nodeCoords[0][0] += 1.0 # move the point in x-direction by 1
    coordinatesStamp += 1 # increment stamp
    while sc.doIteration():
        sc.updateInputs()
        sc.updateOutputs(scp.Complete)

sc.disconnect()

# do a simple test to make sure everything works
# but only if real co-simulation took place
if args.schost:
    # "vin" data came from another solver, but since another solver
    # is just another instance of this same script, and since System Coupling just takes
    # the "vout" value from the other solver and puts it into "vin" of this one,
    # it's really going to end up being equal to "vout"
    assert abs(solutionData["point-cloud"]["vin"] - solutionData["point-cloud"]["vout"]) < 1E-12
