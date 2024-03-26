import ansys.systemcoupling.core as pysyc

syc = pysyc.launch()
syc.start_output()

# add FMU participants
fmu1 = syc.setup.add_participant(input_file = 'rootFind.fmu')
fmu2 = syc.setup.add_participant(input_file = 'rootFind.fmu')

# create coupling interface between FMUs
interface_name = syc.setup.add_interface(
    side_one_participant = fmu1,
    side_two_participant = fmu2)

# create data transfer from FMU1 to FMU2
transfer_name = syc.setup.add_data_transfer(
    interface = interface_name,
    target_side = 'Two',
    source_variable = 'Real_1',
    target_variable = 'Real_0')

# create data transfer from FMU2 to FMU1
transfer_name = syc.setup.add_data_transfer(
    interface = interface_name,
    target_side = 'One',
    target_variable = 'Real_0',
    source_variable = 'Real_1')

# setup steady analysis
syc.setup.analysis_control.analysis_type = "Steady"
syc.setup.solution_control.maximum_iterations = 100
syc.setup.output_control.write_initial_snapshot = False

#solve
syc.solution.solve()

syc.end_output()
syc.exit()
