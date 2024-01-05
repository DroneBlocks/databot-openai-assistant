import asyncio
import json
import logging
from logging import Logger
import threading
import time
from collections import deque
from dataclasses import dataclass
from pathlib import Path

from bleak import BleakClient, BleakScanner, BLEDevice
from bottle import Bottle, run

_LOGGER: Logger = logging.getLogger(__name__)

class DatabotDeviceNotFoundError(Exception):
    pass


class StopGatheringData(Exception):
    pass


class ProcessDatabotDataComplete(Exception):
    pass


databot_sensors = {
    'accl': {
        'sensor_name': 'accl',
        'friendly_name': 'Acceleration',
        'save': False,
        'display': False,
        'data_columns': ['acceleration_x', 'acceleration_y', 'acceleration_z', 'absolute_acceleration']
    },
    'Laccl': {
        'sensor_name': 'Laccl',
        'friendly_name': 'Linear Acceleration',
        'save': False,
        'display': False,
        'data_columns': ['linear_acceleration_x', 'linear_acceleration_y', 'linear_acceleration_z',
                         'absolute_linear_acceleration']
    },
    'gyro': {
        'sensor_name': 'gyro',
        'friendly_name': 'Gyroscope',
        'save': False,
        'display': False,
        'data_columns': ['gyro_x', 'gyro_y', 'gyro_z']
    },
    'magneto': {
        'sensor_name': 'magneto',
        'friendly_name': 'Magneto',
        'save': False,
        'display': False,
        'data_columns': ['mag_x', 'mag_y', 'mag_z']

    },
    # 'IMUTemp': {
    #     'sensor_name': 'IMUTemp',
    #     'friendly_name': 'IMU Temperature',
    #     'save': False,
    #     'display': False
    # },
    'Etemp1': {
        'sensor_name': 'Etemp1',
        'friendly_name': 'External Temperature 1',
        'save': False,
        'display': False,
        'data_columns': ['external_temp_1']
    },
    'Etemp2': {
        'sensor_name': 'Etemp2',
        'friendly_name': 'External Temperature 2',
        'save': False,
        'display': False,
        'data_columns': ['external_temp_2']
    },
    'pressure': {
        'sensor_name': 'pressure',
        'friendly_name': 'Atmospheric Pressure',
        'save': False,
        'display': False,
        'data_columns': ['pressure']
    },
    'alti': {
        'sensor_name': 'alti',
        'friendly_name': 'Altimeter',
        'save': False,
        'display': False,
        'data_columns': ['altitude']
    },
    'ambLight': {
        'sensor_name': 'ambLight',
        'friendly_name': 'Ambient Light',
        'save': False,
        'display': False,
        'data_columns': ['ambient_light_in_lux']
    },
    'rgbLight': {
        'sensor_name': 'rgbLight',
        'friendly_name': 'RGB Light',
        'save': False,
        'display': False,
        'data_columns': ['r_light', 'g_light', 'b_light']
    },
    'UV': {
        'sensor_name': 'UV',
        'friendly_name': 'UltraViolet Light',
        'save': False,
        'display': False,
        'data_columns': ['uv_index']
    },
    'co2': {
        'sensor_name': 'co2',
        'friendly_name': 'CO2',
        'save': False,
        'display': False,
        'data_columns': ['co2']
    },
    'voc': {
        'sensor_name': 'voc',
        'friendly_name': 'Volatile Organic Compound',
        'save': False,
        'display': False,
        'data_columns': ['voc']
    },
    'hum': {
        'sensor_name': 'hum',
        'friendly_name': 'Humidity',
        'save': False,
        'display': False,
        'data_columns': ['humidity']
    },
    'humTemp': {
        'sensor_name': 'humTemp',
        'friendly_name': 'Humidity Adjusted Temperature',
        'save': False,
        'display': False,
        'data_columns': ['humidity_temperature']
    },
    # 'Sdist': {
    #     'sensor_name': 'Sdist',
    #     'friendly_name': 'Short Distance',
    #     'save': False,
    #     'display': False,
    #     'data_columns': ['distance']
    # },
    'noise': {
        'sensor_name': 'noise',
        'friendly_name': 'Noise',
        'save': False,
        'display': False,
        'data_columns': ['noise_sound']
    },
    'Ldist': {
        'sensor_name': 'Ldist',
        'friendly_name': 'Long Distance',
        'save': False,
        'display': False,
        'data_columns': ['distance']

    },
    'gesture': {
        'sensor_name': 'gesture',
        'friendly_name': 'Gesture',
        'save': False,
        'display': False,
        'data_columns': ['gesture']
    },

}

