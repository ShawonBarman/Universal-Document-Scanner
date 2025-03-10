from flask import Flask, request, jsonify, render_template
import os
import logging
import traceback
import time
import io
from werkzeug.utils import secure_filename
from google.cloud import documentai
from google.oauth2 import service_account
from PIL import Image
import PyPDF2
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Google Cloud Configuration from Environment Variables
def create_service_account_credentials():
    """Create service account credentials from environment variables."""
    try:
        # Construct service account info from environment variables
        service_account_info = {
            "type": os.getenv('GOOGLE_CLOUD_TYPE', 'service_account'),
            "project_id": os.getenv('GOOGLE_CLOUD_PROJECT_ID', ''),
            "private_key_id": os.getenv('GOOGLE_CLOUD_PRIVATE_KEY_ID', ''),
            "private_key": os.getenv('GOOGLE_CLOUD_PRIVATE_KEY', '').replace('\\n', '\n'),
            "client_email": os.getenv('GOOGLE_CLOUD_CLIENT_EMAIL', ''),
            "client_id": os.getenv('GOOGLE_CLOUD_CLIENT_ID', ''),
            "auth_uri": os.getenv('GOOGLE_CLOUD_AUTH_URI', 'https://accounts.google.com/o/oauth2/auth'),
            "token_uri": os.getenv('GOOGLE_CLOUD_TOKEN_URI', 'https://oauth2.googleapis.com/token'),
            "auth_provider_x509_cert_url": os.getenv('GOOGLE_CLOUD_AUTH_PROVIDER_CERT_URL', 'https://www.googleapis.com/oauth2/v1/certs'),
            "client_x509_cert_url": os.getenv('GOOGLE_CLOUD_CLIENT_CERT_URL', ''),
            "universe_domain": os.getenv('GOOGLE_CLOUD_UNIVERSE_DOMAIN', 'googleapis.com')
        }

        # Remove any keys with empty values
        service_account_info = {k: v for k, v in service_account_info.items() if v}

        # Create credentials from the dictionary
        credentials = service_account.Credentials.from_service_account_info(service_account_info)
        
        return credentials
    except Exception as e:
        logger.error(f"Failed to create service account credentials: {str(e)}")
        raise

# Ensure upload directory exists
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Allowed file extensions
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'tiff', 'bmp', 'webp', 'pdf'}

def allowed_file(filename):
    """Check if the file extension is allowed."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def convert_image_to_pdf(image_bytes):
    """Convert image to PDF bytes."""
    try:
        image = Image.open(io.BytesIO(image_bytes))
        pdf_bytes = io.BytesIO()
        image.save(pdf_bytes, format='PDF')
        pdf_bytes.seek(0)
        return pdf_bytes.read()
    except Exception as e:
        logger.error(f"Image to PDF conversion error: {str(e)}")
        raise

def extract_document_data(document):
    """Extract structured data from Document AI result."""
    try:
        result_dict = {}
        detailed_data = []

        for entity in document.entities:
            # Comprehensive entity mapping
            entity_mapping = {
                'license_number': 'License Number',
                'full_name': 'Name',
                'date_of_birth': 'Date of Birth',
                'issue_date': 'Issue Date',
                'expiration_date': 'Expiration Date',
                'address': 'Address',
                'sex': 'Sex',
                'height': 'Height',
                'weight': 'Weight',
                'eye_color': 'Eye Color',
                'donor_status': 'Organ Donor',
                'class': 'License Class',
                'restrictions': 'Restrictions'
            }

            # Use mapped key or fallback to original type
            key = entity_mapping.get(entity.type_, entity.type_)
            result_dict[key] = entity.mention_text

            # Detailed data for advanced debugging
            detailed_data.append({
                'type': entity.type_,
                'value': entity.mention_text,
                'confidence': entity.confidence
            })

        return result_dict, detailed_data
    except Exception as e:
        logger.error(f"Data extraction error: {str(e)}")
        raise

# Initialize Google Cloud clients
try:
    # Create credentials
    credentials = create_service_account_credentials()
    
    # Get configuration from environment variables
    PROJECT_ID = os.getenv('GOOGLE_CLOUD_PROJECT_ID', '')
    LOCATION = os.getenv('GOOGLE_CLOUD_LOCATION', 'us')
    PROCESSOR_ID = os.getenv('GOOGLE_CLOUD_PROCESSOR_ID', '')

    # Initialize Document AI client
    docai_client = documentai.DocumentProcessorServiceClient(credentials=credentials)
    resource_name = docai_client.processor_path(PROJECT_ID, LOCATION, PROCESSOR_ID)
    
    logger.info("Google Cloud clients initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize Google Cloud clients: {str(e)}")
    raise

@app.route('/')
def index():
    """Render the main application page."""
    return render_template("license_index_for_document_ai.html")

@app.route('/extract', methods=['POST'])
def extract_document():
    """Main extraction route for documents."""
    # Explicitly import request at the beginning of the function
    from flask import request
    
    request_start_time = time.time()
    logger.debug("Received document extraction request")
    
    try:
        # Rest of the function remains the same
        if 'file' not in request.files:
            logger.error("No file in request")
            return jsonify({"status": "error", "message": "No file uploaded"})
        
        file = request.files['file']
        
        # Check if filename is empty
        if file.filename == '':
            logger.error("No selected file")
            return jsonify({"status": "error", "message": "No selected file"})
        
        # Check if file is allowed
        if not allowed_file(file.filename):
            logger.error(f"Invalid file type: {file.filename}")
            return jsonify({
                "status": "error", 
                "message": "Invalid file type. Please upload supported document."
            })
        
        # Read file content
        file_content = file.read()
        
        # Determine file type and convert if necessary
        file_type = os.path.splitext(file.filename)[1].lower()
        if file_type in ['.png', '.jpg', '.jpeg', '.gif', '.tiff', '.bmp', '.webp']:
            file_content = convert_image_to_pdf(file_content)
        
        try:
            # Prepare Document AI request
            raw_document = documentai.RawDocument(
                content=file_content, 
                mime_type="application/pdf"
            )
            
            # Send request to Document AI
            request = documentai.ProcessRequest(
                name=resource_name, 
                raw_document=raw_document
            )
            
            # Process the document
            result = docai_client.process_document(request=request)
            
            # Extract structured data
            extracted_data, detailed_data = extract_document_data(result.document)
            
            # Calculate processing time
            processing_time = time.time() - request_start_time
            
            return jsonify({
                "status": "success", 
                "data": extracted_data,
                "detailed_data": detailed_data,
                "raw_text": result.document.text,
                "processing_time": {
                    "total_time": f"{processing_time:.2f}s"
                }
            })

        except Exception as e:
            logger.error(f"Document AI processing error: {str(e)}")
            logger.error(traceback.format_exc())
            return jsonify({
                "status": "error", 
                "message": f"Document processing failed: {str(e)}"
            })

    except Exception as e:
        logger.error(f"Unhandled exception in /extract endpoint: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({"status": "error", "message": f"Server error: {str(e)}"})

if __name__ == '__main__':
    logger.info("Starting Flask application")
    app.run(debug=True, host='0.0.0.0', port=5005)