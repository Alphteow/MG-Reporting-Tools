#!/usr/bin/env python3
"""
AYG25 Competition Data Entry Form Launcher
Simple script to start the form server
"""

import os
import sys
import subprocess

def check_requirements():
    """Check if required packages are installed"""
    required_packages = ['flask', 'pandas', 'openpyxl']
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    return missing_packages

def install_requirements():
    """Install required packages"""
    print("📦 Installing required packages...")
    try:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'])
        print("✅ Requirements installed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error installing requirements: {e}")
        return False

def main():
    print("🏆 AYG25 Competition Data Entry Form Launcher")
    print("=" * 50)
    
    # Check if Excel file exists
    excel_file = "AYG25 Competition Schedule (3).xlsx"
    if not os.path.exists(excel_file):
        print(f"❌ Error: Excel file '{excel_file}' not found!")
        print("Please ensure the file exists in the current directory.")
        return
    
    # Check requirements
    missing_packages = check_requirements()
    if missing_packages:
        print(f"⚠️  Missing packages: {', '.join(missing_packages)}")
        print("Installing missing packages...")
        if not install_requirements():
            print("❌ Failed to install requirements. Please install manually:")
            print("pip install -r requirements.txt")
            return
    
    # Check if form files exist
    form_files = ['ayg_data_entry_form.html', 'form_backend.py']
    missing_files = [f for f in form_files if not os.path.exists(f)]
    
    if missing_files:
        print(f"❌ Missing form files: {', '.join(missing_files)}")
        return
    
    print("✅ All requirements met!")
    print("\n🚀 Starting the form server...")
    print("📱 The form will be available at: http://localhost:5000")
    print("💡 Press Ctrl+C to stop the server")
    print("-" * 50)
    
    # Start the Flask server
    try:
        from form_backend import app
        app.run(debug=False, host='0.0.0.0', port=5000)
    except KeyboardInterrupt:
        print("\n👋 Server stopped by user")
    except Exception as e:
        print(f"❌ Error starting server: {e}")

if __name__ == '__main__':
    main()
