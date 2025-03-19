Settings
========

.. gets the module docstring
.. automodule:: skysim.settings


.. rubric:: Classes
   :heading-level: 2
.. autosummary::
   :toctree: ../generated

   Settings
   ImageSettings
   PlotSettings


.. rubric:: Constants
   :heading-level: 2
.. autosummary::
   :toctree: ../generated

   AIRY_DISK_RADIUS
   MAXIMUM_LIGHT_SPREAD


.. rubric:: Functions
   :heading-level: 2

.. rubric:: High-Level Functions
   :heading-level: 3
.. autosummary::
   :toctree: ../generated

   confirm_config_file
   load_from_toml

.. rubric:: Low-Level Functions
   :heading-level: 3
.. autosummary::
   :toctree: ../generated

   toml_to_dicts
   split_nested_key
   access_nested_dictionary
   check_key_exists
   check_mandatory_toml_keys
   parse_angle_dict
   time_to_timedelta
   get_config_option


.. rubric:: Type Aliases
   :heading-level: 2
.. autosummary::
    :toctree: ../generated

    ConfigValue
    ConfigMapping
    TOMLConfig
    SettingsPair
