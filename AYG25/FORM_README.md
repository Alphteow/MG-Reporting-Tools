# 🏆 AYG25 Competition Data Entry Form

A comprehensive web-based form system for collecting and managing Asian Youth Games 2025 competition data. This system provides an intuitive interface for sport coordinators to input competition results and automatically integrates the data with the existing Excel files.

## 🌟 Features

### ✨ User-Friendly Interface
- **Responsive Design**: Works on desktop, tablet, and mobile devices
- **Dynamic Form Fields**: Shows sport-specific fields based on selection
- **Real-time Validation**: Immediate feedback on required fields and data formats
- **Progress Tracking**: Visual indicators for form completion

### 🔧 Smart Data Processing
- **Automatic Excel Integration**: Directly updates the competition schedule
- **Data Validation**: Ensures consistency with existing data formats
- **Backup System**: Creates automatic backups before any changes
- **WhatsApp Message Generation**: Automatically generates formatted messages
- **Multi-format Support**: Updates both main schedule and TeamSG website format

### 📊 Sport-Specific Features
- **Timing Events**: Specialized fields for swimming and athletics
- **Score Events**: Dedicated fields for boxing, pencak silat, wrestling
- **Head-to-Head Results**: Support for team sports and individual competitions
- **Record Tracking**: Personal bests, national records, Asian records
- **Medal Management**: Gold, silver, bronze medal tracking

## 🚀 Quick Start

### Option 1: Simple Launch (Recommended)
```bash
python launch_form.py
```

### Option 2: Manual Setup
```bash
# Install requirements
pip install -r requirements.txt

# Start the server
python form_backend.py
```

### Option 3: Using Virtual Environment
```bash
# Activate virtual environment
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install requirements
pip install -r requirements.txt

# Start the server
python form_backend.py
```

## 📱 Accessing the Form

Once the server is running, open your web browser and navigate to:
```
http://localhost:5000
```

## 📋 Form Fields Guide

### Required Fields
- **Sport**: Select from dropdown (Aquatics, Athletics, Badminton, etc.)
- **Discipline**: Specific discipline within the sport
- **Event**: Detailed event name (include gender)
- **Stage/Round**: Competition round (Heats, Quarterfinals, etc.)
- **Competition Date**: Date of the event
- **Start Time**: Bahrain time (24-hour format)
- **Venue**: Competition venue name
- **Athlete Name**: Full name of Singapore athlete

### Optional Fields
- **End Time**: Event end time
- **Competitor Information**: Opponent name and country
- **Position**: Final position in the round
- **Total Competitors**: Number of participants
- **Advancement**: Whether athlete advanced to next round

### Sport-Specific Fields
- **Timing**: For swimming and athletics events
- **Scores**: For boxing, pencak silat, wrestling
- **Head-to-Head Results**: Win/Lose/Draw for team sports
- **Records**: Personal bests, national records, etc.
- **Medals**: Gold, silver, bronze achievements

## 🔄 Data Flow

1. **Form Submission**: User fills out the web form
2. **Validation**: System validates all required fields and formats
3. **Backup Creation**: Automatic backup of Excel file before changes
4. **Data Processing**: Form data is formatted and processed
5. **Excel Integration**: Data is added to both competition schedule sheets
6. **Message Generation**: WhatsApp and web result messages are created
7. **Confirmation**: User receives confirmation of successful submission

## 📁 File Structure

```
MajorGamesReporting/
├── ayg_data_entry_form.html    # Main web form
├── form_backend.py             # Flask backend server
├── launch_form.py              # Simple launcher script
├── requirements.txt            # Python dependencies
├── FORM_README.md              # This documentation
├── AYG25 Competition Schedule (3).xlsx  # Main Excel file
└── backups/                    # Automatic backup folder
    └── backup_YYYYMMDD_HHMMSS.xlsx
```

## 🛠️ API Endpoints

The system provides several API endpoints for data management:

- `GET /` - Main form interface
- `POST /submit_competition_data` - Submit new competition data
- `GET /get_sports` - Get list of available sports
- `GET /get_athletes` - Get list of registered athletes
- `GET /get_venues` - Get list of competition venues
- `GET /download_excel` - Download updated Excel file
- `GET /status` - System status and health check

## 🔒 Data Security

- **Automatic Backups**: Every submission creates a timestamped backup
- **Input Validation**: All data is validated before processing
- **Error Handling**: Comprehensive error handling and logging
- **Data Integrity**: Checks ensure Excel file structure is maintained

## 📊 Integration with Existing Systems

### Excel File Integration
The form automatically updates two main sheets:
1. **"AYG2025 Competition Schedule"** - Detailed competition data
2. **"TeamSG Website Format"** - Website-ready format

### WhatsApp Integration
- Uses existing templates from "Whatsapp Mapping" sheet
- Generates formatted messages with athlete names, results, and achievements
- Supports different message formats for different sports and rounds

### Data Validation
- Validates against existing sport names from "TEAMSG Sport Name" sheet
- Checks athlete names against "TEAMSG Athlete Names" sheet
- Ensures venue names match existing competition venues

## 🎯 Best Practices

### For Sport Coordinators
1. **Complete Required Fields**: Ensure all mandatory fields are filled
2. **Use Consistent Formats**: Follow the suggested formats for names and times
3. **Verify Data**: Double-check athlete names and competition details
4. **Submit Promptly**: Enter results as soon as competitions finish

### For System Administrators
1. **Regular Backups**: The system creates automatic backups, but consider additional backup strategies
2. **Monitor Logs**: Check server logs for any errors or issues
3. **Update Data**: Keep sport and athlete lists current
4. **Test Regularly**: Verify the system works correctly before major competitions

## 🚨 Troubleshooting

### Common Issues

**Form won't load:**
- Check if the server is running (`python launch_form.py`)
- Verify you're accessing `http://localhost:5000`
- Check console for error messages

**Submission fails:**
- Ensure all required fields are filled
- Check date and time formats
- Verify Excel file exists and is accessible

**Excel file errors:**
- Check file permissions
- Ensure file isn't open in Excel
- Verify backup files in the `backups/` folder

### Getting Help
1. Check the console output for error messages
2. Look at the backup files to restore previous data if needed
3. Verify all required files are present
4. Ensure Python dependencies are installed correctly

## 🔄 Updates and Maintenance

### Regular Maintenance
- **Weekly**: Check backup folder and clean old backups if needed
- **Monthly**: Verify all sports and athletes are up to date
- **Before Events**: Test the form and ensure all coordinators have access

### System Updates
- Keep Python dependencies updated
- Regularly backup the Excel file manually
- Monitor system performance and logs

## 📞 Support

For technical support or questions:
1. Check this documentation first
2. Review the console output for error messages
3. Verify all requirements are met
4. Test with a simple entry to isolate issues

---

**🏆 Good luck with the Asian Youth Games 2025! This system will help ensure accurate and timely competition data collection.**
