import streamlit as st # type: ignore
from pathlib import Path
import cv2 # type: ignore
import base64
import streamlit.components.v1 as components # type: ignore
import os
import torch 
from process_sensor_data.imuDataPipeline import full_sensor_pipeline


# Set page configuration
st.set_page_config(
    page_title="TEMPO - Medical Motion Tracking",
    page_icon="🏥",
    layout="wide"
)


# Define color scheme
PRIMARY_COLOR = "#0066cc"
SECONDARY_COLOR = "#ff9900"
BACKGROUND_COLOR = "#f0f2f6"

# Custom CSS with multiple header style options
st.markdown("""
    <style>
    /* Base styles */
    .main {
        background-color: #f0f2f6;
    }
    .stButton>button {
        background-color: #0066cc;
        color: white;
    }
    .stTextInput>div>div>input {
        background-color: white;
    }
    
    /* Sophisticated header styles */
    .header-modern {
        background-color: white;
        padding: 2rem 3rem;
        margin: -4rem -4rem 2rem -4rem;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    
    .header-split {
        display: flex;
        align-items: center;
        gap: 2rem;
        padding: 1rem;
        background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%);
    }
    
    .header-minimal {
        padding: 2rem;
        border-bottom: 2px solid #eaeaea;
        margin-bottom: 2rem;
    }
    
    .header-image {
        max-width: 100%;
        height: auto;
        object-fit: contain;
    }
    
    .title-modern {
        font-family: 'Inter', sans-serif;
        font-weight: 600;
        font-size: 2.5rem;
        letter-spacing: -0.02em;
        margin-bottom: 0.5rem;
        color: #1a1a1a;
    }
    
    .subtitle-modern {
        font-family: 'Inter', sans-serif;
        font-weight: 400;
        font-size: 1.1rem;
        color: #666666;
        letter-spacing: 0.01em;
        line-height: 1.5;
    }
    
    .animated-border {
        position: relative;
        overflow: hidden;
    }
    
    .animated-border::after {
        content: '';
        position: absolute;
        bottom: 0;
        left: 0;
        width: 100%;
        height: 2px;
        background: linear-gradient(90deg, #0066cc, #00cc99);
        transform: translateX(-100%);
        animation: border-slide 2s ease-in-out infinite;
    }
    
    @keyframes border-slide {
        0% { transform: translateX(-100%); }
        100% { transform: translateX(100%); }
    }
    </style>
    """, unsafe_allow_html=True)


# Render Data Collection HTML: Logic for creating the ensens data collection
# 1. CSS for rendering the esens data collection
# 2. esense-container div - Makes buttons for connecting, recording, stopping recording and downloading data
# 3. Collecting Data
#     * calculateChecksum: error checking in data transmission from earbuds to  app 
#     * startSamplingCommand: Starts IMU sampling at 50Hz, returning a byte array of 0x53 and calculated checksum.
#     * stopSamplingCommand: Stops IMU sampling, returning a byte array with (0x00) to indicate stopping.
#     * parseIMUData: Converts raw IMU data into 16 bit integers by scalaing and adding timestamps 
#     * downloadData: Triggers download of CSV file with parsed IMU data and timestamp
# 4. Data Logging 
#     * connectToESense: Creates bluetooth connection with device beginning with eSense, connects to its GATT server,
#     gets the specific service and characteristics needed for IMU data, and enables the start button once connecte
#     * startSampling: Initialise IMU data sampling, enabling notifications and updates UI 
#     * stopSampling: Stops IMU data sampling 
# 5. Main data handing
#     * handleIMUData: takes raw data and if recording is true, add parsed data to an array to update frontend counter 
#     on how many samples have been collected.

