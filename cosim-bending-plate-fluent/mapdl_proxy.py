import ansys.mapdl.core as pymapdl

from dataclasses import dataclass
from typing import List

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
