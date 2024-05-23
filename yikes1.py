import streamlit as st
import pandas as pd
from io import StringIO

def load_and_clean_data(uploaded_file):
    try:
        uploaded_file.seek(0)
        lines = uploaded_file.readlines()

        start_line = find_header_start(lines)
        if start_line is None:
            st.error(f"Failed to find the header in {uploaded_file.name}. The file does not contain the expected data.")
            return None

        valid_lines = extract_valid_lines(lines[start_line:])
        if not valid_lines:
            st.error(f"No valid data found in {uploaded_file.name}.")
            return None

        data = create_dataframe(valid_lines)
        if data is None:
            return None

        data_cleaned = clean_data(data)
        return data_cleaned

    except Exception as e:
        st.error(f"Unexpected error while processing {uploaded_file.name}: {e}")
        return None

def find_header_start(lines):
    for i, line in enumerate(lines):
        if 'Player position' in line.decode('utf-8'):
            return i
    return None

def extract_valid_lines(lines, expected_fields=3):
    valid_lines = []
    for line in lines:
        decoded_line = line.decode('utf-8').strip()
        if len(decoded_line.split(',')) >= expected_fields:
            valid_lines.append(decoded_line)
    return valid_lines

def create_dataframe(valid_lines):
    try:
        return pd.read_csv(StringIO('\n'.join(valid_lines)), on_bad_lines='skip')
    except pd.errors.ParserError as e:
        st.error(f"Error parsing the data: {e}")
        return None

def clean_data(data):
    st.write("Debug: Original Columns:", data.columns)
    expected_columns = ['EventType', 'TimeStamp', 'EventData', 'Detail1', 'Detail2', 'Detail3', 'Detail4', 
                        'Detail5', 'Detail6', 'Detail7', 'Detail8', 'Detail9', 'Detail10', 'Detail11']
    column_count = len(data.columns)
    data.columns = expected_columns[:column_count]
    data_cleaned = data.dropna(axis=1, how='all')
    return data_cleaned

def calculate_approach_distances(data):
    player_positions = extract_player_positions(data)
    images_data = extract_images_data(data)

    merged_data = merge_data(player_positions, images_data)
    if merged_data is None:  # Handle invalid merged_data
        return pd.DataFrame(columns=['ImageType', 'Distance']) 

    previous_position, previous_direction = None, None
    approach_data = []

    for i in range(1, len(merged_data)):
        current_position = merged_data.iloc[i]['Position']
        if previous_position is not None:
            direction = determine_direction(current_position, previous_position)
            if previous_direction is not None and direction != previous_direction:
                image_type = (
                    merged_data.iloc[i - 1]['RightImageType']
                    if previous_direction == 'Right'
                    else merged_data.iloc[i - 1]['LeftImageType']
                )
                approach_data.append({'ImageType': image_type, 'Distance': previous_position})
            previous_direction = direction
        previous_position = current_position

    return pd.DataFrame(approach_data)  # Return a DataFrame
    
def extract_player_positions(data):
    player_positions = data[data['EventType'] == 'Player position']
    player_positions = player_positions[['TimeStamp', 'EventData']].rename(columns={'EventData': 'Position'})
    player_positions['Position'] = player_positions['Position'].astype(float)
    return player_positions

def extract_images_data(data):
    event_executed_data = data[data['EventType'] == 'Event Executed']
    right_image_data = event_executed_data[event_executed_data['EventData'] == 'RightImage']
    left_image_data = event_executed_data[event_executed_data['EventData'] == 'LeftImage']
    images_data = pd.concat([right_image_data, left_image_data]).sort_values(by='TimeStamp')
    st.write("Debug: Images Data Columns:", images_data.columns)
    return images_data