response_mapping = {
    "a": "acceleration_x",
    "b": "b_light",
    "c": "co2",
    "d": "distance",
    "e": "altitude",
    "f": "acceleration_z",
    "g": "g_light",
    "h": "humidity",
    "i": "mag_x",
    "j": "mag_y",
    "k": "mag_z",
    "l": "ambient_light_in_lux",
    "m": "time",
    "n": "noise_sound",
    "o": "imu_temp",
    "p": "pressure",
    "q": "humidity_temperature",
    "r": "r_light",
    "s": "acceleration_y",
    "t": "external_temp_1",
    "u": "uv_index",
    "v": "voc",
    "w": "external_temp_2",
    "x": "gyro_x",
    "y": "gyro_y",
    "z": "gyro_z",
    "A": "absolute_acceleration",
    "B": "bat_voltage",
    "E": "esp_chip_id",
    "G": "gesture",
    "L": "absolute_linear_acceleration",
    "V": "version_number",
    "X": "linear_acceleration_x",
    "Y": "linear_acceleration_y",
    "Z": "linear_acceleration_z"

}


@dataclass(frozen=True)
class DatabotBLEConfig:
    """
    DatabotBLEConfig

    This class represents the configuration for a Databot Bluetooth Low Energy (BLE) device. It contains the UUIDs for the BLE service, read characteristic, and write characteristic.

    Attributes:
        service_uuid (str): The UUID of the BLE service.
        read_uuid (str): The UUID of the read characteristic.
        write_uuid (str): The UUID of the write characteristic.

    Methods:
        __getitem__(item: str) -> Any:
            Gets the value of the given attribute.

    Usage:
        config = DatabotBLEConfig()
        service_uuid = config['service_uuid']
    """
    service_uuid: str = "0000ffe0-0000-1000-8000-00805f9b34fb"
    read_uuid: str = "0000ffe1-0000-1000-8000-00805f9b34fb"
    write_uuid: str = "0000ffe2-0000-1000-8000-00805f9b34fb"

    def __getitem__(self, item):
        return getattr(self, item)


@dataclass(frozen=False)
class DatabotLEDConfig:
    state: bool
    R: int  # RED: 0-255
    Y: int  # Green: 0-255
    B: int  # Blue: 0-255

    def __getitem__(self, item):
        return getattr(self, item)


@dataclass(frozen=True)
class DefaultDatabotConfig:
    refresh: int = 500  # units = ms.  Number of milliseconds between polling for new data values
    decimal: int = 2  # number of decimal places for the returned sensor values
    timeFactor: int = 1000  # 1000 = the epoch time is reported as seconds.
    timeDec: int = 2  # number of decimal places reported by the databot epoch time
    accl: bool = False
    Laccl: bool = False
    gyro: bool = False
    magneto: bool = False
    IMUTemp: bool = False
    Etemp1: bool = False
    Etemp2: bool = False
    pressure: bool = False
    alti: bool = False
    ambLight: bool = False
    rgbLight: bool = False
    UV: bool = False
    co2: bool = False
    voc: bool = False
    hum: bool = False
    humTemp: bool = False
    Sdist: bool = False
    Ldist: bool = False
    noise: bool = False
    gesture: bool = False
    sysCheck: bool = False
    usbCheck: bool = False
    altCalib: bool = False
    humCalib: bool = False
    DtmpCal: bool = False
    led1: DatabotLEDConfig | None = None
    led2: DatabotLEDConfig | None = None
    led3: DatabotLEDConfig | None = None

    def __getitem__(self, item):
        return getattr(self, item)