def render_data_collection_html():
    return """
    <div style="padding: 20px;">
        <style>
            .esense-container button { 
                padding: 10px 20px; 
                margin: 5px;
                font-size: 16px;
                cursor: pointer;
            }
            .esense-container button:disabled { cursor: not-allowed; }
            #dataDisplay { 
                font-family: monospace;
                white-space: pre;
                margin-top: 20px;
                padding: 10px;
                background-color: #f0f0f0;
                border-radius: 5px;
            }
            .status {
                margin-top: 10px;
                color: #666;
            }
            #recordingStatus {
                color: #ff0000;
                font-weight: bold;
                display: none;
            }
        </style>
        
        <div class="esense-container">
            <button id="connectButton">Connect to eSense</button>
            <button id="startButton" disabled>Start Sampling</button>
            <button id="stopButton" disabled>Stop Sampling</button>
            <button id="downloadButton" disabled>Download Data</button>
            
            <div class="status">
                <span id="recordingStatus">● Recording</span>
                <div id="sampleCount">Samples collected: 0</div>
            </div>

            <div id="dataDisplay"></div>
        </div>

        <script>
            let device;
            let imuDataCharacteristic;
            let configCharacteristic;
            let recordedData = [];
            let isRecording = false;
            let recordingStartTime = null;
            
            function calculateChecksum(dataSize, ...data) {
                const sum = dataSize + data.reduce((a, b) => a + b, 0);
                return sum & 0xFF;
            }

            function startSamplingCommand(rate = 50) {
                return new Uint8Array([
                    0x53,
                    calculateChecksum(0x02, 0x01, rate),
                    0x02,
                    0x01,
                    rate
                ]);
            }

            function stopSamplingCommand() {
                return new Uint8Array([
                    0x53,
                    calculateChecksum(0x02, 0x00, 0x00),
                    0x02,
                    0x00,
                    0x00
                ]);
            }

            function parseIMUData(data) {
                function bytesToInt16(high, low) {
                    const value = (high << 8) | low;
                    return value > 0x7FFF ? value - 0x10000 : value;
                }

                const ACCEL_SCALE = 8192.0;
                const GYRO_SCALE = 65.5;

                const timestamp = Date.now();
                const date = new Date(timestamp);
                const formattedTime = [
                    date.getHours().toString().padStart(2, '0'),
                    date.getMinutes().toString().padStart(2, '0'),
                    date.getSeconds().toString().padStart(2, '0'),
                    date.getMilliseconds().toString().padStart(3, '0')
                ].join(':');

                const elapsedSeconds = recordingStartTime ? (timestamp - recordingStartTime) / 1000 : 0;

                return {
                    timestamp: formattedTime,
                    packetIndex: data.getUint8(1),
                    gyro: {
                        x: bytesToInt16(data.getUint8(3), data.getUint8(4)) / GYRO_SCALE,
                        y: bytesToInt16(data.getUint8(5), data.getUint8(6)) / GYRO_SCALE,
                        z: bytesToInt16(data.getUint8(7), data.getUint8(8)) / GYRO_SCALE
                    },
                    accel: {
                        x: bytesToInt16(data.getUint8(9), data.getUint8(10)) / ACCEL_SCALE,
                        y: bytesToInt16(data.getUint8(11), data.getUint8(12)) / ACCEL_SCALE,
                        z: bytesToInt16(data.getUint8(13), data.getUint8(14)) / ACCEL_SCALE
                    }
                };
            }

            function downloadData() {
                if (recordedData.length === 0) {
                    alert('No data to download');
                    return;
                }

                const timestamp = new Date().toISOString()
                    .replace(/[:.]/g, '')
                    .slice(0, -4);

                const rows = ["timestamp,x-axis (g),y-axis (g),z-axis (g),x-axis (deg/s),y-axis (deg/s),z-axis (deg/s)"];
                recordedData.forEach(data => {
                    rows.push(`${data.timestamp},${data.accel.x.toFixed(6)},${data.accel.y.toFixed(6)},${data.accel.z.toFixed(6)},${data.gyro.x.toFixed(6)},${data.gyro.y.toFixed(6)},${data.gyro.z.toFixed(6)}`);
                });

                const blob = new Blob([rows.join('\\n')], { type: 'text/csv' });
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.setAttribute('href', url);
                a.setAttribute('download', `esense_imu_data_${timestamp}.csv`);
                a.click();
                window.URL.revokeObjectURL(url);
            }

            async function connectToESense() {
                try {
                    device = await navigator.bluetooth.requestDevice({
                        filters: [{ namePrefix: 'eSense' }],
                        optionalServices: ['0000ff06-0000-1000-8000-00805f9b34fb']
                    });

                    const server = await device.gatt.connect();
                    const service = await server.getPrimaryService('0000ff06-0000-1000-8000-00805f9b34fb');
                    
                    configCharacteristic = await service.getCharacteristic('0000ff07-0000-1000-8000-00805f9b34fb');
                    imuDataCharacteristic = await service.getCharacteristic('0000ff08-0000-1000-8000-00805f9b34fb');

                    document.getElementById('startButton').disabled = false;
                    document.getElementById('connectButton').disabled = true;
                    console.log('Connected to eSense!');
                } catch (error) {
                    console.error('Error connecting:', error);
                    alert('Failed to connect: ' + error.message);
                }
            }

            async function startSampling() {
                try {
                    recordedData = [];
                    isRecording = true;
                    recordingStartTime = Date.now();
                    
                    await imuDataCharacteristic.startNotifications();
                    imuDataCharacteristic.addEventListener('characteristicvaluechanged', handleIMUData);
                    
                    await configCharacteristic.writeValue(startSamplingCommand(50));
                    
                    document.getElementById('startButton').disabled = true;
                    document.getElementById('stopButton').disabled = false;
                    document.getElementById('downloadButton').disabled = true;
                    document.getElementById('recordingStatus').style.display = 'inline';
                    
                } catch (error) {
                    console.error('Error starting sampling:', error);
                    alert('Failed to start sampling: ' + error.message);
                }
            }

            async function stopSampling() {
                try {
                    isRecording = false;
                    await configCharacteristic.writeValue(stopSamplingCommand());
                    await imuDataCharacteristic.stopNotifications();
                    
                    document.getElementById('startButton').disabled = false;
                    document.getElementById('stopButton').disabled = true;
                    document.getElementById('downloadButton').disabled = false;
                    document.getElementById('recordingStatus').style.display = 'none';
                    
                } catch (error) {
                    console.error('Error stopping sampling:', error);
                    alert('Failed to stop sampling: ' + error.message);
                }
            }

            function handleIMUData(event) {
                const data = parseIMUData(event.target.value);
                
                if (isRecording) {
                    recordedData.push(data);
                    document.getElementById('sampleCount').textContent = 
                        `Samples collected: ${recordedData.length}`;
                }

                document.getElementById('dataDisplay').textContent = 
                    `Latest IMU Data:\\n` +
                    `Time: ${data.timestamp}\\n` +
                    `Accelerometer (g): x=${data.accel.x.toFixed(3)}, y=${data.accel.y.toFixed(3)}, z=${data.accel.z.toFixed(3)}\\n` +
                    `Gyroscope (deg/s): x=${data.gyro.x.toFixed(3)}, y=${data.gyro.y.toFixed(3)}, z=${data.gyro.z.toFixed(3)}`;
            }

            // Add button event listeners
            document.getElementById('connectButton').addEventListener('click', connectToESense);
            document.getElementById('startButton').addEventListener('click', startSampling);
            document.getElementById('stopButton').addEventListener('click', stopSampling);
            document.getElementById('downloadButton').addEventListener('click', downloadData);
        </script>
    </div>
    """

