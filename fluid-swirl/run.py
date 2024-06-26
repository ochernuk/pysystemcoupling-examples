# import required modules
import ansys.fluent.core as pyfluent
import ansys.systemcoupling.core as pysyc
import math

# launch products
fluent = pyfluent.launch_fluent(start_transcript=True, product_version = "24.2.0")
syc = pysyc.launch(version = "24.2")

# setup fluid analysis
fluent.file.read(file_type="case", file_name="tube.cas.h5")

# generate source
def createSourceFile(fileName):
    forceMag = 5.0
    naxial = 33
    ncirc = 10
    nrad = 20
    radius = 0.025    
    with open(fileName, "w") as f:
        for xi in range(naxial):
            x = (1.0 - 0.0) * xi / (naxial - 1)
            for ti in range(ncirc):
                theta = 2.0 * math.pi * ti / ncirc
                for ri in range(nrad):
                    r = radius * (ri + 1) / nrad
                    z = r * math.cos(theta)
                    y = r * math.sin(theta)
                    fx = 0.0
                    fy = forceMag * math.sin(theta + 0.5 * math.pi)
                    fz = forceMag * math.cos(theta + 0.5 * math.pi)
                    f.write(f"{x}, {y}, {z}, {fx}, {fy}, {fz}\n")

srcFileName = "source.scdt"
createSourceFile(srcFileName)

# setup coupled analysis

# add participants
s = syc.setup.add_participant(input_file = srcFileName)
t = syc.setup.add_participant(participant_session = fluent)

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
    target_variable = "lorentz-force",
    value = "vector(Variable1 * 1.0 [N], Variable2 * 1.0 [N], Variable3 * 1.0 [N])",
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