@dataclass(frozen=False)
class DatabotConfig:
    refresh: int = DefaultDatabotConfig.refresh
    decimal: int = DefaultDatabotConfig.decimal
    timeFactor: int = DefaultDatabotConfig.timeFactor
    timeDec: int = DefaultDatabotConfig.timeDec
    accl: bool = DefaultDatabotConfig.accl
    Laccl: bool = DefaultDatabotConfig.Laccl
    gyro: bool = DefaultDatabotConfig.gyro
    magneto: bool = DefaultDatabotConfig.magneto
    IMUTemp: bool = DefaultDatabotConfig.IMUTemp
    Etemp1: bool = DefaultDatabotConfig.Etemp1
    Etemp2: bool = DefaultDatabotConfig.Etemp2
    pressure: bool = DefaultDatabotConfig.pressure
    alti: bool = DefaultDatabotConfig.alti
    ambLight: bool = DefaultDatabotConfig.ambLight
    rgbLight: bool = DefaultDatabotConfig.rgbLight
    UV: bool = DefaultDatabotConfig.UV
    co2: bool = DefaultDatabotConfig.co2
    voc: bool = DefaultDatabotConfig.voc
    hum: bool = DefaultDatabotConfig.hum
    humTemp: bool = DefaultDatabotConfig.humTemp
    Sdist: bool = DefaultDatabotConfig.Sdist
    Ldist: bool = DefaultDatabotConfig.Ldist
    noise: bool = DefaultDatabotConfig.noise
    gesture: bool = DefaultDatabotConfig.gesture
    sysCheck: bool = DefaultDatabotConfig.sysCheck
    usbCheck: bool = DefaultDatabotConfig.usbCheck
    altCalib: bool = DefaultDatabotConfig.altCalib
    humCalib: bool = DefaultDatabotConfig.humCalib
    DtmpCal: bool = DefaultDatabotConfig.DtmpCal
    led1: DatabotLEDConfig = DefaultDatabotConfig.led1
    led2: DatabotLEDConfig = DefaultDatabotConfig.led2
    led3: DatabotLEDConfig = DefaultDatabotConfig.led3
    # address: str = "774B790E-35DE-4950-842D-81446C06240B"  # "94:3C:C6:99:AA:82"
    address: str = None

    def __getitem__(self, item):
        return getattr(self, item)


