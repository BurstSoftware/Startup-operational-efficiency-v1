import streamlit as st
import pandas as pd
import pm4py
from pm4py.objects.conversion.log import converter as log_converter
from pm4py.algo.discovery.dfg import algorithm as dfg_discovery
from pm4py.visualization.dfg import visualizer as dfg_visualizer
import plotly.graph_objects as go
import io

# Streamlit app configuration
st.set_page_config(page_title="Startup Operational Efficiency Analyzer", layout="wide")
st.title("Startup Operational Efficiency Analyzer")
st.markdown("Analyze operational processes, detect bottlenecks, and optimize efficiency.")

# Sidebar for navigation
st.sidebar.header("Navigation")
page = st.sidebar.radio("Select Feature", ["Upload Data", "Process Analysis", "Cost Analysis", "Recommendations"])

# Initialize session state for data
if 'process_data' not in st.session_state:
    st.session_state.process_data = None
if 'financial_data' not in st.session_state:
    st.session_state.financial_data = None

# Function to load process data
def load_process_data(file):
    try:
        df = pd.read_excel(file)
        required_columns = ['case_id', 'activity', 'timestamp', 'resource', 'duration']
        if not all(col in df.columns for col in required_columns):
            st.error("File must contain columns: case_id, activity, timestamp, resource, duration")
            return None
        return df
    except Exception as e:
        st.error(f"Error loading file: {e}")
        return None

# Function to load financial data
def load_financial_data(file):
    try:
        df = pd.read_excel(file)
        required_columns = ['activity', 'cost']
        if not all(col in df.columns for col in required_columns):
            st.error("File must contain columns: activity, cost")
            return None
        return df
    except Exception as e:
        st.error(f"Error loading financial data: {e}")
        return None

# Function to detect bottlenecks
def detect_bottlenecks(df):
    bottlenecks = []
    avg_durations = df.groupby('activity')['duration'].mean().sort_values(ascending=False)
    for activity, duration in avg_durations.items():
        if duration > avg_durations.mean() + avg_durations.std():
            bottlenecks.append((activity, duration))
    return bottlenecks

# Function to create process log for pm4py
def create_process_log(df):
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    log = log_converter.apply(df.rename(columns={'case_id': 'case:concept:name', 'activity': 'concept:name', 'timestamp': 'time:timestamp'}))
    return log

# Function to generate Sankey diagram
def generate_sankey_diagram(df):
    activities = df['activity'].unique()
    label_map = {act: i for i, act in enumerate(activities)}
    source = []
    target = []
    value = []
    
    for case in df['case_id'].unique():
        case_df = df[df['case_id'] == case].sort_values('timestamp')
        for i in range(len(case_df) - 1):
            source.append(label_map[case_df.iloc[i]['activity']])
            target.append(label_map[case_df.iloc[i + 1]['activity']])
            value.append(1)
    
    fig = go.Figure(data=[go.Sankey(
        node=dict(
            pad=15,
            thickness=20,
            line=dict(color="black", width=0.5),
            label=list(activities),
        ),
        link=dict(
            source=source,
            target=target,
            value=value,
        )
    )])
    fig.update_layout(title_text="Process Flow Diagram", font_size=10)
    return fig

# Function to generate recommendations
def generate_recommendations(bottlenecks):
    recommendations = []
    for activity, duration in bottlenecks:
        recommendations.append(f"**{activity}**: High duration ({duration:.2f} units). Consider automation or resource reallocation.")
    return recommendations

# Page: Upload Data
if page == "Upload Data":
    st.header("Upload Process and Financial Data")
    
    st.subheader("Process Data")
    st.markdown("Upload an Excel file with columns: case_id, activity, timestamp, resource, duration")
    process_file = st.file_uploader("Choose process data file", type=["xlsx"])
    if process_file:
        st.session_state.process_data = load_process_data(process_file)
        if st.session_state.process_data is not None:
            st.success("Process data loaded successfully!")
            st.dataframe(st.session_state.process_data.head())
    
    st.subheader("Financial Data")
    st.markdown("Upload an Excel file with columns: activity, cost")
    financial_file = st.file_uploader("Choose financial data file", type=["xlsx"])
    if financial_file:
        st.session_state.financial_data = load_financial_data(financial_file)
        if st.session_state.financial_data is not None:
            st.success("Financial data loaded successfully!")
            st.dataframe(st.session_state.financial_data.head())

