#!/usr/bin/env python3
"""
Embeddable Highlights Widget Server
Serves a widget that developers can embed in their pages
"""

from flask import Flask, render_template, jsonify, request, send_from_directory
from flask_cors import CORS
import logging
from pathlib import Path
from generate_highlights import HighlightsGenerator
import json

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__, 
            template_folder='templates',
            static_folder='static')
CORS(app)  # Enable CORS for cross-origin embedding

# Default configuration (can be overridden via API)
DEFAULT_CONFIG = {
    'spreadsheet_id': None,
    'sheet_name': None,
    'credentials_file': None,
    'date_filter': None,  # Optional: filter by specific date (YYYY-MM-DD)
    'sport_filter': None  # Optional: filter by specific sport
}


@app.route('/')
def index():
    """Main page showing how to use the widget"""
    return render_template('widget_index.html')


@app.route('/widget')
def widget():
    """
    Widget page - embeddable in an iframe
    Query parameters:
    - spreadsheet_id: Google Sheets spreadsheet ID (required)
    - sheet_name: Worksheet name (required)
    - credentials_file: Path to credentials (optional, can use env var)
    - date: Filter by specific date YYYY-MM-DD (optional)
    - sport: Filter by specific sport (optional)
    """
    spreadsheet_id = request.args.get('spreadsheet_id')
    sheet_name = request.args.get('sheet_name')
    credentials_file = request.args.get('credentials_file')
    date_filter = request.args.get('date')
    sport_filter = request.args.get('sport')
    
    if not spreadsheet_id or not sheet_name:
        return render_template('widget_error.html', 
                             error="Missing required parameters: spreadsheet_id and sheet_name are required")
    
    config = {
        'spreadsheet_id': spreadsheet_id,
        'sheet_name': sheet_name,
        'credentials_file': credentials_file,
        'date_filter': date_filter,
        'sport_filter': sport_filter
    }
    
    return render_template('widget.html', config=config)


@app.route('/api/highlights')
def api_highlights():
    """
    API endpoint to fetch highlights data
    Query parameters:
    - spreadsheet_id: Google Sheets spreadsheet ID (required)
    - sheet_name: Worksheet name (required)
    - credentials_file: Path to credentials (optional)
    - date: Filter by specific date YYYY-MM-DD (optional)
    - sport: Filter by specific sport (optional)
    """
    try:
        spreadsheet_id = request.args.get('spreadsheet_id')
        sheet_name = request.args.get('sheet_name')
        credentials_file = request.args.get('credentials_file')
        date_filter = request.args.get('date')
        sport_filter = request.args.get('sport')
        
        if not spreadsheet_id or not sheet_name:
            return jsonify({
                'error': 'Missing required parameters: spreadsheet_id and sheet_name are required'
            }), 400
        
        # Initialize generator
        generator = HighlightsGenerator(
            spreadsheet_id=spreadsheet_id,
            sheet_name=sheet_name,
            credentials_file=credentials_file
        )
        
        # Load data
        df = generator.load_data()
        
        if df.empty:
            return jsonify({
                'highlights': [],
                'message': 'No highlights data found'
            })
        
        # Apply filters
        from config import COLUMN_MAPPINGS
        if date_filter:
            date_col = COLUMN_MAPPINGS.get('DATE_SGP', 'DATE (SGP)')
            if date_col in df.columns:
                df = df[df[date_col].astype(str).str.contains(date_filter, na=False)]
        
        if sport_filter:
            sport_col = COLUMN_MAPPINGS.get('SPORT', 'SPORT')
            if sport_col in df.columns:
                df = df[df[sport_col].astype(str).str.contains(sport_filter, na=False)]
        
        # Format highlights
        highlights = []
        for _, row in df.iterrows():
            highlight = generator.format_highlight_data(row)
            highlights.append(highlight)
        
        # Group highlights
        grouped_data = generator.group_highlights(df)
        
        # Separate H2H and non-H2H highlights
        h2h_highlights = [h for h in highlights if h['type'] == 'h2h']
        non_h2h_highlights = [h for h in highlights if h['type'] == 'non-h2h']
        
        # Group by sport and gender for easier rendering
        def group_by_sport_gender(highlight_list):
            groups = {}
            for h in highlight_list:
                sport = h.get('sport', 'Unknown')
                gender = h.get('event_gender', 'Mixed')
                key = f"{sport}|{gender}"
                
                if key not in groups:
                    groups[key] = {
                        'sport': sport,
                        'gender': gender,
                        'highlights': []
                    }
                groups[key]['highlights'].append(h)
            
            # Group each sport's highlights by event
            for key, group in groups.items():
                events = {}
                for h in group['highlights']:
                    event = h.get('event', 'Unknown')
                    stage = h.get('stage', '')
                    event_key = f"{event}|{stage}"
                    
                    if event_key not in events:
                        events[event_key] = {
                            'event': event,
                            'stage': stage,
                            'highlights': []
                        }
                    events[event_key]['highlights'].append(h)
                
                group['events'] = list(events.values())
            
            return list(groups.values())
        
        h2h_groups = group_by_sport_gender(h2h_highlights)
        non_h2h_groups = group_by_sport_gender(non_h2h_highlights)
        
        return jsonify({
            'highlights': highlights,
            'h2h_groups': h2h_groups,
            'non_h2h_groups': non_h2h_groups,
            'total': len(highlights),
            'h2h_count': len(h2h_highlights),
            'non_h2h_count': len(non_h2h_highlights)
        })
        
    except Exception as e:
        logger.error(f"Error fetching highlights: {str(e)}")
        return jsonify({
            'error': str(e)
        }), 500


