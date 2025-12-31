from typing import Optional, Union, Tuple
from pathlib import Path

import random

# i wonder if there's a better way to do this
ROOT_ASSET_DIRECTORY = Path(__file__).resolve().parent.parent / "assets"

anySuffixes = Optional[Union[str, Tuple[str, ...]]]

class AssetController:
    def __init__(self, folder: str = "") -> None:
        self.folder = folder

    def blindGetAsset(self, fileName: str) -> Path | None:
        for item in self.iterateDirectory(""):
            if not item.stem == fileName:
                continue

            return item

    def getAsset(self, relativePath: str) -> Path:
        return ROOT_ASSET_DIRECTORY / self.folder / relativePath
    
    def getRandom(self, relativePath: str, suffixes: anySuffixes = None, removeSuffix: bool = True) -> Path | None:
        items = self.listDirectory(relativePath, suffixes)
        
        if not items:
            return None

        return random.choice(items).stem

    def listDirectory(self, relativePath: str, suffixes: anySuffixes = None) -> list[Path]:
        return list(self.iterateDirectory(relativePath, suffixes))

    def iterateDirectory(self, relativePath: str, suffixes: anySuffixes = None):
        directory = self.getAsset(relativePath)
        
        if suffixes is None:
            for item in directory.iterdir():
                yield item
        else:
            # normalize to tuple for consistency
            suffixTuple = (suffixes,) if isinstance(suffixes, str) else suffixes
            suffixTuple = tuple(s.lower() for s in suffixTuple)
            
            for item in directory.iterdir():
                if (not item.is_file()) or (item.suffix.lower() not in suffixTuple):
                    continue
                    
                yield item
