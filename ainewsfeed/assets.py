import os
import requests
import fitz  # PyMuPDF
import io
import time
from pathlib import Path
from PIL import Image

def generate_pdf_preview(pdf_path, paper_id, output_dir):
    """
    Renders the first page of the PDF as a PNG image.
    Returns the relative path to the image.
    """
    try:
        doc = fitz.open(pdf_path)
        page = doc.load_page(0)  # First page
        
        # Render high-res image (zoom=2 for better quality)
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
        
        preview_filename = f"{paper_id}_preview.png"
        preview_path = Path(output_dir) / preview_filename
        
        pix.save(preview_path)
        doc.close()
        
        return preview_filename
    except Exception as e:
        print(f"⚠️ Failed to generate preview for {paper_id}: {e}")
        return None

def download_pdf(pdf_url, output_path):
    """Downloads the PDF with a polite delay."""
    if os.path.exists(output_path):
        return True
        
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        response = requests.get(pdf_url, headers=headers, timeout=15)
        with open(output_path, 'wb') as f:
            f.write(response.content)
        time.sleep(1) # Polite delay
        return True
    except Exception as e:
        print(f"⚠️ PDF Download failed: {e}")
        return False

def extract_figures(pdf_path, paper_id, output_dir, max_figures=3):
    """
    Extracts the first N distinct images from the PDF.
    Returns a list of relative image paths.
    """
    # Setup directories
    figures_dir = Path(output_dir) / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)
    
    doc = fitz.open(pdf_path)
    saved_paths = []
    
    # Iterate through first 5 pages only (figures usually appear early)
    for page_index in range(min(5, len(doc))):
        if len(saved_paths) >= max_figures:
            break
            
        page = doc[page_index]
        image_list = page.get_images(full=True)
        
        for img_index, img in enumerate(image_list):
            if len(saved_paths) >= max_figures:
                break
                
            xref = img[0]
            try:
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                
                # --- Filter 1: Ignore small images (logos, icons) ---
                if len(image_bytes) < 15000: # < 15KB
                    continue
                
                # --- Filter 2: Ignore extreme aspect ratios (lines, dividers) ---
                pil_img = Image.open(io.BytesIO(image_bytes))
                w, h = pil_img.size
                if w < 200 or h < 200: # Too small pixel-wise
                    continue
                aspect = w / h
                if aspect > 5 or aspect < 0.2: # Too skinny
                    continue
                
                # Save Image
                filename = f"{paper_id}_p{page_index}_fig{img_index}.png"
                filepath = figures_dir / filename
                
                # Convert CMYK to RGB if needed
                if pil_img.mode == "CMYK":
                    pil_img = pil_img.convert("RGB")
                    
                pil_img.save(filepath)
                saved_paths.append(f"./figures/{filename}")
                
            except Exception:
                continue
                
    doc.close()
    return saved_paths