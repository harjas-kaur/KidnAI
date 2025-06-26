"""
Microneedle Sensor Array for Kidney Failure Detection
====================================================
This application monitors multiple biomarkers using a microneedle sensor array
to detect early signs of kidney failure. The system continuously measures:
- Blood Urea Nitrogen (BUN)
- Electrolyte levels (K+, Na+, Cl-)
- Creatinine and eGFR
- Albumin and protein levels
- pH and metabolic indicators

Data is transmitted to Azure IoT Hub for real-time analysis and medical alerting.
"""

import joblib
import numpy as np
import random
import time
import json
import os
import warnings
import asyncio
from azure.iot.device import IoTHubDeviceClient, Message
from azure.iot.device.exceptions import ConnectionFailedError, ConnectionDroppedError
from scipy.spatial.distance import jensenshannon

warnings.filterwarnings("ignore")

# ---------- Load Configuration ----------
with open("config.json", "r") as f:
    config = json.load(f)

AZURE_CONNECTION_STRING = config["azure_connection_string"]
DEVICE_ID = config["device_id"]
MESSAGE_TOPIC = config["message_property_topic"]
ALERT_TOPIC = config["alert_property_topic"]
RF_MODEL_PATH = config["rf_model_path"]
SCALER_PATH = config["scaler_path"]
PCA_PATH = config["pca_path"]
CLUSTER_PATH = config["cluster_model_path"]

# ---------- Load Models ----------
#dt_model = joblib.load(DT_MODEL_PATH)
rf_model = joblib.load(RF_MODEL_PATH)
scaler = joblib.load(SCALER_PATH)
pca = joblib.load(PCA_PATH)
kmeans = joblib.load(CLUSTER_PATH)

appliance_labels = [
    "Microneedle_Array_1", "Blood_Chemistry_Analyzer", "pH_Sensor_Module", "Protein_Detector",
    "Electrolyte_Monitor", "Creatinine_Sensor", "BUN_Analyzer", "eGFR_Calculator", "Albumin_Detector", "Metabolic_Monitor"
]

# ---------- Microneedle Sensor Array Configuration ----------
SENSOR_CALIBRATION = {
    "urea_baseline": 20.0,  # mg/dL baseline
    "electrolyte_baseline": 4.0,  # mEq/L baseline  
    "creatinine_baseline": 1.0,  # mg/dL baseline
    "noise_factor": 0.05,  # 5% sensor noise
    "drift_factor": 0.02   # 2% daily drift
}

# Additional biomarkers for comprehensive kidney function assessment
BIOMARKER_RANGES = {
    "albumin": {"normal": (3.5, 5.0), "abnormal": (1.5, 3.4)},  # g/dL
    "phosphorus": {"normal": (2.5, 4.5), "abnormal": (4.6, 8.0)},  # mg/dL
    "calcium": {"normal": (8.5, 10.5), "abnormal": (6.0, 8.4)},  # mg/dL
    "hemoglobin": {"normal": (12.0, 16.0), "abnormal": (7.0, 11.9)},  # g/dL
    "blood_ph": {"normal": (7.35, 7.45), "abnormal": (7.0, 7.34)},  # pH units
    "sodium": {"normal": (135, 145), "abnormal": (125, 134)},  # mEq/L
    "chloride": {"normal": (98, 107), "abnormal": (85, 97)}  # mEq/L
}

# ---------- Azure IoT Hub Setup ----------
device_client = None

async def setup_azure_iot_client():
    global device_client
    try:
        device_client = IoTHubDeviceClient.create_from_connection_string(AZURE_CONNECTION_STRING)
        await device_client.connect()
        print(f"[Azure IoT] Connected to IoT Hub as device: {DEVICE_ID}")
        return device_client
    except (ConnectionFailedError, ConnectionDroppedError) as e:
        print(f"[Azure IoT] Connection failed: {e}")
        return None

