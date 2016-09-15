opto
====

opto is a Python module that allows you to control `Optotune focus
tunable
lenses <http://www.optotune.com/products/focus-tunable-lenses>`__ using
the `Optotune Lens Driver
4 <http://www.optotune.com/products/focus-tunable-lenses/lens-drivers>`__.
Tested with an `Optotune
EL-10-30 <http://www.optotune.com/products/focus-tunable-lenses/electrical-lens-el-10-30?task=view&id=18>`__.

Examples
~~~~~~~~

Opens the serial port, connects to the Optotune, sets the lens current
to 50 mA, and closes the serial port, gently returning the lens to 0 mA
current:

.. code:: python

    from opto import Opto

    o = Opto(port='/dev/cu.usbmodem1411')
    o.connect()
    o.current(50.0)
    o.close(soft_close=True)

Alternatively, here we use the ``with`` statement to create a sinusoidal
transition from minimum to maximum current and back:

.. code:: python

    from opto import Opto
    import numpy as np
    import time

    with Opto(port='/dev/cu.usbmodem1411') as o:
        current_low = o.current_lower()
        current_high = o.current_upper()
        current_delta = current_high-current_low
        for i in np.linspace(0, 2*np.pi, 1000):
            o.current(np.sin(i)*current_delta+current_low)
            time.sleep(0.01)

Installation
------------

Use ``pip`` to install from github:

::

    pip install git+https://github.com/OrganicIrradiation/opto.git

or clone the package using git:

::

    git clone https://github.com/OrganicIrradiation/opto.git

Requirements
------------

Requires `pySerial <https://pypi.python.org/pypi/pyserial>`__
