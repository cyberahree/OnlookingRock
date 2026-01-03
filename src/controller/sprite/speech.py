from ..interfaces.widgets.speechbubble import SpeechBubbleComponent
from ..system.timings import TimingClock

from PySide6.QtCore import QTimer, QEvent, Qt
from PySide6.QtWidgets import QWidget

from typing import Callable, Iterable, Optional
from dataclasses import dataclass
from collections import deque

import random

TAIL_WIDTH = 12

CHARACTERS_PER_SECOND = (25, 45)
READING_DELAY_MS = 4500
READING_WORDS_PER_SECOND = (180 / 60)  # words per second

@dataclass
class SpeechItem:
    text: str
    duration: Optional[int]
    typingDelayMs: int
    interactive: bool = False
    onConfirm: Optional[Callable[[str], None]] = None
    onCancel: Optional[Callable[[], None]] = None
    inputPlaceholder: str = ""
    inputPrefill: str = ""

class SpeechBubbleController(QWidget):
    """
    manages speech bubble display and interactive text input for sprite communication
    """

    def __init__(
        self,
        sprite: QWidget,
        clock: Optional[TimingClock] = None,
        occludersProvider: Optional[Callable[[], Iterable[QWidget]]] = None,
        **kwargs
    ):
        """
        initialise the speech bubble controller with sprite and component references.
        
        :param sprite: The sprite widget to attach the speech bubble to
        :type sprite: QWidget
        :param clock: Optional clock for timing (default None)
        :param occludersProvider: Optional provider for occlusion detection
        :param kwargs: Additional arguments passed to SpeechBubbleComponent
        """

        super().__init__()

        self.bubble = SpeechBubbleComponent(
            sprite,
            clock,
            sprite.soundManager.playSpeechBlip,
            occludersProvider=occludersProvider,
            **kwargs
        )

        self.queue = deque()
        self.active = False
        self.shuttingDown = False

        self._awaitingInput = False
        self._pendingAsk: Optional[SpeechItem] = None

        # allow esc-to-cancel while typing in the embedded input
        try:
            self.bubble.inputField.installEventFilter(self)
        except Exception:
            pass

        # connect once: _confirmAsk() is a no-op unless were awaiting input
        try:
            self.bubble.inputField.returnPressed.connect(self._confirmAsk)
        except Exception:
            pass

        self._nextTimer = QTimer(self)
        self._nextTimer.setSingleShot(True)
        self._nextTimer.timeout.connect(self._showNext)

    def addSpeech(
        self,
        text: str,
        duration: Optional[int] = None
    ):
        """
        add a speech message to the queue for display.
        
        :param text: The text to display
        :type text: str
        :param duration: Display duration in milliseconds (auto-calculated if None)
        :type duration: Optional[int]
        """

        if self.shuttingDown:
            return
        
        typingDelay = (1000 // random.randint(*CHARACTERS_PER_SECOND))

        if duration is None:
            wordCount = len(text.split())
            characterCount = len(text)

            timeTyping = characterCount * typingDelay
            timeReading = (wordCount / READING_WORDS_PER_SECOND) * 1000

            duration = max(timeTyping + timeReading + READING_DELAY_MS, 3000)
    
        self.queue.append(
            SpeechItem(
                text=text,
                duration=duration,
                typingDelayMs=typingDelay,
                interactive=False,
            )
        )

        if not self.active:
            self._showNext()

    def askSpeech(
        self,
        text: str,
        interactive: bool = True,
        onConfirm: Optional[Callable[[str], None]] = None,
        onCancel: Optional[Callable[[], None]] = None,
        inputPlaceholder: str = "",
        inputPrefill: str = "",
        typingDelayMs: Optional[int] = None,
    ):
        """
        queue an interactive speech prompt with optional user input.
        
        :param text: The prompt text to display
        :type text: str
        :param interactive: Whether to show input field (default True)
        :type interactive: bool
        :param onConfirm: Callback invoked with user input on confirmation
        :type onConfirm: Optional[Callable[[str], None]]
        :param onCancel: Callback invoked if user cancels input
        :type onCancel: Optional[Callable[[], None]]
        :param inputPlaceholder: Placeholder text for input field
        :type inputPlaceholder: str
        :param inputPrefill: Pre-filled text in input field
        :type inputPrefill: str
        :param typingDelayMs: Delay between character display (random if None)
        :type typingDelayMs: Optional[int]
        """

        if self.shuttingDown:
            return

        if not interactive:
            # fall back to a normal speech bubble message
            return self.addSpeech(text)

        typingDelay = typingDelayMs or (1000 // random.randint(*CHARACTERS_PER_SECOND))

        self.queue.append(
            SpeechItem(
                text=text,
                duration=None,
                typingDelayMs=typingDelay,
                interactive=True,
                onConfirm=onConfirm,
                onCancel=onCancel,
                inputPlaceholder=inputPlaceholder,
                inputPrefill=inputPrefill,
            )
        )

        if not self.active:
            self._showNext()
    
    def _showNext(self):
        """
        display the next queued speech item or fade out if queue is empty.
        """

        if self.shuttingDown:
            return

        if self._awaitingInput:
            return

        if not self.queue:
            self.active = False
            self._nextTimer.stop()
            self.bubble.fadeOut()
            return
        
        if not self.active:
            self.bubble._reposition()

        self.active = True
        item = self.queue.popleft()

        if item.interactive:
            self._beginAsk(item)
            return

        self.bubble.startTyping(item.text, item.typingDelayMs)

        # schedule next message after duration
        self._nextTimer.stop()
        self._nextTimer.start(int(item.duration or 0))

    def _beginAsk(self, item: SpeechItem) -> None:
        """
        start an interactive input prompt for a speech item.
        
        :param item: The speech item containing prompt and callbacks
        :type item: SpeechItem
        """

        self._awaitingInput = True
        self._pendingAsk = item
        self._nextTimer.stop()

        # avoid duplicate connections
        try:
            self.bubble.inputField.returnPressed.disconnect()
        except Exception:
            pass

        self.bubble.inputField.returnPressed.connect(self._confirmAsk)

        self.bubble.startTyping(
            item.text,
            item.typingDelayMs,
            showInput=True,
            inputPlaceholder=item.inputPlaceholder,
            inputText=item.inputPrefill,
        )

    def _clearAskState(self) -> Optional[SpeechItem]:
        """
        clear the pending input state and return the pending speech item.
        
        :return: The pending speech item if one exists
        :rtype: SpeechItem | None
        """

        item = self._pendingAsk

        try:
            self.bubble.inputField.returnPressed.disconnect()
        except Exception:
            pass

        self._awaitingInput = False
        self._pendingAsk = None
        return item

    def _confirmAsk(self) -> None:
        """
        process user input confirmation and trigger the onConfirm callback.
        """

        if not self._awaitingInput:
            return

        self.bubble.stopTyping(showFullText=True)
        answer = ""

        try:
            answer = self.bubble.inputField.text()
        except Exception:
            pass

        item = self._clearAskState()

        try:
            self.bubble.setInputVisible(False)
        except Exception:
            pass

        if item and callable(item.onConfirm):
            try:
                item.onConfirm(answer)
            except Exception:
                pass

        self._showNext()

    def _cancelAsk(self) -> None:
        """
        cancel the current input prompt and trigger the onCancel callback.
        """

        if not self._awaitingInput:
            return

        item = self._clearAskState()

        try:
            self.bubble.setInputVisible(False)
        except Exception:
            pass

        if item and callable(item.onCancel):
            try:
                item.onCancel()
            except Exception:
                pass

        self._showNext()

    def eventFilter(self, obj, event):
        """
        handle escape key to cancel input prompt.
        
        :param obj: The object that received the event
        :param event: The event to process
        """

        try:
            if (
                (obj is self.bubble.inputField)
                and self._awaitingInput
                and (event.type() == QEvent.KeyPress)
                and (event.key() == Qt.Key_Escape)
            ):
                self._cancelAsk()
                return True
        except Exception:
            pass

        return super().eventFilter(obj, event)

    def shutdown(self):
        """
        shut down the speech bubble controller and clear all queued messages.
        """

        self.shuttingDown = True
        self._nextTimer.stop()
        self.queue.clear()

        try:
            self._clearAskState()
        except Exception:
            pass

        self.bubble.shutdown()
