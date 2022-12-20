import ansys.systemcoupling.core as pysyc

syc = pysyc.launch()

syc.setup.add_participant(input_file="Fluent/fluent.scp")
syc.setup.add_participant(input_file="MAPDL/mapdl.scp")

interface_name = syc.setup.add_interface(
    side_one_participant = "FLUENT-1", side_one_regions = ["wall_deforming"], 
    side_two_participant = "MAPDL-2", side_two_regions = ["FSIN_1"])

syc.setup.add_data_transfer(
    interface = interface_name, target_side = "One", 
    source_variable = "INCD", target_variable = "displacement")

syc.setup.add_data_transfer(
    interface = interface_name, target_side = "Two", 
    source_variable = "force", target_variable = "FORC")

syc.setup.solution_control.end_time = 0.2
syc.setup.solution_control.time_step_size = 0.1

syc.start_output()
syc.solve()
syc.end_output()

syc.exit()
