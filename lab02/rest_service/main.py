from fastapi import FastAPI, HTTPException, File, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional
import shutil
import os

app = FastAPI()

UPLOAD_DIR = "uploaded_images"

if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

class Product(BaseModel):
    id: int
    name: str
    description: str
    icon: Optional[str] = None

class ProductCreate(BaseModel):
    name: str
    description: str

class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None

products_db: List[Product] = []
next_product_id = 0

@app.post("/product", response_model=Product)
async def create_product(product_data: ProductCreate):
    global next_product_id
    new_product = Product(id=next_product_id, name=product_data.name, description=product_data.description, icon=None)
    products_db.append(new_product)
    next_product_id += 1
    return new_product

@app.get("/product/{product_id}", response_model=Product)
async def get_product(product_id: int):
    for product in products_db:
        if product.id == product_id:
            return product
    raise HTTPException(status_code=404, detail="Product not found")

@app.put("/product/{product_id}", response_model=Product)
async def update_product(product_id: int, product_data: ProductUpdate):
    for index, product in enumerate(products_db):
        if product.id == product_id:
            updated_product_data = product.model_copy(update=product_data.model_dump(exclude_unset=True))
            products_db[index] = updated_product_data
            return updated_product_data
    raise HTTPException(status_code=404, detail="Product not found")

@app.delete("/product/{product_id}", response_model=Product)
async def delete_product(product_id: int):
    for index, product in enumerate(products_db):
        if product.id == product_id:
            deleted_product = products_db.pop(index)
            return deleted_product
    raise HTTPException(status_code=404, detail="Product not found")

@app.get("/products", response_model=List[Product])
async def get_all_products():
    return products_db

@app.post("/product/{product_id}/image", response_model=Product)
async def upload_product_image(product_id: int, file: UploadFile = File(...)):
    product_found = None
    product_index = -1
    for index, p in enumerate(products_db):
        if p.id == product_id:
            product_found = p
            product_index = index
            break

    if not product_found:
        raise HTTPException(status_code=404, detail="Product not found")

    safe_filename = f"{product_id}_{file.filename.replace(' ', '_')}"
    file_path = os.path.join(UPLOAD_DIR, safe_filename)

    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    finally:
        file.file.close()

    updated_product_data = product_found.model_copy(update={"icon": safe_filename})
    products_db[product_index] = updated_product_data
    
    return updated_product_data

@app.get("/product/{product_id}/image")
async def get_product_image(product_id: int):
    product_found = None
    for p in products_db:
        if p.id == product_id:
            product_found = p
            break

    if not product_found:
        raise HTTPException(status_code=404, detail="Product not found")

    if not product_found.icon:
        raise HTTPException(status_code=404, detail="Image not found for this product")

    image_path = os.path.join(UPLOAD_DIR, product_found.icon)

    if not os.path.exists(image_path):
        raise HTTPException(status_code=404, detail="Image file not found on server")

    return FileResponse(image_path)

# Чтобы запустить сервис локально, выполните в терминале, находясь в директории lab02/rest_service:
# uvicorn main:app --reload 