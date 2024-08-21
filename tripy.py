import pandas as pd
import streamlit as st
from datetime import datetime
import io

# Function to read files and rename columns
def read_file(uploaded_file):
    """Read uploaded file into a DataFrame."""
    if uploaded_file.name.endswith('.xlsx'):
        return pd.read_excel(uploaded_file)
    elif uploaded_file.name.endswith('.csv'):
        return pd.read_csv(uploaded_file)
    else:
        st.error("Unsupported file format")
        return pd.DataFrame()  # Return empty DataFrame if format is unsupported

def read_file_asin(uploaded_file):
    """Read uploaded file into a DataFrame and rename columns if applicable."""
    # Read the file into a DataFrame
    if uploaded_file.name.endswith('.xlsx'):
        df = pd.read_excel(uploaded_file)
    elif uploaded_file.name.endswith('.csv'):
        df = pd.read_csv(uploaded_file)
    else:
        st.error("Unsupported file format")
        return pd.DataFrame()  # Return empty DataFrame if format is unsupported
    
    # Define renaming dictionaries
    rename_dict_14_day = {
        '14 Day Total Sales (₹)': 'Total Sales',
        '14 Day Total Orders (#)': 'Total Orders',
        '14 Day Total Units (#)': 'Total Units'
    }
    
    rename_dict_7_day = {
        '7 Day Total Sales (₹)': 'Total Sales',
        '7 Day Total Units (#)': 'Total Units',
        '7 Day Total Orders (#)': 'Total Orders'
    }
    
    # Rename columns based on which rename_dict matches the DataFrame columns
    if all(col in df.columns for col in rename_dict_14_day.keys()):
        df.rename(columns=rename_dict_14_day, inplace=True)
    elif all(col in df.columns for col in rename_dict_7_day.keys()):
        df.rename(columns=rename_dict_7_day, inplace=True)
    else:
        st.warning("Expected columns not found. Returning the original DataFrame.")
    
    return df

def process_files(sp_file, sd_file, sb_file, asin_mapping, campaign_mapping, selected_date):
    """Process and merge the uploaded files."""
    
    # Read SP Files
    sp_dfs = [read_file_asin(file) for file in sp_file]
    sp_file_df = pd.concat(sp_dfs, ignore_index=True)
    
    # Read new data
    sd_dfs = [read_file_asin(file) for file in sd_file]
    sb_dfs = [read_file(file) for file in sb_file]

    # Concatenate all DataFrames for each file type
    sd_file_df = pd.concat(sd_dfs, ignore_index=True)
    sb_file_df = pd.concat(sb_dfs, ignore_index=True)

    # Add selected date
    selected_date_str = selected_date.strftime('%Y-%m-%d')
    for df in [sp_file_df, sd_file_df, sb_file_df]:
        df['Selected Date'] = selected_date_str

    # Map ASIN and generate summaries
    merged_data_SP = pd.merge(sp_file_df, asin_mapping, left_on='Advertised ASIN', right_on='ASIN', how='left')
    merged_data_SB = pd.merge(sb_file_df, campaign_mapping, left_on='Campaigns', right_on='SB Campaign Name', how='left')
    merged_data_SD = pd.merge(sd_file_df, asin_mapping, left_on='Advertised ASIN', right_on='ASIN', how='left')

    SP_summary = aggregate_data(merged_data_SP, {
        'Total Orders': 'sum',
        'Total Units': 'sum',
        'Total Sales': 'sum',
        'Spend': 'sum'
    })
    
    SB_summary = aggregate_data(merged_data_SB, {
        'Orders': 'sum',
        'Clicks': 'sum',
        'Sales(INR)': 'sum',
        'Spend(INR)': 'sum'
    })
    
    SD_summary = aggregate_data(merged_data_SD, {
        'Total Orders': 'sum',
        'Total Units': 'sum',
        'Total Sales': 'sum',
        'Spend': 'sum'
    })

    return SP_summary, SD_summary, SB_summary

def aggregate_data(df, agg_dict):
    """Aggregate data based on the provided dictionary."""
    if all(col in df.columns for col in agg_dict.keys()):
        return df.groupby(['Selected Date', 'Sub-Category']).agg(agg_dict).reset_index()
    else:
        st.error("One or more columns are missing for aggregation")
        return pd.DataFrame()  # Return empty DataFrame if columns are missing

def save_df_to_csv(df):
    """Save DataFrame to a CSV file in memory."""
    buffer = io.StringIO()
    df.to_csv(buffer, index=False)
    buffer.seek(0)
    return buffer

# Streamlit UI components
st.title("Data Processing and Upload")

selected_date = st.date_input(
    "Select a date:",
    value=datetime.today(),  # Default date
    min_value=datetime(2000, 1, 1),  # Minimum date
    max_value=datetime(2100, 12, 31)  # Maximum date
)

# Load mappings
ASIN_Mapping = pd.read_csv("ASIN_Mapping_Report.csv")
Campaign_Mapping = pd.read_csv("Campaign_Mapping.csv")

SP_file = st.file_uploader("Choose an SP file", type=["xlsx", "csv"], accept_multiple_files=True)
SD_file = st.file_uploader("Choose an SD file", type=["xlsx", "csv"], accept_multiple_files=True)
SB_file = st.file_uploader("Choose an SB file", type=["xlsx", "csv"], accept_multiple_files=True)

if st.button("Process"):
    SP_summary, SD_summary, SB_summary = process_files(
        SP_file,
        SD_file,
        SB_file,
        ASIN_Mapping,
        Campaign_Mapping,
        pd.Timestamp(selected_date)
    )

    # Save DataFrames to CSV files in memory
    SP_buffer = save_df_to_csv(SP_summary)
    SD_buffer = save_df_to_csv(SD_summary)
    SB_buffer = save_df_to_csv(SB_summary)

    st.success("Processing completed and files have been merged.")
    st.write("SP files have been updated and merged.")
    st.write("SD files have been updated and merged.")
    st.write("SB files have been updated and merged.")

    # Provide download links for the summary files
    st.download_button(
        label="Download Updated SP Summary",
        data=SP_buffer.getvalue(),
        file_name="SP_Summary.csv",
        mime="text/csv"
    )
    st.download_button(
        label="Download Updated SD Summary",
        data=SD_buffer.getvalue(),
        file_name="SD_Summary.csv",
        mime="text/csv"
    )
    st.download_button(
        label="Download Updated SB Summary",
        data=SB_buffer.getvalue(),
        file_name="SB_Summary.csv",
        mime="text/csv"
    )
else:
    st.warning("Please upload all required files (SP, SD, SB).")
