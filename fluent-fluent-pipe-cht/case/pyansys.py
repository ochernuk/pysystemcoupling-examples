#
# Copyright 2023 ANSYS, Inc. Unauthorized use, distribution, or duplication is prohibited.
#

import os

import ansys.fluent.core as pyfluent
import ansys.systemcoupling.core as pysyc

class Fluent_SessionProxy(object):

    class Variable(object):
        def __init__(self, name, display_name, tensor_type, is_extensive, location, quantity_type):
            self.name = name
            self.display_name = display_name
            self.tensor_type = tensor_type
            self.is_extensive = is_extensive
            self.location = location
            self.quantity_type = quantity_type    

    class Region(object):
        def __init__(self, name, display_name, topology, input_variables, output_variables):
            self.name = name
            self.display_name = display_name
            self.topology = topology
            self.input_variables = input_variables
            self.output_variables = output_variables

    def __init__(self, session):
        self.session = session
        self.participant_type = "FLUENT"

    def __getattr__(self, attr):
        return getattr(self.session, attr)

    def __get_syc_setup(self):
        # TODO: skip scp file
        setup_info = dict()
        setup_info["regions"] = list()
        setup_info["variables"] = list()
        import xml.etree.ElementTree
        scp_file_name = "fluent.scp"
        self.session.solver.root.file.export.sc_def_file_settings.write_sc_file(
            file_name = scp_file_name, overwrite = True)    
        assert os.path.exists(scp_file_name)
        xmlRoot = xml.etree.ElementTree.parse(scp_file_name)
        coSimControl = xmlRoot.find("./CosimulationControl")
        setup_info["analysis-type"] = coSimControl.find("AnalysisType").text
        variables = coSimControl.find("Variables").findall("Variable")
        for variable in variables:
            name = variable.find("Name").text
            display_name = variable.find("DisplayName").text
            tensor_type = "Vector" if name in {"force", "lorentz-force"} else "Scalar"
            is_extensive = name in {"force", "lortentz-force", "heatrate", "heatflow"}
            location = "Node" if name in {"displacement"} else "Element"
            quantity_type = variable.find("QuantityType").text
            setup_info["variables"].append(Fluent_SessionProxy.Variable(name, display_name, tensor_type, is_extensive, location, quantity_type))
        regions = coSimControl.find("Regions").findall("Region")
        for region in regions:
            name = region.find("Name").text
            display_name = region.find("DisplayName").text
            topology = region.find("Topology").text
            input_variables = [var.text for var in region.find("InputVariables")]
            output_variables = [var.text for var in region.find("OutputVariables")]
            setup_info["regions"].append(Fluent_SessionProxy.Region(name, display_name, topology, input_variables, output_variables))
        #os.remove(scp_file_name)
        return setup_info

    def get_variables(self):
        return self.__get_syc_setup()["variables"]

    def get_regions(self):
        return self.__get_syc_setup()["regions"]

    def get_analysis_type(self):
        return self.__get_syc_setup()["analysis-type"]

    def syc_connect(self, host, port, name):
        connect_command = f'(%sysc-connect-parallel "{host}" {port} "{name}")'
        self.scheme_eval.exec((connect_command,))

    def syc_solve(self):
        self.scheme_eval.exec(("(sc-init-solve)",))

