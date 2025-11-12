import os
import struct
import subprocess
import tempfile
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
        # Size byte can be 0x88 (8-byte float) or 0x84 (4-byte float)
        if tag_position + 2 >= len(file_data):
            return jsonify({'error': 'File structure invalid - incomplete duration tag'}), 400
        
        size_byte = file_data[tag_position + 2]
        
        # Determine float size based on EBML size byte
        if size_byte == 0x88:
            float_size = 8  # double-precision
            pack_format = '>d'
        elif size_byte == 0x84:
            float_size = 4  # single-precision
            pack_format = '>f'
        else:
            return jsonify({'error': f'Unexpected EBML size byte: 0x{size_byte:02x} (expected 0x88 or 0x84)'}), 400
        
        duration_offset = tag_position + 3
        
        # Ensure we have enough bytes to write the duration
        if duration_offset + float_size > len(file_data):
            return jsonify({'error': 'File structure invalid - not enough bytes after duration tag'}), 400
        
        # Convert milliseconds to seconds (EBML Duration is stored in seconds)
        duration_seconds = duration_ms / 1000.0
        
        # Convert duration to IEEE 754 float (big-endian)
        duration_bytes = struct.pack(pack_format, duration_seconds)
        
        # Replace the duration value
        for i in range(float_size):
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

@app.route('/compress', methods=['POST'])
def compress_file():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        if not file.filename or file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not file.filename.lower().endswith('.webm'):
            return jsonify({'error': 'Only .webm files are supported'}), 400
        
        # Get compression parameters
        crf = request.form.get('crf', '30')  # Quality (15-35, lower = better quality)
        bitrate = request.form.get('bitrate', '500k')  # Target bitrate
        duration_ms = request.form.get('duration')  # Optional duration to set
        
        try:
            crf_value = int(crf)
            if not (15 <= crf_value <= 35):
                return jsonify({'error': 'CRF must be between 15 and 35'}), 400
        except ValueError:
            return jsonify({'error': 'Invalid CRF value'}), 400
        
        # Create temporary files
        with tempfile.NamedTemporaryFile(delete=False, suffix='.webm') as temp_input:
            file.save(temp_input.name)
            input_path = temp_input.name
        
        output_path = tempfile.mktemp(suffix='_compressed.webm')
        
        try:
            # FFmpeg command for WebM compression with VP9 codec
            ffmpeg_cmd = [
                'ffmpeg',
                '-i', input_path,
                '-c:v', 'libvpx-vp9',  # VP9 video codec
                '-pix_fmt', 'yuva420p',  # Pixel format with alpha channel support
                '-crf', str(crf_value),  # Quality setting
                '-b:v', bitrate,  # Target bitrate
                '-c:a', 'libopus',  # Opus audio codec
                '-b:a', '96k',  # Audio bitrate
                '-cpu-used', '4',  # Speed vs quality (0-5, higher = faster)
                '-row-mt', '1',  # Multi-threading
                '-deadline', 'good',  # Encoding quality mode
                '-auto-alt-ref', '0',  # Disable alt-ref frames for transparency
                '-y',  # Overwrite output
                output_path
            ]
            
            # Run FFmpeg
            result = subprocess.run(
                ffmpeg_cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            if result.returncode != 0:
                return jsonify({'error': f'FFmpeg error: {result.stderr}'}), 500
            
            # Read compressed file
            with open(output_path, 'rb') as f:
                compressed_data = bytearray(f.read())
            
            # Clean up temp files
            os.unlink(input_path)
            os.unlink(output_path)
            
            # Modify duration if provided
            if duration_ms:
                try:
                    duration_value = float(duration_ms)
                    if duration_value < 0:
                        return jsonify({'error': 'Duration must be non-negative'}), 400
                    
                    # Search for EBML Duration tag (0x4489)
                    tag_found = False
                    tag_position = -1
                    
                    for i in range(len(compressed_data) - 1):
                        if compressed_data[i] == 0x44 and compressed_data[i + 1] == 0x89:
                            tag_position = i
                            tag_found = True
                            break
                    
                    if tag_found and tag_position + 2 < len(compressed_data):
                        size_byte = compressed_data[tag_position + 2]
                        
                        # Determine float size based on EBML size byte
                        if size_byte == 0x88:
                            float_size = 8
                            pack_format = '>d'
                        elif size_byte == 0x84:
                            float_size = 4
                            pack_format = '>f'
                        else:
                            float_size = 0  # Skip duration modification if unknown format
                        
                        if float_size > 0:
                            duration_offset = tag_position + 3
                            
                            if duration_offset + float_size <= len(compressed_data):
                                duration_seconds = duration_value / 1000.0
                                duration_bytes = struct.pack(pack_format, duration_seconds)
                                
                                for i in range(float_size):
                                    compressed_data[duration_offset + i] = duration_bytes[i]
                
                except ValueError:
                    return jsonify({'error': 'Invalid duration value'}), 400
            
            # Create response
            compressed_file = io.BytesIO(bytes(compressed_data))
            compressed_file.seek(0)
            
            original_filename = secure_filename(file.filename or 'video')
            name_without_ext = os.path.splitext(original_filename)[0]
            download_filename = f"{name_without_ext}_compressed.webm"
            
            return send_file(
                compressed_file,
                mimetype='video/webm',
                as_attachment=True,
                download_name=download_filename
            )
        
        except subprocess.TimeoutExpired:
            if os.path.exists(input_path):
                os.unlink(input_path)
            if os.path.exists(output_path):
                os.unlink(output_path)
            return jsonify({'error': 'Compression timeout (max 5 minutes)'}), 500
        
        except Exception as e:
            if os.path.exists(input_path):
                os.unlink(input_path)
            if os.path.exists(output_path):
                os.unlink(output_path)
            raise e
    
    except Exception as e:
        return jsonify({'error': f'Compression failed: {str(e)}'}), 500

@app.after_request
def add_header(response):
    # Disable caching for development
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
