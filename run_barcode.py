#!/usr/bin/env python3
import os
import sys

# Set library path before importing pyzbar
os.environ['DYLD_LIBRARY_PATH'] = '/opt/homebrew/lib'

# Manually load zbar library before pyzbar tries to
from ctypes import cdll
try:
    cdll.LoadLibrary('/opt/homebrew/lib/libzbar.dylib')
except Exception as e:
    print(f"Warning: Could not preload zbar: {e}")

# Now patch pyzbar to use the correct library path
import pyzbar.zbar_library as zbar_lib

original_load = zbar_lib.load

def patched_load():
    try:
        return cdll.LoadLibrary('/opt/homebrew/lib/libzbar.dylib'), []
    except:
        return original_load()

zbar_lib.load = patched_load

# Now import and run the main program
import cv2
from pyzbar import pyzbar
import requests
import json


def lookup_barcode(barcode_number):
    """Fetch product information from online databases"""
    try:
        # Try Open Food Facts API (works for food products)
        url = f"https://world.openfoodfacts.org/api/v0/product/{barcode_number}.json"
        response = requests.get(url, timeout=3)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 1:
                product = data.get('product', {})
                info = {
                    'name': product.get('product_name', 'Unknown'),
                    'brand': product.get('brands', 'Unknown'),
                    'category': product.get('categories', 'Unknown'),
                    'barcode': barcode_number
                }
                return info
        
        # Fallback: try UPC Item DB API
        url = f"https://api.upcitemdb.com/prod/trial/lookup?upc={barcode_number}"
        response = requests.get(url, timeout=3)
        if response.status_code == 200:
            data = response.json()
            if data.get('items'):
                item = data['items'][0]
                info = {
                    'name': item.get('title', 'Unknown'),
                    'brand': item.get('brand', 'Unknown'),
                    'category': item.get('category', 'Unknown'),
                    'barcode': barcode_number
                }
                return info
                
    except Exception as e:
        print(f"Lookup error: {e}")
    
    return {'name': 'Not found', 'brand': 'N/A', 'category': 'N/A', 'barcode': barcode_number}


def read_barcodes(frame):
    # Find barcodes in the frame and draw rectangles around them
    barcodes = pyzbar.decode(frame)
    for barcode in barcodes:
        x, y, w, h = barcode.rect
        barcode_info = barcode.data.decode('utf-8')
        barcode_type = barcode.type
        
        # Fetch product information from internet
        print(f"\nBarcode detected: {barcode_info} (Type: {barcode_type})")
        print("Fetching product information...")
        product_info = lookup_barcode(barcode_info)
        
        # Draw rectangle around barcode
        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 3)

        # Display the information on the frame
        font = cv2.FONT_HERSHEY_DUPLEX
        y_offset = y - 10
        
        # Show barcode number
        cv2.putText(frame, f"Code: {barcode_info}", (x, y_offset), font, 0.6, (0, 255, 0), 2)
        y_offset -= 25
        
        # Show product name
        cv2.putText(frame, f"Name: {product_info['name'][:30]}", (x, y_offset), font, 0.5, (255, 255, 255), 1)
        y_offset -= 20
        
        # Show brand
        cv2.putText(frame, f"Brand: {product_info['brand'][:30]}", (x, y_offset), font, 0.5, (255, 255, 255), 1)
        
        # Write detailed information to file
        with open("barcode_result.txt", mode='w') as file:
            file.write(f"Barcode: {barcode_info}\n")
            file.write(f"Type: {barcode_type}\n")
            file.write(f"Product Name: {product_info['name']}\n")
            file.write(f"Brand: {product_info['brand']}\n")
            file.write(f"Category: {product_info['category']}\n")
        
        # Print to console
        print(f"✓ Product: {product_info['name']}")
        print(f"✓ Brand: {product_info['brand']}")
        print(f"✓ Category: {product_info['category']}")
        print(f"✓ Saved to barcode_result.txt")
        
    return frame


def main():
    camera = cv2.VideoCapture(0)
    ret, frame = camera.read()
    while ret:
        ret, frame = camera.read()
        frame = read_barcodes(frame)
        cv2.imshow('Barcode/QR code reader', frame)
        if cv2.waitKey(1) & 0xFF == 27:  # Press 'ESC' to quit
            break
    camera.release()
    cv2.destroyAllWindows()


if __name__ == '__main__':
    main()
