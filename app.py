with st.expander("Filters & Sorting"):
    if "filter_destination" not in st.session_state:
        st.session_state.filter_destination = "All"
    if "sort_by" not in st.session_state:
        st.session_state.sort_by = "Time"
    if "search_unit" not in st.session_state:
        st.session_state.search_unit = ""
    
    # Izračun indeksa za selectbox
    options = ["All"] + DESTINATIONS
    current_filter = st.session_state.filter_destination
    filter_index = 0 if current_filter == "All" else DESTINATIONS.index(current_filter) + 1
    
    st.session_state.filter_destination = st.selectbox(
        "Destination Filter",
        options,
        index=filter_index
    )
    st.session_state.sort_by = st.selectbox("Sort By", ["Time", "Destination"], index=["Time", "Destination"].index(st.session_state.sort_by))
    st.session_state.search_unit = st.text_input("Quick Search by Unit", value=st.session_state.search_unit)
    
    if st.button("Clear Filters"):
        st.session_state.filter_destination = "All"
        st.session_state.sort_by = "Time"
        st.session_state.search_unit = ""
        st.rerun()