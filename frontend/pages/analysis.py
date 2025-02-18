import streamlit as st # type: ignore
import cv2 # type: ignore
import os
from pathlib import Path
from process_sensor_data.imuDataPipeline import full_sensor_pipeline
############# DATA ANALYSIS PAGE ######################

def data_analysis_page():
    st.markdown("""
        <style>
        .upload-section {
            margin: 1rem 0;
        }
        
        .metric-container {
            background: white;
            padding: 1rem;
            border-radius: 4px;
            box-shadow: 0 1px 2px rgba(0,0,0,0.1);
            text-align: center;
        }
        
        .metric-value {
            font-size: 1.2em;
            font-weight: bold;
            color: #333;
        }
        
        .metric-label {
            color: #666;
            margin-top: 0.5rem;
        }
        
        /* Clean up tab styling */
        .stTabs [data-baseweb="tab-list"] {
            gap: 0.5rem;
        }
        
        .stTabs [data-baseweb="tab"] {
            padding: 0.5rem 1rem;
        }
        </style>
    """, unsafe_allow_html=True)

    # Display title using home page style
    st.markdown("""
    <style>
    .tempo-title {
        font-family: 'Arial', sans-serif;
        font-size: 3.5em;
        font-weight: bold;
        background: linear-gradient(to right, #2c3e50, #3498db);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 20px;
        padding: 10px;
    }
    
    </style>
    
    <div class="tempo-title">Data Analysis</div>
    """, unsafe_allow_html=True)

    # Create tabs with minimal styling
    tabs = st.tabs([
        "📱 Collect Device Data",
        "📤 Upload Device Data",
        "🎥 3D Pose Video"
    ])

    with tabs[0]:
        create_sensor_section()

    with tabs[1]:
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
        
        # Create two columns for file uploaders
        col1, col2 = st.columns(2)
        
        # Helper function to create minimal file upload section
        def create_file_upload_section(file_name):
            st.markdown(f"#### {file_name}.csv")
            file = st.file_uploader(
                "Upload CSV file",
                type=['csv'],
                key=file_name,
                label_visibility="collapsed"
            )
            
            if file is not None:
                if file.name.lower().replace('.csv', '') == file_name:
                    file_path = os.path.join("1.rawdata", f"{file_name}.csv")
                    with open(file_path, "wb") as f:
                        f.write(file.getvalue())
                    uploaded_files[file_name] = file_path
                    st.success("✅ File uploaded successfully")
                else:
                    st.error(f"Please upload '{file_name}.csv'")
            return file
        
        # Distribute file uploaders between columns
        for i, file_name in enumerate(expected_files):
            with (col1 if i < 3 else col2):
                create_file_upload_section(file_name)

        # Process button section
        st.divider()
        files_uploaded = len(uploaded_files) == len(expected_files)
        
        if not files_uploaded:
            st.info("Please upload all required files before processing")
        
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            if st.button(
                "Process Files",
                key="process_button",
                disabled=not files_uploaded,
                use_container_width=True
            ):
                process_uploaded_files(uploaded_files)

    with tabs[2]:
        st.header("3D Pose Video Analysis")
        
        video_files = list(Path('.').glob('*.mp4'))
        if not video_files:
            st.warning("No MP4 files found in the current directory.")
        else:
            selected_video = st.selectbox(
                "Select video file:",
                options=video_files,
                format_func=lambda x: x.name
            )
            
            if selected_video:
                try:
                    # Create two columns for video and stats
                    video_col, stats_col = st.columns([1, 1])
                    
                    with video_col:
                        # Video display
                        st.video(str(selected_video))
                    
                    with stats_col:
                        # Get video information
                        video = cv2.VideoCapture(str(selected_video))
                        fps = video.get(cv2.CAP_PROP_FPS)
                        frame_count = int(video.get(cv2.CAP_PROP_FRAME_COUNT))
                        duration = frame_count/fps
                        
                        st.subheader("Video Statistics")
                        
                        # Display metrics vertically in the stats column
                        st.metric("FPS", f"{fps:.2f}")
                        st.metric("Total Frames", frame_count)
                        st.metric("Duration", f"{duration:.2f} seconds")
                        
                        # Additional information
                        st.divider()
                        st.subheader("Analysis Results")
                        st.info("Select options below to analyze the video:")
                        
                        # # Add some example analysis options
                        # analysis_type = st.selectbox(
                        #     "Choose Analysis Type",
                        #     ["Joint Angles", "Movement Speed", "Motion Path", "Pose Accuracy"]
                        # )
                        
                        # if st.button("Run Analysis", use_container_width=True):
                        #     st.info("Analysis feature coming soon!")
                    
                except Exception as e:
                    st.error(f"Error processing video: {str(e)}")
                    st.info("Please ensure the video file is not corrupted and is a valid MP4 format.")




