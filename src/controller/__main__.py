import argparse
import logging
import os

def setLogging(debug: bool) -> None:
    """
    Configures the logging settings for Qt based on the debug flag.

    :param debug: Whether to enable debug logging
    :type debug: bool
    """
    key = "true" if debug else "false"
    
    os.environ["QT_LOGGING_RULES"] = """
    qt.multimedia.ffmpeg.*={0};
    qt.multimedia.*={0};
    """.format(key.strip())

    logging.basicConfig(
        level = (logging.DEBUG if debug else logging.INFO),
        format = "[%(asctime)s] [%(levelname)s] %(message)s",
    )

def main():
    """
    Main entry point for the Rockin' Controller application.
    """

    parser = argparse.ArgumentParser(description="Rockin' Controller Application")

    parser.add_argument(
        "--qtargs", "-qt",
        default="",
        help="Additional arguments for the Qt framework"
    )

    parser.add_argument(
        "--debug", "-d",
        action="store_true",
        help="Enable debug logging output"
    )

    arguments = parser.parse_args()

    # logging
    setLogging(arguments.debug)

    # start application
    from .app import RockinWindow

    app = RockinWindow()
    app.startWindowLoop()

if __name__ == "__main__":
    main()
