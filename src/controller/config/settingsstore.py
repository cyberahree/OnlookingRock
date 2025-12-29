from . import ConfigController, getByPath, setByPath

from PySide6.QtCore import QObject, Signal

from typing import Any, Callable
from copy import deepcopy

JsonDict = dict[str, Any]

def _getPathDiffs(old: Any, new: Any, prefix: str = "") -> dict[str, Any]:
    out: dict[str, Any] = {}

    if isinstance(old, dict) and isinstance(new, dict):
        keys = set(old.keys()) | set(new.keys())

        for key in keys:
            path = f"{prefix}.{key}" if prefix else key
            out.update(_getPathDiffs(old.get(key), new.get(key), path))

        return out

    if old != new:
        out[prefix] = new

    return out


class SettingsStore(QObject):
    valueChanged = Signal(str, object)
    valuesChanged = Signal(dict)
    committed = Signal()
    reloaded = Signal()
    saveFailed = Signal(str)

    def __init__(self, config: ConfigController, parent: QObject | None = None):
        super().__init__(parent)
        self._config = config

        self._baseline: JsonDict = deepcopy(self._config.config)
        self._draft: JsonDict | None = None

        self._watchers: dict[str, list[Callable[[Any], None]]] = {}

        self.schema_index = self._buildSchemaIndex(self._config.schema)
        self._validateSchemaPaths()

    @property
    def config(self) -> JsonDict:
        return self._config.config

    @property
    def defaults(self) -> JsonDict:
        return self._config.defaults

    # drafts
    def beginEdit(self) -> None:
        self._draft = deepcopy(self._config.config)

    def discardDraft(self) -> None:
        self._draft = None

    def hasDraft(self) -> bool:
        return self._draft is not None

    def isDirty(self) -> bool:
        if self._draft is None:
            return False

        return bool(
            _getPathDiffs(self._baseline, self._draft)
        )

    def get(self, path: str, draft: bool = False) -> Any:
        data = self._draft if (draft and self._draft is not None) else self._config.config
    
        return getByPath(data, path)

    def setDraft(self, path: str, value: Any) -> None:
        if self._draft is None:
            self.beginEdit()

        assert self._draft is not None

        value = self._coerceFromSchema(path, value)
        setByPath(self._draft, path, value)

    # commits/reloads
    def commitDraft(self) -> bool:
        if self._draft is None:
            return True

        changes = _getPathDiffs(self._baseline, self._draft)

        if not changes:
            self._draft = None
            return True

        try:
            # apply changes to real config
            for path, value in changes.items():
                self._config.setValue(path, value)

            self._config.saveConfig()

            # update baseline to the newly committed state
            self._baseline = deepcopy(self._config.config)
            self._draft = None
        except Exception as e:
            self.saveFailed.emit(str(e))
            return False

        # emit signals AFTER successful save
        self.valuesChanged.emit(changes)

        for path, value in changes.items():
            self.valueChanged.emit(path, value)

            for callback in self._watchers.get(path, []):
                try:
                    callback(value)
                except Exception:
                    pass

        self.committed.emit()
        return True

    def reload(self) -> None:
        self._config.loadConfig()
        self._baseline = deepcopy(self._config.config)
        self._draft = None
        self.reloaded.emit()

    def switchProfile(self, profile: str) -> None:
        self._config.switchProfile(profile)
        self._baseline = deepcopy(self._config.config)
        self._draft = None
        self.reloaded.emit()

    # watching
    def watch(self, path: str, cb: Callable[[Any], None], call_immediately: bool = True) -> None:
        self._watchers.setdefault(path, []).append(cb)

        if call_immediately:
            cb(self.get(path))

    # schema
    def _buildSchemaIndex(self, schema: JsonDict) -> dict[str, JsonDict]:
        index: dict[str, JsonDict] = {}

        for section in schema.get("sections", []):
            for item in section.get("items", []):
                path = item.get("path")

                if not path:
                    continue
                
                index[path] = item

        return index

    def _validateSchemaPaths(self) -> None:
        # if the schema contains paths that do not exist in defaults
        # this SHOULD always raise an error

        for path in self.schema_index.keys():
            getByPath(self._config.defaults, path)

    def _coerceFromSchema(self, path: str, value: Any) -> Any:
        item = self.schema_index.get(path)

        if not item:
            return value

        itemType = item.get("type")

        if itemType == "float":
            try:
                v = float(value)
            except Exception:
                return value

            # clamp if min/max exist
            if "min" in item:
                v = max(float(item["min"]), v)
            if "max" in item:
                v = min(float(item["max"]), v)
            return v

        if itemType == "int":
            try:
                return int(value)
            except Exception:
                return value

        if itemType == "string":
            return str(value)

        if itemType == "enum":
            options = item.get("options", [])
            return value if value in options else (options[0] if options else value)

        return value
