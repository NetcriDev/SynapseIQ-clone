
# Utils
def paginate(items, page: int, page_size: int):
    total_items = len(items)
    total_pages = (total_items + page_size - 1) // page_size
    start = (page - 1) * page_size
    end = start + page_size
    return {
        "items": items[start:end],
        "page": page,
        "page_size": page_size,
        "total_items": total_items,
        "total_pages": total_pages
    }