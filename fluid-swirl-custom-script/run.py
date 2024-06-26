# import required modules
import ansys.fluent.core as pyfluent
import ansys.systemcoupling.core as pysyc
import math
import os
import subprocess
from dataclasses import dataclass
from typing import List

# launch products
fluent = pyfluent.launch_fluent(start_transcript=True, product_version = "24.2.0")
syc = pysyc.launch(version = "24.2")

# setup fluid analysis
fluent.file.read(file_type="case", file_name="tube.cas.h5")

# define source participant
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
            region_discretization_type: str
    
        def __init__(self, solver):
            self.solver = solver

        @property
        def participant_type(self) -> str:
            return "DEFAULT"

        def get_analysis_type(self) -> str:
            return "Steady"

        def get_variables(self):
            variables = list()
            fvar = Solver.SystemCoupling.Variable(
                name="force",
                display_name="force",
                tensor_type="Vector",
                is_extensive=False,
                location="Node",
                quantity_type="Unspecified",
            )
            variables.append(fvar)
            return variables

        def get_regions(self):
            regions = list()
            region = Solver.SystemCoupling.Region(
                name="source",
                display_name="source",
                topology="Volume",
                region_discretization_type="Point Cloud Region",
                input_variables=[],
                output_variables=["force"],
            )
            regions.append(region)
            return regions

        def connect(self, host, port, name):
            print(f"Connecting! Host: {host}, port: {port}, name: {name}", flush=True)
            self.standardOutput = open(f"{name}.stdout", "w")        
            pythonScript = os.path.abspath("participant.py")
            fullPathExeWithArguments = f'python "{pythonScript}" --schost {host} --scport {port} --scname {name}'
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

source_participant = Solver()

# setup coupled analysis

# add participants
s = syc.setup.add_participant(participant_session = source_participant)
t = syc.setup.add_participant(participant_session = fluent)

# temporary: make sure region is correctly set to point cloud
syc.setup.coupling_participant[s].region["source"].region_discretization_type = "Point Cloud Region"

# add interfaces
i = syc.setup.add_interface(
    side_one_participant = s,
    side_one_regions = ["source"],
    side_two_participant = t,
    side_two_regions = ["tube_solid"],
)

# add data transfers
t = syc.setup.add_data_transfer(
    interface = i,
    target_side = "Two",
    source_variable = "force",
    target_variable = "lorentz-force",
)

# solve
syc.solution.solve()

# post-process
fluent.results.graphics.picture.use_window_resolution = False
fluent.results.graphics.picture.x_resolution = 1920
fluent.results.graphics.picture.y_resolution = 1440
fluent.results.graphics.pathline["pathline"] = {}
pathline = fluent.results.graphics.pathline["pathline"]
pathline.field = "velocity-magnitude"
pathline.release_from_surfaces = ["in"]
pathline.display()
fluent.results.graphics.views.restore_view(view_name="isometric")
fluent.results.graphics.views.auto_scale()
fluent.results.graphics.picture.save_picture(file_name="pathline.png")
