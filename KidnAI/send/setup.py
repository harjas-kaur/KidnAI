#!/usr/bin/env python3
"""
Setup script for installing Azure IoT dependencies
"""
import subprocess
import sys
import os

def install_packages():
    """Install required packages from requirements.txt"""
    try:
        print("Installing Azure IoT Device SDK and other dependencies...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("\nInstallation complete!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error installing packages: {e}")
        return False

def check_config():
    """Check if config.json exists and has been updated"""
    config_path = "config.json"
    if not os.path.exists(config_path):
        print(f"Warning: {config_path} not found!")
        return False
    
    with open(config_path, 'r') as f:
        config = f.read()
        if "your-iot-hub" in config or "your-device-id" in config:
            print("\nWarning: config.json contains placeholder values!")
            print("Please update config.json with your actual Azure IoT Hub connection details:")
            print("- azure_connection_string: Your device connection string from Azure IoT Hub")
            print("- device_id: Your device ID")
            print("\nExample connection string format:")
            print("HostName=your-iot-hub.azure-devices.net;DeviceId=your-device-id;SharedAccessKey=your-device-key")
            return False
    
    print("Configuration file looks ready!")
    return True

if __name__ == "__main__":
    print("=== Azure IoT Hub NILM Setup ===\n")
    
    if install_packages():
        print("\n" + "="*50)
        check_config()
        print("\nSetup process completed!")
        print("Run 'python send_data.py' to start the application.")
    else:
        print("Setup failed. Please check the error messages above.")
        sys.exit(1)
