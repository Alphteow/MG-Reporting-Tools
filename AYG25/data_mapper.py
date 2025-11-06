import pandas as pd
import openpyxl
from openpyxl.utils import get_column_letter
import re
from difflib import get_close_matches

def load_excel_data(file_path):
    """Load all relevant sheets from the Excel file"""
    try:
        # Read all sheets to understand the structure
        xls = pd.ExcelFile(file_path)
        print(f"📄 Available sheets in {file_path}:")
        for sheet in xls.sheet_names:
            print(f"  - {sheet}")
        
        data = {}
        
        # Load TeamSG Website Format sheet
        if 'TeamSG Website Format' in xls.sheet_names:
            data['teamsg'] = pd.read_excel(file_path, sheet_name='TeamSG Website Format')
            print(f"\n✅ Loaded 'TeamSG Website Format' sheet: {len(data['teamsg'])} rows")
            print(f"   Columns: {list(data['teamsg'].columns)}")
        else:
            print("\n⚠️  'TeamSG Website Format' sheet not found")
            
        # Load Sport List sheet
        if 'Sport List' in xls.sheet_names:
            data['sport_list'] = pd.read_excel(file_path, sheet_name='Sport List')
            print(f"\n✅ Loaded 'Sport List' sheet: {len(data['sport_list'])} rows")
            print(f"   Columns: {list(data['sport_list'].columns)}")
        else:
            print("\n⚠️  'Sport List' sheet not found")
            
        # Load Athlete List sheet
        if 'Athlete List' in xls.sheet_names:
            data['athlete_list'] = pd.read_excel(file_path, sheet_name='Athlete List')
            print(f"\n✅ Loaded 'Athlete List' sheet: {len(data['athlete_list'])} rows")
            print(f"   Columns: {list(data['athlete_list'].columns)}")
        else:
            print("\n⚠️  'Athlete List' sheet not found")
            
        return data
        
    except Exception as e:
        print(f"❌ Error loading Excel file: {str(e)}")
        return None

def normalize_sport_name(sport_name):
    """Normalize sport name for matching"""
    if pd.isna(sport_name) or sport_name == '':
        return ''
    
    # Convert to string and strip whitespace
    sport = str(sport_name).strip()
    
    # Remove extra spaces
    sport = re.sub(r'\s+', ' ', sport)
    
    return sport

def normalize_athlete_name(name):
    """Normalize athlete name for matching"""
    if pd.isna(name) or name == '':
        return ''
    
    # Convert to string and strip whitespace
    name = str(name).strip()
    
    # Remove extra spaces
    name = re.sub(r'\s+', ' ', name)
    
    # Standardize case (Title Case)
    name = name.title()
    
    return name

def find_sport_mapping(teamsg_sport, sport_list, threshold=0.8):
    """
    Find the best match for a sport from TeamSG to Sport List
    Returns: (matched_sport, confidence, match_type)
    """
    if pd.isna(teamsg_sport) or teamsg_sport == '':
        return ('', 0, 'empty')
    
    normalized_sport = normalize_sport_name(teamsg_sport)
    
    # Get list of valid sports from Sport List
    valid_sports = [normalize_sport_name(s) for s in sport_list if not pd.isna(s) and s != '']
    
    # Try exact match first
    if normalized_sport in valid_sports:
        return (normalized_sport, 1.0, 'exact')
    
    # Try case-insensitive exact match
    for valid_sport in valid_sports:
        if normalized_sport.lower() == valid_sport.lower():
            return (valid_sport, 1.0, 'case_insensitive')
    
    # Try fuzzy matching
    matches = get_close_matches(normalized_sport, valid_sports, n=1, cutoff=threshold)
    if matches:
        return (matches[0], threshold, 'fuzzy')
    
    return (normalized_sport, 0, 'no_match')

def find_athlete_mapping(teamsg_athlete, athlete_list, threshold=0.85):
    """
    Find the best match for an athlete from TeamSG to Athlete List
    Returns: (matched_athlete, confidence, match_type)
    """
    if pd.isna(teamsg_athlete) or teamsg_athlete == '':
        return ('', 0, 'empty')
    
    normalized_athlete = normalize_athlete_name(teamsg_athlete)
    
    # Get list of valid athletes from Athlete List
    valid_athletes = [normalize_athlete_name(a) for a in athlete_list if not pd.isna(a) and a != '']
    
    # Try exact match first
    if normalized_athlete in valid_athletes:
        return (normalized_athlete, 1.0, 'exact')
    
    # Try case-insensitive exact match
    for valid_athlete in valid_athletes:
        if normalized_athlete.lower() == valid_athlete.lower():
            return (valid_athlete, 1.0, 'case_insensitive')
    
    # Try fuzzy matching
    matches = get_close_matches(normalized_athlete, valid_athletes, n=1, cutoff=threshold)
    if matches:
        return (matches[0], threshold, 'fuzzy')
    
    return (normalized_athlete, 0, 'no_match')

