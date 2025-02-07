import pandas as pd
class WatchSensorAligner:
    """
    A class to handle watch sensor data alignment and adjustments.
    Provides methods to clean, standardize timestamp formats, and merge accelerometer
    and gyroscope data into a single file.
    """
    

    def __init__(self):
       self.timestamp_columns = ['timestamp (+0000)', 'timestamp']
       self.epoch_columns = ['epoc (ms)', 'epoch']
       self.elapsed_columns = ['elapsed (s)']
       self.expected_columns = {
           'accel': ['x-axis (g)', 'y-axis (g)', 'z-axis (g)'],
           'gyro': ['x-axis (deg/s)', 'y-axis (deg/s)', 'z-axis (deg/s)']
       }

    def process_timestamp(self, df):
       if df is None:
           return None
           
       timestamp_col = next((col for col in self.timestamp_columns if col in df.columns), None)
       
       if timestamp_col:
           try:
               df['timestamp'] = df[timestamp_col].apply(
                   lambda ts: ts.split('T')[1].replace('.', ':').split('+')[0]
               )
               
               drop_cols = (
                   [timestamp_col] + 
                   [col for col in self.epoch_columns if col in df.columns] +
                   [col for col in self.elapsed_columns if col in df.columns]
               )
               df = df.drop(columns=drop_cols)
               
               cols = ['timestamp'] + [col for col in df.columns if col != 'timestamp']
               df = df[cols]
               
               return df
               
           except Exception as e:
               print(f"Error processing timestamps: {e}")
               return None
       else:
           print(f"No timestamp column found. Expected one of: {self.timestamp_columns}")
           return None

    def align_sensor_data(self, accel_df, gyro_df):
       if accel_df is None or gyro_df is None:
           return None
           
       try:
           accel_df = self.process_timestamp(accel_df)
           gyro_df = self.process_timestamp(gyro_df)
           
           if accel_df is None or gyro_df is None:
               return None
           
           merged_df = pd.merge(accel_df, gyro_df, on='timestamp', how='inner')
           merged_df = merged_df.sort_values('timestamp')
           
           desired_cols = ['timestamp'] + self.expected_columns['accel'] + self.expected_columns['gyro']
           merged_df = merged_df[desired_cols]
           
           return merged_df
           
       except Exception as e:
           print(f"Error merging sensor data: {e}")
           return None
       
    
    def validate_data(self, df, sensor_type):
        if not isinstance(df, pd.DataFrame):
            return False
            
        timestamp_col = next((col for col in self.timestamp_columns if col in df.columns), None)
        if not timestamp_col:
            print(f"Missing required timestamp column. Expected one of: {self.timestamp_columns}")
            return False
            
        expected_cols = self.expected_columns[sensor_type]
        missing_cols = [col for col in expected_cols if col not in df.columns]
        if missing_cols:
            print(f"Watch Missing required {sensor_type} columns: {missing_cols}")
            return False
            
        return True
       
    