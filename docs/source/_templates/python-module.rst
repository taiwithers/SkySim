Module Title
============

.. gets the module docstring, list anything specified in the below region under :exclude-members:
.. doing it this way means that anything new added in the source files will show up here, indicating that it has not yet been sorted into one of the below categories
.. automodule:: package.modules
   :no-index:
   :exclude-members: CONSTANT_1, CONSTANT_2, MyType, ModuleClass, run_module, helper_a, helper_b, subhelper_x, subhelper_y, subhelper_z


Constants
---------
.. autosummary::
   :toctree: ../generated

    CONSTANT_1
    CONSTANT_2


Type Aliases
------------
.. autosummary::
    :toctree: ../generated

    MyType


Classes
-------
.. autosummary::
    :toctree: ../generated

    ModuleClass


Functions
---------
High-Level Functions
^^^^^^^^^^^^^^^^^^^^
.. autosummary::
   :toctree: ../generated

   run_module

Low-Level Functions
^^^^^^^^^^^^^^^^^^^
.. autosummary::
   :toctree: ../generated

   helper_a
   helper_b

Subsection
""""""""""
.. autosummary::
   :toctree: ../generated

   subhelper_x
   subhelper_y
   subhelper_z
