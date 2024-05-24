import streamlit as st
import pandas as pd
from io import StringIO
import re

def clean_raw_data(rawdata):
    # Remove non-printable characters
    cleaned_data = re.sub(b'[\x00-\x1F\x7F-\x9F]', b'', rawdata)
    # Normalize line endings to '\n'
    cleaned_data = cleaned_data.replace(b'\r\n', b'\n').replace(b'\r', b'\n')
    return cleaned_data

def load_and_clean_data(uploaded_file):
    encodings = ['utf-8', 'latin1', 'iso-8859-1', 'cp1252', 'cp1251']
    for encoding in encodings:
        try:
            rawdata = uploaded_file.read()
            cleaned_data = clean_raw_data(rawdata)
            decoded_data = cleaned_data.decode(encoding)
            df = pd.read_csv(StringIO(decoded_data), on_bad_lines='skip')

            # Drop columns with all missing values (NaN)
            df = df.dropna(axis=1, how='all')

            # Standardize column names
            expected_columns = ['EventType', 'TimeStamp', 'EventData', 'Detail1', 'Detail2', 'Detail3', 'Detail4',
                                'Detail5', 'Detail6', 'Detail7', 'Detail8', 'Detail9', 'Detail10', 'Detail11']
            column_count = len(df.columns)  # Adjust columns based on actual data
            df.columns = expected_columns[:column_count]

            # Data validation
            st.write("Data after cleaning:")
            st.write(df)
            return df
        except (UnicodeDecodeError, pd.errors.EmptyDataError, IndexError) as e:
            st.warning(f"Trying next encoding due to error: {e}")

    st.error(f"Failed to decode file {uploaded_file.name} with common encodings.")
    return None
    
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
    st.write("Debug: Player positions columns:", player_positions.columns)  # Debugging line
    st.write("Debug: Images data columns:", images_data.columns)           # Debugging line

    try:
        if 'Detail1' in images_data.columns:
            merged_data = pd.merge_asof(
                player_positions.sort_values('TimeStamp'),
                images_data.sort_values('TimeStamp'),
                on='TimeStamp', direction='backward', suffixes=('', '_image')
            )
            merged_data['RightImageType'] = merged_data['Detail1'].apply(lambda x: 'Spider' if 'Spider' in str(x) else 'Neutral')
            merged_data['LeftImageType'] = merged_data['Detail1'].apply(lambda x: 'Spider' if 'Spider' in str(x) else 'Neutral')

            if merged_data.empty:
                st.error("Merged data is empty after merge_asof!")
                return None
            else:
                return merged_data
        else:
            st.warning("The column 'Detail1' is missing from the images data in some files. These files will be excluded from the analysis.")
            return None

    except Exception as e:
        st.error(f"Error merging data: {e}")
        return None

def determine_direction(current_position, previous_position):
    return 'Right' if current_position > previous_position else 'Left'

def calculate_speed(current_position, previous_position, current_time, previous_time):
    time_diff = current_time - previous_time
    if time_diff == 0:
        return None
    return abs(current_position - previous_position) / time_diff

def determine_movement(merged_data, i, current_position, previous_position):
    direction = 'Right' if current_position > previous_position else 'Left'
    image_type = merged_data.iloc[i]['RightImageType'] if direction == 'Right' else merged_data.iloc[i]['LeftImageType']
    return direction, image_type

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

    if merged_data is None:
        st.error("Merged data is invalid, skipping speed calculation")
        return approach_distances, None

    speed_df = calculate_speed_and_direction(data_cleaned, merged_data)

    if 'Direction' not in merged_data.columns:
        st.error("Direction column is missing after calculation!")

    return approach_distances, speed_df

# Streamlit app setup
st.title("Approach Distances and Speed Analysis")

with st.form("upload_form"):
    uploaded_files = st.file_uploader("Choose CSV files", accept_multiple_files=True, type="csv")
    submit_button = st.form_submit_button("Analyze Files")

    if submit_button and uploaded_files:
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
