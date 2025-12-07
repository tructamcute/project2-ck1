import streamlit as st
from PIL import Image
import requests 
from datetime import datetime
import json
import re
import os

# Import services
from services.genre_service import get_genre_map 
from services.jikan_service import get_character_data, get_one_character_data
from services.gemini_service import ai_vision_detect, ai_analyze_profile
from services.books_service import search_books_by_genre, search_books_by_keyword, get_book_genres

# Import Gemini
import google.generativeai as genai

# ===== CẤU HÌNH GEMINI - HỖ TRỢ CẢ LOCAL VÀ STREAMLIT CLOUD =====
def get_api_key():
    """Lấy API key từ Streamlit secrets hoặc .env"""
    try:
        # Thử lấy từ Streamlit secrets trước (cho Streamlit Cloud)
        if hasattr(st, 'secrets') and "GEMINI_API_KEY" in st.secrets:
            return st.secrets["GEMINI_API_KEY"]
    except:
        pass
    
    # Nếu không có, lấy từ environment variable (cho local)
    return os.getenv("GEMINI_API_KEY")

GEMINI_API_KEY = get_api_key()
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
else:
    st.error("⚠️ Không tìm thấy GEMINI_API_KEY! Vui lòng cấu hình trong Streamlit Secrets hoặc file .env")

# ===== KHỞI TẠO SESSION STATE =====
if 'favorites' not in st.session_state:
    st.session_state.favorites = {'characters': []}

if 'search_history' not in st.session_state:
    st.session_state.search_history = []

if 'current_page' not in st.session_state:
    st.session_state.current_page = "Search Character"

if 'show_character_list' not in st.session_state:
    st.session_state.show_character_list = False

if 'search_results' not in st.session_state:
    st.session_state.search_results = []

if 'selected_character' not in st.session_state:
    st.session_state.selected_character = None

if 'last_search_query' not in st.session_state:
    st.session_state.last_search_query = ""

if 'recommendations' not in st.session_state:
    st.session_state.recommendations = None

if 'current_content_type' not in st.session_state:
    st.session_state.current_content_type = "anime"

# Link mua hàng
PURCHASE_LINK = "https://your-store-link.com"

# ===== LOADING ANIMATION =====
st.markdown("""
<style>
    .loading-overlay {
        position: fixed;
        top: 0;
        left: 0;
        width: 100vw;
        height: 100vh;
        background: rgba(0, 0, 0, 0.9);
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        z-index: 99999;
        animation: fadeOutOverlay 0.5s ease-out 2.5s forwards;
    }
    
    .loading-content {
        text-align: center;
    }
    
    .loading-title {
        font-size: 2rem;
        font-weight: bold;
        color: white;
        margin-bottom: 30px;
    }
    
    .progress-container {
        width: 400px;
        height: 8px;
        background: rgba(255, 255, 255, 0.2);
        border-radius: 10px;
        overflow: hidden;
        margin-bottom: 15px;
    }
    
    .progress-bar {
        height: 100%;
        background: linear-gradient(90deg, #4facfe 0%, #00f2fe 100%);
        border-radius: 10px;
        animation: loadProgress 2s ease-out forwards;
        box-shadow: 0 0 10px rgba(79, 172, 254, 0.5);
    }
    
    @keyframes loadProgress {
        0% { width: 0%; }
        100% { width: 100%; }
    }
    
    .progress-text {
        color: white;
        font-size: 1.2rem;
    }
    
    @keyframes fadeOutOverlay {
        to {
            opacity: 0;
            visibility: hidden;
            pointer-events: none;
        }
    }
    
    .main, .stApp > header, [data-testid="stSidebar"] {
        opacity: 0.3;
        filter: blur(5px);
        animation: clearContent 1s ease-in-out 2.2s forwards;
    }
    
    @keyframes clearContent {
        to {
            opacity: 1;
            filter: blur(0px);
        }
    }
    
    [data-testid="column"] {
        padding: 0 15px !important;
    }
    
    [data-testid="stImage"] {
        margin-bottom: 15px !important;
    }
    
    .purchase-button {
        position: fixed;
        bottom: 30px;
        right: 30px;
        z-index: 9998;
        animation: pulse 2s infinite;
    }
    
    @keyframes pulse {
        0%, 100% {
            transform: scale(1);
        }
        50% {
            transform: scale(1.05);
        }
    }
    
    .purchase-button a {
        display: inline-block;
        padding: 15px 30px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white !important;
        text-decoration: none;
        border-radius: 50px;
        font-size: 1.1rem;
        font-weight: bold;
        box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
        transition: all 0.3s ease;
    }
    
    .purchase-button a:hover {
        transform: translateY(-3px);
        box-shadow: 0 8px 25px rgba(102, 126, 234, 0.6);
        background: linear-gradient(135deg, #764ba2 0%, #667eea 100%);
    }
</style>

<div class="loading-overlay">
    <div class="loading-content">
        <div class="loading-title">-- WHO IS YOUR WAIFU? --</div>
        <div class="progress-container">
            <div class="progress-bar"></div>
        </div>
        <div class="progress-text" id="progress-text">Loading... 0%</div>
    </div>
</div>

<script>
    let progress = 0;
    const interval = setInterval(() => {
        progress += 2;
        if (progress > 100) progress = 100;
        document.getElementById('progress-text').innerText = `Loading... ${progress}%`;
        if (progress >= 100) clearInterval(interval);
    }, 40);
</script>
""", unsafe_allow_html=True)

