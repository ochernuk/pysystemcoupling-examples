# Overview

This case couples Fluent to MAPDL to perform
a steady FSI analysis using System Coupling.

![Setup](bending_plate.png)

# Instrutions

This requires latest v242 build, so set AWP_ROOT environment variable 
to AWP_ROOT242. On Windows:
`set AWP_ROOT=%AWP_ROOT242%`

On Linux:
`export AWP_ROOT=$AWP_ROOT242`

- Install pyFluent

`pip install ansys.fluent.core`

- Install pyMapdl

`pip install ansys.mapdl.core`

- Install pySystemCoupling

`pip install ansys.systemcoupling.core`

- Run script

`python run.py`
