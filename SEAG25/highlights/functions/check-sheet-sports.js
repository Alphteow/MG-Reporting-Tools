/**
 * Get all unique sports from the SPORT column in the Google Sheet
 * and verify icon mappings
 */

const { google } = require('googleapis');
const { JWT } = require('google-auth-library');
const fs = require('fs');
const path = require('path');

// Load credentials
const credentialsPath = path.join(__dirname, '../../../AYG25/ayg-form-system/google_credentials.json');
const credentials = JSON.parse(fs.readFileSync(credentialsPath, 'utf8'));

// Load sport icon mapping
const mappingPath = path.join(__dirname, '../flags/sports/sports-icons-mapping.json');
const mapping = JSON.parse(fs.readFileSync(mappingPath, 'utf8'));

  // Build icon lookup map with variations (matching generateHighlights.js logic)
  const iconMap = new Map();
  mapping.forEach(item => {
    const sport = item.sport.toLowerCase();
    const fileName = item.fileName;
    
    // Add exact match
    iconMap.set(sport, fileName);
    
    // Add common variations
    if (sport === 'batminton') {
      iconMap.set('badminton', fileName);
    }
    if (sport === 'aquatic sports') {
      iconMap.set('swimming', fileName);
      iconMap.set('aquatics', fileName);
    }
    if (sport === 'flying discs') {
      iconMap.set('flying disc', fileName);
    }
    if (sport === 'jui-jitsu') {
      iconMap.set('ju-jitsu', fileName);
      iconMap.set('jiu-jitsu', fileName);
    }
    if (sport === 'mixed martail arts') {
      iconMap.set('mixed martial arts', fileName);
    }
    if (sport === 'esports') {
      iconMap.set('e-sports', fileName);
    }
    // Map sheet sports to icons
    if (sport === 'canoeing') {
      iconMap.set('canoe and rowing', fileName);
      iconMap.set('canoe', fileName);
      iconMap.set('rowing', fileName);
    }
    if (sport === 'exstream sports') {
      iconMap.set('extreme', fileName);
      iconMap.set('exstream sports', fileName);
    }
    if (sport === 'kabaddy') {
      iconMap.set('kabaddi', fileName);
      iconMap.set('kabaddy', fileName);
    }
    if (sport === 'sepak takraw') {
      iconMap.set('sepatakraw', fileName);
      iconMap.set('sepak takraw', fileName);
      iconMap.set('sepatakraw', fileName); // Handle no-space version
    }
  });

async function getUniqueSportsFromSheet() {
  const auth = new JWT({
    email: credentials.client_email,
    key: credentials.private_key,
    scopes: ['https://www.googleapis.com/auth/spreadsheets'],
  });

  const sheets = google.sheets({ version: 'v4', auth });
  const spreadsheetId = '15zXDQdkGeAN2AMMdrJ_qjkjReq_Y3mlU1-_7ciniyS4';
  const sheetName = 'Com Schedule - Test';

  try {
    // Get headers first
    const headersResponse = await sheets.spreadsheets.values.get({
      spreadsheetId,
      range: `${sheetName}!8:8`,
    });

    const headers = headersResponse.data.values[0] || [];
    const sportColIdx = headers.findIndex(h => h && h.trim().toUpperCase() === 'SPORT');

    if (sportColIdx === -1) {
      console.error('SPORT column not found!');
      return;
    }

    console.log(`SPORT column found at index: ${sportColIdx}\n`);

    // Get all data rows (starting from row 9)
    const dataResponse = await sheets.spreadsheets.values.get({
      spreadsheetId,
      range: `${sheetName}!9:1000`, // Get up to 1000 rows
    });

    const rows = dataResponse.data.values || [];
    const sports = new Set();

    rows.forEach(row => {
      const sport = (row[sportColIdx] || '').trim();
      if (sport) {
        sports.add(sport);
      }
    });

    console.log(`Found ${sports.size} unique sports in the sheet:\n`);

    const sportsArray = Array.from(sports).sort();
    const mapped = [];
    const unmapped = [];

    sportsArray.forEach(sport => {
      const sportLower = sport.toLowerCase();
      let iconFile = null;
      let matchType = '';

      // Try exact match
      if (iconMap.has(sportLower)) {
        iconFile = iconMap.get(sportLower);
        matchType = 'exact';
      } else {
        // Try fuzzy match (word-by-word)
        const sportWords = sportLower.split(/\s+/);
        for (const [key, fileName] of iconMap.entries()) {
          const keyWords = key.split(/\s+/);
          // Check if any word matches
          if (sportWords.some(w => keyWords.includes(w)) || keyWords.some(w => sportWords.includes(w))) {
            iconFile = fileName;
            matchType = 'fuzzy';
            break;
          }
          // Also try substring match
          if (sportLower.includes(key) || key.includes(sportLower)) {
            iconFile = fileName;
            matchType = 'fuzzy';
            break;
          }
          // Handle no-space variations (e.g., "sepatakraw" vs "sepak takraw")
          const sportNoSpace = sportLower.replace(/\s+/g, '');
          const keyNoSpace = key.replace(/\s+/g, '');
          if (sportNoSpace === keyNoSpace || sportNoSpace.includes(keyNoSpace) || keyNoSpace.includes(sportNoSpace)) {
            iconFile = fileName;
            matchType = 'fuzzy';
            break;
          }
        }
      }

      if (iconFile) {
        mapped.push({ sport, iconFile, matchType });
      } else {
        unmapped.push(sport);
      }
    });

    console.log('✅ Sports with icons:');
    console.log('====================');
    mapped.forEach(({ sport, iconFile, matchType }) => {
      const matchSymbol = matchType === 'exact' ? '✓' : '~';
      console.log(`  ${matchSymbol} ${sport.padEnd(30)} -> ${iconFile}`);
    });

    if (unmapped.length > 0) {
      console.log('\n❌ Sports without icons:');
      console.log('=======================');
      unmapped.forEach(sport => {
        console.log(`  ✗ ${sport}`);
      });
    } else {
      console.log('\n✅ All sports have icons mapped!');
    }

    // Create a mapping file for easy reference
    const mappingOutput = {
      mapped: mapped.map(({ sport, iconFile }) => ({ sport, iconFile })),
      unmapped,
      total: sportsArray.length,
      mappedCount: mapped.length,
      unmappedCount: unmapped.length,
    };

    const outputPath = path.join(__dirname, '../flags/sports/sheet-sports-mapping.json');
    fs.writeFileSync(outputPath, JSON.stringify(mappingOutput, null, 2));
    console.log(`\n📝 Saved mapping to: ${outputPath}`);

  } catch (error) {
    console.error('Error:', error.message);
    if (error.response) {
      console.error('Response:', error.response.data);
    }
  }
}

getUniqueSportsFromSheet();