class SyC_SessionProxy(object):
    def __init__(self, session):
        self.session = session
        self.participant_sessions = dict()

    def __getattr__(self, attr):
        return getattr(self.session, attr)

    def add_participant(self, session):
        participant_name = f"{session.participant_type}-{len(self.participant_sessions)+1}"
        self.setup.activate_hidden.beta_features = True
        participant_object = self.setup.coupling_participant.create(participant_name)
        participant_object.participant_type = session.participant_type
        if session.participant_type == "FLUENT": participant_object.use_new_apis = True
        participant_object.participant_analysis_type = session.get_analysis_type()
        self.setup.analysis_control.analysis_type = session.get_analysis_type()# TODO: this logic isn't quite right, maybe delegate to controller
        participant_object = self.setup.coupling_participant[participant_name]
        participant_object.execution_control.option = "ExternallyManaged"
        variables = session.get_variables()
        for variable in variables:
            var_object = participant_object.variable.create(variable.name)
            var_object.tensor_type = variable.tensor_type
            var_object.is_extensive = variable.is_extensive
            var_object.location = variable.location
            var_object.quantity_type = variable.quantity_type
            var_object.participant_display_name = variable.display_name
            var_object.display_name = variable.display_name.replace(" ", "_") # TODO: delegate this to controller
        regions = session.get_regions()
        for region in regions:
            reg_object = participant_object.region.create(region.name)
            reg_object.topology = region.topology
            reg_object.input_variables = region.input_variables
            reg_object.output_variables = region.output_variables
            reg_object.display_name = region.display_name

        self.participant_sessions[participant_name] = session
        return participant_name

    def add_thermal_data_transfers(self, interface):
        self._native_api.AddThermalDataTransfers(Interface = interface)

    def get_host_and_port(self, participant_name):
        """
        Query to get server host and port for a given participant name.
        This should ultimately become a controller query.
        Taking participant name is appropriate, since it is possible that
        there will one day be different servers for different participants.
        For now just parse the execution command to get it.
        """
        exe = self.session._native_api.GetExecutionCommand(ParticipantName = participant_name)
        port = int(exe.split("scport=")[1].split(" ")[0])
        host = exe.split("schost=")[1].split(" ")[0]
        print(host)
        print(port)
        return host, port

    def solve(self):
        import threading

        print("creating system coupling solve thread")
        syc_thread = threading.Thread(target = self.session.solve)

        print("creating participant connect threads")
        # connect call must be done asynchronously,
        # because it does not return until all participants are connected
        participant_threads = list()
        for name, session in self.participant_sessions.items():
            host, port = self.get_host_and_port(name)
            participant_session = self.participant_sessions[name]
            participant_thread = threading.Thread(target = participant_session.syc_connect, args = (host,port,name))
            participant_threads.append(participant_thread)

        print("before solve_syc_async")
        syc_thread.start()
        print("after solve_syc_async")

        # start connecting to system coupling
        for participant_thread in participant_threads:
            participant_thread.start()

        # wait until connections are established
        for participant_thread in participant_threads:
            participant_thread.join()

        participant_threads.clear()
        print("connected to solvers")
        print("creating participant solve threads")
        for name, session in self.participant_sessions.items():
            part_thread = threading.Thread(target = session.syc_solve)
            part_thread.start()

        print("waiting until solve complete")
        syc_thread.join()
        for participant_thread in participant_threads:
            participant_thread.join()

        print("solve complete")

pipe_fluid_session = Fluent_SessionProxy(pyfluent.launch_fluent(precision="double", processor_count=2))
pipe_fluid_case_file = os.path.join("pipefluid", "pipefluid.cas.h5")
pipe_fluid_session.solver.root.file.read(file_type="case", file_name=pipe_fluid_case_file)

pipe_solid_session = Fluent_SessionProxy(pyfluent.launch_fluent(precision="double", processor_count=2))
pipe_solid_case_file = os.path.join("pipesolid", "pipesolid.cas.h5")
pipe_solid_session.solver.root.file.read(file_type="case", file_name=pipe_solid_case_file)

syc = SyC_SessionProxy(pysyc.launch())

syc.setup.activate_hidden.alpha_features = True

fluid_name = syc.add_participant(pipe_fluid_session)
solid_name = syc.add_participant(pipe_solid_session)

interface = syc.setup.add_interface(
  side_one_participant = fluid_name, side_one_regions = ["wall"],
  side_two_participant = solid_name, side_two_regions = ["innerwall"])

syc.add_thermal_data_transfers(interface = interface)

syc.setup.solution_control.minimum_iterations = 2
syc.setup.solution_control.maximum_iterations = 2 # should be 100, but for testing 2 is enough

syc.setup.solution_control.available_ports.option = "UserDefined"
syc.setup.solution_control.available_ports.range = "52000,52001,52002"

syc.setup.print_state()

syc.solve()

pipe_fluid_session.exit()
pipe_solid_session.exit()
syc.exit()

print("DONE!")
