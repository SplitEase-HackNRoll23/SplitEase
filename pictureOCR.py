import pytesseract as Tess 
Tess.pytesseract.tesseract_cmd = r'Tesseract-OCR\tesseract.exe'
import cv2
import re
import numpy as np



def image_parser(image):
  # Read in the image
  image = cv2.imread(image)

  # Pre-process the image by resizing and converting it to grayscale
  image = cv2.resize(image, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
  gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

  # Run Tesseract OCR on the image
  text = Tess.image_to_string(gray, lang="eng")

  # Split the OCR text into lines
  lines = text.split("\n")

  # Initialize a list to store the item details
  items = []

  # Iterate over the lines of text
  for line in lines:
    # Use a regular expression to search for the item details
    m = re.search(r'(\d+)\s+(.*?)\s+([\d\.]+)', line)
    if m:
      # If the regular expression matches, extract the quantity, description, and price
      quantity = int(m.group(1))
      description = m.group(2)
      price = float(m.group(3))

      # Add the item details to the list
      if (quantity < 10 and "Total" not in description and price < 200):
        items.append((quantity, description, price))

  answer = []
  # Print the item details
  for item in items:
    answer.append(f'{item[0]} {item[1]} Cost: {item[2]:.2f}')
  
  return answer

# image = 'images/receipt.jpg'

# print(image_parser(image))


