from PySide6.QtCore import QTimer, QObject

from typing import Optional

class FacialAnimationSequence(QObject):
    """
    runs a timed sequence of eye/face sprite changes using a single-shot timer
    """

    def __init__(self, sprite):
        """Bind to a sprite and prepare the timer.

        :param sprite: Object exposing updateSpriteFeatures(face, eyes, forceful)
        """

        super().__init__(sprite)
        self.sprite = sprite

        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self._advance)

        self.sequence = []
        self.currentIndex = 0
        self.onComplete = None

    def addState(
        self,
        duration_ms,
        eyes: Optional[str] = None,
        face: Optional[str] = None
    ):
        """
        Queue a state for the given duration in milliseconds.

        :param duration_ms: How long to display this state (ms)
        :param eyes: Eyes appearance key (e.g. "blink", "idle")
        :type eyes: Optional[str]
        :param face: Face appearance key (or tuple if your sprite expects it)
        :type face: Optional[str]
        """

        self.sequence.append({
            "duration": int(duration_ms),
            "eyes": eyes,
            "face": face
        })

        return self

    def play(self, on_complete: Optional[callable] = None):
        """Start the queued sequence; call on_complete when finished.

        :param on_complete: Optional callback when the sequence ends
        :type on_complete: Optional[callable]
        """

        self.onComplete = on_complete
        self.currentIndex = 0
        self.timer.stop()
        self._advance()

    def _advance(self):
        """
        Apply the current state then schedule the next one.
        """

        if self.currentIndex >= len(self.sequence):
            if self.onComplete:
                self.onComplete()

            return

        state = self.sequence[self.currentIndex]

        # don't swallow exceptions silently while debugging
        if state["face"]:
            self.sprite.updateSpriteFeatures(
                state["face"],
                None,
                True
            )
        
        if state["eyes"]:
            self.sprite.updateSpriteFeatures(
                None,
                state["eyes"],
                True
            )

        self.currentIndex += 1

        # wait THIS state's duration, then advance
        self.timer.start(state["duration"])