class PyDatabot:
    """
    PyDatabot

    This class represents a PyDatabot instance that can connect to a BLE device and collect sensor data.

    Attributes:
        start_collecting_data (bool): Flag indicating whether to start collecting data or not.
        device (BLEDevice | None): BLE device instance representing the connected device.
        databot_config (DatabotConfig): Configuration object for the databot.
        ble_config (DatabotBLEConfig): Configuration object for BLE communication.
        queue (asyncio.Queue): Queue for storing sensor data.
        logger (logging.Logger): Logger instance for logging.

    Methods:
        __init__(self, databot_config: DatabotConfig, log_level: int = logging.INFO)
            Initializes a new PyDatabot instance.

        _get_databot_config_json(self) -> bytearray
            Returns the JSON representation of the DatabotConfig object.

        start_collecting_data(self)
            Sets the flag to start collecting data.

        stop_collecting_data(self)
            Sets the flag to stop collecting data.

        async connect(self)
            Connects to the BLE device and starts data collection.

        async process_sensor_data(self, characteristic: str, raw_data: bytearray)
            Processes the sensor data received from the BLE device.

        async run_queue_consumer(self)
            Runs a consumer task to process the sensor data from the queue.

        process_databot_data(self, epoch, data)
            Custom function to process the sensor data.

        async async_run(self)
            Runs the PyDatabot asynchronously.

        run(self)
            Runs the PyDatabot synchronously.
    """

    def __init__(self, databot_config: DatabotConfig, log_level: int = logging.INFO):
        self.collect_data: bool = False
        self.device: BLEDevice | None = None
        self.databot_config: DatabotConfig = databot_config
        self.ble_config: DatabotBLEConfig = DatabotBLEConfig()
        self.queue: asyncio.Queue = asyncio.Queue()
        self.logger: Logger = _LOGGER
        logging.basicConfig(level=log_level)
        if databot_config.address is None or databot_config.address == "":
            raise ValueError("DatabotConfig must have the address property set.")

    @staticmethod
    def get_databot_address(force_address_read: bool = False):
        """
        :param force_address_read: A boolean value indicating whether to force reading the databot address again, even if it already exists.
        :return: The databot address as a string.

        This method is used to retrieve the databot address either from a previously saved file or by scanning for available devices. If the 'force_address_read' parameter is set to True or
        * if the databot address file does not exist, the method scans for available devices and saves the databot address to the file. Otherwise, it reads the address from the file and returns
        * it.
        """
        async def async_save_databot_address():
            devices = await BleakScanner.discover()
            for d in devices:
                if d.name == "DB_databot":
                    _LOGGER.debug(f"Databot Address: {d.address}")
                    with open("./databot_address.txt", "w") as f:
                        f.write(d.address)
                    break
            else:
                _LOGGER.warning("The DB_databot device could not be found.  Be sure it is powered on")

        if force_address_read or not Path("./databot_address.txt").exists():
            asyncio.run(async_save_databot_address())

        with open("./databot_address.txt", "r") as f:
            databot_address = f.read()
        return databot_address

    def _get_databot_config_json(self):
        # my experience has been that creating
        # json string from the entire DatabotConfig
        # causes the Databot to throw an error that
        # the string is too long, so we are breaking
        # it up
        if not self.databot_config:
            raise ValueError("DatabotConfig is not set")
        default_config = DefaultDatabotConfig()

        json_config = {
            "refresh": self.databot_config.refresh,
            "decimal": self.databot_config.decimal,
            "timeFactor": self.databot_config.timeFactor,
            "timeDec": self.databot_config.timeDec
        }
        db_properties = ["accl", "Laccl", "gyro", "magneto", "IMUTemp", "pressure", "alti", "ambLight",
                         "rgbLight", "UV", "co2", "voc", "hum", "gesture",
                         "Sdist", "Ldist", "noise", "humTemp", "Etemp1", "Etemp2",
                         "sysCheck", "usbCheck", "altCalib", "humCalib", "DtmpCal",
                         "led1", "led2", "led3"]

        for db_property in db_properties:
            if default_config[db_property] != self.databot_config[db_property]:
                if db_property in ['led1', 'led2', 'led3']:
                    json_config[db_property] = {
                        "state": self.databot_config[db_property].state,
                        "R": self.databot_config[db_property].R,
                        "Y": self.databot_config[db_property].Y,
                        "B": self.databot_config[db_property].B
                    }
                else:
                    json_config[db_property] = self.databot_config[db_property]
        # print(json_config)
        return bytearray(json.dumps(json_config), 'utf-8')

    def start_collecting_data(self):
        self.collect_data = True

    def stop_collecting_data(self):
        self.collect_data = False

    async def connect(self):
        """

        Connect to the device and start gathering sensor data.

        :return: None

        """
        self.logger.info("connecting")
        self.device = await BleakScanner(None, [self.ble_config.service_uuid]).find_device_by_address(
            self.databot_config.address)
        config = self._get_databot_config_json()

        async with BleakClient(self.device) as client:
            try:
                service = client.services.get_service(self.ble_config.service_uuid)

                write_char = service.get_characteristic(self.ble_config.write_uuid)
                await client.write_gatt_char(write_char, config, True)
                await asyncio.sleep(2)

                await client.write_gatt_char(write_char, bytearray('1.0', 'utf-8'), True)

                read_char = service.get_characteristic(self.ble_config.read_uuid)
                await client.start_notify(read_char, self.process_sensor_data)
                while True:
                    await asyncio.sleep(1)
                    if not self.collect_data:
                        raise StopGatheringData()
            finally:
                self.logger.info("EXITING.. stop notify")
                await client.stop_notify(read_char)

    async def process_sensor_data(self, characteristic: str, raw_data: bytearray):
        data = raw_data.decode()
        data_fields = data.split(";")
        data_dict = {}
        for data_field in data_fields:
            key = data_field[0:1]
            value = data_field[1:]
            try:
                data_dict[response_mapping[key]] = value
            except:
                pass

        await self.queue.put((time.time(), data_dict))

    async def run_queue_consumer(self):
        self.logger.info("Starting queue consumer")

        try:
            while True:
                # Use await asyncio.wait_for(queue.get(), timeout=1.0) if you want a timeout for getting data.
                epoch, data = await self.queue.get()
                if data is None:
                    self.logger.info(
                        "Got message from client about disconnection. Exiting consumer loop..."
                    )
                    break

                self.process_databot_data(epoch, data)
        finally:
            self.stop_collecting_data()

    def process_databot_data(self, epoch, data):
        """
        Process the data received from the callback in the DataBot.

        Classes that inherit from PyDatabot should override this method to add custom processing of the databot data

        :param epoch: The epoch timestamp when the data was received.
        :param data: The data received from the callback.
        :return: None

        """
        self.logger.info("Received callback data via async queue at %s: %r", epoch, data)

    async def async_run(self):
        client_task = self.connect()
        consumer_task = self.run_queue_consumer()

        try:
            await asyncio.gather(client_task, consumer_task)
        except DatabotDeviceNotFoundError:
            self.logger.error("Databot device not found")
        except StopGatheringData:
            self.logger.info("Stop gathering data")
        except ProcessDatabotDataComplete:
            self.logger.info("Completed Processing Data")
        except Exception as exc:
            self.logger.exception(exc)

        self.logger.info("Main method done.")

    def run(self):
        self.start_collecting_data()
        asyncio.run(self.async_run())


