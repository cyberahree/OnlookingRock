from ..base.anchor import SpriteAnchorMixin
from ..base import InterfaceComponent

from ..base.lookskit import (
    SubheadingLabel,
    applyRockStyle,
    SurfaceFrame,
    RockButton,
    CloseButton,
    Divider
)

from ..base.styling import BORDER_MARGIN, PADDING

from PySide6.QtCore import QSize, Qt, QUrl, Signal, QTimer, QEvent
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtGui import QDesktopServices, QPixmap

from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
    QSizePolicy
)

from typing import Optional

import re

MAX_SIZE = QSize(1280, 720)
MIN_SIZE = QSize(360, 240)

def getYouTubeId(url: str) -> Optional[str]:
    """
    extract a video id from a url-ish string
    
    :param url: Description
    :type url: str
    :return: Description
    :rtype: str | None
    """

    value = (url or "").strip()

    if not value:
        return None

    # its already a valid, full video Id
    if re.fullmatch(r"[A-Za-z0-9_-]{11}", value):
        return value

    for pattern in [
        r"(?:v=)([A-Za-z0-9_-]{11})",
        r"(?:youtu\.be/)([A-Za-z0-9_-]{11})",
        r"(?:/embed/)([A-Za-z0-9_-]{11})",
        r"(?:/shorts/)([A-Za-z0-9_-]{11})"
    ]:
        match = re.search(pattern, value)

        if not match:
            continue

        return match.group(1)

    return None

