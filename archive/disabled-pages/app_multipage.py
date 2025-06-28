"""
Main entry point for Kai VPM v2 multipage Streamlit application
"""

import streamlit as st
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from libs.ui_layout import setup_page_config, setup_sidebar, initialize_session_state, error_boundary


@error_boundary
def main():
    """Main application entry point"""
    # Initialize session state
    initialize_session_state()
    
    # Setup page configuration
    setup_page_config("Home", "🏠")
    
    # Setup sidebar and get selected page
    current_page = setup_sidebar()
    
    # Route to appropriate page
    if current_page == "1_new_project":
        import pages.page_1_new_project as page1
        page1.show_page()
    elif current_page == "2_preview_charter":
        import pages.page_2_preview_charter as page2
        page2.show_page()
    elif current_page == "3_persona_and_wbs":
        import pages.page_3_persona_and_wbs as page3
        page3.show_page()
    else:
        # Default to new project page
        import pages.page_1_new_project as page1
        page1.show_page()


if __name__ == "__main__":
    main()