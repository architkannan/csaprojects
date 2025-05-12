import streamlit as st
import pandas as pd
from bs4 import BeautifulSoup
import datetime
import unicodedata

# Set page configuration
st.set_page_config(layout="wide", page_title="CSA Projects and Tasks Dashboard")

st.markdown(
    """
    <style>
    /* Target the first column in a horizontal block and add a right border */
    [data-testid="stHorizontalBlock"] > div:nth-child(1) {
        border-right: 1px solid #ccc;
        padding-right: 15px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# --------------------------
# Load Data
# --------------------------
# Load the CSV files (ensure these files are in the same directory as this script)
projects_df = pd.read_csv(
    "Project_Snip.csv",
    encoding="ISO-8859-1",
)
tasks_df = pd.read_csv(
    "Task_Snip.csv",
    encoding="ISO-8859-1",
    na_values=["n.a"],
)

tasks_df["Project Key"] = tasks_df["Project Key"].replace(r"^\s*$", pd.NA, regex=True)


# --------------------------
# Normalize the Project ID column
# --------------------------
def normalize_str(s):
    return unicodedata.normalize("NFC", str(s)).strip()


projects_df["Project ID Clean"] = projects_df["Project ID"].apply(normalize_str)


# --------------------------
# Clean Task Description HTML tags using BeautifulSoup
# --------------------------
def clean_html(text):
    if pd.isna(text):
        return text
    return BeautifulSoup(text, "html.parser").get_text()


tasks_df["Task Description"] = tasks_df["Task Description"].apply(clean_html)

# --------------------------
# Standardize Task Subject for Filtering
# --------------------------
tasks_df["Task Subject Clean"] = tasks_df["Task Subject"].astype(str).str.strip()


# --------------------------
# Parse Dates in Projects
# --------------------------
def parse_date(date_str):
    try:
        if date_str != "Date not recorded":
            return pd.to_datetime(date_str, errors="coerce")
        else:
            return None
    except Exception:
        return None


projects_df["Expected Start Date Parsed"] = projects_df["Expected Start Date"].apply(
    parse_date
)
projects_df["Expected End Date Parsed"] = projects_df["Expected End Date"].apply(
    parse_date
)

# --------------------------
# Title and Dashboard Introduction Note
# --------------------------
st.title("Projects and Tasks Dashboard")
st.markdown(
    """
    
    This interactive dashboard allows you to explore projects and their associated tasks. Here’s how to get started:
    
    - **Filters:**  
      Use the sidebar to filter by a project name, filter by tasks, or also refine your results based on project status, priority, and dates.
      
    - **Projects View (Left Column):**  
      Click on a project to expand and view its detailed information including status, start/end dates, priority, and more.
      These are ordered alphabetically by project name. 
      
    - **Tasks View (Right Column):**  
      Explore tasks grouped by their relationship (parent tasks and subtasks). Click on a task to view additional details.
      These are ordered in descending order by Task ID (i.e. ordered by most recent task).
    
    *Whenever you select a project, you will be able to see the specific tasks mapped to that project. Similarly, when you select a task, you will see the project it is associated with.*
    
    Simply select the filters that apply to you and click on the expanders for more information. Enjoy exploring the dashboard!
    """
)

# --------------------------
# Sidebar Global & Project Filters
# --------------------------
st.sidebar.header("Project & Task Filters")

# Global Filter: Project ID selection
global_project_ids = projects_df["Project ID Clean"].dropna().unique().tolist()
global_project_ids.sort()
global_project_selection = st.sidebar.selectbox(
    "Filter by Project Name",
    options=["All"] + global_project_ids,
    key="global_project_selection",
)

# Global Filter: Task selection using a combined label (format: "TaskID | Task Subject")
tasks_df["Task Filter Label"] = tasks_df.apply(
    lambda row: f"{row['Task ID']} | {row['Task Subject Clean']}", axis=1
)
task_filter_options = tasks_df["Task Filter Label"].dropna().unique().tolist()
task_filter_options.sort(reverse=True)
global_task_filter = st.sidebar.selectbox(
    "Filter by Task", options=["All"] + task_filter_options, key="global_task_filter"
)

# --------------------------
# Determine Global Project Keys based on filters
# --------------------------
if global_project_selection != "All":
    project_keys_from_project = (
        projects_df.loc[
            projects_df["Project ID Clean"] == global_project_selection, "Project Key"
        ]
        .dropna()
        .unique()
        .tolist()
    )
else:
    project_keys_from_project = projects_df["Project Key"].dropna().unique().tolist()

if global_task_filter != "All":
    # Extract and normalize the selected task ID
    selected_task_id = global_task_filter.split(" | ")[0].strip()
    tasks_df["Task ID Normalized"] = (
        tasks_df["Task ID"].astype(str).str.strip().str.lower()
    )
    project_keys_from_task = (
        tasks_df.loc[
            tasks_df["Task ID Normalized"] == selected_task_id.lower(), "Project Key"
        ]
        .dropna()
        .unique()
        .tolist()
    )
else:
    project_keys_from_task = tasks_df["Project Key"].dropna().unique().tolist()

if global_project_selection != "All" and global_task_filter != "All":
    global_project_keys = list(
        set(project_keys_from_project).intersection(set(project_keys_from_task))
    )
elif global_project_selection != "All":
    global_project_keys = project_keys_from_project
elif global_task_filter != "All":
    global_project_keys = project_keys_from_task
else:
    global_project_keys = projects_df["Project Key"].dropna().unique().tolist()

# Clean the global_project_keys to remove any unwanted index prefixes (e.g., "0:")
global_project_keys = [key.split(":", 1)[-1].strip() for key in global_project_keys]
st.sidebar.write("Cleaned Global Project Key(s):", global_project_keys)

# Projects view additional filters
project_status_options = projects_df["Status"].dropna().unique().tolist()
selected_status = st.sidebar.multiselect(
    "Filter by Project Status", options=project_status_options
)

project_priority_options = projects_df["Priority"].dropna().unique().tolist()
selected_priority = st.sidebar.multiselect(
    "Filter by Project Priority", options=project_priority_options
)

valid_start_dates = projects_df["Expected Start Date Parsed"].dropna()
valid_end_dates = projects_df["Expected End Date Parsed"].dropna()
if not valid_start_dates.empty and not valid_end_dates.empty:
    overall_min_date = valid_start_dates.min().date()
    overall_max_date = valid_end_dates.max().date()
    if st.sidebar.button("Reset Date Filter"):
        if "date_range" in st.session_state:
            del st.session_state["date_range"]
        try:
            st.experimental_rerun()
        except AttributeError:
            st.warning(
                "Your Streamlit version does not support experimental_rerun. Please upgrade Streamlit (pip install --upgrade streamlit)."
            )
    date_range = st.sidebar.date_input(
        "Filter by Date Range (only for projects with valid dates)",
        value=(overall_min_date, overall_max_date),
        key="date_range",
    )
else:
    date_range = None

# --------------------------
# Apply Global Project Key Filter to both DataFrames
# --------------------------
filtered_projects = projects_df[projects_df["Project Key"].isin(global_project_keys)]
filtered_tasks = tasks_df[tasks_df["Project Key"].isin(global_project_keys)]

if selected_status:
    filtered_projects = filtered_projects[
        filtered_projects["Status"].isin(selected_status)
    ]
if selected_priority:
    filtered_projects = filtered_projects[
        filtered_projects["Priority"].isin(selected_priority)
    ]
if date_range and isinstance(date_range, (tuple, list)) and len(date_range) == 2:
    start_date, end_date = pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1])
    filtered_projects = filtered_projects[
        (
            (filtered_projects["Expected Start Date Parsed"].notna())
            & (
                filtered_projects["Expected Start Date Parsed"].between(
                    start_date, end_date
                )
            )
        )
        | (
            (filtered_projects["Expected End Date Parsed"].notna())
            & (
                filtered_projects["Expected End Date Parsed"].between(
                    start_date, end_date
                )
            )
        )
        | (
            filtered_projects["Expected Start Date Parsed"].isna()
            & filtered_projects["Expected End Date Parsed"].isna()
        )
    ]

# Recompute final global project keys from the fully filtered projects DataFrame
global_project_keys_final = filtered_projects["Project Key"].dropna().unique().tolist()

# Now, re-filter tasks to only include those from the final set of project keys
filtered_tasks = tasks_df[tasks_df["Project Key"].isin(global_project_keys_final)]

# --------------------------
# Apply Task Filter on filtered_tasks if a specific task is selected
# --------------------------
if global_task_filter != "All":
    selected_task_id = global_task_filter.split(" | ")[0].strip().lower()
    filtered_tasks["Task ID Normalized"] = (
        filtered_tasks["Task ID"].astype(str).str.strip().str.lower()
    )
    filtered_tasks["Parent Task Normalized"] = (
        filtered_tasks["Parent Task"].astype(str).str.strip().str.lower()
    )
    filtered_tasks = filtered_tasks[
        (filtered_tasks["Task ID Normalized"] == selected_task_id)
        | (
            filtered_tasks["Parent Task Normalized"].str.contains(
                selected_task_id, na=False
            )
        )
    ]
    st.sidebar.write("Filtered Tasks count:", len(filtered_tasks))

# --------------------------
# Layout: Two Columns - Projects (Left) & Tasks (Right)
# --------------------------
show_projects = st.sidebar.checkbox("Show Projects", value=True)
show_tasks = st.sidebar.checkbox("Show Tasks", value=True)
left_col, right_col = st.columns(2)

# --------------------------
# Left Column: Projects View
# --------------------------
with left_col:
    if show_projects:
        st.header("Projects")
        # Compute counts using the entire projects_df (not filtered_projects)
        total_projects = projects_df.shape[0]
        open_projects_count = projects_df[
            projects_df["Status"].str.lower() == "open"
        ].shape[0]
        # Create two columns for the KPI cards
        kpi_col1, kpi_col2 = st.columns(2)
        kpi_col1.metric("Open Projects", open_projects_count)
        kpi_col2.metric("Total Projects", total_projects)
        if filtered_projects.empty:
            st.write("No projects found with the selected filters.")
        else:
            for idx, row in filtered_projects.iterrows():
                with st.expander(f"{row['Project ID']}"):
                    cols = st.columns(2)
                    with cols[0]:
                        st.markdown(f"**Status:** {row['Status']}")
                        st.markdown(f"**Type:** {row['Project Type']}")
                        st.markdown(f"**Start:** {row['Expected Start Date']}")
                        st.markdown(f"**End:** {row['Expected End Date']}")
                        st.markdown(f"**Priority:** {row['Priority']}")
                    with cols[1]:
                        st.markdown(f"**Department:** {row['Department']}")
                        st.markdown(f"**Funding Agency:** {row['Funding Agency']}")
                        st.markdown(f"**Beneficiaries:** {row['Beneficiary Count']}")
                        st.markdown(f"**Est. Cost:** ₹{row['Estimated Cost']}")
    else:
        st.write("Projects view is hidden. Enable it from the sidebar.")

# --------------------------
# Right Column: Tasks View
# --------------------------
with right_col:
    if show_tasks:
        st.header("Tasks")
        if filtered_tasks.empty:
            st.write("No tasks found for the selected filter(s).")
        else:
            # Sort tasks in descending order by Task ID
            filtered_tasks = filtered_tasks.sort_values(by="Task ID", ascending=False)

            def normalize(s):
                return str(s).strip().lower() if pd.notna(s) else ""

            tasks_with_key = filtered_tasks[filtered_tasks["Project Key"].notna()]
            standalone_tasks = filtered_tasks[
                filtered_tasks["Project Key"].isna()
                | (filtered_tasks["Project Key"].str.strip() == "")
            ]
            st.write("Number of standalone tasks:", len(standalone_tasks))
            root_tasks = tasks_with_key[
                tasks_with_key["Parent Task"].apply(
                    lambda x: normalize(x) in ["", "none", "-"]
                )
            ]
            child_tasks = tasks_with_key[
                tasks_with_key["Parent Task"].apply(
                    lambda x: normalize(x) not in ["", "none", "-"]
                )
            ]
            st.write("Number of Parent Tasks:", len(root_tasks))
            st.write("Number of Sub-Tasks:", len(child_tasks))
            for idx, root in root_tasks.iterrows():
                normalized_root_id = normalize(root["Task ID"])
                with st.expander(f"{root['Task Filter Label']}"):
                    st.markdown(
                        f"**Task Subject:** {root.get('Task Subject Clean', '')}"
                    )
                    st.markdown(f"**Project Mapping:** {root.get('Project Name', '')}")
                    st.markdown(f"**Task Owner:** {root.get('Task Owner', '')}")
                    st.markdown(f"**Annual Target:** {root.get('Annual Target', '')}")
                    st.markdown(f"**Task Type:** {root.get('Task Type', '')}")
                    st.markdown(f"**Task Status:** {root.get('Task Status', '')}")
                    st.markdown(f"**Task Priority:** {root.get('Task Priority', '')}")
                    st.markdown(f"**Task Outcome:** {root.get('Task Outcome', '')}")
                    st.markdown(
                        f"**Means of Verification:** {root.get('Means of Verification', '')}"
                    )
                    st.markdown(
                        f"**Task Completed Date:** {root.get('Task Completed Date', '')}"
                    )
                    st.markdown(f"**Potential Risk:** {root.get('Potential Risk', '')}")
                    st.markdown(
                        f"**Risk Mitigation Plan:** {root.get('Risk Mitigation Plan', '')}"
                    )
                    st.markdown(
                        f"**Expected Start Date:** {root.get('Expected Start Date', '')}"
                    )
                    st.markdown(
                        f"**Expected End Date:** {root.get('Expected End Date', '')}"
                    )
                    st.markdown(
                        f"**Task Description:** {root.get('Task Description', '')}"
                    )
                    st.markdown(
                        f"**Approved Budget:** {root.get('Approved Budget', '')}"
                    )
                    st.markdown(f"**Accrued Budget:** {root.get('Accrued Budget', '')}")
                    st.markdown(f"**Expected Cost:** {root.get('Expected Cost', '')}")
                    st.markdown(f"**Actual Cost:** {root.get('Actual Cost', '')}")
                    subtasks = child_tasks[
                        child_tasks["Parent Task"].apply(lambda x: normalize(x))
                        == normalized_root_id
                    ]
                    if not subtasks.empty:
                        st.markdown("#### Subtasks:")
                        for idx2, child in subtasks.iterrows():
                            st.markdown(
                                f"- **Task ID:** {child.get('Task ID', '')}  \n"
                                f"  **Subject:** {child.get('Task Subject Clean', '')}  \n"
                                f"  **Owner:** {child.get('Task Owner', '')}  \n"
                                f"  **Type:** {child.get('Task Type', '')}  \n"
                                f"  **Status:** {child.get('Status', '')}  \n"
                                f"  **Approved Budget:** {child.get('Approved Budget', '')}"
                            )
            if not standalone_tasks.empty:
                st.markdown("### Standalone Tasks (No Project Mapped)")
                for idx, task in standalone_tasks.iterrows():
                    with st.expander(f"{task['Task Filter Label']}"):
                        st.markdown(
                            f"**Task Subject:** {task.get('Task Subject Clean', '')}"
                        )
                        st.markdown(f"**Task Owner:** {task.get('Task Owner', '')}")
                        st.markdown(
                            f"**Annual Target:** {task.get('Annual Target', '')}"
                        )
                        st.markdown(f"**Task Type:** {task.get('Task Type', '')}")
                        st.markdown(f"**Task:** {task.get('Task', '')}")
                        st.markdown(f"**Status:** {task.get('Status', '')}")
                        st.markdown(
                            f"**Task Priority:** {task.get('Task Priority', '')}"
                        )
                        st.markdown(f"**Task Outcome:** {task.get('Task Outcome', '')}")
                        st.markdown(
                            f"**Means of Verification:** {task.get('Means of Verification', '')}"
                        )
                        st.markdown(
                            f"**Task Completed Date:** {task.get('Task Completed Date', '')}"
                        )
                        st.markdown(
                            f"**Potential Risk:** {task.get('Potential Risk', '')}"
                        )
                        st.markdown(
                            f"**Risk Mitigation Plan:** {task.get('Risk Mitigation Plan', '')}"
                        )
                        st.markdown(
                            f"**Expected Start Date:** {task.get('Expected Start Date', '')}"
                        )
                        st.markdown(
                            f"**Expected End Date:** {task.get('Expected End Date', '')}"
                        )
                        st.markdown(
                            f"**Task Description:** {task.get('Task Description', '')}"
                        )
                        st.markdown(
                            f"**Approved Budget:** {task.get('Approved Budget', '')}"
                        )
                        st.markdown(
                            f"**Accrued Budget:** {task.get('Accrued Budget', '')}"
                        )
                        st.markdown(
                            f"**Expected Cost:** {task.get('Expected Cost', '')}"
                        )
                        st.markdown(f"**Actual Cost:** {task.get('Actual Cost', '')}")
    else:
        st.write("Tasks view is hidden. Enable it from the sidebar.")
