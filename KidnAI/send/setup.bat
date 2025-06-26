@echo off
echo Installing Azure IoT Device SDK and other dependencies...
pip install -r requirements.txt
echo.
echo Installation complete!
echo.
echo Please update config.json with your Azure IoT Hub connection details:
echo - azure_connection_string: Your device connection string from Azure IoT Hub
echo - device_id: Your device ID
echo.
echo Example connection string format:
echo "HostName=your-iot-hub.azure-devices.net;DeviceId=your-device-id;SharedAccessKey=your-device-key"
pause