# ---------- Microneedle Sensor Simulation ----------
def simulate_microneedle_sensor_reading(biomarker, patient_condition="normal"):
    """
    Simulates realistic microneedle sensor readings for various biomarkers
    
    Args:
        biomarker: The biomarker to measure
        patient_condition: "normal", "early_ckd", "advanced_ckd", "esrd"
    """
    base_noise = random.uniform(-SENSOR_CALIBRATION["noise_factor"], SENSOR_CALIBRATION["noise_factor"])
    
    if biomarker not in BIOMARKER_RANGES:
        return 0.0
    
    if patient_condition == "normal":
        min_val, max_val = BIOMARKER_RANGES[biomarker]["normal"]
    else:
        min_val, max_val = BIOMARKER_RANGES[biomarker]["abnormal"]
    
    # Add realistic sensor characteristics
    reading = random.uniform(min_val, max_val)
    reading *= (1 + base_noise)  # Add sensor noise
    
    return round(reading, 2)

def get_comprehensive_blood_chemistry():
    """
    Simulates a comprehensive blood chemistry panel from microneedle array
    """
    # Determine patient condition randomly (in real system, this would be actual patient state)
    conditions = ["normal", "early_ckd", "advanced_ckd", "esrd"]
    patient_condition = random.choice(conditions)
    
    # Primary kidney function markers
    urea = simulate_microneedle_sensor_reading("albumin", patient_condition) * 15  # Convert to BUN equivalent
    electrolyte = simulate_microneedle_sensor_reading("sodium", patient_condition) / 30  # Normalize to 3.5-6.0 range
    creatinine = simulate_microneedle_sensor_reading("albumin", patient_condition) * 2  # Scale appropriately
    
    # Additional biomarkers
    albumin = simulate_microneedle_sensor_reading("albumin", patient_condition)
    phosphorus = simulate_microneedle_sensor_reading("phosphorus", patient_condition)
    calcium = simulate_microneedle_sensor_reading("calcium", patient_condition)
    hemoglobin = simulate_microneedle_sensor_reading("hemoglobin", patient_condition)
    blood_ph = simulate_microneedle_sensor_reading("blood_ph", patient_condition)
    sodium = simulate_microneedle_sensor_reading("sodium", patient_condition)
    chloride = simulate_microneedle_sensor_reading("chloride", patient_condition)
    
    # Calculate estimated GFR (eGFR) using simplified formula
    # eGFR = 186 × (creatinine/88.4)^-1.154 × (age)^-0.203 × (0.742 if female) × (1.210 if black)
    # Simplified for demo: eGFR ≈ 140 / creatinine (rough approximation)
    egfr = max(10, 140 / max(creatinine, 0.5))  # Prevent division by zero
    
    return {
        "primary": (urea, electrolyte, creatinine),
        "extended": {
            "albumin": albumin,
            "phosphorus": phosphorus,
            "calcium": calcium,
            "hemoglobin": hemoglobin,
            "blood_ph": blood_ph,
            "sodium": sodium,
            "chloride": chloride,
            "egfr": round(egfr, 1),
            "patient_condition": patient_condition
        }
    }

def get_sensor_data_from_arduino():
    """Legacy function maintained for compatibility"""
    blood_data = get_comprehensive_blood_chemistry()
    return blood_data["primary"]

# ---------- Feature Calculation ----------
def calculate_features(urea, electrolyte, creatinine):
    clearance_rate = urea * electrolyte  # Urea clearance indicator
    dialysis_efficiency = clearance_rate * creatinine  # Overall dialysis efficiency
    return [electrolyte, clearance_rate, dialysis_efficiency, urea, creatinine]

def calculate_kidney_function_score(blood_data):
    """
    Calculate comprehensive kidney function score from microneedle sensor data
    """
    primary = blood_data["primary"]
    extended = blood_data["extended"]
    
    # Weighted scoring based on clinical significance
    urea_score = min(100, max(0, (100 - (primary[0] - 20) * 2)))  # Lower is better
    creatinine_score = min(100, max(0, (100 - (primary[2] - 1) * 30)))  # Lower is better
    egfr_score = min(100, max(0, extended["egfr"]))  # Higher is better
    albumin_score = min(100, max(0, extended["albumin"] * 20))  # Higher is better
    
    # Composite kidney function score (0-100, higher is better)
    kidney_score = (urea_score * 0.25 + creatinine_score * 0.35 + 
                   egfr_score * 0.30 + albumin_score * 0.10)
    
    return round(kidney_score, 1)

