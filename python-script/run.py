import ansys.systemcoupling.core as pysyc

from dataclasses import dataclass
from typing import List

import subprocess
import os

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
            return "Transient"

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
                topology="Volume",
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

syc = pysyc.launch(version = "24.2")
assert(syc.ping())
syc.start_output()

solver1 = Solver()
solver2 = Solver()

part1_name = syc.setup.add_participant(participant_session = solver1)
part2_name = syc.setup.add_participant(participant_session = solver2)

# temporary: fix up region discretization type
# TODO: fix this in the setup protocol
syc.setup.coupling_participant[part1_name].region["point-cloud"].region_discretization_type = "Point Cloud Region"
syc.setup.coupling_participant[part2_name].region["point-cloud"].region_discretization_type = "Point Cloud Region"

interface_name = syc.setup.add_interface(
    side_one_participant = part1_name,
    side_one_regions = ["point-cloud"],
    side_two_participant = part2_name,
    side_two_regions = ["point-cloud"],
)

# set up two-way transfers
for target_side in ["One", "Two"]:
    dt_name = syc.setup.add_data_transfer(
        interface = interface_name,
        target_side = target_side,
        source_variable = "vout",
        target_variable = "vin")

syc.setup.solution_control.end_time = 1.0
syc.setup.solution_control.time_step_size = 0.25

syc.solution.solve()
