from flask import Flask, request, jsonify
import pandas as pd
import joblib
from sklearn.preprocessing import StandardScaler
from flask_cors import CORS
import logging
from ultralytics import YOLO
import os
from chatbot1 import get_chatbot_response  # Chatbot logic

app = Flask(__name__)
CORS(app)  # Enable CORS
logging.basicConfig(level=logging.DEBUG)

# Load models
cost_overrun_model = joblib.load('models/project_cost_overrun_model.pkl')
scaler = joblib.load('models/scaler.pkl')
yolo_model = YOLO("blueprint.pt")  # YOLO model for object detection

@app.route('/predict', methods=['POST'])
def predict():
    data = request.json
    input_data = pd.DataFrame({
        'Project Size (sq. m)': [data['project_size']],
        'Labor Count': [data['labor_count']],
        'Equipment Count': [data['equipment_count']],
        'Avg Temperature (°C)': [data['avg_temp']],
        'Rainfall (mm)': [data['rainfall']],
        'Milestone': [data['milestone']],
        'External Factor': [data['external_factor']]
    })

    # Preprocess data
    input_data = pd.get_dummies(input_data, drop_first=True)
    missing_cols = set(scaler.feature_names_in_) - set(input_data.columns)
    for col in missing_cols:
        input_data[col] = 0
    input_data = input_data[scaler.feature_names_in_]
    input_data_scaled = scaler.transform(input_data)

    # Predict cost overrun
    prediction = cost_overrun_model.predict(input_data_scaled)
    return jsonify({'prediction': 'Yes' if prediction[0] == 1 else 'No'})

@app.route('/detect', methods=['POST'])
def detect():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    file = request.files['file']
    temp_dir = os.path.join(os.getcwd(), "temp")
    os.makedirs(temp_dir, exist_ok=True)
    file_path = os.path.join(temp_dir, file.filename)
    file.save(file_path)

    # YOLO Inference
    save_dir = os.path.join(os.getcwd(), "runs", "detect", "predict")
    os.makedirs(save_dir, exist_ok=True)
    results = yolo_model.predict(file_path, save=True, save_dir=save_dir)

    annotated_image_path = os.path.join(save_dir, file.filename)
    return jsonify({'annotated_image_path': annotated_image_path})

@app.route('/chatbot', methods=['POST'])
def chatbot():
    data = request.json
    user_input = data.get('message', '')
    response = get_chatbot_response(user_input)
    return jsonify({'response': response})

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000,debug=True)