# Page: Process Analysis
elif page == "Process Analysis":
    st.header("Process Analysis")
    
    if st.session_state.process_data is None:
        st.warning("Please upload process data in the 'Upload Data' section.")
    else:
        df = st.session_state.process_data
        
        # Bottleneck Detection
        st.subheader("Bottleneck Detection")
        bottlenecks = detect_bottlenecks(df)
        if bottlenecks:
            st.write("Detected Bottlenecks:")
            for activity, duration in bottlenecks:
                st.write(f"- {activity}: Average duration {duration:.2f} units")
        else:
            st.write("No significant bottlenecks detected.")
        
        # Process Flow Visualization
        st.subheader("Process Flow Diagram")
        sankey_fig = generate_sankey_diagram(df)
        st.plotly_chart(sankey_fig, use_container_width=True)
        
        # Process Mining with pm4py
        st.subheader("Directly-Follows Graph (DFG)")
        log = create_process_log(df)
        dfg = dfg_discovery.apply(log)
        gviz = dfg_visualizer.apply(dfg, log=log)
        dfg_image = dfg_visualizer.matplotlib_view(gviz)
        
        # Display DFG
        st.image(dfg_image, caption="Directly-Follows Graph", use_column_width=True)

# Page: Cost Analysis
elif page == "Cost Analysis":
    st.header("Cost Analysis")
    
    if st.session_state.process_data is None or st.session_state.financial_data is None:
        st.warning("Please upload both process and financial data in the 'Upload Data' section.")
    else:
        process_df = st.session_state.process_data
        financial_df = st.session_state.financial_data
        
        # Merge process and financial data
        merged_df = process_df.merge(financial_df, on='activity', how='left')
        cost_summary = merged_df.groupby('activity').agg({'cost': 'sum', 'duration': 'mean'}).reset_index()
        
        st.subheader("Cost and Duration by Activity")
        st.dataframe(cost_summary)
        
        # Placeholder for Invoice Generator Integration
        st.subheader("Integration with Invoice Generator")
        st.markdown("This feature would integrate with the Invoice Generator to pull cost data dynamically. Currently, using uploaded financial data.")
        
        # Visualize cost distribution
        fig = go.Figure(data=[
            go.Bar(x=cost_summary['activity'], y=cost_summary['cost'], name='Cost'),
            go.Bar(x=cost_summary['activity'], y=cost_summary['duration'], name='Average Duration')
        ])
        fig.update_layout(barmode='group', title="Cost and Duration Comparison")
        st.plotly_chart(fig, use_container_width=True)

# Page: Recommendations
elif page == "Recommendations":
    st.header("Recommendations for Optimization")
    
    if st.session_state.process_data is None:
        st.warning("Please upload process data in the 'Upload Data' section.")
    else:
        df = st.session_state.process_data
        bottlenecks = detect_bottlenecks(df)
        recommendations = generate_recommendations(bottlenecks)
        
        if recommendations:
            st.write("Recommendations based on bottleneck analysis:")
            for rec in recommendations:
                st.markdown(rec)
        else:
            st.write("No recommendations at this time. Processes appear optimized.")
        
        st.markdown("**General Suggestions**:")
        st.write("- **Automation**: Implement RPA (Robotic Process Automation) for repetitive tasks.")
        st.write("- **Training**: Enhance resource skills for high-duration activities.")
        st.write("- **Process Redesign**: Simplify workflows by removing redundant steps.")

# Footer
st.sidebar.markdown("---")
st.sidebar.markdown("Built with Streamlit, pm4py, pandas, and Plotly")
st.sidebar.markdown("© 2025 Startup Operational Efficiency Analyzer")
