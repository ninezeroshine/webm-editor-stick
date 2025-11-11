import os
import struct
from flask import Flask, request, jsonify, send_file, render_template
from werkzeug.utils import secure_filename
import io

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10MB limit

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        if not file.filename or file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not file.filename.lower().endswith('.webm'):
            return jsonify({'error': 'Only .webm files are supported'}), 400
        
        duration_ms = request.form.get('duration', '3000')
        try:
            duration_ms = float(duration_ms)
        except ValueError:
            return jsonify({'error': 'Invalid duration value'}), 400
        
        # Read the entire file into memory
        file_data = bytearray(file.read())
        
        # Search for EBML Duration tag (0x4489)
        tag_found = False
        tag_position = -1
        
        # Search for the byte sequence 0x44 0x89
        for i in range(len(file_data) - 1):
            if file_data[i] == 0x44 and file_data[i + 1] == 0x89:
                tag_position = i
                tag_found = True
                break
        
        if not tag_found:
            return jsonify({'error': 'Duration tag (0x4489) not found in file'}), 400
        
        # The duration value is stored 3 bytes after the tag
        # According to EBML spec: tag (2 bytes) + size (1 byte) + data
        # Verify the size byte is 0x88 (indicates 8-byte float follows)
        if tag_position + 2 >= len(file_data):
            return jsonify({'error': 'File structure invalid - incomplete duration tag'}), 400
        
        size_byte = file_data[tag_position + 2]
        if size_byte != 0x88:
            return jsonify({'error': f'Unexpected EBML size byte: 0x{size_byte:02x} (expected 0x88)'}), 400
        
        duration_offset = tag_position + 3
        
        # Ensure we have enough bytes to write the duration
        if duration_offset + 8 > len(file_data):
            return jsonify({'error': 'File structure invalid - not enough bytes after duration tag'}), 400
        
        # Convert milliseconds to seconds (EBML Duration is stored in seconds)
        duration_seconds = duration_ms / 1000.0
        
        # Convert duration to IEEE 754 double-precision float (8 bytes, big-endian)
        duration_bytes = struct.pack('>d', duration_seconds)
        
        # Replace the 8-byte duration value
        for i in range(8):
            file_data[duration_offset + i] = duration_bytes[i]
        
        # Create a BytesIO object for the modified file
        modified_file = io.BytesIO(bytes(file_data))
        modified_file.seek(0)
        
        # Generate filename for download
        original_filename = secure_filename(file.filename or 'video')
        name_without_ext = os.path.splitext(original_filename)[0]
        download_filename = f"{name_without_ext}_fixed.webm"
        
        return send_file(
            modified_file,
            mimetype='video/webm',
            as_attachment=True,
            download_name=download_filename
        )
    
    except Exception as e:
        return jsonify({'error': f'Processing failed: {str(e)}'}), 500

@app.after_request
def add_header(response):
    # Disable caching for development
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
