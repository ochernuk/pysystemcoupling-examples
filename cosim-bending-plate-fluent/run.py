import ansys.mapdl.core as pymapdl
import ansys.fluent.core as pyfluent
import ansys.systemcoupling.core as pysyc

from dataclasses import dataclass
from typing import List
import os

"""
TODO:
- fix fluent displacement bug: https://github.com/ansys/pyfluent/pull/2145
- pymapdl additional_switches case issue: https://github.com/ansys/pymapdl/discussions/2418
- mapdl.exit() throws exception when connected to System Coupling
- mapdl should (probably) disconnect during mapdl.finish()
- need to add a new mapdl command to connect to System Coupling, something like mapdl.scconn(host, port, name)
- integrate Mapdl_SessionProxy proxy code into the repo
"""

class Mapdl_SessionProxy(object):
    """
    This proxy class is a wrapper around the actual PyMAPDL solver session.
    It is needed to work around the requirement to connect to System Coupling
    after the solver session is started.

    When launching MAPDL session, just create an instance of this proxy class

    mapdl = Mapdl_SessionProxy()

    and then interact with the mapdl object as if it were a real mapdl
    session handle. In reality, all commands will first be recored
    internally in the proxy object, and then passed through to the
    underlying mapdl session handle.

    When solving the coupled analysis using System Coupling, this proxy
    object will quit the original mapdl session, start a new one that will
    be connected to System Coupling, and will replay all the commands
    that were provided to the original session (in the original order).

    """

    class SystemCouplingInterface(object):

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
    
        def __init__(self, handle):
            self.__handle = handle
            self.__regions = list()
            self.__variables = list()
            self.__structural = False
            self.__thermal = False
            self.__analysis_type = "Steady"

        @property
        def participant_type(self) -> str:
            return "MAPDL"

        def get_variables(self):
            return self.__variables

        def get_regions(self):
            return self.__regions

        def get_analysis_type(self) -> str:
            return self.__analysis_type

        def connect(self, host, port, name):
            self.__handle._mapdl_session.exit()
            self.__handle._mapdl_session = pymapdl.launch_mapdl(additional_switches = f"-scport {port} -schost {host} -scname {name}")

        def solve(self):
            self.__handle._replay()
            self.__handle._mapdl_session.solve()
            self.__handle._mapdl_session.finish()
            # temporary
            self.__handle._mapdl_session.exit()
            del self.__handle._mapdl_session
            self.__handle._mapdl_session = None

        def _add_surface_region(self, region_name):
            region = Mapdl_SessionProxy.SystemCouplingInterface.Region(name=region_name, display_name = f"System Coupling (Surface) Region {len(self.__regions)}", topology = "Surface", input_variables = list(), output_variables = list())
            if self.__structural:
                region.input_variables.append("FORC")
                region.input_variables.append("FDNS")
                region.output_variables.append("INCD")
            if self.__thermal:
                region.input_variables.append("TEMP")
                region.input_variables.append("TBULK")
                region.input_variables.append("HCOEF")
                region.input_variables.append("HFLW")
                region.output_variables.append("TEMP")
                region.output_variables.append("TBULK")
                region.output_variables.append("HCOEF")
                region.output_variables.append("HFLW")
            self.__regions.append(region)

        def _add_volume_region(self, region_name):
            region = Mapdl_SessionProxy.SystemCouplingInterface.Region(name=region_name, display_name = f"System Coupling (Volume) Region {len(self.__regions)}", topology = "Volume", input_variables = list(), output_variables = list())
            if self.__thermal:
                region.input_variables.append("HGEN")
                region.input_variables.append("TPLD")
                region.output_variables.append("TEMP")
            self.__regions.append(region)

        def _activate_structural(self):
            if not self.__structural:
                self.__structural = True
                self.__variables.append(Mapdl_SessionProxy.SystemCouplingInterface.Variable(name="FORC", display_name = "Force", tensor_type = "Vector", is_extensive = True, location = "Node", quantity_type = "Force"))
                self.__variables.append(Mapdl_SessionProxy.SystemCouplingInterface.Variable(name="FDNS", display_name = "Force Density", tensor_type = "Vector", is_extensive = False, location = "Element", quantity_type = "Force"))
                self.__variables.append(Mapdl_SessionProxy.SystemCouplingInterface.Variable(name="INCD", display_name = "Incremental Displacement", tensor_type = "Vector", is_extensive = False, location = "Node", quantity_type = "Incremental Displacement"))
                for region in self.__regions:
                    if region.topology == "Surface":
                        region.input_variables.append("FORC")
                        region.input_variables.append("FDNS")
                        region.output_variables.append("INCD")

        def _activate_thermal(self):
            if not self.__thermal:
                self.__thermal = True
                self.__variables.append(Mapdl_SessionProxy.SystemCouplingInterface.Variable(name="TEMP", display_name = "Temperature", tensor_type = "Scalar", is_extensive = False, location = "Node", quantity_type = "Temperature"))
                self.__variables.append(Mapdl_SessionProxy.SystemCouplingInterface.Variable(name="TBULK", display_name = "Bulk Temperature", tensor_type = "Scalar", is_extensive = False, location = "Node", quantity_type = "Convection Reference Temperature"))
                self.__variables.append(Mapdl_SessionProxy.SystemCouplingInterface.Variable(name="HCOEF", display_name = "Heat Transfer Coefficient", tensor_type = "Scalar", is_extensive = False, location = "Node", quantity_type = "Heat Transfer Coefficient"))
                self.__variables.append(Mapdl_SessionProxy.SystemCouplingInterface.Variable(name="HFLW", display_name = "Heat Flow", tensor_type = "Scalar", is_extensive = True, location = "Node", quantity_type = "Heat Rate"))
                self.__variables.append(Mapdl_SessionProxy.SystemCouplingInterface.Variable(name="HGEN", display_name = "Heat Generation", tensor_type = "Scalar", is_extensive = False, location = "Node", quantity_type = "Heat Rate"))
                self.__variables.append(Mapdl_SessionProxy.SystemCouplingInterface.Variable(name="TPLD", display_name = "Temperature Load", tensor_type = "Scalar", is_extensive = False, location = "Node", quantity_type = "Temperature"))
                self.__variables.append(Mapdl_SessionProxy.SystemCouplingInterface.Variable(name="TEMP", display_name = "Temperature", tensor_type = "Scalar", is_extensive = False, location = "Node", quantity_type = "Temperature"))                
                for region in self.__regions:
                    if region.topology == "Surface":
                        region.input_variables.append("TEMP")
                        region.input_variables.append("TBULK")
                        region.input_variables.append("HCOEF")
                        region.input_variables.append("HFLW")
                        region.output_variables.append("TEMP")
                        region.output_variables.append("TBULK")
                        region.output_variables.append("HCOEF")
                        region.output_variables.append("HFLW")
                    elif region.topology == "Volume":
                        region.input_variables.append("HGEN")
                        region.input_variables.append("TPLD")
                        region.output_variables.append("TEMP")

        def _set_steady(self):
            self.__analysis_type = "Steady"

        def _set_transient(self):
            self.__analysis_type = "Transient"

    def __init__(self, *args, **kwargs):
        self.system_coupling = Mapdl_SessionProxy.SystemCouplingInterface(self)
        self._mapdl_session = pymapdl.launch_mapdl(*args, **kwargs)
        self._command_stack = list()

    def __getattr__(self, attr):
        if attr not in {"eplot"}: # certain commands will need to be ignored when replaying
            self._command_stack.append([attr])
            return self.__handle
        else:
            return getattr(self._mapdl_session, attr)

    def __handle(self, *args, **kwargs):
        cmd = self._command_stack[-1][0]
        for arg in args: self._command_stack[-1].append(arg)
        for k, v in kwargs.items(): self._command_stack[-1].append({k:v})
        if cmd == "sf" and args[1].upper() == "FSIN":
            region_name = args[0]
            self.system_coupling._add_surface_region(region_name)
        elif cmd == "bfe" and args[1].upper() == "FVIN":
            region_name = args[0]
            self.system_coupling._add_volume_region(region_name)
        elif cmd == "antype":
            if args[0] == 0: self.system_coupling._set_steady()
            elif args[0] == 4: self.system_coupling._set_transient()
        elif cmd == "et":
            etype = args[1]
            # TODO: the elements list is far from complete
            if etype in {186}:
                self.system_coupling._activate_structural()
            if etype in {70,90}:
                self.system_coupling._activate_thermal()
        getattr(self._mapdl_session, cmd)(*args, **kwargs)

    def _replay(self):
        for cmd in self._command_stack:
            if len(cmd) == 1:
                getattr(self._mapdl_session, cmd[0])()               
            else:
                getattr(self._mapdl_session, cmd[0])(*cmd[1:])        

    def print_commands(self):
        import pprint
        pprint.pprint(self._command_stack)