class PyDatabotSaveToFileDataCollector(PyDatabot):
    """
    SaveToFileDatabotCollector

    A class that collects data from a PyDatabot and saves it to a file.

    Attributes:
        file_name (str): The name of the file to save the data to.
        file_path (Path): The path to the file.
        record_number (int): The number of records written to the file.
        extra_data (dict): Additional data to be added as new columns to the data being collected.
        number_of_records_to_collect (int | None): The maximum number of records to collect. If None, collect indefinitely.

    Methods:
        __init__(self, databot_config: DatabotConfig, file_name: str, extra_data: dict,
                 number_of_records_to_collect: int | None = None, log_level: int = logging.INFO)
            Initializes a new instance of SaveToFileDatabotCollector.

        process_databot_data(self, epoch, data)
            Processes the data received from the PyDatabot and saves it to the file.
    """

    def __init__(self, databot_config: DatabotConfig, file_name: str, extra_data: dict | None = None,
                 number_of_records_to_collect: int | None = None, log_level: int = logging.INFO):
        super().__init__(databot_config, log_level)
        self.file_name = f"{file_name}"
        self.file_path = Path(self.file_name)
        if self.file_path.exists():
            self.file_path.unlink(missing_ok=True)
        self.record_number = 0
        self.extra_data = extra_data
        self.number_of_records_to_collect = number_of_records_to_collect

    def process_databot_data(self, epoch, data):
        data['timestamp'] = epoch

        with self.file_path.open("a", encoding="utf-8") as f:
            # add the extra data as new columns
            if self.extra_data is not None:
                data.update(**self.extra_data)

            f.write(json.dumps(data))
            f.write("\n")
            self.logger.info(f"wrote record[{self.record_number}]")
            self.record_number = self.record_number + 1
            if self.number_of_records_to_collect is not None:
                if self.record_number >= self.number_of_records_to_collect:
                    raise ProcessDatabotDataComplete("Done collecting data")


