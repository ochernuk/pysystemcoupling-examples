# Overview

This case couples two Fluent instances to perform
a CHT analysis using System Coupling.

![Setup](setup.png)

The purpose of this example is to demonstrate the integration
of pyFluent and pySystemCoupling.

# pyAnsys instrutions

- Make venv

`python -m venv venv`

- Activate venv

`venv\Scripts\activate.bat`

- Install pyFluent

`pip install ansys.fluent.core`

- Install pySystemCoupling

`pip install ansys_systemcoupling_core-0.1.dev0-py3-none-any.whl`

- Force Fluent to use 23.1 version (well at least I needed to do this)
`set AWP_ROOT222=%AWP_ROOT231%`

- Run script

`python run.py`
