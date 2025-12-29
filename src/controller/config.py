from .asset import AssetController

from platformdirs import user_config_dir
from pathlib import Path
from typing import Any

import tempfile
import logging
import json
import os
import re

logger = logging.getLogger(__name__)

ASSETS_DIR = AssetController()
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
        prefix = path.name,
        suffix = ".tmp",
        dir = str(path.parent)
    )

    tempFilePath = Path(temporaryFile)

    try:
        with os.fdopen(fileDescriptor, "w", encoding="utf-8") as file:
            json.dump(
                data,
                file,
                indent = 4,
                sort_keys = True
            )
            file.write("\n")
            
        tempFilePath.replace(path)
    finally:
        deleteFileIfExists(tempFilePath)

# i decided there might be (at some rare point in the future)
# a need for so many different settings that some users
# might want to:
# - not use everything
# - have different settings profiles

# so we can prune for "non-defaults", and save them to a config
# then overlay them on top of defaults
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
    def __init__(
        self,
        appName: str = "OnlookinRock",
        baseConfigPath: Path = None,
        profile: str = "default"
    ):
        if baseConfigPath is None:
            baseConfigPath = ASSETS_DIR.getAsset("baseConfig.json")

        self.appName = appName
        self.baseConfigPath = baseConfigPath
        
        # configuration directory
        self.userProfilesDirectory = Path(
            user_config_dir(appName)
        ) / "profiles"

        self.userProfilePath = self.userProfilesDirectory / f"{profile}.json"

        self.schema = self.loadSchema()
        self.defaults = readJSONFile(self.baseConfigPath)
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
    
    def listProfiles(self) -> list[str]:
        self.userProfilesDirectory.mkdir(parents=True, exist_ok=True)

        profiles = {"default"}

        for file in self.userProfilesDirectory.glob("*.json"):
            profiles.add(file.stem)
        
        return sorted(profiles)

    def isValidProfileName(self, profile: str) -> bool:
        pattern = r"^[a-zA-Z0-9_-]{3,32}$"
        return re.match(pattern, profile) is not None

    def getActiveProfile(self) -> str:
        return self.userProfilePath.stem
    
    def getProfilePath(self, profile: str) -> Path:
        self.userProfilesDirectory.mkdir(parents=True, exist_ok=True)
        return self.userProfilesDirectory / f"{profile}.json"

    def createProfile(
        self,
        profile: str,
        overrides: JsonDict = None,
        overwrite: bool = False
    ):
        if not self.isValidProfileName(profile):
            raise ValueError(f"Invalid profile name: {profile}")
        
        profilePath = self.getProfilePath(profile)

        if profilePath.exists() and not overwrite:
            raise FileExistsError(f"Profile '{profile}' already exists at {profilePath}")
        
        atomicWriteJson(
            profilePath,
            overrides or {}
        )

    def deleteProfile(self, profile: str):
        deleteFileIfExists(
            self.getProfilePath(profile)
        )

    def switchProfile(self, profile: str):
        # this method does not save the current profile
        # it just switches to another one

        self.userProfilePath = self.userProfilesDirectory / f"{profile}.json"
        self.loadConfig()
    
    def loadSchema(self) -> JsonDict:
        schemaPath = ASSETS_DIR.getAsset("configSchema.json")
        loadedSchema = readJSONFile(schemaPath)

        return loadedSchema

    def getValue(self, path: str) -> Any:
        return getByPath(self.config, path)

    def setValue(self, path: str, value: Any) -> None:
        return setByPath(self.config, path, value)
    