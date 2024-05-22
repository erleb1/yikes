import streamlit as st
import pandas as pd

def load_and_clean_data(file):
    # Attempt to load data, skip rows that do not match the expected format
    for i in range(5):
        try:
            data = pd.read_csv(file, skiprows=i)
            if 'Player position' in data.columns[0]:
                break
        except pd.errors.ParserError:
            continue

    # Rename columns for better understanding
    data.columns = ['EventType', 'TimeStamp', 'EventData', 'Detail1', 'Detail2', 'Detail3', 'Detail4', 
                    'Detail5', 'Detail6', 'Detail7', 'Detail8', 'Detail9', 'Detail10', 'Detail11']
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

def process_file(file):
    data_cleaned = load_and_clean_data(file)
    
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
