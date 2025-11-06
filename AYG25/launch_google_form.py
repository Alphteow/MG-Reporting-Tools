#!/usr/bin/env python3
"""
AYG25 Competition Data Entry Form Launcher - Google Sheets Integration
Simple script to start the Google Sheets form server
"""

import os
import sys
import subprocess

def check_requirements():
    """Check if required packages are installed"""
    required_packages = ['flask', 'pandas', 'gspread', 'google.auth']
    missing_packages = []
    
    for package in required_packages:
        try:
            if package == 'google.auth':
                import google.auth
            else:
                __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    return missing_packages

def install_requirements():
    """Install required packages"""
    print("📦 Installing required packages for Google Sheets integration...")
    try:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', 'requirements_google.txt'])
        print("✅ Requirements installed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error installing requirements: {e}")
        return False

def check_google_credentials():
    """Check if Google credentials are configured"""
    credentials_file = "google_credentials.json"
    env_credentials = os.environ.get('GOOGLE_CREDENTIALS_JSON')
    
    if os.path.exists(credentials_file):
        print(f"✅ Found Google credentials file: {credentials_file}")
        return True
    elif env_credentials:
        print("✅ Found Google credentials in environment variable")
        return True
    else:
        print("⚠️  Google credentials not found")
        print("   Please follow the setup guide in GOOGLE_SETUP.md")
        return False

def main():
    print("🏆 AYG25 Competition Data Entry Form Launcher (Google Sheets)")
    print("=" * 60)
    
    # Check if required files exist
    form_files = ['ayg_data_entry_form.html', 'form_backend_google.py', 'google_sheets_integration.py']
    missing_files = [f for f in form_files if not os.path.exists(f)]
    
    if missing_files:
        print(f"❌ Missing form files: {', '.join(missing_files)}")
        return
    
    # Check requirements
    missing_packages = check_requirements()
    if missing_packages:
        print(f"⚠️  Missing packages: {', '.join(missing_packages)}")
        print("Installing missing packages...")
        if not install_requirements():
            print("❌ Failed to install requirements. Please install manually:")
            print("pip install -r requirements_google.txt")
            return
    
    # Check Google credentials
    credentials_ok = check_google_credentials()
    if not credentials_ok:
        print("\n📋 To set up Google credentials:")
        print("1. Follow the guide in GOOGLE_SETUP.md")
        print("2. Create google_credentials.json file")
        print("3. Share your spreadsheet with the service account")
        print("\n⚠️  The server will start but Google Sheets integration won't work without credentials.")
        
        response = input("\nDo you want to continue anyway? (y/N): ")
        if response.lower() != 'y':
            return
    
    print("✅ All requirements met!")
    print("\n🚀 Starting the Google Sheets form server...")
    print("📊 Spreadsheet ID: 1xzFo8qBtGGSqW9V9UyaPVGqT6w5UIypw9hIgV3JZmto")
    print("📋 Sheet Name: Data Collection")
    print("📱 Form: http://localhost:5000")
    print("🔧 Admin Panel: http://localhost:5000/admin")
    print("💡 Press Ctrl+C to stop the server")
    print("-" * 60)
    
    # Start the Flask server
    try:
        from form_backend_google import app
        app.run(debug=False, host='0.0.0.0', port=5000)
    except KeyboardInterrupt:
        print("\n👋 Server stopped by user")
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        print("\n🔧 Troubleshooting:")
        print("1. Check if Google credentials are properly configured")
        print("2. Verify the spreadsheet ID is correct")
        print("3. Ensure all required packages are installed")
        print("4. Check the GOOGLE_SETUP.md guide")

if __name__ == '__main__':
    main()
