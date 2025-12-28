from pathlib import Path
from typing import Optional, Union, Tuple

# i wonder if there's a better way to do this
ROOT_ASSET_DIRECTORY = Path(__file__).resolve().parent.parent / "assets"

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
    
    def iterateDirectory(self, relativePath: str, suffixes: Optional[Union[str, Tuple[str, ...]]] = None):
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
