"""
Streamlit UI for LinkedIn Post Generator.
Run with: streamlit run streamlit_app.py
"""

import streamlit as st
import requests

# API Configuration
API_BASE_URL = "http://127.0.0.1:8000/api"

# Page config
st.set_page_config(
    page_title="LinkedIn Post Generator",
    page_icon="💼",
    layout="wide"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .stButton > button {
        width: 100%;
        background-color: #0077B5;
        color: white;
        font-weight: bold;
        border-radius: 8px;
        padding: 0.5rem 1rem;
    }
    .stButton > button:hover {
        background-color: #005885;
    }
    .post-output {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 20px;
        border-left: 4px solid #0077B5;
    }
    .series-badge {
        background-color: #0077B5;
        color: white;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.8rem;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.title("💼 LinkedIn Post Generator")
st.markdown("Generate engaging LinkedIn posts with AI-powered memory")

# Sidebar for user settings
with st.sidebar:
    st.header("⚙️ Settings")
    user_id = st.text_input("User ID", value="user_123", help="Your unique identifier")
    
    st.divider()
    
    # Fetch and display user's series
    st.subheader("📚 Your Series")
    try:
        response = requests.get(f"{API_BASE_URL}/series/{user_id}")
        if response.status_code == 200:
            series_data = response.json()
            if series_data.get("total_series", 0) > 0:
                for series in series_data.get("series", []):
                    with st.expander(f"📖 {series['first_topic'][:30]}..."):
                        st.write(f"**Posts:** {series['total_posts']}")
                        st.write(f"**Series ID:** `{series['series_id'][:8]}...`")
                        st.write(f"**Latest Topic:** {series['last_topic'][:50]}")
            else:
                st.info("No series yet. Create one below!")
    except:
        st.warning("⚠️ API not connected. Start the FastAPI server first.")

# Main content area
col1, col2 = st.columns([1, 1])

with col1:
    st.header("✍️ Create Post")
    
    # Topic input
    topic = st.text_area(
        "Topic",
        placeholder="e.g., The importance of work-life balance in tech",
        height=100
    )
    
    # Style options in a grid
    subcol1, subcol2 = st.columns(2)
    
    with subcol1:
        tone = st.selectbox(
            "🎭 Tone",
            options=["professional", "casual", "storytelling", "inspirational", "educational", "humorous"],
            index=0
        )
        
        length = st.selectbox(
            "📏 Length",
            options=["short", "medium", "long"],
            index=1,
            help="Short: 100-300 chars | Medium: 300-800 chars | Long: 800-2000 chars"
        )
    
    with subcol2:
        audience = st.selectbox(
            "👥 Audience",
            options=["general", "recruiters", "engineers", "founders", "marketers", "students"],
            index=0
        )
        
        style_mode = st.selectbox(
            "🎨 Style Mode",
            options=["similar", "different"],
            index=0,
            help="Similar = match past style | Different = fresh approach"
        )
    
    # Additional options
    st.subheader("🔧 Options")
    opt_col1, opt_col2, opt_col3 = st.columns(3)
    
    with opt_col1:
        include_emoji = st.checkbox("Include Emojis", value=True)
    with opt_col2:
        include_hashtags = st.checkbox("Include Hashtags", value=True)
    with opt_col3:
        num_hashtags = st.number_input("# of Hashtags", min_value=0, max_value=10, value=3)
    
    # Series configuration
    st.subheader("📚 Series")
    is_series = st.checkbox("Part of a Series", value=False)
    
    series_id = None
    if is_series:
        series_option = st.radio(
            "Series Option",
            options=["Start New Series", "Continue Existing Series"],
            horizontal=True
        )
        
        if series_option == "Continue Existing Series":
            # Fetch existing series for dropdown
            try:
                response = requests.get(f"{API_BASE_URL}/series/{user_id}")
                if response.status_code == 200:
                    series_data = response.json()
                    series_list = series_data.get("series", [])
                    if series_list:
                        series_options = {
                            f"{s['first_topic'][:40]}... ({s['total_posts']} posts)": s['series_id'] 
                            for s in series_list
                        }
                        selected_series = st.selectbox(
                            "Select Series",
                            options=list(series_options.keys())
                        )
                        series_id = series_options[selected_series]
                    else:
                        st.info("No existing series found. Start a new one!")
            except:
                st.error("Could not fetch series. Check API connection.")
    
    # Generate button
    st.divider()
    generate_clicked = st.button("🚀 Generate Post", use_container_width=True)

with col2:
    st.header("📝 Generated Post")
    
    if generate_clicked:
        if not topic:
            st.error("Please enter a topic!")
        else:
            with st.spinner("Generating your post..."):
                try:
                    payload = {
                        "user_id": user_id,
                        "topic": topic,
                        "tone": tone,
                        "audience": audience,
                        "length": length,
                        "style_mode": style_mode,
                        "include_emoji": include_emoji,
                        "include_hashtags": include_hashtags,
                        "num_hashtags": num_hashtags,
                        "is_series": is_series,
                        "series_id": series_id
                    }
                    
                    response = requests.post(
                        f"{API_BASE_URL}/generate",
                        json=payload
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        
                        # Success message
                        st.success("✅ Post generated successfully!")
                        
                        # Display metadata
                        meta_col1, meta_col2, meta_col3 = st.columns(3)
                        with meta_col1:
                            if result.get("is_series_post"):
                                st.markdown(f"<span class='series-badge'>Series Post #{result.get('series_order', 1)}</span>", unsafe_allow_html=True)
                        with meta_col2:
                            if result.get("is_similar_to_past"):
                                st.warning("⚠️ Similar topic posted before")
                        with meta_col3:
                            st.info(f"📊 Posts: {result.get('total_user_posts', 0)}")
                        
                        # Display the post
                        st.markdown("---")
                        st.markdown(f"### Your Post")
                        st.markdown(f"""
                        <div class="post-output">
                        {result.get('post', '')}
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # Copy button
                        st.code(result.get('post', ''), language=None)
                        
                        # Similar topics if any
                        similar = result.get("similar_topics", [])
                        if similar:
                            with st.expander("📎 Similar Past Topics"):
                                for s in similar:
                                    st.write(f"• {s}")
                    else:
                        st.error(f"Error: {response.json().get('detail', 'Unknown error')}")
                        
                except requests.exceptions.ConnectionError:
                    st.error("❌ Cannot connect to API. Make sure the FastAPI server is running!")
                except Exception as e:
                    st.error(f"Error: {str(e)}")
    else:
        st.info("👈 Configure your post settings and click 'Generate Post'")
        
        # Show recent posts
        st.subheader("📜 Recent Posts")
        try:
            response = requests.get(f"{API_BASE_URL}/history/{user_id}?limit=5")
            if response.status_code == 200:
                history = response.json()
                if history.get("posts"):
                    for post in history["posts"]:
                        with st.expander(f"📌 {post['topic'][:50]}..."):
                            st.write(f"**Tone:** {post['tone']} | **Audience:** {post['audience']}")
                            st.write(post['post_preview'])
                else:
                    st.write("No posts yet. Generate your first one!")
        except:
            st.write("Start the API server to see your history.")

# Footer
st.divider()
st.markdown("""
<div style="text-align: center; color: #666; font-size: 0.8rem;">
    Made with ❤️ using Streamlit + FastAPI + Qdrant
</div>
""", unsafe_allow_html=True)
