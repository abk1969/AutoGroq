import base64
import streamlit as st
import json
import os
import re

from api_utils import send_request_to_groq_api
from file_utils import write_agent_file
from ui_utils import update_discussion_and_whiteboard

def add_or_update_agent(index, expert_name, description):
    if index is None:  # Add new agent
        st.session_state.agents.append({"expert_name": expert_name, "description": description})
    else:  # Update existing agent
        st.session_state.agents[index] = {"expert_name": expert_name, "description": description}

    # Write the agent file
    write_agent_file(expert_name, description)

    # Create a directory for the agents if it doesn't exist
    if not os.path.exists("agents"):
        os.makedirs("agents")

    # Write the JSON file
    with open(f"agents/{expert_name}.json", "w") as f:
        json.dump(agent_data, f, indent=2)


def agent_button_callback(agent_index):
    # Callback function to handle state update and logic execution
    def callback():
        st.session_state['selected_agent_index'] = agent_index
        st.session_state['form_agent_name'] = st.session_state.agents[agent_index]['expert_name']
        st.session_state['form_agent_description'] = st.session_state.agents[agent_index]['description']
        # Directly call process_agent_interaction here if appropriate
        process_agent_interaction(agent_index)
    return callback

def delete_agent(index):
    if 0 <= index < len(st.session_state.agents):
        expert_name = st.session_state.agents[index]["expert_name"]
        del st.session_state.agents[index]
        
        # Get the full path to the JSON file
        agents_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "agents"))
        json_file = os.path.join(agents_dir, f"{expert_name}.json")
        
        # Delete the corresponding JSON file
        if os.path.exists(json_file):
            os.remove(json_file)
            print(f"JSON file deleted: {json_file}")
        else:
            print(f"JSON file not found: {json_file}")
        
        st.experimental_rerun()

def display_agents():
    if "agents" in st.session_state and st.session_state.agents:
        st.sidebar.title("Test Agents")
        st.sidebar.subheader("click to interact")
        for index, agent in enumerate(st.session_state.agents):
            expert_name = agent["expert_name"]
            # Use callback for button click
            st.sidebar.button(expert_name, key=f"agent_{index}", on_click=agent_button_callback(index))


def display_file_management_sidebar():
    agents_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "agents"))
    workflows_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "workflows"))
    
    # Get the list of files in the "agents" folder
    agent_files = [file for file in os.listdir(agents_dir) if os.path.isfile(os.path.join(agents_dir, file))]
    
    if agent_files:
        st.sidebar.title("Download Agents")
        st.sidebar.subheader("for import into AutoGen")
        
        for file in agent_files:
            file_path = os.path.join(agents_dir, file)
            
            # Read the file content
            with open(file_path, "rb") as f:
                file_content = f.read()
            
            # Encode the file content as base64
            file_content_base64 = base64.b64encode(file_content).decode("utf-8")
            
            # Create a data URL for the file
            data_url = f"data:application/json;base64,{file_content_base64}"
            
            # Display the file name as a hyperlink
            st.sidebar.markdown(f'<a href="{data_url}" download="{file}" target="_blank">{file}</a>', unsafe_allow_html=True)
    
    # Get the list of files in the "workflows" folder
    workflow_files = [file for file in os.listdir(workflows_dir) if os.path.isfile(os.path.join(workflows_dir, file))]
    
    if workflow_files:
        st.sidebar.title("Download Workflow")
        st.sidebar.subheader("for import into AutoGen")
        
        for file in workflow_files:
            file_path = os.path.join(workflows_dir, file)
            
            # Read the file content
            with open(file_path, "rb") as f:
                file_content = f.read()
            
            # Encode the file content as base64
            file_content_base64 = base64.b64encode(file_content).decode("utf-8")
            
            # Create a data URL for the file
            data_url = f"data:application/json;base64,{file_content_base64}"
            
            # Display the file name as a hyperlink
            st.sidebar.markdown(f'<a href="{data_url}" download="{file}" target="_blank">{file}</a>', unsafe_allow_html=True)
            

def download_agent_file(expert_name):
    # Format the expert_name
    formatted_expert_name = re.sub(r'[^a-zA-Z0-9\s]', '', expert_name)  # Remove non-alphanumeric characters
    formatted_expert_name = formatted_expert_name.lower().replace(' ', '_')  # Convert to lowercase and replace spaces with underscores

    # Get the full path to the agent JSON file
    agents_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "agents"))
    json_file = os.path.join(agents_dir, f"{formatted_expert_name}.json")

    # Check if the file exists
    if os.path.exists(json_file):
        # Read the file content
        with open(json_file, "r") as f:
            file_content = f.read()

        # Encode the file content as base64
        b64_content = base64.b64encode(file_content.encode()).decode()

        # Create a download link
        href = f'<a href="data:application/json;base64,{b64_content}" download="{formatted_expert_name}.json">Download {formatted_expert_name}.json</a>'
        st.markdown(href, unsafe_allow_html=True)
    else:
        st.error(f"File not found: {json_file}")


def process_agent_interaction(agent_index):
    # Retrieve agent information using the provided index
    agent = st.session_state.agents[agent_index]

    # Preserve the original "Act as" functionality
    expert_name = agent["expert_name"]
    description = agent["description"]
    user_request = st.session_state.get('user_request', '')
    user_input = st.session_state.get('user_input', '')
    rephrased_request = st.session_state.get('rephrased_request', '')

    request = f"Act as the {expert_name} who {description}."
    if user_request:
        request += f" Original request was: {user_request}."
    if rephrased_request:
        request += f" You are helping a team work on satisfying {rephrased_request}."
    if user_input:
        request += f" Additional input: {user_input}."
    if st.session_state.discussion:
        request += f" The discussion so far has been {st.session_state.discussion[-50000:]}."

    response = send_request_to_groq_api(expert_name, request)
    if response:
        update_discussion_and_whiteboard(expert_name, response, user_input)

    # Additionally, populate the sidebar form with the agent's information
    st.session_state['form_agent_name'] = expert_name
    st.session_state['form_agent_description'] = description
    st.session_state['selected_agent_index'] = agent_index  # Keep track of the selected agent for potential updates/deletes