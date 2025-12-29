from PySide6.QtCore import QPropertyAnimation, QEasingCurve
from PySide6.QtWidgets import QGraphicsOpacityEffect

class FadeableMixin:
    def initFadeable(
        self,
        *,
        durationMs: int,
        startOpacity: float = 1.0,
        easing: QEasingCurve = QEasingCurve.OutCubic,
    ) -> None:
        # effect
        self.opacityEffect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacityEffect)
        self.opacityEffect.setOpacity(max(0.0, min(1.0, float(startOpacity))))

        # animation
        self.fadeAnimation = QPropertyAnimation(self.opacityEffect, b"opacity", self)
        self.fadeAnimation.setEasingCurve(easing)
        self.fadeAnimation.setDuration(int(max(1, durationMs)))
        self.fadeAnimation.finished.connect(self._fadeable_onFadeFinished)

        # flags
        self.enableFadeAnimation = True
        self.fadeHideWhenZero = True

    # exposed methods
    def setOpacity(self, value: float) -> None:
        self.opacityEffect.setOpacity(max(0.0, min(1.0, float(value))))

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

            self._fadeable_emitFinished(float(self.opacityEffect.opacity()))
            return

        target = max(0.0, min(1.0, float(target)))
        self.fadeHideWhenZero = bool(hideWhenZero)

        if showIfHidden and target > 0.001 and self.isHidden():
            self.show()

        self.fadeAnimation.stop()
        self.fadeAnimation.setStartValue(float(self.opacityEffect.opacity()))
        self.fadeAnimation.setEndValue(float(target))
        self.fadeAnimation.start()

    def fadeIn(self) -> None:
        self.fadeTo(1.0, showIfHidden=True, hideWhenZero=False)

    def fadeOut(self) -> None:
        self.fadeTo(0.0, showIfHidden=False, hideWhenZero=True)

    def stopFade(self) -> None:
        if hasattr(self, "fadeAnimation"):
            self.fadeAnimation.stop()

    # internal methods
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
        endOpacity = float(self.opacityEffect.opacity())

        if getattr(self, "fadeHideWhenZero", True) and endOpacity <= 0.001:
            self.hide()

        self._fadeable_emitFinished(endOpacity)
