import os

import ansys.systemcoupling.core as pysyc

syc = pysyc.launch()

mech_srv_name = syc.setup.add_participant(participant_type="MECH-SRV", input_file=os.path.join("mech", "file.rst"))
cfd_srv_name = syc.setup.add_participant(participant_type="CFD-SRV", input_file=os.path.join("cfd", "cfd.input1.csv"))

syc.setup.coupling_participant[cfd_srv_name].execution_control.base_output_file_name =  "cfd.output1"

interface_name = syc.setup.add_interface(
  side_one_participant=mech_srv_name,
  side_one_regions=["BLADESURF"],
  side_two_participant=cfd_srv_name,
  side_two_regions=["R1 Blade"])

syc.native_api.AddAerodampingDataTransfers(Interface = interface_name)

syc.start_output()
syc.solve()
syc.end_output()
syc.exit()