# ===== NÚT MUA HÀNG =====
st.markdown(f"""
<div class="purchase-button">
    <a href="https://temp1a.netlify.app/" target="_blank">
        🛒 Bạn muốn mua, ấn vào đây!
    </a>
</div>
""", unsafe_allow_html=True)

# ===== CẤU HÌNH TRANG =====
chitoge_icon = Image.open("itooklogo.jpg")
st.set_page_config(page_title="ITook Library", page_icon=chitoge_icon, layout="wide")

from styles_css import set_background_image, add_corner_gif
set_background_image("utsuro.webp")
add_corner_gif()

# ===== HELPER FUNCTIONS =====
def add_to_favorites(item_type, item_data):
    """Thêm item vào favorites - CHỈ cho characters"""
    if item_type != 'characters':
        return False
        
    existing_ids = [item.get('id') for item in st.session_state.favorites[item_type]]
    item_id = item_data.get('id') or item_data.get('mal_id')
    
    if item_id not in existing_ids:
        item_data['added_date'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        st.session_state.favorites[item_type].append(item_data)
        return True
    else:
        return False

def add_to_history(search_type, query, result=None):
    """Thêm vào lịch sử tìm kiếm"""
    history_entry = {
        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'type': search_type,
        'query': query,
        'result': result
    }
    st.session_state.search_history.insert(0, history_entry)
    if len(st.session_state.search_history) > 50:
        st.session_state.search_history = st.session_state.search_history[:50]

def get_ai_recommendations(age, interests, mood, reading_style, content_type):
    """Lấy gợi ý từ AI dựa trên thông tin người dùng"""
    
    if not GEMINI_API_KEY:
        st.error("Không thể sử dụng AI Recommend - thiếu API key!")
        return None
    
    prompt = f"""
Bạn là chuyên gia tư vấn sách và anime. Dựa trên thông tin sau:
- Độ tuổi: {age}
- Sở thích: {interests}
- Tâm trạng: {mood}
- Phong cách: {reading_style}

Hãy đề xuất 5 {content_type} phù hợp. Trả về ĐÚNG format JSON này (không thêm text nào khác):
[
  {{
    "title": "Tên tác phẩm",
    "reason": "Lý do phù hợp với người dùng (2-3 câu)",
    "genre": "Thể loại",
    "search_keyword": "từ khóa search"
  }}
]

CHỈ trả về JSON array, không giải thích gì thêm.
"""
    
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(prompt)
        response_text = response.text
        
        # Tìm JSON trong response
        json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
        if json_match:
            recommendations = json.loads(json_match.group())
            return recommendations
        else:
            return None
    except Exception as e:
        st.error(f"AI Error: {e}")
        return None

def search_content_by_keyword(keyword, content_type):
    """Tìm kiếm anime/manga/books theo keyword"""
    if content_type in ["anime", "manga"]:
        url = f"https://api.jikan.moe/v4/{content_type}?q={keyword}&limit=1"
        try:
            response = requests.get(url)
            if response.status_code == 200:
                data = response.json()
                results = data.get('data', [])
                if results:
                    return results[0]
        except:
            pass
    else:  # books
        books = search_books_by_keyword(keyword, max_results=1)
        if books:
            return books[0]
    return None

# ===== SIDEBAR MENU =====
with st.sidebar:
    st.markdown("## 🎯 Which tool?")
    st.markdown("**Tell me what you need**")
    
    menu_options = ["🔍 Texting", "🖼️ Uploading", "📚 Genre", "❤️ Favorites", "📜 History", "🤖 AI Recommend"]
    
    page_map = {
        "🔍 Texting": "Search Character",
        "🖼️ Uploading": "Upload Image",
        "🤖 AI Recommend": "AI Recommend",
        "📚 Genre": "Discover Media",
        "❤️ Favorites": "Favorites",
        "📜 History": "History"
    }
    
    current_index = 0
    for i, option in enumerate(menu_options):
        if page_map[option] == st.session_state.current_page:
            current_index = i
            break
    
    selected_menu = st.radio(
        "navigation",
        options=menu_options,
        index=current_index,
        label_visibility="collapsed"
    )
    
    new_page = page_map[selected_menu]
    if st.session_state.current_page != new_page:
        st.session_state.current_page = new_page
        st.session_state.show_character_list = False
        st.session_state.search_results = []
        st.session_state.selected_character = None
        st.rerun()
    
    st.markdown("---")
    st.info("**A-I-T Model - Tứ Đại Bổ Ách**")

# ===== MAIN CONTENT =====
st.title("🎌 ITOOK LIBRARY - Find Your Characters & Books 🌸")
st.markdown("---")

# ========================================
# PAGE 1: SEARCH CHARACTER BY TEXT
# ========================================
if st.session_state.current_page == "Search Character":
    st.header("🔍 Search for Anime Characters by Name")
    
    with st.form(key="search_form", clear_on_submit=False):
        search_query = st.text_input(
            "Enter the character name (E.g: Naruto, Luffy, Goku...):",
            value=st.session_state.last_search_query
        )
        submit_button = st.form_submit_button("🔍 Search", use_container_width=True)
    
    if submit_button and search_query:
        results = get_character_data(search_query)
        if results:
            st.session_state.search_results = results
            st.session_state.show_character_list = True
            st.session_state.selected_character = None
            st.session_state.last_search_query = search_query
        else:
            st.warning("No character found!")
            st.session_state.show_character_list = False
    
    if st.session_state.selected_character:
        info = st.session_state.selected_character
        
        if st.button("⬅️ Choose Another Character", use_container_width=True):
            st.session_state.selected_character = None
            st.rerun()
        
        st.markdown("---")
        
        with st.spinner(f"Loading the profile of {info['name']}..."):
            ai_text = ai_analyze_profile(info)
            add_to_history('character_text', st.session_state.last_search_query, info['name'])
            
            st.subheader(f"📋 Profile: {info['name']}")
            
            col_a, col_b = st.columns([1, 2])
            
            with col_a:
                st.image(info['images']['jpg']['image_url'], use_container_width=True)
                st.metric("Favorites", info['favorites'])
                
                if st.button("❤️ Add to Favorites", key=f"fav_char_{info['mal_id']}_main", use_container_width=True):
                    success = add_to_favorites('characters', {
                        'id': info['mal_id'],
                        'name': info['name'],
                        'image': info['images']['jpg']['image_url'],
                        'favorites': info['favorites']
                    })
                    if success:
                        st.success("✅ Added to favorites!")
                    else:
                        st.warning("⚠️ Already in favorites!")
            
            with col_b:
                st.write(f"**Japanese name:** {info.get('name_kanji', 'N/A')}")
                st.markdown("### 📄 AI Analysis Report")
                st.success(ai_text, icon="📄")
    
    elif st.session_state.show_character_list and st.session_state.search_results:
        st.markdown("---")
        st.markdown("**📋 Multiple results found. Choose your character to analyze:**")
        
        cols = st.columns(5, gap="large")
        for idx, char in enumerate(st.session_state.search_results):
            with cols[idx % 5]:
                img_url = char['images']['jpg']['image_url']
                st.image(img_url, use_container_width=True)
                
                if st.button(
                    f"{char['name']}", 
                    key=f"select_char_{char['mal_id']}_{idx}",
                    use_container_width=True
                ):
                    st.session_state.selected_character = char
                    st.rerun()

# ========================================
# PAGE 2: UPLOAD IMAGE
# ========================================
elif st.session_state.current_page == "Upload Image":
    st.header("🖼️ Search by Image Upload")
    
    uploaded_file = st.file_uploader("Choose a Character Image...", type=["jpg", "png", "jpeg"])
    
    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        st.image(image, caption="Uploaded Image", width=300)
        
        if st.button("🔍 Image Scanning & Analysis"):
            with st.spinner("AI is identifying the face..."):
                detected_name = ai_vision_detect(image)
            
            if detected_name and detected_name != "Unknown":
                st.success(f"AI detected: **{detected_name}**")
                
                with st.spinner(f"Searching for {detected_name}..."):
                    info = get_one_character_data(detected_name)
                
                if info:
                    ai_text = ai_analyze_profile(info)
                    add_to_history('character_image', 'Image Upload', detected_name)
                    
                    st.markdown("---")
                    st.subheader(f"📋 Profile: {info['name']}")
                    
                    col1, col2 = st.columns([1, 2])
                    with col1:
                        st.image(info['images']['jpg']['image_url'], use_container_width=True)
                        st.metric("Favorites", info['favorites'])
                        
                        if st.button("❤️ Add to Favorites", key=f"fav_char_img_{info['mal_id']}", use_container_width=True):
                            success = add_to_favorites('characters', {
                                'id': info['mal_id'],
                                'name': info['name'],
                                'image': info['images']['jpg']['image_url'],
                                'favorites': info['favorites']
                            })
                            if success:
                                st.success("✅ Added to favorites!")
                            else:
                                st.warning("⚠️ Already in favorites!")
                    
                    with col2:
                        st.write(f"**Japanese name:** {info.get('name_kanji', 'N/A')}")
                        st.markdown("### 📄 AI Analysis Report")
                        st.success(ai_text, icon="📄")
                else:
                    st.warning(f"Cannot find detailed data for '{detected_name}'")
            else:
                st.error("AI couldn't identify this character. Try a different image!")

# ========================================
# PAGE 3: AI RECOMMEND
# ========================================
elif st.session_state.current_page == "AI Recommend":
    st.header("🤖 AI Personal Recommendation System")
    st.markdown("*Let AI understand you and suggest the perfect content!*")
    
    st.markdown("---")
    
    with st.form("recommendation_form"):
        st.markdown("### 📝 Tell me about yourself:")
        
        col1, col2 = st.columns(2)
        
        with col1:
            age = st.slider("🎂 Your age:", 5, 80, 20)
            
            mood = st.selectbox(
                "🎭 Current mood:",
                ["Happy & Energetic", "Calm & Relaxed", "Sad & Need Comfort", 
                 "Excited & Adventurous", "Thoughtful & Introspective"]
            )
        
        with col2:
            content_type = st.selectbox(
                "📖 What to recommend:",
                ["anime", "manga", "books"]
            )
            
            reading_style = st.selectbox(
                "📚 Your style:",
                ["Fast-paced action", "Slow & detailed", "Emotional & dramatic",
                 "Light & funny", "Dark & mysterious"]
            )
        
        interests = st.text_area(
            "💭 Your interests & hobbies:",
            placeholder="E.g: I love fantasy worlds, space exploration, psychology, cooking, sports...",
            height=100
        )
        
        submit = st.form_submit_button("✨ Get AI Recommendations", use_container_width=True)
    
    if submit:
        if not interests:
            st.warning("Please tell me about your interests!")
        else:
            with st.spinner("🤖 AI is analyzing your profile..."):
                recommendations = get_ai_recommendations(age, interests, mood, reading_style, content_type)
                
                if recommendations:
                    st.session_state.recommendations = recommendations
                    st.session_state.current_content_type = content_type
                    add_to_history('ai_recommend', f"{content_type} for {age}yo", f"{len(recommendations)} items")
                else:
                    st.error("Sorry, couldn't generate recommendations. Try again!")
    
    # Hiển thị recommendations
    if st.session_state.recommendations:
        st.markdown("---")
        st.success(f"### 🎯 Perfect Matches For You!")
        
        for idx, rec in enumerate(st.session_state.recommendations):
            with st.container():
                st.markdown(f"### {idx + 1}. {rec['title']}")
                
                col1, col2 = st.columns([1, 2])
                
                with col1:
                    content = search_content_by_keyword(rec['search_keyword'], st.session_state.current_content_type)
                    if content:
                        if st.session_state.current_content_type in ["anime", "manga"]:
                            img_url = content.get('images', {}).get('jpg', {}).get('image_url')
                            if img_url:
                                st.image(img_url, use_container_width=True)
                            st.write(f"⭐ **Score:** {content.get('score', 'N/A')}")
                            if st.session_state.current_content_type == "anime":
                                st.write(f"📺 **Episodes:** {content.get('episodes', 'N/A')}")
                            else:
                                st.write(f"📖 **Chapters:** {content.get('chapters', 'N/A')}")
                        else:
                            if content.get('thumbnail'):
                                st.image(content['thumbnail'], use_container_width=True)
                            st.write(f"✏️ **Author:** {', '.join(content.get('authors', ['N/A']))}")
                            if content.get('average_rating') != 'N/A':
                                st.write(f"⭐ **Rating:** {content['average_rating']}")
                
                with col2:
                    st.markdown(f"**🎭 Genre:** {rec['genre']}")
                    st.markdown("**💡 Why perfect for you:**")
                    st.info(rec['reason'])
                    
                    if content:
                        if st.session_state.current_content_type in ["anime", "manga"]:
                            synopsis = content.get('synopsis', 'No description')
                            if synopsis and len(synopsis) > 300:
                                synopsis = synopsis[:300] + "..."
                            st.markdown("**📄 Synopsis:**")
                            st.write(synopsis)
                            st.markdown(f"[🔗 View on MyAnimeList]({content.get('url', '#')})")
                        else:
                            description = content.get('description', 'No description')
                            if len(description) > 300:
                                description = description[:300] + "..."
                            st.markdown("**📄 Description:**")
                            st.write(description)
                            st.markdown(f"[🔗 Preview Book]({content.get('preview_link', '#')})")
                
                st.markdown("---")

# ========================================
# PAGE 4: DISCOVER MEDIA
# ========================================
elif st.session_state.current_page == "Discover Media":
    st.header("📚 Discover Books, Anime & Manga")
    
    content_type = st.selectbox(
        "📖 Content Type:",
        options=["anime", "manga", "books"]
    )
    
    if content_type in ["anime", "manga"]:
        with st.spinner(f"Loading {content_type} genres..."):
            genre_map = get_genre_map(content_type)
        
        if genre_map:
            excluded_genres = ["Hentai", "Ecchi"]
            genre_map = {k: v for k, v in genre_map.items() if v not in excluded_genres}
            genre_options = {v: k for k, v in genre_map.items()}
            genre_names = sorted(genre_options.keys())
            
            selected_genre_names = st.multiselect("🎭 Choose genres:", options=genre_names)
            selected_genre_ids = [genre_options[name] for name in selected_genre_names]
            order_by = st.selectbox("📅 Sort by:", options=["Newest", "Oldest", "Most Popular"])
            
            if st.button(f"🔍 Search {content_type.capitalize()}"):
                if not selected_genre_ids:
                    st.warning("Choose at least one genre!")
                else:
                    genre_params = ",".join(map(str, selected_genre_ids))
                    
                    if order_by == "Newest":
                        order_param, sort_param = "start_date", "desc"
                    elif order_by == "Oldest":
                        order_param, sort_param = "start_date", "asc"
                    else:
                        order_param, sort_param = "score", "desc"
                    
                    url = f"https://api.jikan.moe/v4/{content_type}?genres={genre_params}&order_by={order_param}&sort={sort_param}&limit=10"
                    add_to_history(f'{content_type}_genre', ', '.join(selected_genre_names))
                    
                    try:
                        response = requests.get(url)
                        if response.status_code == 200:
                            data = response.json()
                            results = data.get('data', [])
                            
                            if results:
                                st.success(f"✅ Found {len(results)} results!")
                                
                                for item in results:
                                    with st.expander(f"📺 {item.get('title', 'N/A')}"):
                                        col1, col2 = st.columns([1, 3])
                                        
                                        with col1:
                                            img_url = item.get('images', {}).get('jpg', {}).get('image_url')
                                            if img_url:
                                                st.image(img_url, use_container_width=True)
                                        
                                        with col2:
                                            st.write(f"**Japanese:** {item.get('title_japanese', 'N/A')}")
                                            st.write(f"**Score:** {item.get('score', 'N/A')} ⭐")
                                            
                                            aired = item.get('aired', {}) if content_type == "anime" else item.get('published', {})
                                            if aired:
                                                from_date = aired.get('from', 'N/A')
                                                if from_date and from_date != 'N/A':
                                                    year = from_date.split('-')[0]
                                                    st.write(f"**Year:** {year}")
                                            
                                            if content_type == "anime":
                                                st.write(f"**Episodes:** {item.get('episodes', 'N/A')}")
                                            else:
                                                st.write(f"**Chapters:** {item.get('chapters', 'N/A')}")
                                            
                                            genres = item.get('genres', [])
                                            if genres:
                                                genre_list = [g['name'] for g in genres]
                                                st.write(f"**Genres:** {', '.join(genre_list)}")
                                            
                                            synopsis = item.get('synopsis', 'No description')
                                            if synopsis and len(synopsis) > 200:
                                                synopsis = synopsis[:200] + "..."
                                            st.write(f"**Summary:** {synopsis}")
                                            st.markdown(f"[🔗 View]({item.get('url', '#')})")
                            else:
                                st.warning("No results found")
                        else:
                            st.error(f"API Error: {response.status_code}")
                    except Exception as e:
                        st.error(f"Error: {e}")
    
    elif content_type == "books":
        book_genres = get_book_genres()
        
        language = st.radio("🌐 Language:", ["English", "Vietnamese"], horizontal=True)
        lang_code = "vi" if language == "Vietnamese" else "en"
        
        if language == "Vietnamese":
            st.info("📌 Vietnamese books may have limited results")
        
        selected_book_genres = st.multiselect("📚 Choose book genres:", options=list(book_genres.keys()))
        
        if st.button("🔍 Search Books"):
            if not selected_book_genres:
                st.warning("Choose at least one genre!")
            else:
                genre_queries = [book_genres[g] for g in selected_book_genres]
                
                with st.spinner("Searching books..."):
                    books = search_books_by_genre(genre_queries, max_results=10, language=lang_code)
                
                add_to_history('books_genre', ', '.join(selected_book_genres))
                
                if books:
                    st.success(f"✅ Found {len(books)} books!")
                    
                    for book in books:
                        with st.expander(f"📖 {book['title']}"):
                            col1, col2 = st.columns([1, 3])
                            
                            with col1:
                                if book['thumbnail']:
                                    st.image(book['thumbnail'], use_container_width=True)
                            
                            with col2:
                                st.write(f"**Author:** {', '.join(book['authors'])}")
                                st.write(f"**Publisher:** {book['publisher']}")
                                st.write(f"**Published:** {book['published_date']}")
                                
                                if book['average_rating'] != 'N/A':
                                    st.write(f"**Rating:** {book['average_rating']} ⭐")
                                
                                description = book['description']
                                if len(description) > 300:
                                    description = description[:300] + "..."
                                st.write(f"**Description:** {description}")
                                
                                if book['preview_link']:
                                    st.markdown(f"[🔗 Preview]({book['preview_link']})")
                else:
                    st.warning("No books found")

# ========================================
# PAGE 5: FAVORITES
# ========================================
elif st.session_state.current_page == "Favorites":
    st.header("❤️ Your Favorite Characters")
    st.markdown("---")

    fav_chars = st.session_state.favorites.get('characters', [])

    if not fav_chars:
        st.info("You haven't added any characters to your favorites yet. Go find your waifu!")
    else:
        st.success(f"You have {len(fav_chars)} favorite characters!")
        
        def remove_from_favorites(char_id):
            st.session_state.favorites['characters'] = [
                char for char in st.session_state.favorites['characters'] if char.get('id') != char_id
            ]

        cols = st.columns(4, gap="large")
        for idx, char in enumerate(fav_chars):
            with cols[idx % 4]:
                st.image(char['image'], use_container_width=True, caption=char['name'])
                st.write(f"**{char['name']}**")
                st.write(f"⭐ {char['favorites']} Favorites")
                
                if st.button("🗑️ Remove", key=f"remove_fav_{char['id']}", use_container_width=True):
                    remove_from_favorites(char['id'])
                    st.rerun()
    
    st.markdown("---")
    st.markdown(f"**Total Favorites:** {len(fav_chars)}")

# ========================================
# PAGE 6: HISTORY
# ========================================
elif st.session_state.current_page == "History":
    st.header("📜 Search History")
    st.markdown("---")

    history = st.session_state.search_history

    if not history:
        st.info("No search history yet.")
    else:
        st.markdown(f"**Total entries:** {len(history)}")
        
        if st.button("🗑️ Clear History", type="secondary"):
            st.session_state.search_history = []
            st.rerun()

        st.markdown("---")

        for entry in history:
            with st.expander(f"[{entry['timestamp']}] - **{entry['type'].upper().replace('_', ' ')}**"):
                st.write(f"**Query:** `{entry['query']}`")
                if entry['result']:
                    st.write(f"**Result:** {entry['result']}")
