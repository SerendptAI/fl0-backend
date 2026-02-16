import streamlit as st
import requests
import json
import os

# api configuration
API_URL = "http://localhost:8001/api/v1"

st.set_page_config(page_title="Semantic Search Verifier", layout="wide")
st.title("🤖 Semantic Search Backend Verifier")

# session state for auth
if "token" not in st.session_state:
    st.session_state.token = None
if "user_info" not in st.session_state:
    st.session_state.user_info = None

# helper: api request wrapper
def authenticated_request(method, endpoint, **kwargs):
    if not st.session_state.token:
        st.error("Please login first.")
        return None
        
    headers = kwargs.get("headers", {})
    headers["Authorization"] = f"Bearer {st.session_state.token}"
    kwargs["headers"] = headers
    
    try:
        response = requests.request(method, f"{API_URL}{endpoint}", **kwargs)
        if response.status_code == 401:
            st.error("Session expired or invalid token.")
            st.session_state.token = None
            st.rerun()
        return response
    except requests.exceptions.ConnectionError:
        st.error("Could not connect to backend. Is it running on localhost:8001?")
        return None

# sidebar: authentication
with st.sidebar:
    st.header("Authentication")
    
    if not st.session_state.token:
        st.warning("Not logged in")
        
        st.markdown(f"""
        ### Steps to Login:
        1. [Click here to Login with Google]({API_URL}/auth/login)
        2. You will be redirected to Google, and then to a results page.
        3. Copy the `access_token` from the JSON response.
        4. Paste it below.
        """)
        
        token_input = st.text_input("Paste Access Token Here", type="password")
        
        if st.button("Set Token"):
            if token_input:
                st.session_state.token = token_input
                # Verify token by fetching user info
                res = authenticated_request("GET", "/auth/me")
                if res and res.status_code == 200:
                    st.session_state.user_info = res.json()
                    st.success(f"Welcome, {st.session_state.user_info.get('name')}!")
                    st.rerun()
                else:
                    st.error("Invalid token.")
    else:
        if st.session_state.user_info:
            st.success(f"Logged in as: {st.session_state.user_info.get('name')}")
            st.caption(f"ID: {st.session_state.user_info.get('user_id')}")
            
        if st.button("Logout"):
            st.session_state.token = None
            st.session_state.user_info = None
            st.rerun()

# main tabs
tab1, tab2, tab3 = st.tabs(["📝 Ingest Data", "📂 View Submissions", "🔍 Smart Autofill"])

if not st.session_state.token:
    st.info("Please log in via the sidebar to access the tools.")
else:
    # tab 1: ingest
    with tab1:
        st.header("Ingest Form Data")
        st.markdown("Simulate a user submitting a form on a website.")
        website = st.text_input("Website URL", "https://example.com/careers")
        
        st.subheader("Form Fields")
        if "form_fields" not in st.session_state:
            st.session_state.form_fields = [{"key": "Full Name", "value": "John Doe"}]
            
        for i, field in enumerate(st.session_state.form_fields):
            c1, c2 = st.columns(2)
            with c1:
                field["key"] = st.text_input(f"Key {i+1}", field["key"], key=f"key_{i}")
            with c2:
                field["value"] = st.text_input(f"Value {i+1}", field["value"], key=f"val_{i}")
                
        if st.button("+ Add Field"):
            st.session_state.form_fields.append({"key": "", "value": ""})
            st.rerun()
            
        if st.button("Submit Data", type="primary"):
            data_payload = {f["key"]: f["value"] for f in st.session_state.form_fields if f["key"]}
            if not data_payload:
                st.error("Please add at least one field.")
            else:
                payload = {
                    "website": website,
                    "data": data_payload
                }
                
                with st.spinner("Ingesting..."):
                    res = authenticated_request("POST", "/submissions/", json=payload)
                    
                if res and res.status_code == 200:
                    st.success("Data ingested successfully!")
                    st.json(res.json())
                elif res:
                    st.error(f"Error: {res.text}")

    # tab 2: view submissions
    with tab2:
        st.header("Your Submissions")
        
        col1, col2 = st.columns([3, 1])
        with col2:
            if st.button("Refresh List"):
                res = authenticated_request("GET", "/submissions/")
                if res and res.status_code == 200:
                    st.session_state.submissions = res.json()
                elif res:
                     st.error(f"Error: {res.text}")

        if "submissions" in st.session_state and st.session_state.submissions:
            for sub in st.session_state.submissions:
                with st.expander(f"{sub.get('website', 'Unknown Site')} - {sub.get('timestamp')}"):
                    st.write(f"**ID:** {sub['id']}")
                    st.caption("Click 'Fetch Full Detail' to see the data.")
                    
                    if st.button(f"Fetch Full Detail {sub['id'][:8]}", key=sub['id']):
                        detail_res = authenticated_request("GET", f"/submissions/{sub['id']}")
                        if detail_res and detail_res.status_code == 200:
                            st.json(detail_res.json())
                        elif detail_res:
                            st.error(f"Failed to fetch detail: {detail_res.text}")
        else:
            st.info("Click 'Refresh List' to see your submissions.")

    # tab 3: smart autofill
    with tab3:
        st.header("Semantic Autofill Test")
        st.markdown("Simulate visiting a **new** website with different field names.")
        
        # Simulating a new form
        target_keys = st.multiselect(
            "Select fields to autofill",
            ["Name", "Full Name", "Phone", "Mobile Number", "Cell Phone", "Email", "Address", "Role", "Job Title", "Experience", "Years of Exp"],
            default=["Name", "Phone"]
        )
        
        c1, c2 = st.columns(2)
        with c1:
            threshold = st.slider("Similarity Threshold", 0.0, 1.0, 0.8)
        with c2:
            multiple = st.checkbox("Multiple Suggestions?")
            limit = st.number_input("Limit", 1, 10, 3, disabled=not multiple)
            
        if st.button("Autofill", type="primary"):
            if not target_keys:
                st.error("Select at least one key.")
            else:
                req_payload = {
                    "keys": target_keys,
                    "threshold": threshold,
                    "multiple": multiple,
                    "limit": limit
                }
                
                with st.spinner("Searching..."):
                    res = authenticated_request("POST", "/autofill", json=req_payload)
                
                if res and res.status_code == 200:
                    suggestions = res.json()["suggestions"]
                    st.subheader("Results")
                    st.json(suggestions)
                elif res:
                    st.error(f"Error: {res.text}")
