import pandas as pd
import openpyxl
from openpyxl.utils import get_column_letter
import numpy as np

def analyze_competition_schedule(file_path):
    """Analyze the AYG25 Competition Schedule Excel file to understand its structure"""
    
    print("="*80)
    print("AYG25 COMPETITION SCHEDULE ANALYSIS")
    print("="*80)
    
    try:
        # Read all sheets to understand the structure
        xls = pd.ExcelFile(file_path)
        print(f"\n📄 Available sheets in {file_path}:")
        for i, sheet in enumerate(xls.sheet_names, 1):
            print(f"  {i}. {sheet}")
        
        # Analyze each sheet
        for sheet_name in xls.sheet_names:
            print(f"\n" + "="*60)
            print(f"SHEET: {sheet_name}")
            print("="*60)
            
            try:
                # Read the sheet
                df = pd.read_excel(file_path, sheet_name=sheet_name)
                
                print(f"📊 Sheet dimensions: {df.shape[0]} rows × {df.shape[1]} columns")
                print(f"📋 Column names:")
                for i, col in enumerate(df.columns, 1):
                    print(f"   {i:2d}. {col}")
                
                # Show first few rows
                print(f"\n📝 First 5 rows of data:")
                print(df.head().to_string())
                
                # Check for empty cells
                empty_cells = df.isnull().sum()
                if empty_cells.sum() > 0:
                    print(f"\n⚠️  Empty cells by column:")
                    for col, count in empty_cells.items():
                        if count > 0:
                            percentage = (count / len(df)) * 100
                            print(f"   {col}: {count} empty ({percentage:.1f}%)")
                
                # Check for potential key fields
                key_fields = []
                for col in df.columns:
                    col_lower = str(col).lower()
                    if any(keyword in col_lower for keyword in ['sport', 'event', 'athlete', 'name', 'date', 'time', 'venue', 'discipline']):
                        key_fields.append(col)
                
                if key_fields:
                    print(f"\n🔑 Potential key fields identified:")
                    for field in key_fields:
                        unique_count = df[field].nunique()
                        print(f"   {field}: {unique_count} unique values")
                        
                        # Show sample values
                        sample_values = df[field].dropna().head(3).tolist()
                        print(f"      Sample: {sample_values}")
                
                # Check for patterns in the data
                print(f"\n🔍 Data patterns:")
                
                # Check if there are any sport-related columns
                sport_cols = [col for col in df.columns if 'sport' in str(col).lower()]
                if sport_cols:
                    print(f"   Sports identified in columns: {sport_cols}")
                    for col in sport_cols:
                        sports = df[col].dropna().unique()
                        print(f"      {col}: {len(sports)} unique sports")
                        if len(sports) <= 10:
                            print(f"         {list(sports)}")
                
                # Check for date/time columns
                date_cols = [col for col in df.columns if any(keyword in str(col).lower() for keyword in ['date', 'time', 'start', 'end'])]
                if date_cols:
                    print(f"   Date/Time columns: {date_cols}")
                
                # Check for athlete/participant columns
                athlete_cols = [col for col in df.columns if any(keyword in str(col).lower() for keyword in ['athlete', 'participant', 'name', 'player'])]
                if athlete_cols:
                    print(f"   Athlete/Participant columns: {athlete_cols}")
                
            except Exception as e:
                print(f"❌ Error reading sheet '{sheet_name}': {str(e)}")
        
        # Provide recommendations
        print(f"\n" + "="*80)
        print("RECOMMENDATIONS FOR DATA COLLECTION")
        print("="*80)
        
        print(f"\n💡 Based on the analysis, here are recommendations for getting people to fill in appropriate fields:")
        
        # Analyze the main sheet (usually the first one or the largest one)
        main_sheet = None
        max_rows = 0
        for sheet_name in xls.sheet_names:
            try:
                df = pd.read_excel(file_path, sheet_name=sheet_name)
                if len(df) > max_rows:
                    max_rows = len(df)
                    main_sheet = (sheet_name, df)
            except:
                continue
        
        if main_sheet:
            sheet_name, df = main_sheet
            print(f"\n📋 Primary sheet analysis: '{sheet_name}'")
            
            # Identify required vs optional fields
            required_fields = []
            optional_fields = []
            
            for col in df.columns:
                col_lower = str(col).lower()
                empty_count = df[col].isnull().sum()
                empty_percentage = (empty_count / len(df)) * 100
                
                # Determine if field is required based on completion rate and field type
                if any(keyword in col_lower for keyword in ['sport', 'event', 'athlete', 'name', 'date', 'time']):
                    if empty_percentage < 20:  # Less than 20% empty suggests it's important
                        required_fields.append(col)
                    else:
                        optional_fields.append(col)
                else:
                    optional_fields.append(col)
            
            print(f"\n✅ REQUIRED FIELDS (high completion rate):")
            for field in required_fields:
                empty_count = df[field].isnull().sum()
                completion_rate = ((len(df) - empty_count) / len(df)) * 100
                print(f"   • {field} ({completion_rate:.1f}% complete)")
            
            print(f"\n📝 OPTIONAL/ADDITIONAL FIELDS:")
            for field in optional_fields:
                empty_count = df[field].isnull().sum()
                completion_rate = ((len(df) - empty_count) / len(df)) * 100
                print(f"   • {field} ({completion_rate:.1f}% complete)")
            
            # Provide specific recommendations
            print(f"\n🎯 SPECIFIC RECOMMENDATIONS:")
            print(f"   1. CREATE VALIDATION RULES:")
            print(f"      - Use data validation dropdowns for sport names")
            print(f"      - Create standardized athlete name formats")
            print(f"      - Set up date/time validation")
            
            print(f"\n   2. PROVIDE CLEAR INSTRUCTIONS:")
            print(f"      - Create a 'Data Entry Guide' sheet with examples")
            print(f"      - Include field descriptions and expected formats")
            print(f"      - Add sample data for each sport")
            
            print(f"\n   3. IMPLEMENT QUALITY CONTROLS:")
            print(f"      - Use conditional formatting to highlight incomplete rows")
            print(f"      - Create summary sheets showing completion status")
            print(f"      - Add data validation to prevent common errors")
            
            print(f"\n   4. ORGANIZE BY SPORT:")
            print(f"      - Consider creating separate sheets for each sport")
            print(f"      - Or use filters/grouping by sport for easier data entry")
            print(f"      - Assign sport-specific coordinators")
        
    except Exception as e:
        print(f"❌ Error analyzing file: {str(e)}")
        return None
    
    return xls.sheet_names

