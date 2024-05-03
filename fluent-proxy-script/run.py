import ansys.fluent.core as pyfluent
import ansys.systemcoupling.core as pysyc

from dataclasses import dataclass
from typing import List

import subprocess
import os

#===

class Solver():

    class SystemCoupling():
    
        @dataclass
        class Variable:
            name: str
            display_name: str
            tensor_type: str
            is_extensive: bool
            location: str
            quantity_type: str    

        @dataclass
        class Region:
            name: str
            display_name: str
            topology: str
            input_variables: List[str]
            output_variables: List[str]
    
        def __init__(self, solver):
            self.solver = solver

        @property
        def participant_type(self) -> str:
            return "DEFAULT"

        def get_analysis_type(self) -> str:
            return "Steady"

        def get_variables(self):
            variables = list()
            vin = Solver.SystemCoupling.Variable(
                name="vin",
                display_name="vin",
                tensor_type="Scalar",
                is_extensive=False,
                location="Node",
                quantity_type="Unspecified",
            )
            vout = Solver.SystemCoupling.Variable(
                name="vout",
                display_name="vout",
                tensor_type="Scalar",
                is_extensive=False,
                location="Node",
                quantity_type="Unspecified",
            )
            variables.append(vin)
            variables.append(vout)
            return variables

        def get_regions(self):
            regions = list()
            region = Solver.SystemCoupling.Region(
                name="point-cloud",
                display_name="point-cloud",
                topology="Surface",
                input_variables=["vin"],
                output_variables=["vout"],
            )
            regions.append(region)
            return regions

        def connect(self, host, port, name):
            print(f"Connecting! Host: {host}, port: {port}, name: {name}", flush=True)
            self.standardOutput = open(f"{name}.stdout", "w")        
            pythonScript = os.path.abspath("participant.py")
            # temporary hack (TODO: fix): need to set SYSC_ROOT
            os.environ["SYSC_ROOT"] = os.path.join(os.environ["AWP_ROOT242"], "SystemCoupling")
            batchScript = os.path.join(os.environ["AWP_ROOT242"], "SystemCoupling", "Participants", "Scripts", "PythonScript.bat")
            fullPathExeWithArguments = f'"{batchScript}" --pyscript "{pythonScript}" --schost {host} --scport {port} --scname {name}'
            print(f"Full executable: {fullPathExeWithArguments}")
            self.participant_process = subprocess.Popen(            
                fullPathExeWithArguments,
                stdin=subprocess.PIPE,
                stdout=self.standardOutput,
                stderr=self.standardOutput,
                shell=True,
            )
            if not (self.participant_process and self.participant_process.poll() == None):
                raise RuntimeError("Something went wrong. Check participant log output.")
            print("Connected!", flush=True)

        def solve(self):
            print("Solving!", flush=True)
            self.participant_process.communicate()
            print("Finished solving!", flush=True)

    def __init__(self):
        self.system_coupling = Solver.SystemCoupling(self)
#===

my_solver = Solver()

#===

# launch Fluent session and read in mesh file
pipe_fluid_session = pyfluent.launch_fluent(start_transcript=False)
pipe_fluid_mesh_file = "pipe_fluid.msh.h5"
pipe_fluid_session.file.read(file_type="mesh", file_name=pipe_fluid_mesh_file)

# turn on energy model
pipe_fluid_session.setup.models.energy.enabled = True

# add water material
pipe_fluid_session.setup.materials.database.copy_by_name(type="fluid", name="water-liquid")

# set up cell zone conditions
pipe_fluid_session.setup.cell_zone_conditions.fluid["fluid"].material = "water-liquid"

# set up boundary conditions
pipe_fluid_session.setup.boundary_conditions.velocity_inlet["inlet"].momentum.velocity = 0.1
pipe_fluid_session.setup.boundary_conditions.wall['wall'].thermal.thermal_condition = "via System Coupling"

# set up solver settings - 1 fluent iteration per 1 coupling iteration
pipe_fluid_session.solution.run_calculation.iter_count = 1

#===

# launch System Coupling session
syc = pysyc.launch()
syc.start_output()

# add two Fluent sessions above as participants
fluid_name = syc.setup.add_participant(participant_session = pipe_fluid_session)
my_solver_name = syc.setup.add_participant(participant_session = my_solver)
syc.setup.coupling_participant[fluid_name].display_name = "Fluid"
syc.setup.coupling_participant[my_solver_name].display_name = "My Solver"

# temporary: fix up region discretization type
syc.setup.coupling_participant[my_solver_name].region["point-cloud"].region_discretization_type = "Point Cloud Region"

# add a coupling interface
interface = syc.setup.add_interface(
  side_one_participant = fluid_name, side_one_regions = ["wall"],
  side_two_participant = my_solver_name, side_two_regions = ["point-cloud"])

# set up 2-way coupling - add temperature and heat flow data transfers
syc.setup.add_data_transfer(
  interface = interface,
  target_side = "Two",
  source_variable = "temperature",
  target_variable = "vin")

syc.setup.solution_control.maximum_iterations = 2

#===

# solve the coupled analysis
syc.solution.solve()

#===

# clean up at the end
pipe_fluid_session.exit()
syc.exit()