def assess_kidney_failure_risk(kidney_score, extended_data):
    """
    Assess kidney failure risk based on comprehensive biomarker analysis
    """
    if kidney_score >= 80:
        risk_level = "LOW"
        recommendation = "Continue routine monitoring"
    elif kidney_score >= 60:
        risk_level = "MODERATE"
        recommendation = "Increase monitoring frequency, lifestyle modifications"
    elif kidney_score >= 40:
        risk_level = "HIGH"
        recommendation = "Immediate nephrology consultation required"
    else:
        risk_level = "CRITICAL"
        recommendation = "Emergency medical intervention needed"
    
    return {
        "risk_level": risk_level,
        "kidney_score": kidney_score,
        "recommendation": recommendation,
        "egfr": extended_data["egfr"],
        "stage": get_ckd_stage(extended_data["egfr"])
    }

def get_ckd_stage(egfr):
    """Determine Chronic Kidney Disease stage based on eGFR"""
    if egfr >= 90:
        return "Stage 1 (Normal)"
    elif egfr >= 60:
        return "Stage 2 (Mild decrease)"
    elif egfr >= 45:
        return "Stage 3a (Moderate decrease)"
    elif egfr >= 30:
        return "Stage 3b (Moderate decrease)"
    elif egfr >= 15:
        return "Stage 4 (Severe decrease)"
    else:
        return "Stage 5 (Kidney failure)"

# ---------- Send to Azure IoT Hub ----------
async def send_data_to_azure(urea, electrolyte, creatinine, extended_data=None):
    global device_client
    if device_client is None:
        print("[Azure IoT] Device client not connected")
        return
        
    payload = {
        "device_id": DEVICE_ID,
        "sensor_type": "microneedle_array",
        "primary_biomarkers": {
            "bun_level": round(urea, 2),
            "electrolyte_level": round(electrolyte, 2),
            "creatinine_level": round(creatinine, 2)
        },
        "timestamp": int(time.time())
    }
    
    # Add extended biomarker data if available
    if extended_data:
        payload["extended_biomarkers"] = {
            "albumin": extended_data["albumin"],
            "phosphorus": extended_data["phosphorus"],
            "calcium": extended_data["calcium"],
            "hemoglobin": extended_data["hemoglobin"],
            "blood_ph": extended_data["blood_ph"],
            "sodium": extended_data["sodium"],
            "chloride": extended_data["chloride"],
            "egfr": extended_data["egfr"]
        }
        payload["patient_condition"] = extended_data["patient_condition"]
    
    try:
        message = Message(json.dumps(payload))
        message.custom_properties["messageType"] = MESSAGE_TOPIC
        message.custom_properties["deviceType"] = "microneedle_sensor_array"
        await device_client.send_message(message)
        print(f"[Azure IoT] Published microneedle sensor data: Primary biomarkers sent")
    except Exception as e:
        print(f"[Azure IoT] Failed to send data: {e}")

async def send_kidney_assessment_to_azure(assessment_data):
    global device_client
    if device_client is None:
        print("[Azure IoT] Device client not connected")
        return
        
    try:
        assessment = {
            "device_id": DEVICE_ID,
            "assessment_type": "kidney_function_analysis",
            **assessment_data,
            "timestamp": int(time.time())
        }
        message = Message(json.dumps(assessment))
        message.custom_properties["messageType"] = "kidney_assessment"
        message.custom_properties["priority"] = "high" if assessment_data["risk_level"] in ["HIGH", "CRITICAL"] else "normal"
        await device_client.send_message(message)
        print(f"[Azure IoT] Published kidney assessment: Risk Level {assessment_data['risk_level']}")
    except Exception as e:
        print(f"[Azure IoT] Failed to send assessment: {e}")

