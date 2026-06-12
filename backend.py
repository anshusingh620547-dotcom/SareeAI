import sqlite3

def search_sarees(occasion=None, max_budget=None, fabric=None, color=None):
    """
    Connects to the database and searches for sarees based on user preferences.
    If a preference is missing or 'Any', it ignores that filter.
    """
    conn = sqlite3.connect("saree_inventory.db")
    cursor = conn.cursor()
    
    # Start with a base query that selects everything
    query = "SELECT name, occasion, budget, fabric, color, image_url FROM sarees WHERE 1=1"
    parameters = []
    
    # Dynamically build the query based on what fields are provided
    if occasion and occasion != "Any":
        query += " AND occasion = ?"
        parameters.append(occasion)
        
    if max_budget:
        query += " AND budget <= ?"
        parameters.append(int(max_budget))
        
    if fabric and fabric != "Any":
        query += " AND fabric = ?"
        parameters.append(fabric)
        
    if color and color != "Any":
        query += " AND color = ?"
        parameters.append(color)
        
    cursor.execute(query, parameters)
    results = cursor.fetchall()
    conn.close()
    
    # Convert database rows into a clean list of dictionaries for our frontend
    matched_sarees = []
    for row in results:
        matched_sarees.append({
            "name": row[0],
            "occasion": row[1],
            "budget": row[2],
            "fabric": row[3],
            "color": row[4],
            "image_url": row[5]
        })
        
    return matched_sarees

# Quick local test to make sure it works perfectly
if __name__ == "__main__":
    print("Testing backend database search function...")
    # Let's test searching for a Wedding saree under 20,000 rupees
    sample_results = search_sarees(occasion="Wedding", max_budget=20000)
    print(f"Found {len(sample_results)} matches:")
    for saree in sample_results:
        print(f"- {saree['name']} ({saree['fabric']}, {saree['color']}) Costs: Rs.{saree['budget']}")