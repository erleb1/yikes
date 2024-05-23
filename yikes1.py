import streamlit as st
import pandas as pd
from io import StringIO

def load_and_clean_data(uploaded_file):
    uploaded_file.seek(0)
    lines = uploaded_file.readlines()
    
    # Find the start line with 'Player position'
    start_line = 0
    found_header = False
    for i, line in enumerate(lines):
        if 'Player position' in line.decode('utf-8'):
            start_line = i
            found_header = True
            break

    if not found_header:
        st.error(f"Failed to find the header in {uploaded_file.name}. The file does not contain the expected data.")
        return None

    # Prepare valid lines by skipping lines with incorrect number of fields
    valid_lines = []
    expected_fields = 3  # Adjust this based on the actual minimum number of expected fields
    for line in lines[start_line:]:
        decoded_line = line.decode('utf-8').strip()
        if len(decoded_line.split(',')) >= expected_fields:
            valid_lines.append(decoded_line)
    
    # Create a DataFrame from the valid lines
    if not valid_lines:
        st.error(f"No valid data found in {uploaded_file.name}.")
        return None

    try:
        data = pd.read_csv(StringIO('\n'.join(valid_lines)))
    except pd.errors.ParserError as e:
        st.error(f"Error parsing {uploaded_file.name}: {e}")
        return None

    expected_columns = ['EventType', 'TimeStamp', 'EventData', 'Detail1', 'Detail2', 'Detail3', 'Detail4', 
                        'Detail5', 'Detail6', 'Detail7', 'Detail8', 'Detail9', 'Detail10', 'Detail11']
    
    # Dynamically adjust column renaming
    column_count = len(data.columns)
    data.columns = expected_columns[:column_count]
    data_cleaned = data.dropna(axis=1, how='all')
    return data_cleaned

def calculate_approach_distances(data):
    approach_distances = {'Spider': [], 'Neutral': []}
    
    player_positions = data[data['EventType'] == 'Player position']
    player_positions = player_positions[['TimeStamp', 'EventData']].rename(columns={'EventData': 'Position'})
    player_positions['Position'] = player_positions['Position'].astype(float)
    
    event_executed_data = data[data['EventType'] == 'Event Executed']
    right_image_data = event_executed_data[event_executed_data['EventData'] == 'RightImage']
    left_image_data = event_executed_data[event_executed_data['EventData'] == 'LeftImage']
    images_data = pd.concat([right_image_data, left_image_data]).sort_values(by='TimeStamp')

    merged_data = pd.merge_asof(player_positions.sort_values('TimeStamp'), images_data.sort_values('TimeStamp'),
                                on='TimeStamp', direction='backward', suffixes=('', '_image'))

    merged_data['RightImageType'] = merged_data['Detail1'].apply(lambda x: 'Spider' if 'Spider' in str(x) else 'Neutral')
    merged_data['LeftImageType'] = merged_data['Detail1'].apply(lambda x: 'Spider' if 'Spider' in str(x) else 'Neutral')

    previous_position = None
    previous_direction = None

    for i in range(1, len(merged_data)):
        current_position = merged_data.iloc[i]['Position']
        if previous_position is not None:
            direction = 'Right' if current_position > previous_position else 'Left'
            if previous_direction is not None and direction != previous_direction:
                if previous_direction == 'Right' and previous_position > 0.5:
                    if merged_data.iloc[i-1]['RightImageType'] == 'Spider':
                        approach_distances['Spider'].append(previous_position)
                    else:
                        approach_distances['Neutral'].append(previous_position)
                elif previous_direction == 'Left' and previous_position < 0.5:
                    if merged_data.iloc[i-1]['LeftImageType'] == 'Spider':
                        approach_distances['Spider'].append(previous_position)
                    else:
                        approach_distances['Neutral'].append(previous_position)
            previous_direction = direction
        previous_position = current_position
    
    return approach_distances

def calculate_speed_and_direction(data):
    speeds = []
    directions = []
    image_types = []

    player_positions = data[data['EventType'] == 'Player position']
    player_positions = player_positions[['TimeStamp', 'EventData']].rename(columns={'EventData': 'Position'})
    player_positions['Position'] = player_positions['Position'].astype(float)

    event_executed_data = data[data['EventType'] == 'Event Executed']
    right_image_data = event_executed_data[event_executed_data['EventData'] == 'RightImage']
    left_image_data = event_executed_data[event_executed_data['EventData'] == 'LeftImage']
    images_data = pd.concat([right_image_data, left_image_data]).sort_values(by='TimeStamp')

    merged_data = pd.merge_asof(player_positions.sort_values('TimeStamp'), images_data.sort_values('TimeStamp'),
                                on='TimeStamp', direction='backward', suffixes=('', '_image'))

    merged_data['RightImageType'] = merged_data['Detail1'].apply(lambda x: 'Spider' if 'Spider' in str(x) else 'Neutral')
    merged_data['LeftImageType'] = merged_data['Detail1'].apply(lambda x: 'Spider' if 'Spider' in str(x) else 'Neutral')

    for i in range(1, len(merged_data)):
        current_time = merged_data.iloc[i]['TimeStamp']
        previous_time = merged_data.iloc[i-1]['TimeStamp']
        current_position = merged_data.iloc[i]['Position']
        previous_position = merged_data.iloc[i-1]['Position']
        
        time_diff = current_time - previous_time
        if time_diff == 0:
            continue
        speed = abs(current_position - previous_position) / time_diff

        if current_position > previous_position:
            direction = 'Right'
            image_type = merged_data.iloc[i]['RightImageType']
        else:
            direction = 'Left'
            image_type = merged_data.iloc[i]['LeftImageType']
        
        speeds.append(speed)
        directions.append(direction)
        image_types.append(image_type)
    
    results = pd.DataFrame({
        'Speed': speeds,
        'Direction': directions,
        'ImageType': image_types
    })
    
    return results

def process_file(uploaded_file):
    data_cleaned = load_and_clean_data(uploaded_file)
    if data_cleaned is None:
        return None, None
    
    approach_distances = calculate_approach_distances(data_cleaned)
    approach_df = pd.DataFrame({
        'Distance': approach_distances['Spider'] + approach_distances['Neutral'],
        'ImageType': ['Spider'] * len(approach_distances['Spider']) + ['Neutral'] * len(approach_distances['Neutral'])
    })
    
    speed_df = calculate_speed_and_direction(data_cleaned)
    
    return approach_df, speed_df

st.title("Approach Distances and Speed Analysis")

uploaded_files = st.file_uploader("Choose CSV files", accept_multiple_files=True, type="csv")

if uploaded_files:
    all_approach_results = []
    all_speed_results = []
    for uploaded_file in uploaded_files:
        st.write(f"Processing file: {uploaded_file.name}")
        approach_df, speed_df = process_file(uploaded_file)
        
        if approach_df is None or speed_df is None:
            st.error(f"Failed to process file: {uploaded_file.name}")
            continue
        
        st.write("Approach Distance Analysis:")
        st.write(approach_df.groupby('ImageType').describe())
        all_approach_results.append(approach_df)
        
        st.write("Speed Analysis:")
        st.write(speed_df.groupby(['Direction', 'ImageType']).describe())
        all_speed_results.append(speed_df)
    
    if all_approach_results and all_speed_results:
        final_approach_df = pd.concat(all_approach_results)
        final_speed_df = pd.concat(all_speed_results)
        
        st.write("Combined Approach Distance Results:")
        st.write(final_approach_df.groupby('ImageType').describe())
        
        st.write("Combined Speed Results:")
        st.write(final_speed_df.groupby(['Direction', 'ImageType']).describe())
