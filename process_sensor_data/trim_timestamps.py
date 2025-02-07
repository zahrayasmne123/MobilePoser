def time_to_ms(time_str):
   hours, minutes, seconds, ms = map(int, time_str.split(':'))
   return ((hours * 60 + minutes) * 60 + seconds) * 1000 + ms


def trim_dataframes(dataframes, df_names):
   # Check for missing timestamp column and invalid dataframes
   valid_dfs = []
   valid_names = []
   for df, name in zip(dataframes, df_names):
       if df is None:
           print(f"{name} dataframe is None - skipping")
           continue
       

       df = df.copy()  # Create copy to ensure modifications persist
       if 'time' in df.columns:
            df = df.rename(columns={'time': 'timestamp'})

       if 'timestamp' not in df.columns:
           print("\nDEBUG INFO:")
           for df, name in zip(dataframes, df_names):
            if df is None:
                print(f"{name} is None")
                continue

            print(f"\n{name} columns:", df.columns.tolist())
            print(f"{name} first few rows:\n", df.head())
           print(f"{name} missing timestamp column - skipping")
           continue
       
       valid_dfs.append(df)
       valid_names.append(name)
   
   if not valid_dfs:
       print("No valid dataframes to trim")
       return []
       
   # Add milliseconds for comparison
   for df in valid_dfs:
       df['time_ms'] = df['timestamp'].apply(time_to_ms)
   
   latest_start_ms = max(df['time_ms'].min() for df in valid_dfs)
   earliest_end_ms = min(df['time_ms'].max() for df in valid_dfs)
   
   trimmed_dfs = []
   for df, name in zip(valid_dfs, valid_names):
       trimmed_df = df[
           (df['time_ms'] >= latest_start_ms) & 
           (df['time_ms'] <= earliest_end_ms)
       ].copy()
       trimmed_df = trimmed_df.drop('time_ms', axis=1)
       trimmed_dfs.append(trimmed_df)
       
       print(f"\nProcessed {name}:")
       print(f"Original rows: {len(df)}")
       print(f"Trimmed rows: {len(trimmed_df)}")
       print(f"Start time: {trimmed_df['timestamp'].iloc[0]}")
       print(f"End time: {trimmed_df['timestamp'].iloc[-1]}")
       
   return trimmed_dfs
