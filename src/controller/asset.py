from typing import Optional, Union, Tuple
from pathlib import Path

import random

# i wonder if there's a better way to do this
ROOT_ASSET_DIRECTORY = Path(__file__).resolve().parent.parent / "assets"

anySuffixes = Optional[Union[str, Tuple[str, ...]]]

class AssetController:
    """
    manages access to asset files in the assets directory.
    provides utilities for loading, listing, and randomly selecting assets from folders.
    """

    def __init__(self, folder: str = "") -> None:
        """
        initialise the asset controller for a specific folder.
        
        :param folder: relative path within assets directory
        :type folder: str
        """

        self.folder = folder

    def blindGetAsset(self, fileName: str) -> Path | None:
        """
        get an asset by file name without extension.
        
        :param fileName: the file name to search for
        :type fileName: str
        :return: the asset path or None if not found
        :rtype: Optional[Path]
        """

        for item in self.iterateDirectory(""):
            if not item.stem == fileName:
                continue

            return item

    def getAsset(self, relativePath: str) -> Path:
        """
        get the full path to an asset.
        
        :param relativePath: relative path within the folder
        :type relativePath: str
        :return: the absolute asset path
        :rtype: Path
        """

        return ROOT_ASSET_DIRECTORY / self.folder / relativePath
    
    def getRandom(
        self,
        relativePath: str = "",
        suffixes: anySuffixes = None,
        removeSuffix: bool = True,
    ) -> Optional[Union[str, Path]]:
        """
        get a random asset from a directory.
        
        :param relativePath: relative path within the folder
        :type relativePath: str
        :param suffixes: file extensions to filter by
        :type suffixes: Optional[Union[str, Tuple[str, ...]]]
        :param removeSuffix: whether to remove file extension from result
        :type removeSuffix: bool
        :return: random asset path or name
        :rtype: Optional[Union[str, Path]]
        """

        items = self.listDirectory(relativePath, suffixes)
        
        if not items:
            return None

        choice = random.choice(items)
        return choice.stem if removeSuffix else choice

    def listDirectory(self, relativePath: str = "", suffixes: anySuffixes = None) -> list[Path]:
        """
        list all assets in a directory.
        
        :param relativePath: relative path within the folder
        :type relativePath: str
        :param suffixes: file extensions to filter by
        :type suffixes: Optional[Union[str, Tuple[str, ...]]]
        :return: list of asset paths
        :rtype: list[Path]
        """

        return list(self.iterateDirectory(relativePath, suffixes))

    def iterateDirectory(self, relativePath: str = "", suffixes: anySuffixes = None):
        """
        iterate over assets in a directory.
        
        :param relativePath: relative path within the folder
        :type relativePath: str
        :param suffixes: file extensions to filter by
        :type suffixes: Optional[Union[str, Tuple[str, ...]]]
        """

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
