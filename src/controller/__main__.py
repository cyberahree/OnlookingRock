from .app import RockinWindow

import argparse

def main():
    parser = argparse.ArgumentParser(description="Rockin' Controller Application")

    parser.add_argument("--profile", "-p", default=None, help="Specify the configuration profile to use")
    parser.add_argument("--qtargs", "-qt", default="", help="Additional arguments for the Qt framework")

    arguments = parser.parse_args()

    # start application
    app = RockinWindow(
        configProfile=arguments.profile,
    )

    app.startWindowLoop()

if __name__ == "__main__":
    app = RockinWindow()
    app.startWindowLoop()