def merge_data(player_positions, images_data):
    try:
        # Check if Detail1 exists before using it
        if 'Detail1' in images_data.columns:
            merged_data = pd.merge_asof(
                player_positions.sort_values('TimeStamp'), 
                images_data.sort_values('TimeStamp'),
                on='TimeStamp', direction='backward', suffixes=('', '_image')
            )
            merged_data['RightImageType'] = merged_data['Detail1'].apply(lambda x: 'Spider' if 'Spider' in str(x) else 'Neutral')
            merged_data['LeftImageType'] = merged_data['Detail1'].apply(lambda x: 'Spider' if 'Spider' in str(x) else 'Neutral')
            return merged_data
        else:
            st.warning("The column 'Detail1' is missing from the images data in some files. These files will be excluded from the analysis.")
            return None

    except Exception as e:
        st.error(f"Error merging data: {e}")
        return None


def determine_direction(current_position, previous_position):
    return 'Right' if current_position > previous_position else 'Left'

def update_approach_distances(approach_distances, merged_data, i, previous_direction, previous_position):
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



def calculate_speed(current_position, previous_position, current_time, previous_time):
    time_diff = current_time - previous_time
    if time_diff == 0:
        return None
    return abs(current_position - previous_position) / time_diff

def determine_movement(merged_data, i, current_position, previous_position):
    direction = 'Right' if current_position > previous_position else 'Left'
    image_type = merged_data.iloc[i]['RightImageType'] if direction == 'Right' else merged_data.iloc[i]['LeftImageType']
    return direction, image_type

def process_file(uploaded_file):
    data_cleaned = load_and_clean_data(uploaded_file)
    if data_cleaned is None:
        return None, None

    approach_distances = calculate_approach_distances(data_cleaned)
    player_positions = extract_player_positions(data_cleaned)
    images_data = extract_images_data(data_cleaned)
    merged_data = merge_data(player_positions, images_data)
    speed_df = calculate_speed_and_direction(data_cleaned, merged_data) 

    return approach_distances, speed_df  # Return two DataFrames

def calculate_speed_and_direction(data, merged_data):
    if merged_data is None:
        return pd.DataFrame()

    speeds = []
    directions = []
    image_types = []

    for i in range(1, len(merged_data)):
        current_time = merged_data.iloc[i]['TimeStamp']
        previous_time = merged_data.iloc[i - 1]['TimeStamp']
        current_position = merged_data.iloc[i]['Position']
        previous_position = merged_data.iloc[i - 1]['Position']

        speed = calculate_speed(current_position, previous_position, current_time, previous_time)
        if speed is None:
            continue

        direction, image_type = determine_movement(merged_data, i, current_position, previous_position)

        speeds.append(speed)
        directions.append(direction)
        image_types.append(image_type)
        # Add direction to the merged_data DataFrame
        merged_data.at[i, 'Direction'] = direction

    return pd.DataFrame({'Speed': speeds, 'Direction': directions, 'ImageType': image_types})


def process_file(uploaded_file):
    data_cleaned = load_and_clean_data(uploaded_file)
    if data_cleaned is None:
        return None, None

    approach_distances = calculate_approach_distances(data_cleaned)
    player_positions = extract_player_positions(data_cleaned)
    images_data = extract_images_data(data_cleaned)
    merged_data = merge_data(player_positions, images_data)
    speed_df = calculate_speed_and_direction(data_cleaned, merged_data) 

    return approach_distances, speed_df  # Return two DataFrames

import streamlit as st
import pandas as pd
from io import StringIO

# ... (Your other functions remain the same)

st.title("Approach Distances and Speed Analysis")

with st.form("upload_form"):
    uploaded_files = st.file_uploader("Choose CSV files", accept_multiple_files=True, type="csv")
    submit_button = st.form_submit_button("Analyze Files")

    if submit_button and uploaded_files:  # Check if button clicked and files uploaded
        all_approach_results = []
        all_speed_results = []
        for uploaded_file in uploaded_files:
            st.write(f"Processing file: {uploaded_file.name}")
            approach_df, speed_df = process_file(uploaded_file)  # Unpack the returned DataFrames

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
