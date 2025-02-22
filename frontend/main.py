import streamlit as st
import requests
import os
import joblib
import tempfile
import pandas as pd
from ultralytics import YOLO
from PIL import Image
import together
from together import Together
from dotenv import load_dotenv
import uuid
import time

# Load environment variables
load_dotenv()
together.api_key = os.getenv("TOGETHER_API_KEY1")  # Set your Together AI API key

# Load models and encoders
METRO_MODEL_PATH = "../backend/metro/xgboost_metro_classifier.pkl"
ENCODER_PATH = "../backend/metro/label_encoders.pkl"
classifier = joblib.load(METRO_MODEL_PATH)
regressor = joblib.load("../backend/metro/xgboost_metro_regressor.pkl")
label_encoders = joblib.load(ENCODER_PATH)
client = Together(api_key=together.api_key)
# Define expected features (must match training data)
expected_columns = [
    "City", "Tunnel Length (km)", "Num of Stations", "Num of Workers", 
    "Equipment Factor (%)", "Signal System Complexity (%)", "Material Factor (%)", 
    "Gov Regulation Factor (%)", "Urban Congestion Impact (%)", 
    "Expected Completion Time (months)", "Budget (in Crores)"
]

def generate_ai_explanation(risk_level, delay_days, input_data):
    """Generates an AI-based explanation using Together AI (LLaMA 2-70B)"""
    
    prompt = f"""
    A metro project has the following characteristics:
    - City: {input_data['City'].values[0]}
    - Tunnel Length: {input_data['Tunnel Length (km)'].values[0]} km
    - Number of Stations: {input_data['Num of Stations'].values[0]}
    - Number of Workers: {input_data['Num of Workers'].values[0]}
    - Equipment Factor: {input_data['Equipment Factor (%)'].values[0]}%
    - Signal System Complexity: {input_data['Signal System Complexity (%)'].values[0]}%
    - Material Factor: {input_data['Material Factor (%)'].values[0]}%
    - Government Regulation Factor: {input_data['Gov Regulation Factor (%)'].values[0]}%
    - Urban Congestion Impact: {input_data['Urban Congestion Impact (%)'].values[0]}%
    - Expected Completion Time: {input_data['Expected Completion Time (months)'].values[0]} months
    - Budget: ₹{input_data['Budget (in Crores)'].values[0]} crores

    The project has been classified as having a **{risk_level}** risk level and is expected to face a delay of **{delay_days:.2f}** days.

    Explain the results in simple terms, highlighting the key factors contributing to the risk level and delay. Also, suggest mitigation strategies.
    """

    # Call Together AI with LLaMA 2-70B
    response = client.chat.completions.create(
        model="meta-llama/Llama-3.3-70B-Instruct-Turbo",
        messages=[{"role": "user", "content": prompt}]
    )
    

    # Debug: Print the raw API response
    st.write(response.choices[0].message.content)

    # Extract the generated text from the response
    # if "choices" in response and len(response["choices"]) > 0:
    #     return response["choices"][0]["text"]
    # else:
    #     return "❌ Error: Unable to generate an explanation. Please check the API response."

def generate_detection_explanation(detected_objects, detection_type):
    """Generates an AI-based explanation for detected objects using Together AI (LLaMA 2-70B)"""
    
    prompt = f"Explain the following detected objects in simple terms for {detection_type}:\n\n"
    for obj in detected_objects:
        prompt += f"- Class: {obj['class_name']}, Confidence: {obj['confidence']:.2f}, Bounding Box: {obj['bbox']}\n"

    if detection_type == "Blueprint Detection":
        prompt += "\n Basically purpose of Blueprint detection is to help builders save time, cost and delays which happen due to problems in the blueprint itself. Explain what each term means, why it is important, and how it relates to blueprint analysis. Find faults in the blueprint based on the detection  or appreciate if something is right. Also, suggest any necessary actions or precautions."
    elif detection_type == "Risk Detection":
        prompt += "\nExplain what each term means, why it is important, and what exactly are the risks in the image. Also, suggest any necessary actions or precautions."

    # Call Together AI with LLaMA 2-70B
    response = client.chat.completions.create(
        model="meta-llama/Llama-3.3-70B-Instruct-Turbo",
        messages=[{"role": "user", "content": prompt}]
    )

    # Extract the generated text from the response
    return response.choices[0].message.content