def create_sensor_section():
    st.header("Data Collection Hub")
    st.write("Connect and manage your sensor devices in one place. Follow the guided steps for each device.")
    
    #Session state for tracking progress initialised 
    if 'wrist_step' not in st.session_state:
        st.session_state.wrist_step = 0
    if 'phone_step' not in st.session_state:
        st.session_state.phone_step = 0
    if 'esense_step' not in st.session_state:
        st.session_state.esense_step = 0
    
    # Phone Sensors Expander
    with st.expander("📱 Phone Sensors", expanded=False):
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
    
    # Wrist Sensors Expander
    with st.expander("⌚ Wrist Sensors", expanded=False):
        st.subheader("MetaSens Wrist Sensors")
        
        # Create progress tracking with only two steps
        steps = ["Install App", "Configure Sensors"]
        current_step = st.session_state.wrist_step
        
        # Show progress indicator if not completed
        if current_step < len(steps):
            st.write(f"Current Step: {steps[current_step]}")
        
        # Step content 
        if current_step == 0:
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
    
    # eSense Expander
    with st.expander("🎧 eSense Earbuds", expanded=False):
        st.subheader("eSense Earbuds")
        
        # Create progress tracking with steps
        steps = ["Web App Setup", "Link to Data Collection"]
        current_step = st.session_state.esense_step
        
        # Show progress indicator if not completed
        if current_step < len(steps):
            st.progress(current_step / (len(steps) - 1))
            st.write(f"Current Step: {steps[current_step]}")
        
        # Step 1: Web App Introduction
        if current_step == 0:
            st.markdown("""
            ### eSense Data Recording Web App
            
            eSense can record data using our specialized web application:
            
            #### Key Features:
            - Real-time sensor data collection
            - Compatible with eSense earbuds
            - Seamless data export
            
            #### Getting Started:
            1. Ensure your eSense earbuds are charged
            2. Have Bluetooth enabled on your device
            3. Prepare for data collection
            """)
            
            if st.button("✅ Web App Setup Complete"):
                st.session_state.esense_step = 1
                st.rerun()
        
        # Step 2: Link to Data Collection
        elif current_step == 1:
            st.markdown("""
            ### Link to Data Collection
            
            You are now ready to proceed to the data collection page:
            
            - Ensure eSense earbuds are paired
            - Check Bluetooth connectivity
            - Prepare your recording environment
            """)
            
            if st.button("🎧 Launch eSense Data Collection Web Application"):
                st.switch_page("pages/esens_collection.py")
                # Here you would typically use st.switch_page() or navigate to the data collection page
                st.success("Redirecting to Data Collection Page...")
                # Placeholder for page navigation
                # st.switch_page("pages/data_collection.py")  # Uncomment if using multi-page app
                st.session_state.esense_step = 2
                st.rerun()
        
        # Completion Card
        elif current_step == 2:
            st.success("🎉 eSense Setup Complete!")
            st.info("""
            You have successfully:
            - Set up the eSense Web App
            - Prepared for data collection
            
            Your eSense earbuds are ready for recording!
            """)
            
            if st.button("🔄 Start from Beginning"):
                st.session_state.esense_step = 0
                st.rerun()



def process_uploaded_files(uploaded_files, output_dir='output/'):
    try:
        st.info("Processing start...")
        full_sensor_pipeline()
 
        st.success("Processing complete!")
        
    except Exception as e:
        st.error(f"Error during processing: {str(e)}")
        raise
    