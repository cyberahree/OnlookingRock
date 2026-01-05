from .asset import ROOT_ASSET_DIRECTORY

from PySide6.QtCore import Signal, QObject

from platformdirs import user_config_dir
from typing import Any, Optional
from copy import deepcopy
from pathlib import Path

import tempfile
import logging
import json
import os

logger = logging.getLogger(__name__)
JsonDict = dict[str, Any]

def readJSONFile(path: Path) -> JsonDict:
    """
    read a JSON file and return its contents as a dictionary.
    returns an empty dict if the file does not exist.
    
    :param path: the path to the JSON file
    :type path: Path
    :return: the parsed JSON data
    :rtype: JsonDict
    """
    if not path.exists():
        return {}

    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)

def deleteFileIfExists(path: Path) -> None:
    """
    delete a file if it exists, silently ignoring any errors.
    
    :param path: the path to the file to delete
    :type path: Path
    """
    if path.exists():
        try:
            path.unlink()
        except Exception:
            pass

def atomicWriteJson(
    path: Path,
    data: JsonDict
) -> None:
    """
    write JSON data to a file atomically using a temporary file.
    ensures data integrity by writing to a temporary file first, then replacing the target.
    creates parent directories if they do not exist.
    
    :param path: the target path to write to
    :type path: Path
    :param data: the JSON data to write
    :type data: JsonDict
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    fileDescriptor, temporaryFile = tempfile.mkstemp(
        prefix=path.name,
        suffix=".tmp",
        dir=str(path.parent)
    )

    tempFilePath = Path(temporaryFile)

    try:
        with os.fdopen(fileDescriptor, "w", encoding="utf-8") as file:
            json.dump(
                data,
                file,
                indent=4,
                sort_keys=True
            )
            file.write("\n")

        tempFilePath.replace(path)
    finally:
        deleteFileIfExists(tempFilePath)

def deepMerge(
    base: JsonDict,
    overlay: JsonDict
) -> JsonDict:
    """
    recursively merge an overlay dictionary into a base dictionary.
    nested dictionaries are merged recursively; other values are overwritten.
    
    :param base: the base dictionary to merge into
    :type base: JsonDict
    :param overlay: the dictionary with values to overlay on top of the base
    :type overlay: JsonDict
    :return: the merged dictionary
    :rtype: JsonDict
    """
    out = deepcopy(base)

    for (key, value) in overlay.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = deepMerge(out[key], value)
        else:
            out[key] = deepcopy(value)

    return out

def pruneForDefaults(
    defaults: JsonDict,
    current: JsonDict
) -> JsonDict:
    """
    prune configuration values that match their defaults.
    recursively compares current values against defaults, returning only the differences.
    returns None if no differences exist.
    
    :param defaults: the default configuration values
    :type defaults: JsonDict
    :param current: the current configuration values to compare
    :type current: JsonDict
    :return: only the values that differ from defaults, or None if identical
    :rtype: JsonDict
    """
    if isinstance(defaults, dict) and isinstance(current, dict):
        out: JsonDict = {}
        hasChanges = False

        for (key, value) in current.items():
            defaultValue = defaults.get(key)
            
            # key doesn't exist in defaults, keep it
            if defaultValue is None:
                out[key] = value
                hasChanges = True
                continue
            
            # check nested dicts
            if isinstance(value, dict) and isinstance(defaultValue, dict):
                difference = pruneForDefaults(defaultValue, value)
                if difference is not None:
    
                    out[key] = value
                    hasChanges = True
            elif type(defaultValue) == type(value) and defaultValue == value:
                continue
            else:
                out[key] = value
                hasChanges = True

        return out if hasChanges else None

    if type(defaults) != type(current):
        return current

    # primitive
    return None if defaults == current else current

def getByPath(
    data: JsonDict,
    path: str
) -> Any:
    """
    retrieve a value from nested dictionaries using a dot-separated path.
    raises KeyError if the path does not exist in the data.
    
    :param data: the dictionary to retrieve from
    :type data: JsonDict
    :param path: dot-separated path to the value (e.g. "sprite.scale")
    :type path: str
    :return: the value at the specified path
    :rtype: Any
    :raises KeyError: if the path is not found in the data
    """
    current = data

    for part in path.split("."):
        if (not isinstance(current, dict)) or (part not in current):
            raise KeyError(f"Path '{path}' (at part {part}) not found in data")

        current = current[part]

    return current

def setByPath(
    data: JsonDict,
    path: str,
    value: Any
) -> None:
    """
    set a value in nested dictionaries using a dot-separated path.
    creates intermediate dictionaries as needed.
    
    :param data: the dictionary to modify
    :type data: JsonDict
    :param path: dot-separated path to the value (e.g. "sprite.scale")
    :type path: str
    :param value: the value to set
    :type value: Any
    """
    parts = path.split(".")
    current = data

    for part in parts[:-1]:
        if part not in current or not isinstance(current[part], dict):
            current[part] = {}

        current = current[part]

    current[parts[-1]] = value

class ConfigController(QObject):
    """
    manages application configuration with persistence to json.
    merges default configuration with user overrides, provides path-based access to settings, and emits signals on changes.
    """

    onValueChanged = Signal(str, object)

    def __init__(self):
        """
        initialise the configuration controller and load config from disk.
        """

        super().__init__()

        # configuration directory
        self.userProfilesDirectory = Path(
            user_config_dir("OnlookinRock")
        ) / "profiles"

        self.userProfilePath = self.userProfilesDirectory / "profile.json"
        self.defaults = readJSONFile(ROOT_ASSET_DIRECTORY / "baseConfig.json")
        self.currentOverrides = {}
        self.config = {}

        self.loadConfig()

    def loadConfig(
        self,
        configurationFile: Optional[Path] = None
    ):
        """
        load configuration from file and merge with defaults.
        
        :param configurationFile: optional path to load from instead of default location
        :type configurationFile: Optional[Path]
        """

        profileToLoad = (configurationFile if configurationFile is not None else self.userProfilePath)

        try:
            if profileToLoad.exists():
                self.currentOverrides = readJSONFile(profileToLoad)
            else:
                self.currentOverrides = {}
        except (OSError, ValueError, KeyError) as e:
            logger.warning(f"Failed to load config from {profileToLoad}: {e}")
            self.currentOverrides = {}

        self.config = deepMerge(
            self.defaults,
            self.currentOverrides
        )

        logger.debug("Loaded config: %s", self.config)
        return self.config

    def saveConfig(self):
        """
        save the current configuration to disk, omitting default values.
        """

        pruned = pruneForDefaults(
            self.defaults,
            self.config
        )

        atomicWriteJson(
            self.userProfilePath,
            pruned or {}
        )

    def getValue(self, path: str) -> Any:
        """
        get a configuration value by dot-separated path.
        
        :param path: the config path (e.g. "sprite.scale")
        :type path: str
        :return: the configuration value
        :rtype: Any
        """

        return getByPath(self.config, path)

    def setValue(self, path: str, value: Any):
        """
        set a configuration value by dot-separated path and emit change signal.
        
        :param path: the config path to set
        :type path: str
        :param value: the value to set
        :type value: Any
        """

        setByPath(self.config, path, value)
        self.onValueChanged.emit(path, value)

    def bulkSetValues(self, updates: dict[str, Any], parentPath: str = None):
        """
        set multiple configuration values and emit change signals for each.
        
        :param updates: a dictionary of path-value pairs to update
        :type updates: dict[str, Any]
        """

        if (parentPath is not None) and not parentPath.endswith("."):
            parentPath += "."

        for (path, value) in updates.items():
            self.setValue(parentPath + path, value)