# Load the supplier recommendation model & vectorizer
SUPPLIER_MODEL_PATH = "../backend/train/supply_chain_nlp/supplier_recommendation_model.pkl"
VECTORIZER_PATH = "../backend/train/supply_chain_nlp/vectorizer.pkl"
supplier_model = joblib.load(SUPPLIER_MODEL_PATH)
vectorizer = joblib.load(VECTORIZER_PATH)

# Set up the Streamlit page
st.set_page_config(page_title="BuildSmart", page_icon="🏗️", layout="wide")
st.title("🏗️ BuildSmart - Construction AI")

# Custom CSS for UI enhancement
st.markdown(
    """
    <style>
    body {
        font-family: 'Arial', sans-serif;
        background-color: #000000 !important;
        color: #ffffff;
    }
    .block-container {
            padding-top: 35px !important;
            
        }
    .main-title {
        text-align: center;
        font-size: 36px;
        font-weight: bold;
        color: #FFD700; /* Yellow */
    }
    .landing-container {
        text-align: center;
        margin-top: 50px;
    }
    .landing-button {
        font-size: 20px;
        padding: 12px 25px;
        background-color: #FFD700; /* Yellow */
        color: #000000;
        border: none;
        border-radius: 8px;
        cursor: pointer;
        transition: 0.3s;
    }
    .landing-button:hover {
        background-color: #FFC107; /* Slightly darker yellow */
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.sidebar.markdown(
    """
    <style>
        [data-testid="stSidebar"] {
            padding-top: 35px !important; 
            background-color: #f1c232 !important; /* Sidebar background */
            width: 200px !important;
            min-width: 200px !important;
            max-width: 200px !important;
        }
        /* Sidebar Title */
        [data-testid="stSidebar"] h1, 
        [data-testid="stSidebar"] h2, 
        [data-testid="stSidebar"] h3 {
            color: black !important; /* Title remains black */
            text-align: center;
        }
        [data-testid="stSidebar"] hr {
            border-top: 2px solid black !important; /* Makes the separator black */
        }
        /* Sidebar Items */
        .sidebar-item {
            font-size: 18px;
            padding: 12px 15px;
            background-color: #333333 !important; /* Dark grey button */
            color: white !important; /* White text */
            border-radius: 8px;
            text-align: center;
            margin: 8px 0;
            cursor: pointer;
            transition: 0.3s;
            font-weight: 500;
        }
        .sidebar-item:hover {
            background-color: #444444 !important; /* Slightly lighter grey on hover */
        }
    </style>
    """,
    unsafe_allow_html=True
)

if "page" not in st.session_state:
    st.session_state.page = "Home" # Default page
# Sidebar Buttons
if st.sidebar.button("🏠 Home"):
    st.session_state.page = "Home"

if st.sidebar.button("📊 Dashboard"):
    st.session_state.page = "Dashboard"

st.sidebar.markdown("---")  # Separator

if st.sidebar.button("🚇 Metro Risk Prediction"):
    st.session_state.page = "Metro Risk Prediction"



if st.sidebar.button("💬 Chatbot"):
    st.session_state.page = "Chatbot"

if st.sidebar.button("📐 Blueprint Detection"):
    st.session_state.page = "Blueprint Detection and Analysis"

if st.sidebar.button("🔗 Supply Chain Copilot"):
    st.session_state.page = "Supply Chain Copilot"

if st.sidebar.button("⚠️ Risk Detection"):
    st.session_state.page = "Risk Detection"

# # Display Selected Page
# st.write(f"### {st.session_state.page} Page Content")

# Home (Landing Page)
if st.session_state.page == "Home":
    st.markdown('<div class="landing-container">', unsafe_allow_html=True)
    st.image("https://source.unsplash.com/1600x600/?construction,building", use_container_width=True)
    st.markdown('<h1 class="main-title">🏗️ BuildSmart - AI for Smarter Construction</h1>', unsafe_allow_html=True)
    st.write("🚀 AI-powered solutions for project risk assessment, cost optimization, and safety monitoring.")
    st.markdown('<a href="?page=dashboard"><button class="landing-button">Get Started</button></a>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

### 🏗️ DASHBOARD SECTION ###
elif st.session_state.page == "Dashboard":
    st.subheader("📊 Project Cost Overrun Prediction & Safety Analysis")

    with st.expander("🔍 Predict Cost Overrun"):
        col1, col2 = st.columns(2)
        with col1:
            project_size = st.number_input("Project Size (sq. m)", min_value=0)
            labor_count = st.number_input("Labor Count", min_value=0)
            equipment_count = st.number_input("Equipment Count", min_value=0)
        with col2:
            avg_temp = st.number_input("Avg Temperature (°C)", min_value=-50, max_value=50)
            rainfall = st.number_input("Rainfall (mm)", min_value=0)
            milestone = st.text_input("Milestone")
            external_factor = st.text_input("External Factor")

        if st.button("🔮 Predict Cost Overrun"):
            with st.spinner("Predicting..."):
                response = requests.post(f"http://127.0.0.1:5000/predict", json={
                    "project_size": project_size,
                    "labor_count": labor_count,
                    "equipment_count": equipment_count,
                    "avg_temp": avg_temp,
                    "rainfall": rainfall,
                    "milestone": milestone,
                    "external_factor": external_factor
                })
                if response.status_code == 200:
                    prediction = response.json().get("prediction", "N/A")
                    st.success(f"**Prediction:** {prediction}")
                else:
                    st.error("Failed to get a prediction. Please try again.")

### 🚆 METRO RISK PREDICTION SECTION ###
elif st.session_state.page == "Metro Risk Prediction":
    st.subheader("🚆 Metro Project Risk Level Prediction")

    with st.form("metro_risk_form"):
        city = st.selectbox("City", ["Delhi", "Mumbai", "Bangalore", "Hyderabad", "Chennai", "Kolkata"])
        tunnel_length = st.number_input("Tunnel Length (km)", min_value=1.0, max_value=50.0, step=0.1)
        num_stations = st.number_input("Number of Stations", min_value=5, max_value=100)
        num_workers = st.number_input("Number of Workers", min_value=100, max_value=5000)
        equipment_factor = st.slider("Equipment Factor (%)", 0, 100)
        signal_complexity = st.slider("Signal System Complexity (%)", 0, 100)
        material_factor = st.slider("Material Factor (%)", 0, 100)
        gov_regulation = st.slider("Government Regulation Factor (%)", 0, 100)
        urban_congestion = st.slider("Urban Congestion Impact (%)", 0, 100)
        budget = st.number_input("Budget (in Crores)", min_value=500.0, max_value=5000.0, step=10.0)
        expected_completion_time = st.number_input("Expected Completion Time (months)", min_value=24, max_value=120)

        submitted = st.form_submit_button("🚀 Predict Risk Level")

    if submitted:
        with st.spinner("Predicting risk level..."):
            city_encoded = label_encoders["City"].transform([city])[0]

            input_data = pd.DataFrame([[
                city_encoded, tunnel_length, num_stations, num_workers,
                equipment_factor, signal_complexity, material_factor,
                gov_regulation, urban_congestion, expected_completion_time, budget
            ]], columns=["City", "Tunnel Length (km)", "Num of Stations", "Num of Workers",
                         "Equipment Factor (%)", "Signal System Complexity (%)", "Material Factor (%)",
                         "Gov Regulation Factor (%)", "Urban Congestion Impact (%)",
                         "Expected Completion Time (months)", "Budget (in Crores)"])

            # Predict risk level
            risk_prediction = classifier.predict(input_data)[0]
            risk_label = label_encoders["Risk Level"].inverse_transform([risk_prediction])[0]
            st.success(f"✅ **Predicted Risk Level:** {risk_label}")

            # Predict delay (if you have a regression model for delay)
            delay_days = 45.23  # Replace with actual delay prediction if available

            # Generate AI Explanation
            st.subheader("🤖 AI Explanation")
            explanation = generate_ai_explanation(risk_label, delay_days, input_data)
            st.write(explanation)

### 🔍 SUPPLY CHAIN COPILOT ###
elif st.session_state.page == "Supply Chain Copilot":
    st.subheader("🔗 Construction Supplier Copilot")

    query = st.text_input("Enter Material Type or Supplier Need (e.g., 'Steel Supplier in Mumbai')")

    if st.button("Get Recommendations"):
        with st.spinner("Fetching recommendations..."):
            query_vector = vectorizer.transform([query])
            distances, indices = supplier_model.kneighbors(query_vector)

            st.write("### 🔍 Recommended Suppliers:")
            for i in range(len(indices[0])):
                supplier_idx = indices[0][i]
                st.write(f"**Supplier {i+1}:**")
                st.write(f"🔹 **Supplier Name:** {supplier_idx}")
                st.write(f"🔹 **Similarity Score:** {round(distances[0][i], 3)}")
                st.write("---")

### 🤖 AI CHATBOT SECTION ###
elif st.session_state.page == "Chatbot":
    st.subheader("🤖 AI Construction Chatbot")
    st.write("💬 Ask anything about construction risks, safety, and cost optimization!")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if user_input := st.chat_input("Type your message..."):
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        with st.spinner("Thinking..."):
            response = requests.post(f"http://127.0.0.1:5000/chatbot", json={"message": user_input})
            if response.status_code == 200:
                bot_response = response.json().get("response", "No response")
                st.session_state.messages.append({"role": "assistant", "content": bot_response})
                with st.chat_message("assistant"):
                    st.markdown(bot_response)
            else:
                st.error("Chatbot failed to respond. Please try again.")

### 🔍 YOLO IMAGE DETECTION SECTION ###
elif st.session_state.page == "Blueprint Detection and Analysis":
    st.subheader("📸 Upload an Image for Blueprint Detection")

    uploaded_file = st.file_uploader("Choose an image...", type=["jpg", "png", "jpeg"])

    # Define a fixed prediction folder
    predict_folder = "runs/detect/predictBlueprint"
    os.makedirs(predict_folder, exist_ok=True)  # Ensure the folder exists

    if uploaded_file:
        st.image(uploaded_file, caption="Uploaded Image", use_container_width=True)

        if st.button("🚀 Detect Blueprint"):
            with st.spinner("Running detection..."):
                # Save uploaded file temporarily
                temp_dir = tempfile.mkdtemp()
                image_path = os.path.join(temp_dir, uploaded_file.name)
                with open(image_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())

                # Generate a unique name for the output image
                unique_id = uuid.uuid4().hex[:8]  # Short UUID
                timestamp = int(time.time())  # Timestamp
                new_image_name = f"BuildSmart_detected_blueprint_{unique_id}.png"  # Unique image name
                new_image_path = os.path.join(predict_folder, new_image_name)

                # Load YOLO model and perform inference
                model = YOLO("../backend/blueprint.pt")
                results = model.predict(image_path, save=True)  # Save images in default location

                # Find the latest prediction folder
                saved_images = sorted(
                    [f for f in os.listdir("runs/detect") if f.startswith("predict")], 
                    key=lambda x: os.path.getctime(os.path.join("runs/detect", x)), 
                    reverse=True
                )

                if saved_images:
                    latest_predict_folder = os.path.join("runs/detect", saved_images[0])
                    detected_images = [f for f in os.listdir(latest_predict_folder) if f.endswith((".png", ".jpg", ".jpeg"))]

                    if detected_images:
                        old_image_path = os.path.join(latest_predict_folder, detected_images[0])
                        os.rename(old_image_path, new_image_path)  # Move and rename file

                        # Display annotated image
                        st.image(Image.open(new_image_path), caption="Annotated Image", use_container_width=True)

                        # Show detected objects
                        st.write("### 📌 Detected Objects:")
                        detected_objects = []
                        for result in results:
                            for box in result.boxes:
                                class_id = int(box.cls)
                                class_name = result.names[class_id]
                                confidence = float(box.conf)
                                bbox = box.xyxy.tolist()
                                detected_objects.append({
                                    "class_name": class_name,
                                    "confidence": confidence,
                                    "bbox": bbox
                                })
                                st.write(f"🔹 *Class:* {class_name}, *Confidence:* {confidence:.2f}, *Bounding Box:* {bbox}")

                        # Generate AI Explanation for detected objects
                        st.subheader("🤖 AI Explanation for Detected Objects")
                        explanation = generate_detection_explanation(detected_objects, "Blueprint Detection")
                        st.write(explanation)
                    else:
                        st.error("Error: Could not find the saved prediction image.")
                else:
                    st.error("⚠️ No objects detected. Try another image.")

### 🔍 YOLO IMAGE DETECTION SECTION ###
elif st.session_state.page == "Risk Detection":
    st.subheader("📸 Upload a Construction Site Image for Risk Detection")

    uploaded_file = st.file_uploader("Choose an image...", type=["jpg", "png", "jpeg"])

    # Define a fixed prediction folder
    predict_folder = "runs/detect/predictRisk"
    os.makedirs(predict_folder, exist_ok=True)  # Ensure the folder exists

    if uploaded_file:
        st.image(uploaded_file, caption="Uploaded Image", use_container_width=True)

        if st.button("🚀 Detect Risk"):
            with st.spinner("Running detection..."):
                # Save uploaded file temporarily
                temp_dir = tempfile.mkdtemp()
                image_path = os.path.join(temp_dir, uploaded_file.name)
                with open(image_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())

                # Generate a unique name for the output image
                unique_id = uuid.uuid4().hex[:8]  # Short UUID
                timestamp = int(time.time())  # Timestamp
                new_image_name = f"BuildSmart_detected_risk_{unique_id}.png"  # Unique image name
                new_image_path = os.path.join(predict_folder, new_image_name)

                # Load YOLO model and perform inference
                model = YOLO("../backend/PPE/models/best_2.pt")
                results = model.predict(image_path, save=True)  # Save images in default location

                # Find the latest prediction folder
                saved_images = sorted(
                    [f for f in os.listdir("runs/detect") if f.startswith("predict")], 
                    key=lambda x: os.path.getctime(os.path.join("runs/detect", x)), 
                    reverse=True
                )

                if saved_images:
                    latest_predict_folder = os.path.join("runs/detect", saved_images[0])
                    detected_images = [f for f in os.listdir(latest_predict_folder) if f.endswith((".png", ".jpg", ".jpeg"))]

                    if detected_images:
                        old_image_path = os.path.join(latest_predict_folder, detected_images[0])
                        os.rename(old_image_path, new_image_path)  # Move and rename file

                        # Display annotated image
                        st.image(Image.open(new_image_path), caption="Annotated Image", use_container_width=True)

                        # Show detected objects
                        st.write("### 📌 Detected Objects:")
                        detected_objects = []
                        for result in results:
                            for box in result.boxes:
                                class_id = int(box.cls)
                                class_name = result.names[class_id]
                                confidence = float(box.conf)
                                bbox = box.xyxy.tolist()
                                detected_objects.append({
                                    "class_name": class_name,
                                    "confidence": confidence,
                                    "bbox": bbox
                                })
                                st.write(f"🔹 *Class:* {class_name}, *Confidence:* {confidence:.2f}, *Bounding Box:* {bbox}")

                        # Generate AI Explanation for detected objects
                        st.subheader("🤖 AI Explanation for Detected Objects")
                        explanation = generate_detection_explanation(detected_objects, "Risk Detection")
                        st.write(explanation)
                    else:
                        st.error("Error: Could not find the saved prediction image.")
                else:
                    st.error("⚠️ No objects detected. Try another image.")