# """ Create Sensor Section: Section for managing different sensor devices (Phone Sensors, Wrist Sensors, eSense Earbuds)"""
def create_sensor_section():
    st.header("Data Collection Hub")
    st.write("Connect and manage your sensor devices in one place. Follow the guided steps for each device.")
    
    tabs = st.tabs(["📱 Phone Sensors", "⌚ Wrist Sensors", "🎧 eSense Earbuds"])
    
    #Ssession state for tracking progress initialised 
    if 'wrist_step' not in st.session_state:
        st.session_state.wrist_step = 0
    if 'phone_step' not in st.session_state:
        st.session_state.phone_step = 0
    if 'esense_step' not in st.session_state:
        st.session_state.esense_step = 0
    
    # Phone Sensors Tab
    with tabs[0]:
        st.subheader("Phone Sensors")
        # Define the steps for phone setup
        steps = ["Install App", "Configure Settings"]
        current_step = st.session_state.phone_step
        
        # Show progress indicator if not completed
        if current_step < len(steps):
            st.progress(current_step / (len(steps) - 1))
            st.write(f"Current Step: {steps[current_step]}")
        
        # Step 1: Installation
        if current_step == 0:
            with st.expander("📱 Installation Guide", expanded=True):
                st.markdown("""
                ### Download Physics Toolbox Sensor Suite
                
                Choose your device's app store and install the application:
                
                - [🤖 Google Play Store](https://play.google.com/store/apps/details?id=com.chrystianvieyra.physicstoolboxsuite&hl=en_GB)
                - [📱 iOS App Store](https://apps.apple.com/us/app/physics-toolbox-sensor-suite/id1128914250)
                
                #### Installation Tips:
                - Ensure you have a stable internet connection
                - Allow all required permissions during installation
                - Check that your device meets the minimum requirements
                - Make sure you have enough storage space
                """)
                
                # Added key "phone_install_complete"
                if st.button("✅ Mark Installation Complete", key="phone_install_complete"):
                    st.session_state.phone_step = 1
                    st.rerun()
        
        # Step 2: Configuration
        elif current_step == 1:
            with st.expander("⚙️ Sensor Configuration", expanded=True):
                st.markdown("""
                ### Configure Your Phone Sensors
                
                1. Open Physics Toolbox Sensor Suite
                2. Configure the following settings:
                - Set sampling rate to 50Hz
                - Enable accelerometer and gyroscope
                - Verify sensors are working correctly
                3. Test the recording function
                4. Ensure CSV export is working properly
                """)
                
                # Added key "phone_config_complete"
                if st.button("✅ Configuration Complete", key="phone_config_complete"):
                    st.session_state.phone_step = 2
                    st.rerun()
        
        # Completion Card
        elif current_step == 2:
            st.success("🎉 Phone Setup Complete!")
            st.info("""
            You have successfully:
            - Installed Physics Toolbox Sensor Suite
            - Configured all necessary sensor settings
            - Verified the recording and export functionality
            
            Your phone is now ready for data collection!
            """)
            
            # Added key "phone_start_over"
            if st.button("🔄 Start from Beginning", key="phone_start_over"):
                st.session_state.phone_step = 0
                st.rerun() 
    
    # Wrist Sensors Tab
    with tabs[1]:
        st.subheader("MetaSens Wrist Sensors")
        
        # Create progress tracking with only two steps
        steps = ["Install App", "Configure Sensors"]
        current_step = st.session_state.wrist_step
        
        # Show progress indicator if not completed
        if current_step < len(steps):
            # progress = st.progress(current_step / (len(steps) - 1))
            st.write(f"Current Step: {steps[current_step]}")
        
        # Step content with expanders
        if current_step == 0:
            with st.expander("📱 Installation Guide", expanded=True):
                st.markdown("""
                ### Getting Started
                Download the MetaWear app for your device:
                
                - [📱 iOS App Store](https://apps.apple.com/us/app/metawear/id1547334547)
                - [🤖 Google Play Store](https://play.google.com/store/apps/details?id=com.mbientlab.metawear.app)
                
                #### Installation Tips:
                - Ensure Bluetooth is enabled on your device
                - Allow necessary permissions when prompted
                - Check for minimum OS requirements
                """)
                
                if st.button("✅ Mark Installation Complete"):
                    st.session_state.wrist_step = 1
                    st.rerun()
                    
        elif current_step == 1:
            with st.expander("⚙️ Sensor Configuration", expanded=True):
                st.markdown("""
                ### Configure Your Sensors
                
                1. Open the MetaWear app
                2. Set sampling rates:
                - Accelerometer: 50Hz
                - Gyroscope: 50Hz
                3. Verify connection status
                4. Download csv files 
                """)
                
                if st.button("✅ Configuration Complete"):
                    st.session_state.wrist_step = 2
                    st.rerun()
        
        # Show completion card when all steps are done
        elif current_step == 2:
            st.success("🎉 Setup Complete!")
            st.info("You have successfully set up the wrist sensors and configured all necessary parameters.")
            
            # Add the start over button
            if st.button("🔄 Start from Beginning"):
                st.session_state.wrist_step = 0
                st.rerun()
    
    # eSense Tab
    with tabs[2]:
        st.subheader("eSense Earbuds")
        components.html(render_data_collection_html(), height=600)



