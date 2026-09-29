# seed_db.py
from app.db.session import SessionLocal, engine, Base
from app.models.product import Category, Brand, Product, ProductAttribute, ProductAttributeValue, ProductVariant, VariantAttributeMapping
from app.models.enums import ProductStatus
from decimal import Decimal

def seed():
    db = SessionLocal()
    try:
        # 1. Create Category & Brand
        cat = Category(name="دستگاه", slug="device", is_landing_category=True)
        brand = Brand(name="VooPoo", slug="voopoo")
        db.add_all([cat, brand])
        db.flush()

        # 2. Create Product
        product = Product(
            title="دستگاه ویپ ووپو",
            title_en="VooPoo Drag X",
            description="A premium vape device.",
            status=ProductStatus.ACTIVE,
            category_id=cat.id,
            brand_id=brand.id
        )
        db.add(product)
        db.flush()

        # 3. Create Dynamic Attributes (Flavor & Color) - NO hardcoding!
        attr_flavor = ProductAttribute(product_id=product.id, name="Flavor")
        attr_color = ProductAttribute(product_id=product.id, name="Color")
        db.add_all([attr_flavor, attr_color])
        db.flush()

        # 4. Create Values
        val_mint = ProductAttributeValue(attribute_id=attr_flavor.id, value="Mint")
        val_black = ProductAttributeValue(attribute_id=attr_color.id, value="Black")
        db.add_all([val_mint, val_black])
        db.flush()

        # 5. Create Variant with Stock and Purchase Cost (1,000,000 Tomans)
        variant = ProductVariant(
            product_id=product.id,
            sku="VOO-MINT-BLK",
            purchase_cost=Decimal("1000000.00"), 
            stock_quantity=15
        )
        db.add(variant)
        db.flush()

        # 6. Map Variant to Values
        db.add_all([
            VariantAttributeMapping(variant_id=variant.id, attribute_value_id=val_mint.id),
            VariantAttributeMapping(variant_id=variant.id, attribute_value_id=val_black.id)
        ])
        
        db.commit()
        print("✅ Database seeded successfully! Check Swagger UI now.")
    except Exception as e:
        db.rollback()
        print(f"❌ Error seeding database: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed()