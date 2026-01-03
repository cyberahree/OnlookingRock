"""
controller for interactability flags

flags that are currently tracked by the sprite system;
- "drag" -> controls user dragging of rockin
- "blink" -> controls blinking of rockin's eyes
- "petting" -> controls petting interaction
- "eyetrack" -> controls cursor tracking
- "autopilot" -> disables the sprite update loop; events are expected to set sprite features manually

any flag can be acquired by any owner, and will remain disabled until all owners have released it
"""

from typing import Dict, Iterable, Set
from dataclasses import dataclass

@dataclass
class FlagToken:
    """
    this is a handle returned by InteractabilityFlags.acquire()
    """

    owner: str
    flags: tuple[str, ...]

    _controller: "InteractabilityFlags"
    isReleased: bool = False

    def release(self):
        if self.isReleased:
            return
        
        self.isReleased = True
        self._controller.release(self.flags, self.owner)

    def __exit__(self, _type, _value, _traceback):
        self.release()

class InteractabilityFlags:
    """
    controller for interactability flags
    """

    def __init__(self):
        self.locks: Dict[str, Set[str]] = {}

    def isEnabled(self, flag: str) -> bool:
        """
        determine if a flag is enabled
        
        :param flag: The flag to check
        :type flag: str

        :return: true if the flag is enabled, false otherwise
        :rtype: bool
        """
        return flag not in self.locks or len(self.locks[flag]) == 0

    def anyDisabled(self, flags: Iterable[str]) -> bool:
        """
        determine if any of the given flags are disabled
        
        :param flags: the flags to check
        :type flags: Iterable[str]

        :return: true if any of the flags are disabled, false otherwise
        :rtype: bool
        """
        return any(not self.isEnabled(flag) for flag in flags)

    def acquire(self, owner: str, flags: Iterable[str]) -> FlagToken:
        """
        acquire the given flags for the given owner
        
        :param flags: the flags to acquire
        :type flags: Iterable[str]

        :param owner: the owner acquiring the flags
        :type owner: str

        :return: a token representing the acquired flags
        :rtype: FlagToken
        """

        if isinstance(flags, str):
            flags = (flags,)
        
        flagsTuple = tuple(flags)

        for flag in flagsTuple:
            self.locks.setdefault(flag, set()).add(owner)

        return FlagToken(
            owner=owner,
            flags=flagsTuple,
            _controller=self
        )

    def release(self, flags: Iterable[str], owner: str):
        """
        release the given flags for the given owner
        
        :param flags: the flags to release
        :type flags: Iterable[str]

        :param owner: the owner releasing the flags
        :type owner: str
        """

        if isinstance(flags, str):
            flags = (flags,)

        for flag in flags:
            owners = self.locks.get(flag)

            if not owners:
                continue

            owners.discard(owner)

            if len(owners) == 0:
                del self.locks[flag]

    def clearOwner(self, owner: str):
        """
        clear all flags for the given owner
        
        :param owner: Description
        :type owner: str
        """

        toClear = []

        for flag, owners in self.locks.items():
            if owner not in owners:
                continue

            owners.discard(owner)

        for flag in toClear:
            del self.locks[flag]