# def load_header():
#     """Load and display the TEMPO header GIF"""
#     try:
#         # The path should match where you save the header GIF
#         header_path = Path("tempo_header.gif")
#         if not header_path.exists():
#             st.error("Header GIF not found. Please ensure 'tempo_header.gif' is in the application directory.")
#             return False
            
#         # Display the header with custom HTML to ensure proper sizing
#         st.markdown(
#             f"""
#             <div class="header-container">
#                 <img src="data:image/gif;base64,{get_base64_encoded_image(header_path)}"
#                      style="width: 100%; height: auto;">
#             </div>
#             """,
#             unsafe_allow_html=True
#         )
#         return True
#     except Exception as e:
#         st.error(f"Error loading header: {str(e)}")
#         return False

def get_base64_encoded_image(image_path):
    """Convert an image file to base64 encoding"""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode()

def home_page():
    """Render the home page with multiple header style options"""
    # Option 1: Modern Split Layout
    st.markdown("""
        <div class="header-modern">
            <div class="header-split">
                <div style="flex: 1;">
                    <h1 class="title-modern">TEMPO</h1>
                    <p class="subtitle-modern">Tracking and Estimating Motion for Patient Observation</p>
                </div>
                <div style="flex: 1; text-align: right;">
                    <img src="data:image/gif;base64,{}" class="header-image" style="max-width: 400px;">
                </div>
            </div>
            <div class="animated-border"></div>
        </div>
    """.format(get_base64_encoded_image("tempo_header.gif")), unsafe_allow_html=True)
    


    # Add the rest of the home page content
    st.markdown("<div style='margin-top: 2rem;'></div>", unsafe_allow_html=True)
    
    # Introduction text with enhanced styling
    st.markdown("""
        <div>
            <h2 style="color: #1a1a1a; margin-bottom: 1rem;">Advanced Motion Analysis Platform</h2>
            <p style="color: #444444; line-height: 1.6;">
                TEMPO combines cutting-edge wearable technology with sophisticated 3D pose estimation 
                to provide comprehensive motion analysis for medical professionals and researchers.
            </p>
                 **Key Features:**
    - Real-time motion tracking
    - Wearable device integration
    - 3D pose visualization
    - Data analysis and reporting
    
    Use the navigation menu to access different features of the application.
        </div>
    """, unsafe_allow_html=True)
    
    

    
    # Add some example visualizations or statistics for the homepage
    st.subheader("System Overview")
    col1, col2 = st.columns(2)
    
    with col1:
        st.info("📊 Data Processing Pipeline")
        st.markdown("""
        1. Collect wearable device data
        2. Process motion patterns
        3. Generate 3D pose estimation
        4. Analyze results
        """)
    
    with col2:
        st.info("🎯 Benefits")
        st.markdown("""
        - Accurate motion tracking
        - Real-time feedback
        - Comprehensive analysis
        - Patient progress monitoring
        """)

