import cv2

# Use OpenCV's built-in QR code detector instead of pyzbar
detector = cv2.QRCodeDetector()


def read_barcodes(frame):
    # Detect and decode QR codes using OpenCV
    data, bbox, _ = detector.detectAndDecode(frame)
    
    if bbox is not None and data:
        # Draw rectangle around detected QR code
        bbox = bbox[0].astype(int)
        cv2.polylines(frame, [bbox], True, (0, 255, 0), 2)
        
        # Display the QR code data
        font = cv2.FONT_HERSHEY_DUPLEX
        cv2.putText(frame, data, (bbox[0][0], bbox[0][1] - 10), font, 0.5, (255, 255, 255), 1)
        
        # Write the barcode information to a text file
        with open("barcode_result.txt", mode='w') as file:
            file.write("recognised_barcode:" + data + "\n")
    
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
    

    
