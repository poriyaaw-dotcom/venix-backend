with open('app/api/v1/admin.py', 'r') as f:
    content = f.read()

old_text = "    db.delete(brand)\n    db.commit()\n    return {\"message\": \"Brand deleted successfully\"}"
new_text = "    # Safely unlink products from this brand so the database doesn't crash\n    db.query(Product).filter(Product.brand_id == brand_id).update({\"brand_id\": None})\n    \n    db.delete(brand)\n    db.commit()\n    return {\"message\": \"Brand deleted successfully\"}"

if old_text in content:
    content = content.replace(old_text, new_text)
    with open('app/api/v1/admin.py', 'w') as f:
        f.write(content)
    print("✅ Brand delete button fixed safely!")
else:
    print("❌ Could not find the exact code. Let me know!")
