from ..asset import ROOT_ASSET_DIRECTORY

from PySide6.QtCore import Signal

from platformdirs import user_config_dir
from pathlib import Path
from typing import Any

import tempfile
import logging
import json
import os

logger = logging.getLogger(__name__)
JsonDict = dict[str, Any]

def readJSONFile(path: Path) -> JsonDict:
    if not path.exists():
        return {}

    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)

def deleteFileIfExists(path: Path) -> None:
    if path.exists():
        try:
            path.unlink()
        except Exception:
            pass

# why an atomic write for a config file?
# because i fkin love data integrity that's why
def atomicWriteJson(
    path: Path,
    data: JsonDict
) -> None:
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
    out = dict(base)

    for (key, value) in overlay.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = deepMerge(out[key], value)
        else:
            out[key] = value

    return out

def pruneForDefaults(
    defaults: JsonDict,
    current: JsonDict
) -> JsonDict:
    if isinstance(defaults, dict) and isinstance(current, dict):
        out: JsonDict = {}

        for (key, value) in current.items():
            defaultValue = defaults.get(key)
            difference = pruneForDefaults(defaultValue, value)

            if difference is not None:
                out[key] = difference

        return out if len(out) > 0 else None

    if type(defaults) != type(current):
        return current

    # primitive
    return None if defaults == current else current

def getByPath(
    data: JsonDict,
    path: str
) -> Any:
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
    parts = path.split(".")
    current = data

    for part in parts[:-1]:
        if part not in current or not isinstance(current[part], dict):
            current[part] = {}

        current = current[part]

    current[parts[-1]] = value

class ConfigController:
    onValueChanged = Signal(str, object)

    def __init__(self):
        self.appName = "OnlookinRock"

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
        configurationFile: Path = None
    ):
        profileToLoad = (configurationFile if configurationFile is not None else self.userProfilePath)

        try:
            assert profileToLoad.exists()
            self.currentOverrides = readJSONFile(profileToLoad)
        except BaseException:
            self.currentOverrides = {}

        self.config = deepMerge(
            self.defaults,
            self.currentOverrides
        )

        logger.debug("Loaded config: %s", self.config)
        return self.config

    def saveConfig(self):
        pruned = pruneForDefaults(
            self.defaults,
            self.config
        )

        atomicWriteJson(
            self.userProfilePath,
            pruned or {}
        )

    def getValue(self, path: str) -> Any:
        return getByPath(self.config, path)

    def setValue(self, path: str, value: Any) -> None:
        self.onValueChanged.emit(path, value)
        return setByPath(self.config, path, value)
