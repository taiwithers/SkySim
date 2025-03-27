# `settings`

```{eval-rst}
.. generate the module docstring, and manually prevent duplicated docs of items defined in the module
.. doing it this way means that anything new added in the source files will show up here, indicating that it has not yet been sorted into one of the below categories
.. automodule:: skysim.settings
   :no-index:
   :exclude-members: Settings, ImageSettings, PlotSettings, AIRY_DISK_RADIUS, MAXIMUM_LIGHT_SPREAD, confirm_config_file, load_from_toml, toml_to_dicts, split_nested_key, access_nested_dictionary, check_key_exists, check_mandatory_toml_keys, parse_angle_dict, time_to_timedelta, get_config_option, ConfigValue, ConfigMapping, TOMLConfig, SettingsPair, angle_to_dms, check_for_overwrite
```

## Constants

```{eval-rst}
.. autosummary::
   :toctree: ../generated

   AIRY_DISK_RADIUS
   MAXIMUM_LIGHT_SPREAD
```

## Type Aliases

```{eval-rst}
.. autosummary::
    :toctree: ../generated

    ConfigValue
    ConfigMapping
    TOMLConfig
    SettingsPair
```

## Classes

```{eval-rst}
.. autosummary::
   :toctree: ../generated

   Settings
   ImageSettings
   PlotSettings
```

## Functions

### High-Level Functions

```{eval-rst}
.. autosummary::
   :toctree: ../generated

   confirm_config_file
   load_from_toml
   check_for_overwrite
```

## Low-Level Functions

```{eval-rst}
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
   angle_to_dms
```
