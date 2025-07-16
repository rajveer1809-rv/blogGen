from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
import google.generativeai as genai
from textwrap import dedent
import os

# API Keys configuration - Primary and backup keys
GEMINI_API_KEYS = [
    os.getenv('GEMINI_API_KEY', "AIzaSyBtPaVl-1y_e2_sUsWzBMoP7AldUdSNlxU"),  # Primary key
    os.getenv('GEMINI_API_KEY_BACKUP_1', "AIzaSyCoFogEj8LWnNWwffhQvsw4JKfQzbTpvYs"),  # Backup key 1
    os.getenv('GEMINI_API_KEY_BACKUP_2', "AIzaSyChFyd44dI20oZPcP_o4ZNPeU1AxMl3jAs"),  # Backup key 2
    os.getenv('GEMINI_API_KEY_BACKUP_3', "AIzaSyBO_EgfG5h0H8cr0npShoLfv_6n32aq4Rg"),  # Backup key 3
]

# Filter out empty keys
GEMINI_API_KEYS = [key for key in GEMINI_API_KEYS if key.strip()]

# Global variables to track API status
current_api_key_index = 0
API_CONFIGURED = False
model = None

def test_api_key(api_key):
    """Test if an API key is working"""
    try:
        genai.configure(api_key=api_key)
        test_model = genai.GenerativeModel(model_name='gemini-1.5-flash')
        # Try a simple test prompt
        response = test_model.generate_content("Hello")
        return response and hasattr(response, 'text')
    except Exception as e:
        print(f"❌ API key test failed: {e}")
        return False

def configure_api():
    """Configure the API with the first working key"""
    global API_CONFIGURED, model, current_api_key_index
    
    for i, api_key in enumerate(GEMINI_API_KEYS):
        if test_api_key(api_key):
            try:
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel(model_name='gemini-1.5-flash')
                API_CONFIGURED = True
                current_api_key_index = i
                print(f"✅ Gemini API configured successfully with key {i+1} (backup {i})")
                return True
            except Exception as e:
                print(f"❌ Failed to configure Gemini API with key {i+1}: {e}")
                continue
    
    API_CONFIGURED = False
    model = None
    print("❌ All API keys failed to configure")
    return False

def switch_to_next_api_key():
    """Switch to the next available API key"""
    global current_api_key_index, API_CONFIGURED, model
    
    current_api_key_index = (current_api_key_index + 1) % len(GEMINI_API_KEYS)
    print(f"🔄 Switching to API key {current_api_key_index + 1}")
    
    if configure_api():
        return True
    else:
        # If we've tried all keys, reset to first and return False
        current_api_key_index = 0
        return False

# Initial API configuration
configure_api()

@csrf_exempt  # For demo only; use proper CSRF in production
def blog_generator(request):
    global API_CONFIGURED, model
    
    result = None
    error = None
    
    print(f"🔍 Request method: {request.method}")
    
    if not API_CONFIGURED:
        error = "API not configured properly. Please check your Gemini API keys."
        print("❌ API not configured")
        return render(request, 'generator/blog_form.html', {
            'result': result,
            'error': error
        })
    
    if request.method == 'POST':
        print("📝 Processing POST request...")
        topic = request.POST.get('topic', '')
        style = request.POST.get('style', 'informative')
        length = request.POST.get('length', '500')
        audience = request.POST.get('audience', 'general')
        content_type = request.POST.get('content_type', 'how-to')
        
        print(f"📋 Form data - Topic: '{topic}', Style: {style}, Length: {length}")
        
        if not topic:
            error = 'Please enter a topic!'
            print("❌ No topic provided")
        else:
            prompt = dedent(f"""
            Write a {style}-style blog post about: {topic}
            
            Requirements:
            - Target length: {length} words
            - Target audience: {audience}
            - Content type: {content_type}
            - Include a compelling headline
            - Use proper paragraph structure
            - Add section headings if appropriate
            - Maintain a natural, human-like tone
            - Make it engaging and informative
            
            Format the response as a proper blog post with clear sections.
            """)
            
            print("🤖 Sending request to Gemini API...")
            
            # Try with current API key, fallback to others if needed
            max_retries = len(GEMINI_API_KEYS)
            retry_count = 0
            
            while retry_count < max_retries:
                try:
                    response = model.generate_content(prompt)
                    if response and hasattr(response, 'text'):
                        result = response.text
                        print(f"✅ Blog generated successfully! Length: {len(result)} characters")
                        break
                    else:
                        error = "No response received from the AI model"
                        print("❌ No response from API")
                        break
                except Exception as e:
                    print(f"❌ API Error with key {current_api_key_index + 1}: {e}")
                    retry_count += 1
                    
                    if retry_count < max_retries:
                        print(f"🔄 Retrying with next API key... (attempt {retry_count + 1}/{max_retries})")
                        if not switch_to_next_api_key():
                            error = "All API keys are currently unavailable. Please try again later."
                            break
                    else:
                        error = f"Failed to generate blog post after trying all API keys: {str(e)}"
                        print("❌ All API keys failed")
    else:
        print("📄 GET request - showing form")
    
    return render(request, 'generator/blog_form.html', {
        'result': result,
        'error': error
    })