def create_data_entry_template(file_path, output_path=None):
    """Create a data entry template with validation rules"""
    
    if output_path is None:
        output_path = file_path.replace('.xlsx', '_DataEntryTemplate.xlsx')
    
    print(f"\n" + "="*80)
    print("CREATING DATA ENTRY TEMPLATE")
    print("="*80)
    
    try:
        # Read the original file
        xls = pd.ExcelFile(file_path)
        
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            
            # Copy the main sheet (assuming first sheet is the main one)
            main_sheet_name = xls.sheet_names[0]
            main_df = pd.read_excel(file_path, sheet_name=main_sheet_name)
            
            # Create the main data entry sheet
            main_df.to_excel(writer, sheet_name='Data Entry', index=False)
            
            # Create instruction sheet
            instructions_data = {
                'Field': [],
                'Description': [],
                'Required': [],
                'Format/Example': [],
                'Validation Rules': []
            }
            
            # Analyze each column and create instructions
            for col in main_df.columns:
                col_lower = str(col).lower()
                instructions_data['Field'].append(col)
                
                # Determine if required
                empty_count = main_df[col].isnull().sum()
                completion_rate = ((len(main_df) - empty_count) / len(main_df)) * 100
                required = "Yes" if completion_rate > 80 else "Optional"
                instructions_data['Required'].append(required)
                
                # Add descriptions based on column name
                if 'sport' in col_lower:
                    instructions_data['Description'].append('Name of the sport/discipline')
                    instructions_data['Format/Example'].append('e.g., Athletics, Swimming, Basketball')
                    instructions_data['Validation Rules'].append('Must match official sport list')
                elif 'athlete' in col_lower or 'name' in col_lower:
                    instructions_data['Description'].append('Athlete/participant name')
                    instructions_data['Format/Example'].append('e.g., John Smith, Mary Johnson')
                    instructions_data['Validation Rules'].append('Full name, proper capitalization')
                elif 'date' in col_lower:
                    instructions_data['Description'].append('Date of event/competition')
                    instructions_data['Format/Example'].append('DD/MM/YYYY or DD-MM-YYYY')
                    instructions_data['Validation Rules'].append('Valid date format')
                elif 'time' in col_lower:
                    instructions_data['Description'].append('Time of event')
                    instructions_data['Format/Example'].append('HH:MM (24-hour format)')
                    instructions_data['Validation Rules'].append('Valid time format')
                elif 'venue' in col_lower:
                    instructions_data['Description'].append('Competition venue/location')
                    instructions_data['Format/Example'].append('e.g., Singapore Sports Hub, OCBC Arena')
                    instructions_data['Validation Rules'].append('Official venue names')
                else:
                    instructions_data['Description'].append('Additional information')
                    instructions_data['Format/Example'].append('As specified')
                    instructions_data['Validation Rules'].append('Follow existing patterns')
            
            instructions_df = pd.DataFrame(instructions_data)
            instructions_df.to_excel(writer, sheet_name='Data Entry Guide', index=False)
            
            # Create completion tracking sheet
            completion_data = {
                'Sport/Event': [],
                'Total Records': [],
                'Complete Records': [],
                'Completion %': [],
                'Assigned To': [],
                'Last Updated': []
            }
            
            # Analyze by sport if sport column exists
            sport_col = None
            for col in main_df.columns:
                if 'sport' in str(col).lower():
                    sport_col = col
                    break
            
            if sport_col:
                sport_groups = main_df.groupby(sport_col)
                for sport, group in sport_groups:
                    total = len(group)
                    complete = len(group.dropna(how='any'))
                    completion_pct = (complete / total) * 100
                    
                    completion_data['Sport/Event'].append(sport)
                    completion_data['Total Records'].append(total)
                    completion_data['Complete Records'].append(complete)
                    completion_data['Completion %'].append(f"{completion_pct:.1f}%")
                    completion_data['Assigned To'].append('')  # To be filled
                    completion_data['Last Updated'].append('')  # To be filled
            
            completion_df = pd.DataFrame(completion_data)
            completion_df.to_excel(writer, sheet_name='Completion Tracking', index=False)
        
        print(f"✅ Data entry template created: {output_path}")
        print(f"   Sheets included:")
        print(f"   - Data Entry: Main data entry sheet")
        print(f"   - Data Entry Guide: Field descriptions and validation rules")
        print(f"   - Completion Tracking: Progress monitoring by sport")
        
    except Exception as e:
        print(f"❌ Error creating template: {str(e)}")

def main():
    """Main execution function"""
    file_path = 'AYG25 Competition Schedule (3).xlsx'
    
    # Analyze the competition schedule
    sheets = analyze_competition_schedule(file_path)
    
    if sheets:
        # Create data entry template
        create_data_entry_template(file_path)
        
        print(f"\n" + "="*80)
        print("NEXT STEPS")
        print("="*80)
        print(f"1. Review the analysis above to understand the data structure")
        print(f"2. Use the created template for organized data entry")
        print(f"3. Assign sport coordinators to specific sports")
        print(f"4. Set up regular data quality checks")
        print(f"5. Create validation rules in Excel for consistent data entry")

if __name__ == '__main__':
    main()