def data_analysis_page():
    """Render the data analysis page"""
    st.title("Data Analysis")
    tab1, tab2, tab3 = st.tabs(["Collect Device Data", "Upload Device Data", "3D Pose Video"])
    

    with tab1:
        create_sensor_section()
            
    with tab2:
        st.header("Device Data Upload")
        os.makedirs("1.rawdata", exist_ok=True)
        
        expected_files = [
            "leftgyroscopewatch",
            "leftaccelerometerwatch",
            "rightgyroscopewatch",
            "rightaccelerometerwatch",
            "phonedata",
            "earbuddata"
        ]
        
        uploaded_files = {}
        
        col1, col2 = st.columns(2)
        for i, file_name in enumerate(expected_files):
            with (col1 if i < 3 else col2):
                file = st.file_uploader(
                    f"Upload {file_name}.csv",
                    type=['csv'],
                    key=file_name
                )
                
                if file is not None:
                    file_path = os.path.join("1.rawdata", f"{file_name}.csv")
                    with open(file_path, "wb") as f:
                        f.write(file.getvalue())
                    uploaded_files[file_name] = file_path
                    st.success(f"✅ {file_name}.csv has been saved!")

        st.write("---")
        files_uploaded = len(uploaded_files) == len(expected_files)
        if st.button("Process Files", key="process_button", disabled=not files_uploaded):
            process_uploaded_files(uploaded_files)


    
    # 3D Pose Video Tab
    with tab3:
        st.header("3D Pose Video Analysis")
        
        # Get list of MP4 files in the current directory
        video_files = list(Path('.').glob('*.mp4'))
        if not video_files:
            st.warning("No MP4 files found in the current directory. Please add your videos to the same folder as this script.")
        else:
            # Create a dropdown to select from available videos
            selected_video = st.selectbox(
                "Select video file from current directory:",
                options=video_files,
                format_func=lambda x: x.name
            )
            
            if selected_video:
                try:
                    # Display the selected video
                    st.video(str(selected_video))
                    
                    # Add video information
                    video = cv2.VideoCapture(str(selected_video))
                    fps = video.get(cv2.CAP_PROP_FPS)
                    frame_count = int(video.get(cv2.CAP_PROP_FRAME_COUNT))
                    duration = frame_count/fps
                    
                    # Display video details in columns
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("FPS", f"{fps:.2f}")
                    with col2:
                        st.metric("Total Frames", frame_count)
                    with col3:
                        st.metric("Duration (seconds)", f"{duration:.2f}")
                    
    
                    
                except Exception as e:
                    st.error(f"Error processing video: {str(e)}")
                    st.info("Please ensure the video file is not corrupted and is a valid MP4 format.")




def process_uploaded_files(uploaded_files, output_dir='output/'):
    try:
        st.info("Processing started...")
        os.makedirs(output_dir, exist_ok=True) # Create output directory if it doesn't exist
        full_sensor_pipeline()
        st.success("Processing complete!")
        
    except Exception as e:
        st.error(f"Error during processing: {str(e)}")
        raise
    


def main():
    """Main function to run the Streamlit app"""
    # Create sidebar navigation
    st.sidebar.title("Navigation")
    page = st.sidebar.radio("Go to", ["Home", "Data Analysis"])
    
    # Display selected page
    if page == "Home":
        home_page()
    else:
        data_analysis_page()

if __name__ == "__main__":
    main()