#================================

mapdl = Mapdl_SessionProxy()

mapdl.prep7()

# define material properties
mapdl.mp("DENS", 1, 2550)
mapdl.mp("ALPX", 1, 1.2e-05)
mapdl.mp("C", 1, 434)
mapdl.mp("KXX", 1, 60.5)
mapdl.mp("RSVX", 1, 1.7e-07)
mapdl.mp("EX", 1, 2500000)
mapdl.mp("NUXY", 1, 0.35)
mapdl.mp("MURX", 1, 10000)

# set element types to SOLID186
mapdl.et(1, 186)
mapdl.keyopt(1,2,1)

# make geometry
mapdl.block(10.00, 10.06, 0.0, 1.0, 0.0, 0.4)
mapdl.vsweep(1)

# add fixed support at y=0
mapdl.nsel("S", "LOC", "Y", 0)
mapdl.d("all", "all")

# add FSI interface
mapdl.nsel("S", "LOC", "X", 10.0)
mapdl.nsel("A", "LOC", "Y", 1.0)
mapdl.nsel("A", "LOC", "X", 10.06)
mapdl.cm("FSIN_1", "NODE")
mapdl.sf("FSIN_1", "FSIN", 1)

mapdl.allsel()

mapdl.run("/SOLU")

# set analysis type to steady
mapdl.antype(0)