class PyDatabotSaveToQueueDataCollector(PyDatabot):
    """
    SaveToQueueDatabotCollector

    A class that collects data from a PyDatabot and saves it to an internal Queue.

    Attributes:
        extra_data (dict): Additional data to be added as new columns to the data being collected.
        number_of_records_to_collect (int | None): The maximum number of records to collect. If None, collect indefinitely.
        queue_size (int): The depth of the queue. By default the depth is one, meaning it only holds the very latest value.

    Methods:
        __init__(self, databot_config: DatabotConfig, file_name: str, extra_data: dict,
                 number_of_records_to_collect: int | None = None, log_level: int = logging.INFO)
            Initializes a new instance of SaveToFileDatabotCollector.

        process_databot_data(self, epoch, data)
            Processes the data received from the PyDatabot and saves it to the file.
    """

    class FixedLengthQueue:
        """
        Class representing a fixed length queue.

        :param max_size: The maximum size of the queue.
        :type max_size: int

        :ivar queue: The underlying deque object used to store the items.
        :vartype queue: collections.deque

        """
        def __init__(self, max_size):
            self.queue = deque(maxlen=max_size)

        def add(self, item):
            self.queue.append(item)

        def display(self):
            return list(self.queue)

        def get_latest(self):
            if self.queue:  # check if queue is not empty
                return self.queue[-1]  # get the last item
            else:
                return None  # return None if the queue is empty


    def __init__(self, databot_config: DatabotConfig, extra_data: dict | None = None,
                 queue_size: int = 1,
                 number_of_records_to_collect: int | None = None,
                 log_level: int = logging.INFO):
        super().__init__(databot_config, log_level)

        self.record_number = 0
        self.queue_size = queue_size
        self.q = PyDatabotSaveToQueueDataCollector.FixedLengthQueue(max_size=queue_size)
        self.extra_data = extra_data
        self.number_of_records_to_collect = number_of_records_to_collect

    def process_databot_data(self, epoch, data):
        data['timestamp'] = epoch

        if self.extra_data is not None:
            data.update(**self.extra_data)

        item = json.dumps(data)
        self.q.add(item)
        self.logger.info(f"Time: {data['time']} - Queued record[{self.record_number}]")
        self.logger.debug(f"Record Details: {item}")
        self.record_number = self.record_number + 1
        if self.number_of_records_to_collect is not None:
            if self.record_number >= self.number_of_records_to_collect:
                raise ProcessDatabotDataComplete("Done collecting data")

    def get_item(self):
        """
        Get the oldest item from the queue
        :return: JSON data record from the databot
        """
        try:
            item = self.q.get_latest()
            return item
        except:
            return None


# private reference to the queue based databot collector
# used by the web server to retrieve databot data
_web_databot: PyDatabotSaveToQueueDataCollector|None = None
_bottle_app = None

def _databot_index():
    if _web_databot is None:
        return {
            "message": "reference to PyDatabotSaveToQueueDataCollector is None"
        }

    item = _web_databot.get_item()
    return item


def _web_server_worker(host: str, port: int):
    run(_bottle_app, host=host, port=port)


def start_databot_webserver(queue_data_collector: PyDatabotSaveToQueueDataCollector,
                            host: str = "localhost", port: int = 8321) -> threading.Thread:
    """
    Start the Databot web server.

    :param queue_data_collector: The PyDatabotSaveToQueueDataCollector object that will handle saving data to the queue.
    :param host: The host address on which the web server will listen. Default is "localhost".
    :param port: The port number on which the web server will listen. Default is 8321.
    :return: A threading.Thread object representing the web server thread.
    """
    global _web_databot, _bottle_app
    _bottle_app = Bottle()
    _web_databot = queue_data_collector
    _bottle_app.route(path="/", method="GET", callback=_databot_index)

    t = threading.Thread(target=_web_server_worker, args=(host, port,), daemon=True)
    t.start()

    return t


def main():
    c = DatabotConfig()
    # c.accl = True
    # c.Laccl = True
    # c.gyro = True
    # c.magneto = True
    # c.IMUTemp = True # I get no data returned
    # c.humTemp = True
    # c.gesture = True
    # c.Sdist = True  # what is Sdist
    # c.Ldist = True # what is Ldist
    # c.sysCheck = True
    # c.ambLight = True
    # c.led1 = DatabotLEDConfig(True, 255, 0, 0)
    c.led3 = DatabotLEDConfig(True, 0, 0, 255)
    # c.led2 = DatabotLEDConfig(True, 0, 255, 0)
    # c.rgbLight = True
    # c.pressure = True
    # c.hum = True
    # c.humTemp = True
    # c.alti = True
    # c.UV = True
    c.Ldist = True
    db = PyDatabot(c)
    db.run()


if __name__ == '__main__':
    main()
