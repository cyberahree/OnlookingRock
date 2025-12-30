from PySide6.QtCore import QPropertyAnimation, QEasingCurve
from PySide6.QtWidgets import QGraphicsOpacityEffect

def clamp(value: float) -> float:
    return max(0.0, min(1.0, float(value)))

class FadeableMixin:
    def initFadeable(
        self,
        *,
        durationMs: int,
        startOpacity: float = 1.0,
        easing: QEasingCurve = QEasingCurve.OutCubic,
        useWindowOpacity: bool = None,
    ) -> None:        
        startOpacity = clamp(startOpacity)

        if useWindowOpacity is None:
            try:
                useWindowOpacity = bool(self.isWindow())
            except Exception:
                useWindowOpacity = False

        self._fadeable_useWindowOpacity = bool(useWindowOpacity)

        if self._fadeable_useWindowOpacity:
            self.opacityEffect = None

            try:
                self.setWindowOpacity(startOpacity)
            except Exception:
                self._fadeable_useWindowOpacity = False

        if not self._fadeable_useWindowOpacity:
            self.opacityEffect = QGraphicsOpacityEffect(self)
            self.setGraphicsEffect(self.opacityEffect)
            self.opacityEffect.setOpacity(startOpacity)

        if self._fadeable_useWindowOpacity:
            self.fadeAnimation = QPropertyAnimation(self, b"windowOpacity", self)
        else:
            self.fadeAnimation = QPropertyAnimation(self.opacityEffect, b"opacity", self)

        self.fadeAnimation.setEasingCurve(easing)
        self.fadeAnimation.setDuration(int(max(1, durationMs)))
        self.fadeAnimation.finished.connect(self._fadeable_onFadeFinished)

        self.enableFadeAnimation = True
        self.fadeHideWhenZero = True

    def _fadeable_emitFinished(self, endOpacity: float) -> None:
        hook = getattr(self, "onFadeFinished", None)

        if callable(hook):
            try:
                hook(float(endOpacity))
            except Exception:
                pass

        sig = getattr(self, "fadeFinished", None)

        if sig is not None and hasattr(sig, "emit"):
            try:
                sig.emit(float(endOpacity))
            except Exception:
                pass

    def _fadeable_onFadeFinished(self) -> None:
        endOpacity = self._fadeable_currentOpacity()

        if getattr(self, "fadeHideWhenZero", True) and endOpacity <= 0.001:
            self.hide()

        self._fadeable_emitFinished(endOpacity)

    def _fadeable_currentOpacity(self) -> float:
        if getattr(self, "_fadeable_useWindowOpacity", False):
            try:
                return float(self.windowOpacity())
            except Exception:
                return 1.0

        return float(self.opacityEffect.opacity())

    def setOpacity(self, value: float) -> None:
        value = clamp(value)

        if getattr(self, "_fadeable_useWindowOpacity", False):
            self.setWindowOpacity(value)
        else:
            self.opacityEffect.setOpacity(value)

    def fadeTo(
        self,
        target: float,
        *,
        showIfHidden: bool = True,
        hideWhenZero: bool = True,
    ) -> None:
        if not getattr(self, "enableFadeAnimation", True):
            self.setOpacity(target)

            if target <= 0.001 and hideWhenZero:
                self.hide()
            elif showIfHidden and self.isHidden():
                self.show()

            self._fadeable_emitFinished(self._fadeable_currentOpacity())
            return

        target = clamp(target)
        self.fadeHideWhenZero = bool(hideWhenZero)

        if showIfHidden and target > 0.001 and self.isHidden():
            self.show()

        self.fadeAnimation.stop()
        self.fadeAnimation.setStartValue(self._fadeable_currentOpacity())
        self.fadeAnimation.setEndValue(float(target))
        self.fadeAnimation.start()

    def fadeIn(self) -> None:
        self.fadeTo(1.0, showIfHidden=True, hideWhenZero=False)

    def fadeOut(self) -> None:
        self.fadeTo(0.0, showIfHidden=False, hideWhenZero=True)

    def stopFade(self) -> None:
        if not hasattr(self, "fadeAnimation"):
            return
        
        self.fadeAnimation.stop()