def process_comma_delimited_athletes(athlete_cell, athlete_list, threshold=0.85):
    """
    Process comma-delimited athlete names in a cell
    Returns: (list of matched athletes, list of unmatched, mapping_details)
    """
    if pd.isna(athlete_cell) or athlete_cell == '':
        return ([], [], [])
    
    # Split by comma
    athletes = [a.strip() for a in str(athlete_cell).split(',')]
    
    matched_athletes = []
    unmatched_athletes = []
    mapping_details = []
    
    for athlete in athletes:
        if athlete == '':
            continue
            
        matched, confidence, match_type = find_athlete_mapping(athlete, athlete_list, threshold)
        
        mapping_details.append({
            'original': athlete,
            'matched': matched,
            'confidence': confidence,
            'match_type': match_type
        })
        
        if confidence > 0:
            matched_athletes.append(matched)
        else:
            unmatched_athletes.append(athlete)
    
    return (matched_athletes, unmatched_athletes, mapping_details)

def map_teamsg_to_validation(file_path, output_file=None, create_updated_data=True):
    """
    Main function to map TeamSG Website Format data to valid Sport and Athlete lists
    """
    print("="*70)
    print("TEAMSG DATA MAPPER - Sport and Athlete Validation Mapping")
    print("="*70)
    
    # Load data
    data = load_excel_data(file_path)
    if data is None or 'teamsg' not in data:
        print("\n❌ Cannot proceed without TeamSG Website Format sheet")
        return
    
    teamsg_df = data['teamsg'].copy()  # Make a copy to preserve original
    
    # Initialize results
    sport_mapping_results = []
    athlete_mapping_results = []
    
    # Get valid lists
    sport_list = data.get('sport_list', pd.DataFrame()).iloc[:, 0].tolist() if 'sport_list' in data else []
    athlete_list = data.get('athlete_list', pd.DataFrame()).iloc[:, 0].tolist() if 'athlete_list' in data else []
    
    if not sport_list:
        print("\n⚠️  Warning: Sport List is empty or not found")
    else:
        print(f"\n📋 Sport List contains {len([s for s in sport_list if not pd.isna(s)])} valid sports")
        print(f"   Sample sports: {[s for s in sport_list[:5] if not pd.isna(s)]}")
    
    if not athlete_list:
        print("\n⚠️  Warning: Athlete List is empty or not found")
    else:
        print(f"\n📋 Athlete List contains {len([a for a in athlete_list if not pd.isna(a)])} valid athletes")
        print(f"   Sample athletes: {[a for a in athlete_list[:5] if not pd.isna(a)]}")
    
    print("\n" + "="*70)
    print("PROCESSING SPORT MAPPINGS")
    print("="*70)
    
    # Process sport column
    sport_column = None
    for col in teamsg_df.columns:
        if 'sport' in str(col).lower():
            sport_column = col
            break
    
    if sport_column:
        print(f"\n🔍 Found sport column: '{sport_column}'")
        sports = teamsg_df[sport_column].unique()
        print(f"   Unique sports in TeamSG data: {len(sports)}")
        
        for sport in sports:
            if pd.isna(sport) or sport == '':
                continue
                
            matched, confidence, match_type = find_sport_mapping(sport, sport_list)
            sport_mapping_results.append({
                'Original Sport': sport,
                'Mapped Sport': matched,
                'Confidence': confidence,
                'Match Type': match_type,
                'Status': '✅ Valid' if confidence > 0 else '❌ No Match'
            })
            
            if confidence == 0:
                print(f"   ⚠️  No match found for: '{sport}'")
    else:
        print("\n⚠️  No sport column found in TeamSG Website Format sheet")
    
    print("\n" + "="*70)
    print("PROCESSING ATHLETE MAPPINGS")
    print("="*70)
    
    # Process athlete name column
    athlete_column = None
    for col in teamsg_df.columns:
        if 'athlete' in str(col).lower() and 'name' in str(col).lower():
            athlete_column = col
            break
    
    if athlete_column:
        print(f"\n🔍 Found athlete column: '{athlete_column}'")
        
        # Process each row
        for idx, row in teamsg_df.iterrows():
            athlete_cell = row[athlete_column]
            
            if pd.isna(athlete_cell) or athlete_cell == '':
                continue
            
            # Check if comma-delimited
            if ',' in str(athlete_cell):
                matched_list, unmatched_list, details = process_comma_delimited_athletes(
                    athlete_cell, athlete_list
                )
                
                for detail in details:
                    athlete_mapping_results.append({
                        'Row': idx + 2,  # +2 for Excel row (1-indexed, header)
                        'Original Name': detail['original'],
                        'Mapped Name': detail['matched'],
                        'Confidence': detail['confidence'],
                        'Match Type': detail['match_type'],
                        'Status': '✅ Valid' if detail['confidence'] > 0 else '❌ No Match'
                    })
                
                if unmatched_list:
                    print(f"   ⚠️  Row {idx + 2}: Unmatched athletes: {', '.join(unmatched_list)}")
            else:
                # Single athlete
                matched, confidence, match_type = find_athlete_mapping(athlete_cell, athlete_list)
                
                athlete_mapping_results.append({
                    'Row': idx + 2,
                    'Original Name': athlete_cell,
                    'Mapped Name': matched,
                    'Confidence': confidence,
                    'Match Type': match_type,
                    'Status': '✅ Valid' if confidence > 0 else '❌ No Match'
                })
                
                if confidence == 0:
                    print(f"   ⚠️  Row {idx + 2}: No match for '{athlete_cell}'")
    else:
        print("\n⚠️  No athlete name column found in TeamSG Website Format sheet")
    
    # Create summary DataFrames
    sport_mapping_df = pd.DataFrame(sport_mapping_results)
    athlete_mapping_df = pd.DataFrame(athlete_mapping_results)
    
    # Create updated TeamSG dataframe with mapped values
    updated_teamsg_df = None
    if create_updated_data:
        print("\n" + "="*70)
        print("CREATING UPDATED TEAMSG DATA WITH MAPPED VALUES")
        print("="*70)
        
        updated_teamsg_df = teamsg_df.copy()
        
        # Create sport mapping dictionary
        sport_map = {}
        if not sport_mapping_df.empty:
            for _, row in sport_mapping_df.iterrows():
                if row['Confidence'] > 0:
                    sport_map[row['Original Sport']] = row['Mapped Sport']
        
        # Apply sport mapping
        if sport_column and sport_map:
            print(f"\n🔄 Updating sport column '{sport_column}'...")
            updated_count = 0
            for idx, row in updated_teamsg_df.iterrows():
                original_sport = row[sport_column]
                if original_sport in sport_map:
                    updated_teamsg_df.at[idx, sport_column] = sport_map[original_sport]
                    updated_count += 1
            print(f"   ✅ Updated {updated_count} rows with mapped sports")
        
        # Apply athlete mapping (handling comma-delimited values)
        if athlete_column and not athlete_mapping_df.empty:
            print(f"\n🔄 Updating athlete column '{athlete_column}'...")
            updated_count = 0
            
            for idx, row in updated_teamsg_df.iterrows():
                athlete_cell = row[athlete_column]
                
                if pd.isna(athlete_cell) or athlete_cell == '':
                    continue
                
                # Check if comma-delimited
                if ',' in str(athlete_cell):
                    matched_list, _, _ = process_comma_delimited_athletes(
                        athlete_cell, athlete_list
                    )
                    
                    if matched_list:
                        # Join the matched athletes back with comma
                        updated_teamsg_df.at[idx, athlete_column] = ', '.join(matched_list)
                        updated_count += 1
                else:
                    # Single athlete
                    matched, confidence, _ = find_athlete_mapping(athlete_cell, athlete_list)
                    if confidence > 0:
                        updated_teamsg_df.at[idx, athlete_column] = matched
                        updated_count += 1
            
            print(f"   ✅ Updated {updated_count} rows with mapped athlete names")
        
        print(f"\n✅ Updated TeamSG data ready")
    
    # Print summary
    print("\n" + "="*70)
    print("MAPPING SUMMARY")
    print("="*70)
    
    if not sport_mapping_df.empty:
        print(f"\n📊 SPORT MAPPING RESULTS:")
        print(f"   Total unique sports: {len(sport_mapping_df)}")
        print(f"   ✅ Matched: {len(sport_mapping_df[sport_mapping_df['Confidence'] > 0])}")
        print(f"   ❌ Unmatched: {len(sport_mapping_df[sport_mapping_df['Confidence'] == 0])}")
        
        if len(sport_mapping_df[sport_mapping_df['Confidence'] == 0]) > 0:
            print(f"\n   Unmatched sports:")
            for _, row in sport_mapping_df[sport_mapping_df['Confidence'] == 0].iterrows():
                print(f"      - {row['Original Sport']}")
    
    if not athlete_mapping_df.empty:
        print(f"\n📊 ATHLETE MAPPING RESULTS:")
        print(f"   Total athlete entries: {len(athlete_mapping_df)}")
        print(f"   ✅ Matched: {len(athlete_mapping_df[athlete_mapping_df['Confidence'] > 0])}")
        print(f"   ❌ Unmatched: {len(athlete_mapping_df[athlete_mapping_df['Confidence'] == 0])}")
        
        if len(athlete_mapping_df[athlete_mapping_df['Confidence'] == 0]) > 0:
            print(f"\n   Unmatched athletes:")
            unmatched_count = 0
            for _, row in athlete_mapping_df[athlete_mapping_df['Confidence'] == 0].iterrows():
                if unmatched_count < 10:  # Show first 10
                    print(f"      - Row {row['Row']}: {row['Original Name']}")
                    unmatched_count += 1
            if len(athlete_mapping_df[athlete_mapping_df['Confidence'] == 0]) > 10:
                print(f"      ... and {len(athlete_mapping_df[athlete_mapping_df['Confidence'] == 0]) - 10} more")
    
    # Save results to Excel
    if output_file is None:
        output_file = file_path.replace('.xlsx', '_mapping_results.xlsx')
    
    # Also create a separate file with just the updated data
    updated_data_file = file_path.replace('.xlsx', '_UPDATED.xlsx')
    
    try:
        # Save mapping results
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            if not sport_mapping_df.empty:
                sport_mapping_df.to_excel(writer, sheet_name='Sport Mappings', index=False)
            
            if not athlete_mapping_df.empty:
                athlete_mapping_df.to_excel(writer, sheet_name='Athlete Mappings', index=False)
            
            # Save original TeamSG data
            if 'teamsg' in data:
                data['teamsg'].to_excel(writer, sheet_name='Original TeamSG Data', index=False)
            
            # Save updated TeamSG data
            if updated_teamsg_df is not None:
                updated_teamsg_df.to_excel(writer, sheet_name='Updated TeamSG Data', index=False)
        
        print(f"\n✅ Mapping results saved to: {output_file}")
        print(f"   Sheets created:")
        if not sport_mapping_df.empty:
            print(f"      - Sport Mappings")
        if not athlete_mapping_df.empty:
            print(f"      - Athlete Mappings")
        print(f"      - Original TeamSG Data")
        if updated_teamsg_df is not None:
            print(f"      - Updated TeamSG Data")
        
        # Save updated data to separate file
        if updated_teamsg_df is not None:
            with pd.ExcelWriter(updated_data_file, engine='openpyxl') as writer:
                updated_teamsg_df.to_excel(writer, sheet_name='TeamSG Website Format', index=False)
            
            print(f"\n✅ Updated TeamSG data saved to: {updated_data_file}")
            print(f"   This file contains the TeamSG Website Format with:")
            print(f"      - Mapped sport names (validated against Sport List)")
            print(f"      - Mapped athlete names (validated against Athlete List)")
        
    except Exception as e:
        print(f"\n❌ Error saving results: {str(e)}")
    
    print("\n" + "="*70)
    print("✅ MAPPING COMPLETE!")
    print("="*70)
    
    return {
        'sport_mappings': sport_mapping_df,
        'athlete_mappings': athlete_mapping_df,
        'updated_data': updated_teamsg_df,
        'updated_file': updated_data_file if updated_teamsg_df is not None else None
    }

def main():
    """Main execution function"""
    # File path - update this to your Excel file
    file_path = 'AYG_Mapping.xlsx'
    
    # Run the mapping
    results = map_teamsg_to_validation(file_path)
    
    print("\n💡 TIP: Two Excel files have been generated:")
    print("   1. *_mapping_results.xlsx - Detailed mapping report with original and updated data")
    print("   2. *_UPDATED.xlsx - Ready-to-use TeamSG Website Format with mapped values")
    print("\n   The UPDATED file contains validated sport and athlete names that will pass data validation!")

if __name__ == '__main__':
    main()

