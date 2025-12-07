import requests

def search_books_by_genre(genres, max_results=10, language="en"):
    """
    Tìm kiếm sách theo thể loại từ Google Books API.
    
    Args:
        genres: List các thể loại (ví dụ: ["fiction", "mystery"])
        max_results: Số lượng kết quả tối đa (mặc định 10)
        language: Ngôn ngữ sách ("en" = English, "vi" = Vietnamese)
    
    Returns:
        List các dict chứa thông tin sách
    """
    # Nối các thể loại thành query string
    genre_query = "+".join([f"subject:{g}" for g in genres])
    
    url = f"https://www.googleapis.com/books/v1/volumes"
    params = {
        "q": genre_query,
        "maxResults": max_results,
        "orderBy": "relevance",
        "printType": "books"
    }
    
    # Chỉ thêm langRestrict nếu là tiếng Anh
    # Với tiếng Việt, để trống để tìm rộng hơn
    if language == "en":
        params["langRestrict"] = "en"
    
    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            items = data.get("items", [])
            
            # Parse dữ liệu thành format dễ dùng
            books = []
            for item in items:
                volume_info = item.get("volumeInfo", {})
                
                # Lấy thumbnail (ưu tiên lớn hơn)
                image_links = volume_info.get("imageLinks", {})
                thumbnail = image_links.get("thumbnail") or image_links.get("smallThumbnail")
                
                book = {
                    "id": item.get("id"),
                    "title": volume_info.get("title", "N/A"),
                    "authors": volume_info.get("authors", ["Unknown"]),
                    "publisher": volume_info.get("publisher", "N/A"),
                    "published_date": volume_info.get("publishedDate", "N/A"),
                    "description": volume_info.get("description", "No description available"),
                    "page_count": volume_info.get("pageCount", "N/A"),
                    "categories": volume_info.get("categories", ["N/A"]),
                    "average_rating": volume_info.get("averageRating", "N/A"),
                    "thumbnail": thumbnail,
                    "preview_link": volume_info.get("previewLink", "#"),
                    "info_link": volume_info.get("infoLink", "#")
                }
                books.append(book)
            
            return books
        else:
            print(f"Google Books API Error: {response.status_code}")
            return []
    except Exception as e:
        print(f"Error connecting to Google Books: {e}")
        return []


def search_books_by_keyword(keyword, max_results=10, language="en"):
    """
    Tìm kiếm sách theo từ khóa (tên sách, tác giả, chủ đề).
    
    Args:
        keyword: Từ khóa tìm kiếm
        max_results: Số lượng kết quả
        language: Ngôn ngữ sách ("en" = English, "vi" = Vietnamese)
    
    Returns:
        List các dict chứa thông tin sách
    """
    url = f"https://www.googleapis.com/books/v1/volumes"
    params = {
        "q": keyword,
        "maxResults": max_results,
        "orderBy": "relevance"
    }
    
    if language == "en":
        params["langRestrict"] = "en"
    
    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            items = data.get("items", [])
            
            books = []
            for item in items:
                volume_info = item.get("volumeInfo", {})
                image_links = volume_info.get("imageLinks", {})
                thumbnail = image_links.get("thumbnail") or image_links.get("smallThumbnail")
                
                book = {
                    "id": item.get("id"),
                    "title": volume_info.get("title", "N/A"),
                    "authors": volume_info.get("authors", ["Unknown"]),
                    "publisher": volume_info.get("publisher", "N/A"),
                    "published_date": volume_info.get("publishedDate", "N/A"),
                    "description": volume_info.get("description", "No description available"),
                    "page_count": volume_info.get("pageCount", "N/A"),
                    "categories": volume_info.get("categories", ["N/A"]),
                    "average_rating": volume_info.get("averageRating", "N/A"),
                    "thumbnail": thumbnail,
                    "preview_link": volume_info.get("previewLink", "#"),
                    "info_link": volume_info.get("infoLink", "#")
                }
                books.append(book)
            
            return books
        else:
            return []
    except Exception as e:
        print(f"Error: {e}")
        return []


# Danh sách thể loại sách phổ biến
BOOK_GENRES = {
    "Fiction": "fiction",
    "Non-Fiction": "nonfiction",
    "Mystery": "mystery",
    "Thriller": "thriller",
    "Romance": "romance",
    "Science Fiction": "science+fiction",
    "Fantasy": "fantasy",
    "Horror": "horror",
    "Biography": "biography",
    "History": "history",
    "Self-Help": "self+help",
    "Business": "business",
    "Cooking": "cooking",
    "Travel": "travel",
    "Young Adult": "young+adult",
    "Children": "children",
    "Poetry": "poetry",
    "Psychology": "psychology",
    "Philosophy": "philosophy",
    "Religion": "religion"
}


def get_book_genres():
    """Trả về dict các thể loại sách"""
    return BOOK_GENRES