class MediaViewWindow(InterfaceComponent, SpriteAnchorMixin):
    """
    A window for displaying images or web pages next to the sprite
    """

    userClosed = Signal()

    EMPTY_PAGE_INDEX = 0
    IMAGE_PAGE_INDEX = 1
    WEB_PAGE_INDEX = 2

    def __init__(self, sprite: QWidget, clock: QTimer):
        """
        initialise the media view window

        :param sprite: the sprite widget to anchor next to
        :param clock: the clock to use for timing animations
        :type sprite: QWidget
        :type clock: QTimer
        """
        super().__init__(sprite, clock)

        self.setWindowFlags(
            Qt.Tool |
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint
        )
    
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)

        self.setMinimumSize(MIN_SIZE)
        self.setMaximumSize(MAX_SIZE)

        self.lastPixmap: Optional[QPixmap] = None
        self.lastURL: Optional[str] = None

    def build(self) -> None:
        """
        build the media view window UI
        """
        applyRockStyle(self)

        root = SurfaceFrame(padding=PADDING)
        rootLayout = root.contentLayout
        rootLayout.setSpacing(PADDING)

        # header
        headerWidget = QWidget()
        headerLayout = QHBoxLayout(headerWidget)
        headerLayout.setContentsMargins(0, 0, 0, 0)
        headerLayout.setSpacing(PADDING // 2)

        self.titleLabel = SubheadingLabel("Panel")
        headerLayout.addWidget(self.titleLabel, 1)

        self.openBrowserButton = RockButton("Open Externally", onClick=self._openInBrowser)
        self.openBrowserButton.setVisible(False)
        headerLayout.addWidget(self.openBrowserButton, 0, Qt.AlignRight)

        self.closeButton = CloseButton(onClick=self._onClosed)
        headerLayout.addWidget(self.closeButton, 0, Qt.AlignRight)

        rootLayout.addWidget(headerWidget)
        rootLayout.addWidget(Divider())

        # content stack
        self.stack = QStackedWidget()

        # 0) empty page
        self.emptyLabel = QLabel("Nothing to show yet.")
        self.emptyLabel.setAlignment(Qt.AlignCenter)
        self.stack.addWidget(self.emptyLabel)

        # 1) image page (scrollable)
        self.imageLabel = QLabel()
        self.imageLabel.setAlignment(Qt.AlignCenter)
        self.imageLabel.setMinimumSize(1, 1)

        self.imageLabel.setSizePolicy(
            QSizePolicy.Ignored,
            QSizePolicy.Ignored
        )

        self.imageScroll = QScrollArea()
        self.imageScroll.setWidgetResizable(True)
        self.imageScroll.setFrameShape(QScrollArea.NoFrame)
        self.imageScroll.setWidget(self.imageLabel)

        self.imageScroll.viewport().installEventFilter(self)
        self.stack.addWidget(self.imageScroll)

        # 2) web page
        self.webView = QWebEngineView()
        self.stack.addWidget(self.webView)

        rootLayout.addWidget(self.stack, 1)

        # outer layout
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(root)

        self.stack.setCurrentIndex(self.EMPTY_PAGE_INDEX)

    def _reposition(self):
        """
        reposition the media view window next to the sprite
        """
        target = self.anchorNextToSprite(
            yAlign="center",
            preferredSide="right",
            margin=BORDER_MARGIN,
        )

        self.animateTo(target)

    def eventFilter(self, watched, event):
        if (watched is self.imageScroll.viewport()) and event.type() == QEvent.Resize:
            self._applyScaledPixmap()

        return super().eventFilter(watched, event)

    def resizeEvent(self, event):
        """
        handle when the media view window is resized

        :param event: the resize event
        :type event: QResizeEvent
        """
        super().resizeEvent(event)
        self._applyScaledPixmap()

    def _onClosed(self):
        """
        handle when the user closes the media view window
        """
        self.userClosed.emit()
        self.close()

    def _openInBrowser(self):
        """
        open the current URL in the user's default browser
        """
        if self.lastURL:
            QDesktopServices.openUrl(QUrl(self.lastURL))

    def clear(self, title: str = "Panel", openPanel: bool = False) -> None:
        """
        clear the media view window content

        :param title: the title to set
        :type title: str
        :param openPanel: whether to open the panel after clearing
        :type openPanel: bool
        """
        self.ensureBuilt()

        self.lastPixmap = None
        self.lastURL = None

        self.imageLabel.clear()
        self.titleLabel.setText(title)
        self.stack.setCurrentIndex(self.EMPTY_PAGE_INDEX)
        self.openBrowserButton.setVisible(False)

        if openPanel:
            self.open()

    def showImage(
        self,
        pixmap: QPixmap,
        title: str = "Image",
        openPanel: bool = False
    ) -> None:
        """
        show an image in the media view window

        :param pixmap: the pixmap to show
        :type pixmap: QPixmap
        :param title: the title to set
        :type title: str
        :param openPanel: whether to open the panel after showing the image
        :type openPanel: bool
        """
        self.ensureBuilt()

        self.titleLabel.setText(title)
        self.stack.setCurrentIndex(self.IMAGE_PAGE_INDEX)
        self.openBrowserButton.setVisible(False)

        if openPanel:
            self.open()

        self.lastPixmap = pixmap
        QTimer.singleShot(0, self._syncImageToViewport)

    def showImagefromBytes(
        self,
        imageBytes: bytes,
        title: str = "Image",
        openPanel: bool = False
    ) -> None:
        """
        load and show an image from bytes in the media view window
        
        :param imageBytes: the image data in bytes
        :type imageBytes: bytes
        :param title: the title to set
        :type title: str
        :param openPanel: whether to open the panel after showing the image
        :type openPanel: bool
        """
        self.ensureBuilt()

        pixmap = QPixmap()
        pixmap.loadFromData(imageBytes)

        self.showImage(
            pixmap,
            title=title,
            openPanel=openPanel
        )

    def showURL(
        self,
        url: str,
        title: str = "Web Page",
        openPanel: bool = False
    ) -> None:
        """
        show a web page in the media view window

        :param url: the URL to show
        :type url: str
        :param title: the title to set
        :type title: str
        :param openPanel: whether to open the panel after showing the web page
        :type openPanel: bool
        """
        self.ensureBuilt()

        self.lastURL = url
        self.titleLabel.setText(title)
        self.stack.setCurrentIndex(self.WEB_PAGE_INDEX)
        self.openBrowserButton.setVisible(True)

        self.webView.load(
            QUrl(url)
        )

        if openPanel:
            self.open()

    def showYouTube(
        self,
        urlOrId: str,
        title: str = "Video",
        openPanel: bool = False
    ) -> None:
        """
        show a YouTube video in the media view window

        :: warning ::
            THIS FUNCTION IS BROKEN - YouTube embedding is currently disabled due to WebCodecs issues.
            this function will raise a NotImplementedError when called

        :param urlOrId: the video URL or ID
        :type urlOrId: str
        :param title: the title to set
        :type title: str
        :param openPanel: whether to open the panel after showing the video
        :type openPanel: bool
        """
        raise NotImplementedError("YouTube embedding is currently disabled due to WebCodecs issues.")

        self.ensureBuilt()

        videoId = getYouTubeId(urlOrId)
        if not videoId:
            return

        # open externally url
        watchUrl = f"https://www.youtube.com/watch?v={videoId}"

        # embedded url
        embedUrl = f"https://www.youtube.com/embed/{videoId}?rel=0"

        self.lastURL = watchUrl
        self.titleLabel.setText(title)

        self.stack.setCurrentIndex(self.WEB_PAGE_INDEX)
        self.openBrowserButton.setVisible(True)

        # iframe wrapper
        iframeSource = f'<iframe src="{embedUrl}" allow="encrypted-media;"></iframe>'

        htmlContent = self._buildiFrameHTML(iframeSource)
        self.webView.setHtml(htmlContent)

        if openPanel:
            self.open()

    def _buildiFrameHTML(self, iFrame: str) -> str:
        return f"""
            <!doctype html>
                <html>
                    <head>
                        <meta charset="utf-8" />
                        <meta name="viewport" content="width=device-width, initial-scale=1" />
                        <style>
                            html, body {{
                            margin: 0;
                            padding: 0;
                            background: #000;
                            width: 100%;
                            height: 100%;
                            overflow: hidden;
                            }}
                            .wrap {{
                            position: absolute;
                            inset: 0;
                            }}
                            iframe {{
                            position: absolute;
                            inset: 0;
                            width: 100%;
                            height: 100%;
                            border: 0;
                            }}
                        </style>
                    </head>
                <body>
                    <div class="wrap">{iFrame}</div>
                </body>
            </html>
        """

    def _syncImageToViewport(self) -> None:
        self._resizeWindowToFitPixmap()
        self._applyScaledPixmap()

    def _resizeWindowToFitPixmap(self) -> None:
        if self.stack.currentIndex() != self.IMAGE_PAGE_INDEX:
            return

        if not self.lastPixmap or self.lastPixmap.isNull():
            return

        viewport = self.imageScroll.viewport().size()
        if viewport.width() <= 5 or viewport.height() <= 5:
            return

        chromeWidth = self.width() - viewport.width()
        chromeHeight = self.height() - viewport.height()

        maxViewWidth = max(1, MAX_SIZE.width() - chromeWidth)
        maxViewHeight = max(1, MAX_SIZE.height() - chromeHeight)
        minViewWidth = max(1, MIN_SIZE.width() - chromeWidth)
        minViewHeight = max(1, MIN_SIZE.height() - chromeHeight)

        imageWidth = self.lastPixmap.width()
        imageHeight = self.lastPixmap.height()

        if imageWidth <= 0 or imageHeight <= 0:
            return

        scale = min(maxViewWidth / imageWidth, maxViewHeight / imageHeight)

        minScale = max(minViewWidth / imageWidth, minViewHeight / imageHeight)
        scale = max(scale, minScale)
        scale = min(scale, min(maxViewWidth / imageWidth, maxViewHeight / imageHeight))

        targetViewWidth = int(imageWidth * scale)
        targetViewHeight = int(imageHeight * scale)

        targetWidth = targetViewWidth + chromeWidth
        targetHeight = targetViewHeight + chromeHeight

        targetWidth = max(MIN_SIZE.width(), min(MAX_SIZE.width(), targetWidth))
        targetHeight = max(MIN_SIZE.height(), min(MAX_SIZE.height(), targetHeight))

        if targetWidth != self.width() or targetHeight != self.height():
            self.resize(targetWidth, targetHeight)
            self._reposition()

    def _applyScaledPixmap(self) -> None:
        """
        apply a scaled version of the current-set pixmap to the image label
        """

        if self.stack.currentIndex() != self.IMAGE_PAGE_INDEX:
            return

        if not self.lastPixmap or self.lastPixmap.isNull():
            return

        try:
            viewport = self.imageScroll.viewport().size()
        except Exception:
            viewport = self.size()

        if viewport.width() <= 5 or viewport.height() <= 5:
            return

        scaled = self.lastPixmap.scaled(
            viewport,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )

        self.imageLabel.setPixmap(scaled)
