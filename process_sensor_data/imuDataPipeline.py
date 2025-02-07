from finalpipeline.phone_processor import PhoneSensorAligner
from finalpipeline.watch_processor import WatchSensorAligner
from finalpipeline.earbuds_processor import EarbudSensorAligner
from finalpipeline.rotation_processor import robust_rotation_matrices_dataframes
from finalpipeline.synchronise_dataframes import robust_synchronise_dataframes
from finalpipeline.csvtotensor import create_mobileposer_tensor
from finalpipeline.trim_timestamps import trim_dataframes

import os
import pandas as pd

def align_all_sensor_data(data_directory):
    # Initialize sensor aligners
    phone = PhoneSensorAligner()
    watch_aligner = WatchSensorAligner()
    earbuds_aligner = EarbudSensorAligner()

    # Load data files
    data_files = {
        'phone': os.path.join(data_directory, 'phonedata.csv'),
        'earbud': os.path.join(data_directory, 'earbuddata.csv'),
        'left_accel': os.path.join(data_directory, 'leftaccelerometerwatch.csv'),
        'left_gyro': os.path.join(data_directory, 'leftgyroscopewatch.csv'),
        'right_accel': os.path.join(data_directory, 'rightaccelerometerwatch.csv'),
        'right_gyro': os.path.join(data_directory, 'rightgyroscopewatch.csv')
    }

    # Read all CSV files
    try:
        phone_df = pd.read_csv(data_files['phone'])
        phone_df = phone_df.drop(columns=[col for col in phone_df.columns if 'Unnamed:' in col])
        earbud_df = pd.read_csv(data_files['earbud'])
        leftaccel_df = pd.read_csv(data_files['left_accel'])
        leftgyro_df = pd.read_csv(data_files['left_gyro'])
        rightaccel_df = pd.read_csv(data_files['right_accel'])
        rightgyro_df = pd.read_csv(data_files['right_gyro'])
    except FileNotFoundError as e:
        raise FileNotFoundError(f"Could not find required data file: {e.filename}")



    # Align sensor data
    phone_aligned_df = phone.align_sensor_data(phone_df)
    earbud_aligned_df = earbuds_aligner.align_sensor_data(earbud_df)
    left_watch_aligned_df = watch_aligner.align_sensor_data(leftaccel_df, leftgyro_df)
    right_watch_aligned_df = watch_aligner.align_sensor_data(rightaccel_df, rightgyro_df)

    return phone_aligned_df, earbud_aligned_df, left_watch_aligned_df, right_watch_aligned_df


def process_aligned_sensor_data(aligned_dfs, df_names=None):
    if df_names is None:
        df_names = ['Phone', 'Earbud', 'Left Watch', 'Right Watch']

    # Validate inputs
    if len(aligned_dfs) != len(df_names):
        raise ValueError(f"Number of dataframes ({len(aligned_dfs)}) must match number of names ({len(df_names)})")

    # Step 1: Trim dataframes
    print("\nTrimming dataframes...")
    trimmed_dfs_list = trim_dataframes(aligned_dfs, df_names)


    # Step 2: Calculate rotation matrices
    print("\nCalculating rotation matrices...")
    rotated_trimmed_dfs_list = robust_rotation_matrices_dataframes(trimmed_dfs_list)


    # Step 3: Synchronize dataframes
    print("\nSynchronizing dataframes...")
    synced_dfs = robust_synchronise_dataframes(rotated_trimmed_dfs_list, 
                                     df_names)


    # Step 4: Create MobilePoser tensor
    print("\nCreating MobilePoser tensor...")
    tensor = create_mobileposer_tensor(synced_dfs)

    return synced_dfs, tensor


def full_sensor_pipeline(data_dir='1.data/'):
    # Step 1: Align sensor data
    print("Aligning sensor data...")
    aligned_dfs = align_all_sensor_data(data_dir)

    # Step 2: Process aligned data
    df_names = ['Phone', 'Earbud', 'Left Watch', 'Right Watch']
    synced_dfs, tensor = process_aligned_sensor_data(aligned_dfs, df_names)

    return synced_dfs, tensor


# Example usage:
def main():
    try:
        # Run the full pipeline
        synced_dfs, tensor = full_sensor_pipeline()
        
        # Print final results
        print("\nFinal Processing Results:")
        print("------------------------")
        print(f"Tensor shape: {tensor.shape}")
        df_names = ['Phone', 'Earbud', 'Left Watch', 'Right Watch']
        for i, df in enumerate(synced_dfs):
            print(f"{df_names[i]} final shape: {df.shape}")
            
    except Exception as e:
        print(f"Error during processing: {str(e)}")
        raise

if __name__ == "__main__":
    main()