#================================

fluent = pyfluent.launch_fluent(product_version="24.1.0", start_transcript=False)
case_file = "case.cas.gz"
fluent.file.read(file_type="case", file_name="case.cas.h5")
fluent.solution.run_calculation.iter_count = 1

#================================

syc = pysyc.launch(version = "24.1")
syc.start_output()

fluid_name = syc.setup.add_participant(participant_session = fluent)
solid_name = syc.setup.add_participant(participant_session = mapdl)

syc.setup.coupling_participant[fluid_name].display_name = "Fluid"
syc.setup.coupling_participant[solid_name].display_name = "Solid"

# temporary until bug is fixed
syc.setup.coupling_participant[fluid_name].variable["displacement"].tensor_type = "Vector"

# add a coupling interface
interface = syc.setup.add_interface(
  side_one_participant = fluid_name, side_one_regions = ["wall_deforming"],
  side_two_participant = solid_name, side_two_regions = ["FSIN_1"])

# set up 2-way FSI coupling - add force & displacement data transfers
syc.setup.add_data_transfer(
    interface = interface,
    target_side = "One",
    source_variable = "INCD",
    target_variable = "displacement",
)

syc.setup.add_data_transfer(
    interface = interface,
    target_side = "Two",
    source_variable = "force",
    target_variable = "FDNS",
)

syc.setup.solution_control.maximum_iterations = 20

syc.solution.solve()