async def send_alert_to_azure(alert_data):
    global device_client
    if device_client is None:
        print("[Azure IoT] Device client not connected")
        return
        
    try:
        alert = {
            **alert_data,
            "timestamp": int(time.time())
        }
        message = Message(json.dumps(alert))
        message.custom_properties["messageType"] = ALERT_TOPIC
        await device_client.send_message(message)
        print(f"[Azure IoT Alert] Published alert: {alert}")
    except Exception as e:
        print(f"[Azure IoT] Failed to send alert: {e}")

# ---------- Prediction ----------
def predict_and_print(features):
    features_np = np.array([features])
    #dt_pred = dt_model.predict(features_np)[0]
    rf_pred = rf_model.predict(features_np)[0]

    print("\n--- Microneedle Sensor Array Status ---")
    print("Sensor Modules:     ", "  ".join([label[:6] for label in appliance_labels]))
    #print("Decision Tree (DT):", "   ".join(map(str, dt_pred)))
    print("Random Forest (RF):", "   ".join(map(str, rf_pred)))

def display_comprehensive_results(blood_data, kidney_assessment):
    """Display comprehensive kidney function analysis"""
    primary = blood_data["primary"]
    extended = blood_data["extended"]
    
    print("\n" + "="*60)
    print("MICRONEEDLE SENSOR ARRAY - KIDNEY FUNCTION ANALYSIS")
    print("="*60)
    print(f"Patient Condition Simulation: {extended['patient_condition'].upper()}")
    print(f"Kidney Function Score: {kidney_assessment['kidney_score']}/100")
    print(f"Risk Level: {kidney_assessment['risk_level']}")
    print(f"CKD Stage: {kidney_assessment['stage']}")
    print(f"eGFR: {kidney_assessment['egfr']} mL/min/1.73m²")
    print("-" * 60)
    print("PRIMARY BIOMARKERS:")
    print(f"  BUN (Blood Urea Nitrogen): {primary[0]:.2f} mg/dL")
    print(f"  Electrolytes (K+): {primary[1]:.2f} mEq/L")
    print(f"  Creatinine: {primary[2]:.2f} mg/dL")
    print("-" * 60)
    print("EXTENDED BIOMARKERS:")
    print(f"  Albumin: {extended['albumin']:.2f} g/dL")
    print(f"  Phosphorus: {extended['phosphorus']:.2f} mg/dL")
    print(f"  Calcium: {extended['calcium']:.2f} mg/dL")
    print(f"  Hemoglobin: {extended['hemoglobin']:.2f} g/dL")
    print(f"  Blood pH: {extended['blood_ph']:.2f}")
    print(f"  Sodium: {extended['sodium']:.1f} mEq/L")
    print(f"  Chloride: {extended['chloride']:.1f} mEq/L")
    print("-" * 60)
    print(f"RECOMMENDATION: {kidney_assessment['recommendation']}")
    print("="*60)

