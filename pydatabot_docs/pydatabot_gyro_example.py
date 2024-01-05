from pathlib import Path
import sys

root_dir = str(Path(__file__).resolve().parent.parent)
sys.path.append(root_dir)

from databot.PyDatabot import PyDatabot, DatabotConfig


def main():
    """
    An example of how to collect Gyroscope values from the databot using the PyDatabot API.

    :return: None
    """
    c = DatabotConfig()
    c.gyro = True
    c.address = PyDatabot.get_databot_address()
    db = PyDatabot(c)
    db.run()


if __name__ == '__main__':
    main()
