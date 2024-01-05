# databot-py

The databot-py python package contains a bluetooth Python interface for interacting with the databot sensor device.

The classes in this package provide a Pythonic interface for interfacing with the databot sensor device.  These classes allow the user to select different sensors of interest and retrieve the sensor values on a user selected periodic polling frequency.  The sensor values can be returned to the host Python script by either a file, a queue interface, a web service interface, etc.

The `PyDatabot` class provides the foundation for building custom classes to process the data returned from the databot, while the `PyDatabot` class handles all of the setup and data retrieval.

## Github Repository

The github repository for the databot-py Python package can be found at the following url:

* https://github.com/dbaldwin/databot-py

## Install

It is recommended that you use a package manager like `pip-tools` or `poetry` and do not rely on a existing requirements.txt

The reason is that operating system dependent libraries need to be installed to support bluetooth.

Basic installation, just pip install the `databot-py` package from PyPI.

e.g.
`pip install databot-py`

If using pip-tools in your project then

* pip install pip-tools
* create a file called `requirements.in`
* add:  `databot-py`
* pip-compile
* pip-sync

This will install all of the OS specific versions of libraries.

## Classes
![classes](./media/classes.png)

### PyDatabot

This class is the base class implementation for interacting with the databot over bluetooth.

This class can be used directly and will print the data read from the databot.

However, this class is really meant to be inherited from and the derived class should override the method `process_databot_data`.

The `process_databot_data` method will be called for each data record from the databot and the derived class can then process the data in a specific way.

### PyDatabotSaveToFileDataCollector

This class extends the `PyDatabot` class and overrides the `process_databot_data` method to save values to a file.

This class is used primarily to easily read values from the databot and save them to a file for future processing.

### PyDatabotSaveToQueueDataCollector

This class extends the `PyDatabot` class and overrides the `process_databot_data` method to save values to an internal queue.

This class is used primarily with the databot webserver to provide the latest readings from the databot.

## Local WebServer Interface

A local web service interface is available to get data values from the databot.

![webarch](./media/webserver_arch.png)

Create an instance of the `PyDatabotSaveToQueueDataCollector` class with the desired sensors configured.

Then call the function `start_databot_webserver` in the PyDatabot module passing a reference to the `PyDatabotSaveToQueueDataCollector`

See the example in:

`examples/pydatabot_webserver_example.py`

## Run Locally

### Install Local Requirements

Recommended steps to install locally

* `pip install pip-tools` or `python -m pip install pip-tools`
* `pip-compile`
* `pip-sync`

## Examples

### Locate the Databot BlueTooth address

Every databot has a bluetooth address.  The find the address use the static method:

`PyDatabot.get_databot_address()`

and it is used in the configration like:

```python
    c = DatabotConfig()
    c.address = PyDatabot.get_databot_address()

```


### Simple Databot interfacing to print data values

This example will show you how to connect to the `databot` and display the selected data values.

### Custom Databot consumer

The PyDatabot class performs all of the necessary steps to interface with the databot and collect data from the databot.  However, the PyDatabot class does not do anything with the collected data excepti to print it.

For any custom processing of the databot data, a custom databot consumer is needed.

For an example and test of how to do this see:

`examples/pydatabot_custom_consumer.py`

```python
from databot.PyDatabot import PyDatabot, DatabotConfig


class CustomPyDatabotConsumer(PyDatabot):

    def process_databot_data(self, epoch, data):
        self.logger.info(f"{data}")
        self.logger.info(f"Linear Acceleration: {data['linear_acceleration_x']}, {data['linear_acceleration_y']}, {data['linear_acceleration_z']}")


def main():
    c = DatabotConfig()
    c.Laccl = True
    c.address = PyDatabot.get_databot_address()
    db = CustomPyDatabotConsumer(c)
    db.run()


if __name__ == '__main__':
    main()

```

### Save databot data to file

This example shows how to write the collected values to a file for later processing

`examples/pydatabot_save_data_to_file.py`

```python
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

```

### View Ambient Light Sensor Values

This example shows how to read ambient light sensor values.  Start the example and then cover the sensor with your hand.

Notice the light level values goes down.

`examples/pydatabot_light_level_example.py`

```python
from databot.PyDatabot import PyDatabot, DatabotConfig


def main():
    """
    An example of how to collect the Ambient Light values from the databot using the PyDatabot API

    :return: None
    """
    c = DatabotConfig()
    c.ambLight = True
    c.address = PyDatabot.get_databot_address()
    db = PyDatabot(c)
    db.run()


if __name__ == '__main__':
    main()

```

### Breath Detector

This example shows how to read co2 level.  Start the example and then breath on the databot.
Watch the co2 values go up.

`examples/pydatabot_co2_level_example.py`

```python
from databot.PyDatabot import PyDatabot, DatabotConfig


def main():
    """
    An example of how to collect CO2 values from the databot using the PyDatabot API.

    :return: None
    """
    c = DatabotConfig()
    c.co2 = True
    c.address = PyDatabot.get_databot_address()
    db = PyDatabot(c)
    db.run()


if __name__ == '__main__':
    main()

```

### Databot WebServer Access

This example shows how to start a simple webserver interface to get the current values from the databot.

`examples/pydatabot_webserver_example.py`

```python
import logging
from databot.PyDatabot import start_databot_webserver, PyDatabot, PyDatabotSaveToQueueDataCollector, DatabotConfig

def main():
    c = DatabotConfig()
    c.accl = True
    c.Laccl = True
    c.gyro = True
    c.magneto = True
    c.ambLight = True
    c.co2 = True
    c.hum = True
    c.pressure = True
    c.Etemp1 = True
    c.Etemp2 = True
    c.voc = True
    c.refresh = 1000
    c.address = PyDatabot.get_databot_address()
    db = PyDatabotSaveToQueueDataCollector(c, log_level=logging.DEBUG)

    t =start_databot_webserver(queue_data_collector=db, host="localhost", port=8321)
    db.run()


if __name__ == '__main__':
    main()

```

You can then open a browser and navigate to:
`http://localhost:8321`

And the sensor values will be displayed as a JSON string.

### Databot Save data to Queue

This example shows how to use the PyDatabotSaveToQueueDataCollector class to collect databot sensor values in an in memory queue.

This is particularly useful if you need to have access to the latest databot sensor values, but do not need to store the values in a file.

`examples/pydatabot_webserver_example.py`

```python
import threading
import time
from databot.PyDatabot import PyDatabot, PyDatabotSaveToQueueDataCollector, DatabotConfig


def worker(pydb: PyDatabotSaveToQueueDataCollector, wait_time_in_sec:int):
    while True:
        item = pydb.get_item()
        print(f'Data Item: {item}')
        time.sleep(wait_time_in_sec)


def main():

    c = DatabotConfig()
    c.accl = True
    c.Laccl = True
    c.gyro = True
    c.magneto = True
    c.address = PyDatabot.get_databot_address()
    db = PyDatabotSaveToQueueDataCollector(c)

    threading.Thread(target=worker, args=(db,0.5), daemon=True).start()

    db.run()


if __name__ == '__main__':
    main()

```

## Available Sensor Names

The names of the sensors that the PyDatabot class can retrieve are the following:

* Acceleration
* Altimeter
* Ambient Light
* Atmospheric Pressure
* CO2
* External Temperature 1
* External Temperature 2
* Gesture
* Gyroscope
* Humidity
* Humidity Adjusted Temperature
* Linear Acceleration
* Long Distance
* Magneto
* Noise
* RGB Light
* UltraViolet Light
* Volatile Organic Compound