# ---------- Anomaly Detection ----------
async def detect_anomaly(buffer, threshold=0.1, alert_percentage=0.5):
    try:
        # Step 1: Scale the buffer using the loaded scaler
        buffer_scaled = scaler.transform(buffer)

        # Step 2: Apply PCA to reduce dimensionality
        buffer_pca = pca.transform(buffer_scaled)

        js_divergences = []
        for sample in buffer_pca:
            # Calculate the JS divergence between the point and all cluster centroids
            distances = np.linalg.norm(kmeans.cluster_centers_ - sample, axis=1)
            js_scores = [jensenshannon(sample, centroid) for centroid in kmeans.cluster_centers_]
            js_divergences.append(np.min(js_scores))  # Taking the minimum JS score
        
        exceeded_threshold = sum([1 for js in js_divergences if js > threshold])
        
        if exceeded_threshold / len(js_divergences) >= alert_percentage:
            alert_message = {
                "alert": "Kidney Function Anomaly Detected",
                "alert_type": "biomarker_deviation",
                "severity": "HIGH" if exceeded_threshold / len(js_divergences) > 0.7 else "MODERATE",
                "exceeded_threshold_percentage": exceeded_threshold / len(js_divergences),
                "num_samples_exceeding": exceeded_threshold,
                "total_samples": len(js_divergences),
                "device_type": "microneedle_sensor_array"
            }
            # Send the alert to Azure IoT Hub
            await send_alert_to_azure(alert_message)
            print(f"[ALERT] Kidney function anomaly detected! Alert sent to Azure IoT Hub. {exceeded_threshold} out of {len(js_divergences)} samples exceeded threshold.")
        else:
            print("[INFO] No significant kidney function anomaly detected.")
        
    except Exception as e:
        print(f"[ERROR] Kidney function anomaly detection failed: {e}")

def check_buffer(buffer, sample_counter, window_size):
    if sample_counter >= window_size:
        print("Microneedle sensor buffer collected:")
        print(np.array(buffer))  # Printing the entire buffer of features
        buffer.clear()  # Clears the buffer
        sample_counter = 0  # Reset counter 
    return buffer, sample_counter

# ---------- Main Loop ----------
async def main():
    # Setup Azure IoT Hub connection
    await setup_azure_iot_client()
    
    buffer = []
    sample_counter = 0
    WINDOW_SIZE = 1
    JS_threshold = 0.1
    alert_percentage = 0.5
    
    print("[Azure IoT] Starting microneedle sensor array monitoring...")
    print("[SYSTEM] Initializing kidney function assessment protocols...")
    
    try:
        while True:
            # Get comprehensive blood chemistry from microneedle sensor array
            blood_data = get_comprehensive_blood_chemistry()
            urea, electrolyte, creatinine = blood_data["primary"]
            extended_data = blood_data["extended"]
            
            # Calculate kidney function metrics
            kidney_score = calculate_kidney_function_score(blood_data)
            kidney_assessment = assess_kidney_failure_risk(kidney_score, extended_data)
            
            # Legacy feature calculation for ML model compatibility
            features = calculate_features(urea, electrolyte, creatinine)
            
            buffer.append(features)
            sample_counter += 1
            buffer, sample_counter = check_buffer(buffer, sample_counter, WINDOW_SIZE)
            
            if len(buffer) == WINDOW_SIZE:  # Buffer is full, execute anomaly detection
                await detect_anomaly(buffer, JS_threshold, alert_percentage)

            # Send comprehensive data to Azure IoT Hub
            await send_data_to_azure(urea, electrolyte, creatinine, extended_data)
            await send_kidney_assessment_to_azure(kidney_assessment)
            
            # Display comprehensive results
            display_comprehensive_results(blood_data, kidney_assessment)
            predict_and_print(features)
            
            # Send critical alerts if high risk detected
            if kidney_assessment["risk_level"] in ["HIGH", "CRITICAL"]:
                critical_alert = {
                    "alert": f"Critical Kidney Function Alert - {kidney_assessment['risk_level']} Risk",
                    "kidney_score": kidney_assessment["kidney_score"],
                    "ckd_stage": kidney_assessment["stage"],
                    "egfr": kidney_assessment["egfr"],
                    "recommendation": kidney_assessment["recommendation"],
                    "device_type": "microneedle_sensor_array",
                    "priority": "CRITICAL"
                }
                await send_alert_to_azure(critical_alert)
            
            await asyncio.sleep(5)  # Increased interval for comprehensive analysis
            
    except KeyboardInterrupt:
        print("\n[Azure IoT] Stopping microneedle sensor array monitoring...")
    except Exception as e:
        print(f"[ERROR] Main loop error: {e}")
    finally:
        if device_client:
            await device_client.disconnect()
            print("[Azure IoT] Disconnected from IoT Hub")

if __name__ == "__main__":
    asyncio.run(main())