@app.route('/embed.js')
def embed_script():
    """JavaScript file for easy embedding"""
    script = """
(function() {
    function createWidget(config) {
        var iframe = document.createElement('iframe');
        var params = new URLSearchParams();
        
        params.set('spreadsheet_id', config.spreadsheet_id);
        params.set('sheet_name', config.sheet_name);
        
        if (config.credentials_file) {
            params.set('credentials_file', config.credentials_file);
        }
        if (config.date) {
            params.set('date', config.date);
        }
        if (config.sport) {
            params.set('sport', config.sport);
        }
        
        var baseUrl = config.baseUrl || window.location.origin;
        iframe.src = baseUrl + '/widget?' + params.toString();
        iframe.width = '1920';
        iframe.height = '1080';
        iframe.style.border = 'none';
        iframe.style.display = 'block';
        iframe.style.margin = '0 auto';
        iframe.style.maxWidth = '100%';
        iframe.style.height = 'auto';
        iframe.style.aspectRatio = '1920 / 1080';
        
        var container = document.getElementById(config.containerId || 'highlights-widget');
        if (container) {
            container.appendChild(iframe);
        } else {
            console.error('Container element not found. Please create an element with id="highlights-widget"');
        }
    }
    
    // Auto-initialize if data attributes are present
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function() {
            var widgetEl = document.getElementById('highlights-widget');
            if (widgetEl) {
                var config = {
                    spreadsheet_id: widgetEl.dataset.spreadsheetId,
                    sheet_name: widgetEl.dataset.sheetName,
                    credentials_file: widgetEl.dataset.credentialsFile || null,
                    date: widgetEl.dataset.date || null,
                    sport: widgetEl.dataset.sport || null,
                    baseUrl: widgetEl.dataset.baseUrl || window.location.origin
                };
                
                if (config.spreadsheet_id && config.sheet_name) {
                    createWidget(config);
                }
            }
        });
    } else {
        var widgetEl = document.getElementById('highlights-widget');
        if (widgetEl) {
            var config = {
                spreadsheet_id: widgetEl.dataset.spreadsheetId,
                sheet_name: widgetEl.dataset.sheetName,
                credentials_file: widgetEl.dataset.credentialsFile || null,
                date: widgetEl.dataset.sheetName || null,
                sport: widgetEl.dataset.sport || null,
                baseUrl: widgetEl.dataset.baseUrl || window.location.origin
            };
            
            if (config.spreadsheet_id && config.sheet_name) {
                createWidget(config);
            }
        }
    }
    
    // Export for manual initialization
    window.HighlightsWidget = {
        create: createWidget
    };
})();
"""
    return script, 200, {'Content-Type': 'application/javascript'}


if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)

