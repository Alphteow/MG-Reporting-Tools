#!/usr/bin/env python3
"""
AYG25 Competition Data Entry Form Backend
Handles form submissions and integrates with Excel files
"""

import pandas as pd
import openpyxl
from openpyxl import Workbook, load_workbook
from datetime import datetime, time
import json
import os
import logging
from flask import Flask, request, jsonify, send_file, render_template_string
from werkzeug.utils import secure_filename
import re

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

class AYGDataProcessor:
    def __init__(self, excel_file_path):
        self.excel_file_path = excel_file_path
        self.backup_dir = "backups"
        self.ensure_backup_dir()
        
    def ensure_backup_dir(self):
        """Create backup directory if it doesn't exist"""
        if not os.path.exists(self.backup_dir):
            os.makedirs(self.backup_dir)
    
    def create_backup(self):
        """Create a backup of the current Excel file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"backup_{timestamp}.xlsx"
        backup_path = os.path.join(self.backup_dir, backup_filename)
        
        try:
            import shutil
            shutil.copy2(self.excel_file_path, backup_path)
            logger.info(f"Backup created: {backup_path}")
            return backup_path
        except Exception as e:
            logger.error(f"Failed to create backup: {str(e)}")
            return None
    
    def load_excel_data(self):
        """Load all sheets from the Excel file"""
        try:
            xls = pd.ExcelFile(self.excel_file_path)
            data = {}
            
            for sheet_name in xls.sheet_names:
                data[sheet_name] = pd.read_excel(self.excel_file_path, sheet_name=sheet_name)
            
            logger.info(f"Loaded {len(data)} sheets from Excel file")
            return data
        except Exception as e:
            logger.error(f"Error loading Excel file: {str(e)}")
            return None
    
    def validate_form_data(self, data):
        """Validate the form data before processing"""
        required_fields = [
            'sport', 'discipline', 'event', 'round', 'date', 
            'time_start_hr', 'venue', 'athlete_name'
        ]
        
        missing_fields = []
        for field in required_fields:
            if not data.get(field):
                missing_fields.append(field)
        
        if missing_fields:
            return False, f"Missing required fields: {', '.join(missing_fields)}"
        
        # Validate date format
        try:
            datetime.strptime(data['date'], '%Y-%m-%d')
        except ValueError:
            return False, "Invalid date format"
        
        # Validate time format
        try:
            datetime.strptime(data['time_start_hr'], '%H:%M')
        except ValueError:
            return False, "Invalid time format"
        
        return True, "Valid"
    
    def format_athlete_name(self, name):
        """Format athlete name to match existing data"""
        if not name:
            return ""
        
        # Convert to uppercase and clean up
        formatted_name = str(name).strip().upper()
        
        # Remove extra spaces
        formatted_name = re.sub(r'\s+', ' ', formatted_name)
        
        return formatted_name
    
    def format_event_name(self, event):
        """Format event name to match existing data"""
        if not event:
            return ""
        
        # Convert to uppercase and standardize
        formatted_event = str(event).strip().upper()
        
        # Standardize gender prefixes
        formatted_event = re.sub(r'^MEN\s+', 'MEN ', formatted_event)
        formatted_event = re.sub(r'^WOMEN\s+', 'WOMEN ', formatted_event)
        formatted_event = re.sub(r'^MIXED\s+', 'MIXED ', formatted_event)
        
        # Standardize measurements
        formatted_event = re.sub(r'(\d+)\s*M\b', r'\1M', formatted_event)
        formatted_event = re.sub(r'(\d+)\s*-\s*(\d+)\s*KG', r'\1 - \2KG', formatted_event)
        
        return formatted_event
    
    def generate_whatsapp_message(self, data):
        """Generate WhatsApp message based on the data"""
        try:
            # Load WhatsApp templates
            xls = pd.ExcelFile(self.excel_file_path)
            if 'Whatsapp Mapping' in xls.sheet_names:
                templates_df = pd.read_excel(self.excel_file_path, sheet_name='Whatsapp Mapping')
                
                # Find matching template
                sport = data['sport'].upper()
                discipline = data['discipline'].upper()
                event = data['event'].upper()
                round_name = data['round'].upper()
                
                matching_template = None
                for _, row in templates_df.iterrows():
                    if (row['Sport'].upper() == sport and 
                        row['Discipline'].upper() == discipline and
                        event in row['Event'].upper() and
                        round_name in row['Rounds'].upper()):
                        matching_template = row['Templates']
                        break
                
                if matching_template:
                    # Replace placeholders
                    message = str(matching_template)
                    message = message.replace('{SPORT}', data['sport'])
                    message = message.replace('{DISCIPLINE}', data['discipline'])
                    message = message.replace('{EVENT}', data['event'])
                    message = message.replace('{ROUNDS}', data['round'])
                    message = message.replace('{NAME}', data['athlete_name'])
                    message = message.replace('{TIME}', data.get('sgp_time', ''))
                    message = message.replace('{PLACEMENT}', str(data.get('position', '')))
                    message = message.replace('{TOTAL}', str(data.get('total_competitors', '')))
                    
                    # Add advancement status
                    if data.get('advanced') == 'YES':
                        message += "\n\nAdvanced to next round!"
                    elif data.get('medal'):
                        message += f"\n\nWon {data['medal']} medal!"
                    
                    return message
        except Exception as e:
            logger.error(f"Error generating WhatsApp message: {str(e)}")
        
        # Fallback message
        return f"*{data['sport']} - {data['event']} {data['round']}*\n\n{data['athlete_name']} (SINGAPORE)\n\nCompetition details updated."
    
    def generate_web_result(self, data):
        """Generate web result text"""
        result_parts = []
        
        # Add athlete name and country
        result_parts.append(f"{data['athlete_name']} (SINGAPORE)")
        
        # Add result details
        if data.get('sgp_score') and data.get('competitor_score'):
            result_parts.append(f"Score: {data['sgp_score']} - {data['competitor_score']}")
        
        if data.get('sgp_time'):
            result_parts.append(f"Time: {data['sgp_time']}")
        
        if data.get('position') and data.get('total_competitors'):
            result_parts.append(f"Position: {data['position']} out of {data['total_competitors']}")
        
        if data.get('medal'):
            result_parts.append(f"Medal: {data['medal']}")
        
        if data.get('advanced') == 'YES':
            result_parts.append("Advanced to next round!")
        
        if data.get('records'):
            records = data['records'].split(', ')
            result_parts.append(f"Records: {', '.join(records)}")
        
        return "<br><br>".join(result_parts)
    
    def add_to_competition_schedule(self, data):
        """Add new entry to the competition schedule"""
        try:
            # Create backup
            self.create_backup()
            
            # Load the Excel file
            xls = pd.ExcelFile(self.excel_file_path)
            
            # Get the main competition schedule sheet
            if 'AYG2025 Competition Schedule' in xls.sheet_names:
                schedule_df = pd.read_excel(self.excel_file_path, sheet_name='AYG2025 Competition Schedule')
            else:
                logger.error("Competition schedule sheet not found")
                return False, "Competition schedule sheet not found"
            
            # Create new row data
            new_row = {}
            
            # Map form data to Excel columns (based on the analysis)
            column_mapping = {
                'Unnamed: 2': data.get('date', ''),
                'Unnamed: 4': data.get('time_start_hr', '').replace(':', ''),
                'Unnamed: 6': data.get('time_start_hr', '').replace(':', ''),  # Singapore time
                'Unnamed: 8': data['sport'],
                'Unnamed: 9': data['discipline'],
                'Unnamed: 10': 'WOMEN' if 'WOMEN' in data['event'].upper() else 'MEN' if 'MEN' in data['event'].upper() else '',
                'Unnamed: 11': self.format_event_name(data['event']),
                'Unnamed: 12': data['round'],
                'Unnamed: 13': data['venue'],
                'Unnamed: 15': self.format_athlete_name(data['athlete_name']),
                'Unnamed: 17': data.get('competitor_name', ''),
                'Unnamed: 18': data.get('competitor_country', ''),
                'Unnamed: 19': data.get('position', ''),
                'Unnamed: 20': data.get('total_competitors', ''),
                'Unnamed: 21': data.get('medal', ''),
                'Unnamed: 22': data.get('sgp_score', ''),
                'Unnamed: 23': data.get('competitor_score', ''),
                'Unnamed: 24': data.get('sgp_time', ''),
                'Unnamed: 25': data.get('competitor_time', ''),
                'Unnamed: 26': data.get('h2h_result', ''),
                'Unnamed: 27': data.get('advanced', ''),
                'Unnamed: 28': data.get('records', ''),
                'Time: 56.08s\nFinished 2nd out of 8. Advanced to the Finals.\nNew Personal Best.': data.get('remarks', ''),
                'Unnamed: 31': data.get('personal_best', ''),
                'Unnamed: 32': data.get('records', ''),
                'Unnamed: 34': self.generate_whatsapp_message(data),
                'Unnamed: 35': self.generate_web_result(data),
            }
            
            # Create new row with all columns
            new_row_data = {}
            for col in schedule_df.columns:
                if col in column_mapping:
                    new_row_data[col] = column_mapping[col]
                else:
                    new_row_data[col] = ''
            
            # Add the new row
            new_df = pd.concat([schedule_df, pd.DataFrame([new_row_data])], ignore_index=True)
            
            # Save back to Excel
            with pd.ExcelWriter(self.excel_file_path, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
                new_df.to_excel(writer, sheet_name='AYG2025 Competition Schedule', index=False)
            
            logger.info("Successfully added new entry to competition schedule")
            return True, "Entry added successfully"
            
        except Exception as e:
            logger.error(f"Error adding to competition schedule: {str(e)}")
            return False, f"Error: {str(e)}"
    
    def add_to_teamsg_format(self, data):
        """Add new entry to TeamSG Website Format"""
        try:
            # Load the Excel file
            xls = pd.ExcelFile(self.excel_file_path)
            
            if 'TeamSG Website Format' in xls.sheet_names:
                teamsg_df = pd.read_excel(self.excel_file_path, sheet_name='TeamSG Website Format')
            else:
                logger.error("TeamSG Website Format sheet not found")
                return False, "TeamSG Website Format sheet not found"
            
            # Create new row data for TeamSG format
            new_row_data = {
                'Unnamed: 1': f"{data['date']} {data['time_start_hr']}:00",
                'Unnamed: 2': data['sport'],
                'Unnamed: 3': self.format_event_name(data['event']),
                'Unnamed: 4': self.format_athlete_name(data['athlete_name']),
                'Unnamed: 5': data['round'],
                'Unnamed: 6': data['venue'],
                'Unnamed: 7': self.generate_web_result(data),
                'Unnamed: 9': f"{data['date']} {data['time_start_hr']}:00",
                'Unnamed: 10': data['sport'],
                'Unnamed: 11': self.format_event_name(data['event']),
                'Unnamed: 12': self.format_athlete_name(data['athlete_name']),
                'Unnamed: 13': data['round'],
                'Unnamed: 14': data['venue'],
                'Unnamed: 15': self.generate_web_result(data),
                'Unnamed: 16': False,  # REMOVED flag
            }
            
            # Add the new row
            new_df = pd.concat([teamsg_df, pd.DataFrame([new_row_data])], ignore_index=True)
            
            # Save back to Excel
            with pd.ExcelWriter(self.excel_file_path, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
                new_df.to_excel(writer, sheet_name='TeamSG Website Format', index=False)
            
            logger.info("Successfully added new entry to TeamSG Website Format")
            return True, "Entry added to TeamSG format"
            
        except Exception as e:
            logger.error(f"Error adding to TeamSG format: {str(e)}")
            return False, f"Error: {str(e)}"

# Initialize the data processor
excel_file_path = "AYG25 Competition Schedule (3).xlsx"
data_processor = AYGDataProcessor(excel_file_path)

@app.route('/')
def index():
    """Serve the main form"""
    try:
        with open('ayg_data_entry_form.html', 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return "Form file not found. Please ensure ayg_data_entry_form.html exists.", 404

@app.route('/submit_competition_data', methods=['POST'])
def submit_competition_data():
    """Handle form submission"""
    try:
        data = request.get_json()
        
        # Validate the data
        is_valid, message = data_processor.validate_form_data(data)
        if not is_valid:
            return jsonify({'success': False, 'error': message}), 400
        
        # Add to competition schedule
        success1, msg1 = data_processor.add_to_competition_schedule(data)
        if not success1:
            return jsonify({'success': False, 'error': f"Competition schedule error: {msg1}"}), 500
        
        # Add to TeamSG format
        success2, msg2 = data_processor.add_to_teamsg_format(data)
        if not success2:
            return jsonify({'success': False, 'error': f"TeamSG format error: {msg2}"}), 500
        
        logger.info(f"Successfully processed submission for {data['athlete_name']}")
        
        return jsonify({
            'success': True, 
            'message': 'Data submitted successfully',
            'whatsapp_message': data_processor.generate_whatsapp_message(data)
        })
        
    except Exception as e:
        logger.error(f"Error processing submission: {str(e)}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@app.route('/get_sports', methods=['GET'])
def get_sports():
    """Get list of available sports"""
    try:
        data = data_processor.load_excel_data()
        if data and 'TEAMSG Sport Name' in data:
            sports = data['TEAMSG Sport Name']['Sport Name'].dropna().tolist()
            return jsonify({'sports': sports})
        else:
            # Fallback sports list
            return jsonify({'sports': [
                'Aquatics', 'Athletics', 'Badminton', 'Basketball', 'Boxing',
                'Pencak Silat', 'Triathlon', 'Weightlifting', 'Wrestling'
            ]})
    except Exception as e:
        logger.error(f"Error getting sports: {str(e)}")
        return jsonify({'sports': []}), 500

@app.route('/get_athletes', methods=['GET'])
def get_athletes():
    """Get list of available athletes"""
    try:
        data = data_processor.load_excel_data()
        if data and 'TEAMSG Athlete Names' in data:
            athletes = data['TEAMSG Athlete Names']['Name'].dropna().tolist()
            return jsonify({'athletes': athletes})
        else:
            return jsonify({'athletes': []})
    except Exception as e:
        logger.error(f"Error getting athletes: {str(e)}")
        return jsonify({'athletes': []}), 500

@app.route('/get_venues', methods=['GET'])
def get_venues():
    """Get list of available venues"""
    try:
        data = data_processor.load_excel_data()
        venues = set()
        
        # Extract venues from competition schedule
        if data and 'AYG2025 Competition Schedule' in data:
            venue_col = 'Unnamed: 13'  # Based on the analysis
            if venue_col in data['AYG2025 Competition Schedule'].columns:
                venue_data = data['AYG2025 Competition Schedule'][venue_col].dropna()
                venues.update([str(v).strip() for v in venue_data if str(v).strip()])
        
        venues_list = sorted(list(venues))
        return jsonify({'venues': venues_list})
    except Exception as e:
        logger.error(f"Error getting venues: {str(e)}")
        return jsonify({'venues': []}), 500

@app.route('/download_excel', methods=['GET'])
def download_excel():
    """Download the updated Excel file"""
    try:
        return send_file(
            excel_file_path,
            as_attachment=True,
            download_name=f"AYG25_Competition_Schedule_Updated_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    except Exception as e:
        logger.error(f"Error downloading Excel file: {str(e)}")
        return "Error downloading file", 500

@app.route('/status', methods=['GET'])
def status():
    """Get system status"""
    try:
        data = data_processor.load_excel_data()
        if data:
            return jsonify({
                'status': 'healthy',
                'sheets_loaded': len(data),
                'last_backup': os.listdir(data_processor.backup_dir)[-1] if os.path.exists(data_processor.backup_dir) and os.listdir(data_processor.backup_dir) else None
            })
        else:
            return jsonify({'status': 'error', 'message': 'Cannot load Excel file'}), 500
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    # Check if Excel file exists
    if not os.path.exists(excel_file_path):
        logger.error(f"Excel file not found: {excel_file_path}")
        print(f"❌ Error: Excel file '{excel_file_path}' not found!")
        print("Please ensure the file exists in the current directory.")
        exit(1)
    
    print("🚀 Starting AYG25 Data Entry Form Server...")
    print(f"📄 Excel file: {excel_file_path}")
    print("🌐 Form will be available at: http://localhost:5000")
    print("📊 API endpoints:")
    print("   - GET  /                 (Main form)")
    print("   - POST /submit_competition_data (Submit data)")
    print("   - GET  /get_sports       (Get sports list)")
    print("   - GET  /get_athletes     (Get athletes list)")
    print("   - GET  /get_venues       (Get venues list)")
    print("   - GET  /download_excel   (Download updated Excel)")
    print("   - GET  /status           (System status)")
    print("\n💡 Press Ctrl+C to stop the server")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
