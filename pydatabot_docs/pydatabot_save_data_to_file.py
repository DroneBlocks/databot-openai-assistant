import sys
from pathlib import Path

root_dir = str(Path(__file__).resolve().parent.parent)
sys.path.append(root_dir)

from databot.PyDatabot import PyDatabot, DatabotConfig, PyDatabotSaveToFileDataCollector


def main():
    c = DatabotConfig()
    c.accl = True
    c.Laccl = True
    c.gyro = True
    c.magneto = False
    c.address = PyDatabot.get_databot_address()
    db = PyDatabotSaveToFileDataCollector(c, file_name="data/test_data.txt", number_of_records_to_collect=10)
    db.run()


if __name__ == '__main__':
    main()
