/**
 * Highlights Generator for SEAG25
 * 
 * Generates HTML highlights from Google Sheets data
 * Adapted from AYG25 highlights generator
 */

const { google } = require('googleapis');
const { JWT } = require('google-auth-library');
const { Readable } = require('stream');
const { Storage } = require('@google-cloud/storage');
let puppeteer = null;
let chromium = null;
try {
  puppeteer = require('puppeteer-core');
  chromium = require('@sparticuz/chromium');
} catch (e) {
  console.log('Puppeteer not available - screenshot generation will be disabled');
}

// SEAG25 Column Mappings (based on SEAG25 Competition Schedule structure)
const COLUMN_MAPPINGS = {
  SPORT: 'SPORT',
  SPORT_TEAMSG: 'SPORT (TEAMSG WEBSITE)',
  DISCIPLINE: 'DISCIPLINE',
  EVENT: 'EVENT',
  EVENT_CUSTOM: 'CUSTOM EVENT NAME (TEAMSG WEBSITE)',
  EVENT_GENDER: 'EVENT GENDER',
  STAGE: 'STAGE / ROUND OF COMPETITION',
  STAGE_TEMPLATE: 'STAGE / ROUND OF COMPETITION (TEMPLATE)',
  HEAT: 'HEAT NUMBER',
  VENUE: 'COMPETITION VENUE',
  DATE_SGP: 'DATE',
  TIME_START_SGP: 'TIME START (SGP) 24HR CLOCK',
  TIME_END_SGP: 'TIME END (SGP) 24HR CLOCK',
  ATHLETE_NAME: 'NAME OF ATHLETE (SGP)',
  COUNTRY_SGP: 'COUNTRY NAME (SGP)',
  TIMING_SGP: 'TIMING (SGP) hh:mm:ss.ms',
  SCORE_SGP: 'SCORE/DISTANCE/HEIGHT (SGP)', // Singapore score for H2H sports
  SCORE_COMPETITOR: 'SCORE (COMPETITOR)', // Opponent score for H2H sports
  COMPETITOR_NAME: 'NAME OF ATHLETE (COMPETITOR)', // Opponent name
  COMPETITOR_COUNTRY: 'COUNTRY NAME (COMPETITOR)', // Opponent country
  WIN_DRAW_LOSE: 'H2H WIN/DRAW/LOSE',
  POSITION: 'POSITION',
  FINAL_POSITION: 'FINAL POSITION IN EVENT',
  ADVANCED: 'ADVANCED',
  MEDALS: 'MEDAL',
  REMARKS: 'REMARKS',
};

const DATA_START_ROW = 8;

/**
 * Get sport icon URL from local files or SEAG25 Firebase Storage
 * Uses scraped icons from flags/sports/ directory
 */
let sportIconMapping = null;

function loadSportIconMapping() {
  if (sportIconMapping) return sportIconMapping;
  
  const fs = require('fs');
  const path = require('path');
  const mappingPath = path.join(__dirname, '../sports/sports-icons-mapping.json');
  
  try {
    if (fs.existsSync(mappingPath)) {
      const data = fs.readFileSync(mappingPath, 'utf8');
      const mapping = JSON.parse(data);
      sportIconMapping = {};
      
      // Create lookup with multiple variations
      mapping.forEach(item => {
        const sport = item.sport.toLowerCase();
        const fileName = item.fileName;
        
        // Add exact match
        sportIconMapping[sport] = `sports/${fileName}`;
        
      // Add common variations
      if (sport === 'batminton') {
        sportIconMapping['badminton'] = `sports/${fileName}`;
      }
      if (sport === 'aquatic sports') {
        sportIconMapping['swimming'] = `sports/${fileName}`;
        sportIconMapping['aquatics'] = `sports/${fileName}`;
      }
      if (sport === 'flying discs') {
        sportIconMapping['flying disc'] = `sports/${fileName}`;
      }
      if (sport === 'jui-jitsu') {
        sportIconMapping['ju-jitsu'] = `sports/${fileName}`;
        sportIconMapping['jiu-jitsu'] = `sports/${fileName}`;
      }
      if (sport === 'mixed martail arts') {
        sportIconMapping['mixed martial arts'] = `sports/${fileName}`;
      }
      if (sport === 'esports') {
        sportIconMapping['e-sports'] = `sports/${fileName}`;
      }
      // Map sheet sports to icons
      if (sport === 'canoeing') {
        sportIconMapping['canoe and rowing'] = `sports/${fileName}`;
        sportIconMapping['canoe'] = `sports/${fileName}`;
        sportIconMapping['rowing'] = `sports/${fileName}`;
      }
      if (sport === 'exstream sports') {
        sportIconMapping['extreme'] = `sports/${fileName}`;
        sportIconMapping['exstream sports'] = `sports/${fileName}`;
      }
      if (sport === 'kabaddy') {
        sportIconMapping['kabaddi'] = `sports/${fileName}`;
        sportIconMapping['kabaddy'] = `sports/${fileName}`;
      }
      if (sport === 'sepak takraw') {
        sportIconMapping['sepatakraw'] = `sports/${fileName}`;
        sportIconMapping['sepak takraw'] = `sports/${fileName}`;
        sportIconMapping['sepatakraw'] = `sports/${fileName}`;
        // Handle no-space version from sheet
        sportIconMapping['sepatakraw'] = `sports/${fileName}`;
      }
      });
    }
  } catch (error) {
    console.error('Error loading sport icon mapping:', error);
  }
  
  if (!sportIconMapping) {
    sportIconMapping = {};
  }
  
  return sportIconMapping;
}

function getSportIconUrl(sportName) {
  if (!sportName) return '';
  
  const mapping = loadSportIconMapping();
  const sportKey = sportName.trim().toLowerCase();
  
  // Try exact match
  if (mapping[sportKey]) {
    return mapping[sportKey];
  }
  
  // Try partial/fuzzy matches
  for (const [key, iconPath] of Object.entries(mapping)) {
    // Check if sport name contains key or vice versa
    if (sportKey.includes(key) || key.includes(sportKey)) {
      return iconPath;
    }
    // Check word-by-word match
    const sportWords = sportKey.split(/\s+/);
    const keyWords = key.split(/\s+/);
    if (sportWords.some(w => keyWords.includes(w)) || keyWords.some(w => sportWords.includes(w))) {
      return iconPath;
    }
    // Handle no-space variations (e.g., "sepatakraw" vs "sepak takraw")
    const sportNoSpace = sportKey.replace(/\s+/g, '');
    const keyNoSpace = key.replace(/\s+/g, '');
    if (sportNoSpace === keyNoSpace || sportNoSpace.includes(keyNoSpace) || keyNoSpace.includes(sportNoSpace)) {
      return iconPath;
    }
  }
  
  // Fallback: try local file directly with variations
  const fs = require('fs');
  const path = require('path');
  const localIconsDir = path.join(__dirname, '../sports');
  const variations = [
    `Icon_${sportName.trim().replace(/\s+/g, '_')}.png`,
    `Icon_${sportName.trim().replace(/\s+/g, ' ')}.png`,
    `Icon_${sportName.trim()}.png`,
  ];
  
  for (const fileName of variations) {
    const localPath = path.join(localIconsDir, fileName);
    if (fs.existsSync(localPath)) {
      return `sports/${fileName}`;
    }
  }
  
  // Last resort: Firebase Storage URL
  const sportUpper = sportName.trim().toUpperCase();
  const folderName = `SPORTS-${sportUpper.replace(/\s+/g, '-')}`;
  const iconFileName = `Icon_${encodeURIComponent(sportName.trim())}.png`;
  
  return `https://storage.googleapis.com/seagames-2025.firebasestorage.app/content/${folderName}/${iconFileName}`;
}

/**
 * Normalize date to YYYY-MM-DD format
 */
function normalizeDate(dateInput) {
  if (!dateInput) return '';
  if (typeof dateInput === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(dateInput)) {
    return dateInput;
  }
  
  let dateObj;
  if (dateInput instanceof Date) {
    dateObj = dateInput;
  } else if (typeof dateInput === 'string') {
    const parts = dateInput.split(/[\/\-]/);
    if (parts.length === 3) {
      const day = parseInt(parts[0], 10);
      const month = parseInt(parts[1], 10);
      const year = parseInt(parts[2], 10);
      if (year > 2000) {
        if (parts[0].length === 4) {
          dateObj = new Date(year, month - 1, day);
        } else {
          dateObj = new Date(year, month - 1, day);
        }
      } else {
        dateObj = new Date(parts[2], parts[0] - 1, parts[1]);
      }
    } else {
      dateObj = new Date(dateInput);
    }
  } else {
    return '';
  }
  
  if (isNaN(dateObj.getTime())) {
    return '';
  }
  
  const year = dateObj.getFullYear();
  const month = String(dateObj.getMonth() + 1).padStart(2, '0');
  const day = String(dateObj.getDate()).padStart(2, '0');
  
  return `${year}-${month}-${day}`;
}

/**
 * Load WA Template Mapping to determine H2H sports
 */
let h2hSportsCache = null;

async function loadH2HSportsMapping(sheetsClient, spreadsheetId) {
  if (h2hSportsCache) {
    return h2hSportsCache;
  }
  
  try {
    const response = await sheetsClient.spreadsheets.values.get({
      spreadsheetId,
      range: 'WA Template Mapping!A:F',
    });
    
    const rows = response.data.values || [];
    if (rows.length < 2) {
      h2hSportsCache = new Set();
      return h2hSportsCache;
    }
    
    const headers = rows[0] || [];
    const sportsColIdx = headers.findIndex(h => h && h.toUpperCase() === 'SPORTS');
    const disciplinesColIdx = headers.findIndex(h => h && h.toUpperCase() === 'DISCIPLINES');
    const h2hColIdx = headers.findIndex(h => h && h.toUpperCase() === 'H2H');
    
    if (sportsColIdx < 0 || h2hColIdx < 0) {
      h2hSportsCache = new Set();
      return h2hSportsCache;
    }
    
    const h2hCombinations = new Set();
    
    for (let i = 1; i < rows.length; i++) {
      const row = rows[i] || [];
      const h2h = (row[h2hColIdx] || '').trim().toLowerCase();
      
      if (h2h === 'yes') {
        const sports = (row[sportsColIdx] || '').trim();
        const disciplines = disciplinesColIdx >= 0 ? (row[disciplinesColIdx] || '').trim() : '';
        
        const sportList = sports ? sports.split(/\n|,/).map(s => s.trim().toUpperCase()) : [];
        const disciplineList = disciplines ? disciplines.split(/\n|,/).map(d => d.trim().toUpperCase()) : [];
        
        if (sportList.length > 0) {
          if (disciplineList.length > 0) {
            sportList.forEach(sport => {
              disciplineList.forEach(discipline => {
                h2hCombinations.add(`${sport}|${discipline}`);
              });
            });
          } else {
            sportList.forEach(sport => {
              h2hCombinations.add(`${sport}|*`);
            });
          }
        }
      }
    }
    
    h2hSportsCache = h2hCombinations;
    return h2hCombinations;
  } catch (error) {
    console.error('Error loading H2H sports mapping:', error);
    h2hSportsCache = new Set();
    return h2hSportsCache;
  }
}

/**
 * Check if a sport/discipline combination is H2H
 */
function isH2HSport(sport, discipline, h2hMapping) {
  if (!h2hMapping || h2hMapping.size === 0) {
    return false;
  }
  
  const sportUpper = (sport || '').trim().toUpperCase();
  const disciplineUpper = (discipline || '').trim().toUpperCase();
  
  // Check exact sport|discipline match
  if (disciplineUpper && h2hMapping.has(`${sportUpper}|${disciplineUpper}`)) {
    return true;
  }
  
  // Check sport with wildcard discipline
  if (h2hMapping.has(`${sportUpper}|*`)) {
    return true;
  }
  
  // Check sport with empty discipline (sport|)
  if (!disciplineUpper && h2hMapping.has(`${sportUpper}|`)) {
    return true;
  }
  
  return false;
}

/**
 * Initialize Google Sheets API client
 */
async function getSheetsClient() {
  const credentialsJson = process.env.GOOGLE_CREDENTIALS_JSON;
  
  if (!credentialsJson) {
    throw new Error('GOOGLE_CREDENTIALS_JSON environment variable not set');
  }

  const credentials = JSON.parse(credentialsJson);
  
  const auth = new JWT({
    email: credentials.client_email,
    key: credentials.private_key,
    scopes: [
      'https://www.googleapis.com/auth/spreadsheets',
      'https://www.googleapis.com/auth/drive',
      'https://www.googleapis.com/auth/drive.file',
    ],
  });

  return google.sheets({ version: 'v4', auth });
}

/**
 * Initialize Google Cloud Storage client
 */
function getStorageClient() {
  return new Storage({
    projectId: process.env.GCLOUD_PROJECT || 'major-e910d',
  });
}

/**
 * Save HTML to Google Cloud Storage
 */
async function saveHtmlToGCS(storageClient, bucketName, folderPath, fileName, htmlContent) {
  try {
    const bucket = storageClient.bucket(bucketName);
    const filePath = `${folderPath}/${fileName}`;
    const file = bucket.file(filePath);
    
    await file.save(htmlContent, {
      metadata: {
        contentType: 'text/html',
        cacheControl: 'public, max-age=3600',
      },
      public: true,
    });
    
    const publicUrl = `https://storage.googleapis.com/${bucketName}/${filePath}`;
    
    return {
      filePath,
      publicUrl,
      gsUri: `gs://${bucketName}/${filePath}`,
    };
  } catch (error) {
    console.error('Error saving HTML to GCS:', error);
    throw error;
  }
}

/**
 * Save screenshot image to Google Cloud Storage
 */
async function saveImageToGCS(storageClient, bucketName, folderPath, fileName, imageBuffer) {
  try {
    const bucket = storageClient.bucket(bucketName);
    const filePath = `${folderPath}/${fileName}`;
    const file = bucket.file(filePath);
    
    await file.save(imageBuffer, {
      metadata: {
        contentType: 'image/png',
        cacheControl: 'public, max-age=3600',
      },
      public: true,
    });
    
    const publicUrl = `https://storage.googleapis.com/${bucketName}/${filePath}`;
    
    return {
      filePath,
      publicUrl,
      gsUri: `gs://${bucketName}/${filePath}`,
    };
  } catch (error) {
    console.error('Error saving image to GCS:', error);
    throw error;
  }
}

/**
 * Load data from Google Sheets
 */
async function loadData(sheetsClient, spreadsheetId, sheetName, startRow = DATA_START_ROW) {
  try {
    try {
      const spreadsheet = await sheetsClient.spreadsheets.get({
        spreadsheetId,
        fields: 'sheets.properties.title',
      });
      
      const availableSheets = spreadsheet.data.sheets.map(s => s.properties.title);
      console.log('Available sheets:', availableSheets);
      
      if (!availableSheets.includes(sheetName)) {
        throw new Error(`Sheet "${sheetName}" not found. Available sheets: ${availableSheets.join(', ')}`);
      }
    } catch (metadataError) {
      console.error('Error getting spreadsheet metadata:', metadataError.message);
    }
    
    const response = await sheetsClient.spreadsheets.values.get({
      spreadsheetId,
      range: `${sheetName}!A:ZZ`,
    });

    const rows = response.data.values || [];
    
    if (rows.length < startRow) {
      return { headers: [], data: [] };
    }

    const headers = rows[startRow - 1].map(h => (h || '').trim().replace(/\s+/g, ' '));
    
    const dataRows = rows.slice(startRow).map(row => {
      const obj = {};
      headers.forEach((header, idx) => {
        obj[header] = row[idx] || '';
      });
      return obj;
    });

    return { headers, data: dataRows };
  } catch (error) {
    console.error('Error loading data from Google Sheets:', error);
    throw error;
  }
}

/**
 * Filter highlight rows (gold medals only)
 */
function filterHighlightRows(data) {
  const validRows = [];

  const getCol = (row, key) => {
    const colName = COLUMN_MAPPINGS[key];
    return (row[colName] || '').trim();
  };

  const hasValue = (row, key) => {
    const val = getCol(row, key);
    return val !== '';
  };

  for (const row of data) {
    const medals = getCol(row, 'MEDALS');
    const medalText = (medals || '').trim();
    const isGoldMedal = medalText && 
                       !['na', 'n/a', 'none', 'no medal', 'nil'].includes(medalText.toLowerCase()) && 
                       medalText.toLowerCase().includes('gold');
    
    if (!isGoldMedal) {
      continue;
    }
    
    const hasCompetitorName = hasValue(row, 'COMPETITOR_NAME');
    const hasCompetitorCountry = hasValue(row, 'COMPETITOR_COUNTRY');
    const isH2H = hasCompetitorName && hasCompetitorCountry;

    if (isH2H) {
      const hasBasic = hasValue(row, 'SPORT') && 
                      hasValue(row, 'EVENT') && 
                      hasValue(row, 'STAGE') && 
                      hasValue(row, 'ATHLETE_NAME');
      const hasScore = hasValue(row, 'SCORE_SGP') || hasValue(row, 'SCORE_COMPETITOR');
      
      if (hasBasic && hasScore) {
        validRows.push(row);
      }
    } else {
      const hasBasic = hasValue(row, 'SPORT') && 
                      hasValue(row, 'EVENT') && 
                      hasValue(row, 'STAGE') && 
                      hasValue(row, 'ATHLETE_NAME');
      const hasResult = hasValue(row, 'TIMING_SGP') || hasValue(row, 'SCORE_SGP');
      
      if (hasBasic && hasResult) {
        validRows.push(row);
      }
    }
  }

  return validRows;
}

/**
 * Format timing string
 * Removes leading zeros and colons
 * Examples: 01:00.10 → 1:00.10, 00:01:10.28 → 1:10.28
 */
function formatTiming(timingStr) {
  if (!timingStr) return '';
  let result = String(timingStr).trim();
  
  // Remove leading zeros and colons
  // Pattern: hh:mm:ss.ms or mm:ss.ms or ss.ms
  const parts = result.split(':');
  
  if (parts.length === 3) {
    // Format: hh:mm:ss.ms
    const hours = parseInt(parts[0], 10) || 0;
    const minutes = parseInt(parts[1], 10) || 0;
    const seconds = parts[2];
    
    if (hours === 0 && minutes === 0) {
      // 00:00:ss.ms → ss.ms
      return seconds;
    } else if (hours === 0) {
      // 00:mm:ss.ms → mm:ss.ms (remove leading 0 from minutes if present)
      const minStr = minutes.toString();
      return `${minStr}:${seconds}`;
    } else {
      // hh:mm:ss.ms (remove leading 0 from hours if present)
      const hourStr = hours.toString();
      const minStr = minutes.toString();
      return `${hourStr}:${minStr}:${seconds}`;
    }
  } else if (parts.length === 2) {
    // Format: mm:ss.ms
    const minutes = parseInt(parts[0], 10) || 0;
    const seconds = parts[1];
    
    if (minutes === 0) {
      // 00:ss.ms → ss.ms
      return seconds;
    } else {
      // mm:ss.ms (remove leading 0 from minutes if present)
      const minStr = minutes.toString();
      return `${minStr}:${seconds}`;
    }
  } else {
    // Format: ss.ms (already in correct format, just return)
    return result;
  }
}

/**
 * Format highlight data from row
 */
function formatHighlightData(row, h2hMapping = null) {
  const getCol = (key) => {
    const colName = COLUMN_MAPPINGS[key];
    return (row[colName] || '').trim();
  };

  const sport = getCol('SPORT');
  const sportTeamsg = getCol('SPORT_TEAMSG') || sport;
  const discipline = getCol('DISCIPLINE');
  
  const isH2H = h2hMapping ? isH2HSport(sport, discipline, h2hMapping) : false;
  
  const competitorName = getCol('COMPETITOR_NAME');
  const competitorCountry = getCol('COMPETITOR_COUNTRY');

  return {
    sport,
    sportTeamsg,
    discipline,
    event: getCol('EVENT'),
    eventCustom: getCol('EVENT_CUSTOM'),
    eventGender: getCol('EVENT_GENDER'),
    stage: getCol('STAGE'),
    heat: getCol('HEAT'),
    venue: getCol('VENUE'),
    dateSgp: getCol('DATE_SGP'),
    athleteName: getCol('ATHLETE_NAME'),
    countrySgp: getCol('COUNTRY_SGP') || 'SGP',
    timingSgp: formatTiming(getCol('TIMING_SGP')),
    scoreSgp: getCol('SCORE_SGP'),
    scoreCompetitor: getCol('SCORE_COMPETITOR'),
    competitorName,
    competitorCountry,
    winDrawLose: getCol('WIN_DRAW_LOSE'),
    position: getCol('POSITION'),
    finalPosition: getCol('FINAL_POSITION'),
    advanced: getCol('ADVANCED'),
    medals: getCol('MEDALS'),
    remarks: getCol('REMARKS'),
    type: isH2H ? 'h2h' : 'non-h2h',
  };
}

/**
 * Resolve flag image path from country code/name
 * Uses flag images from the flags folder
 */
function resolveFlag(countryValue) {
  if (!countryValue) return { icon: '', image: '' };
  const country = String(countryValue).trim().toUpperCase();
  if (!country) return { icon: '', image: '' };
  
  // Map country codes to flag filenames
  const flagMap = {
    'SGP': { code: 'SIN', ext: 'png' },
    'SINGAPORE': { code: 'SIN', ext: 'png' },
    'MAS': { code: 'MAS', ext: 'png' },
    'MALAYSIA': { code: 'MAS', ext: 'png' },
    'THA': { code: 'THA', ext: 'png' },
    'THAILAND': { code: 'THA', ext: 'png' },
    'PHI': { code: 'PHI', ext: 'png' },
    'PHILIPPINES': { code: 'PHI', ext: 'png' },
    'VIE': { code: 'VIE', ext: 'png' },
    'VIETNAM': { code: 'VIE', ext: 'png' },
    'INA': { code: 'INA', ext: 'png' },
    'INDONESIA': { code: 'INA', ext: 'png' },
    'MYA': { code: 'MYA', ext: 'png' },
    'MYANMAR': { code: 'MYA', ext: 'png' },
    'CAM': { code: 'CAM', ext: 'png' },
    'CAMBODIA': { code: 'CAM', ext: 'png' },
    'LAO': { code: 'LAO', ext: 'png' },
    'LAOS': { code: 'LAO', ext: 'png' },
    'BRU': { code: 'BRU', ext: 'jpg' },
    'BRUNEI': { code: 'BRU', ext: 'jpg' },
    'TLS': { code: 'TLS', ext: 'png' },
    'TIMOR-LESTE': { code: 'TLS', ext: 'png' },
  };
  
  let flagInfo = flagMap[country];
  if (!flagInfo) {
    for (const [key, info] of Object.entries(flagMap)) {
      if (country.includes(key) || key.includes(country)) {
        flagInfo = info;
        break;
      }
    }
  }
  
  if (flagInfo) {
    return {
      icon: '',
      image: `flags/${flagInfo.code}.${flagInfo.ext}`,
    };
  }
  
  return { icon: '', image: '' };
}

/**
 * Normalize medal value to label and icon
 */
function normalizeMedal(medalValue) {
  if (!medalValue) return { label: '', icon: '' };
  
  const medalText = String(medalValue).trim().toLowerCase();
  if (!medalText || ['na', 'n/a', 'none', 'no medal', 'nil'].includes(medalText)) {
    return { label: '', icon: '' };
  }
  
  if (medalText.includes('gold')) {
    return { label: medalValue.trim(), icon: '🥇' };
  } else if (medalText.includes('silver')) {
    return { label: medalValue.trim(), icon: '🥈' };
  } else if (medalText.includes('bronze')) {
    return { label: medalValue.trim(), icon: '🥉' };
  }
  
  return { label: '', icon: '' };
}

/**
 * Build card from highlight data
 */
function buildCardFromHighlight(highlight, index) {
  const sport = (highlight.sport || 'Sport Name').trim();
  const sportTeamsg = (highlight.sportTeamsg || sport).trim();
  
  const eventCustom = (highlight.eventCustom || highlight.event || '').trim();
  const stage = (highlight.stage || '').trim();
  const eventDetails = eventCustom && stage 
    ? `${eventCustom} - ${stage}`
    : eventCustom || stage || 'Event Details';
  
  const scoreSgp = (highlight.scoreSgp || '').trim();
  const scoreCompetitor = (highlight.scoreCompetitor || '').trim();
  const timing = (highlight.timingSgp || '').trim();
  
  let primaryScore = '';
  let opponentScore = '';
  const isH2H = highlight.type === 'h2h';
  
  if (isH2H) {
    // For H2H sports, use both scores if available
    if (scoreSgp && scoreCompetitor) {
      primaryScore = scoreSgp;
      opponentScore = scoreCompetitor;
    } else if (scoreSgp) {
      primaryScore = scoreSgp;
      opponentScore = scoreCompetitor || ''; // Still show opponent even without score
    } else if (scoreCompetitor) {
      primaryScore = scoreSgp || '';
      opponentScore = scoreCompetitor;
    }
  } else {
    // For non-H2H sports, use score or timing
    if (scoreSgp) {
      primaryScore = scoreSgp;
    } else if (timing) {
      primaryScore = timing;
    }
  }
  
  const { label: medalLabel, icon: medalIcon } = normalizeMedal(highlight.medals);
  
  const competitors = [];
  const primaryName = (highlight.athleteName || 'Athlete Name').trim();
  const primaryCountry = (highlight.countrySgp || 'SGP').trim();
  
  const primaryFlag = resolveFlag(primaryCountry);
  competitors.push({
    flagIcon: primaryFlag.icon,
    flagImage: primaryFlag.image,
    name: primaryName,
    country: primaryCountry,
    score: primaryScore,
    isPrimary: true,
  });
  
  // For H2H sports, always show opponent if competitor data exists
  if (isH2H) {
    const competitorName = (highlight.competitorName || '').trim();
    const competitorCountry = (highlight.competitorCountry || '').trim();
    
    if (competitorName || competitorCountry) {
      const opponentFlag = resolveFlag(competitorCountry);
      competitors.push({
        flagIcon: opponentFlag.icon,
        flagImage: opponentFlag.image,
        name: competitorName || 'Opponent',
        country: competitorCountry,
        score: opponentScore,
        isPrimary: false,
      });
    }
  }
  
  const resultBadge = (highlight.winDrawLose || '').trim() || medalLabel;
  
  return {
    index,
    sport: sportTeamsg,
    sportIconUrl: getSportIconUrl(sport), // Use SPORT column for icon mapping
    medalLabel,
    medalIcon,
    athletes: primaryName,
    eventDetails,
    resultSummary: generateResultSummary(highlight),
    resultBadge: resultBadge && !['na', 'n/a', 'none'].includes(resultBadge.toLowerCase()) ? resultBadge : '',
    competitors,
  };
}

/**
 * Chunk cards into slides (9 cards per slide)
 */
function chunkCards(cards, chunkSize = 9) {
  if (chunkSize <= 0) return [cards];
  
  const slides = [];
  for (let i = 0; i < cards.length; i += chunkSize) {
    slides.push(cards.slice(i, i + chunkSize));
  }
  
  return slides.length > 0 ? slides : [[]];
}

/**
 * Generate result summary text
 */
function generateResultSummary(highlight) {
  const parts = [];
  
  if (highlight.type === 'h2h') {
    if (highlight.scoreSgp && highlight.scoreCompetitor) {
      parts.push(`${highlight.scoreSgp}-${highlight.scoreCompetitor}`);
    } else if (highlight.scoreSgp) {
      parts.push(highlight.scoreSgp);
    }
  } else {
    if (highlight.timingSgp) {
      parts.push(`Time: ${highlight.timingSgp}`);
    } else if (highlight.scoreSgp) {
      parts.push(`Score: ${highlight.scoreSgp}`);
    }
  }
  
  if (highlight.medals) {
    parts.push(highlight.medals);
  }
  
  return parts.join(' | ') || 'Result information';
}

/**
 * Generate highlights HTML
 */
function generateHTML(highlights, groupKey) {
  const cards = highlights.map((highlight, idx) => buildCardFromHighlight(highlight, idx + 1));
  
  cards.sort((a, b) => a.sport.localeCompare(b.sport));
  
  cards.forEach((card, idx) => {
    card.index = idx + 1;
  });
  
  const slides = chunkCards(cards, 9);
  
  let goldCount = 0;
  for (const highlight of highlights) {
    const medals = (highlight.medals || '').trim().toLowerCase();
    if (medals && !['na', 'n/a', 'none', 'no medal', 'nil'].includes(medals) && medals.includes('gold')) {
      goldCount++;
    }
  }
  
  let formattedDate = groupKey;
  if (groupKey && /^\d{4}-\d{2}-\d{2}$/.test(groupKey)) {
    try {
      const dateObj = new Date(groupKey + 'T00:00:00');
      const months = ['January', 'February', 'March', 'April', 'May', 'June', 
                     'July', 'August', 'September', 'October', 'November', 'December'];
      formattedDate = `${dateObj.getDate()} ${months[dateObj.getMonth()]} ${dateObj.getFullYear()}`;
    } catch (e) {
    }
  }
  
  const sectionTitle = formattedDate ? `GOLD MEDALS FOR ${formattedDate.toUpperCase()}` : 'GOLD MEDALS FOR THE DAY';
  const subtitle = 'SEAG25 Competition Results';
  const generationDate = new Date().toISOString().replace('T', ' ').substring(0, 19);
  
  // Get unique sports for header icon (use first sport's icon)
  const uniqueSports = [...new Set(cards.map(c => c.sport.split(' - ')[0]))];
  return generateHTMLTemplate(cards, slides, sectionTitle, subtitle, groupKey, generationDate, goldCount);
}

/**
 * Generate HTML template
 */
function generateHTMLTemplate(cards, slides, sectionTitle, subtitle, groupKey, generationDate, goldCount) {
  return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>${sectionTitle} | SEAG25</title>
    <style>
        * { box-sizing: border-box; }
        body {
            margin: 0;
            background: #e9e9ee;
            font-family: 'Montserrat', 'Helvetica Neue', Arial, sans-serif;
            color: #1f1f1f;
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
        }
        .results-canvas {
            width: 1920px;
            height: 1080px;
            background: #f4f4f8;
            padding: 32px 48px;
            box-sizing: border-box;
            overflow-y: auto;
            border-radius: 28px;
            box-shadow: 0 18px 48px rgba(0, 0, 0, 0.12);
        }
        .results-section { max-width: 100%; margin: 0 auto; }
        .results-header {
            margin-bottom: 32px;
            padding: 0;
            background: transparent;
            display: flex;
            align-items: stretch;
            gap: 24px;
        }
        .results-title-container {
            flex: 3;
            padding: 24px 32px;
            background: #bd1e2d;
            color: #ffffff;
            border-radius: 20px;
            box-shadow: 0 14px 30px rgba(189, 30, 45, 0.28);
            display: flex;
            align-items: center;
            gap: 16px;
        }
        .results-title {
            margin: 0;
            font-size: 30px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.12em;
        }
        .results-sport-icon {
            width: 48px;
            height: 48px;
            object-fit: contain;
            flex-shrink: 0;
        }
        .results-medal-tally {
            flex: 0 0 auto;
            padding: 24px 20px;
            background: #bd1e2d;
            color: #ffffff;
            border-radius: 20px;
            box-shadow: 0 14px 30px rgba(189, 30, 45, 0.28);
            font-size: 32px;
            font-weight: 700;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            white-space: nowrap;
        }
        .results-grid {
            display: grid;
            grid-template-columns: repeat(3, minmax(300px, 1fr));
            gap: 24px;
        }
        .results-carousel {
            position: relative;
        }
        .carousel-track {
            position: relative;
            width: 100%;
        }
        .carousel-slide {
            display: none;
        }
        .carousel-slide.active {
            display: block;
            animation: fadeIn 200ms ease-in;
        }
        .carousel-dots {
            margin-top: 18px;
            display: flex;
            gap: 10px;
            justify-content: center;
        }
        .carousel-dot {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            background: rgba(189, 30, 45, 0.25);
            border: none;
            cursor: pointer;
            transition: transform 160ms ease, background 160ms ease;
        }
        .carousel-dot.active {
            background: #bd1e2d;
            transform: scale(1.2);
        }
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .result-card {
            display: flex;
            flex-direction: column;
            min-height: 240px;
            background: #fff;
            border-radius: 20px;
            box-shadow: 0 16px 40px rgba(0, 0, 0, 0.08);
            overflow: hidden;
            position: relative;
        }
        .card-header {
            padding: 16px 22px;
            background: #ffffff;
            border-bottom: 3px solid #bd1e2d;
            display: flex;
            flex-direction: column;
            gap: 8px;
        }
        .card-header-title-row {
            display: flex;
            align-items: center;
            gap: 12px;
        }
        .card-header-icon-container {
            width: 32px;
            height: 32px;
            min-width: 32px;
            min-height: 32px;
            max-width: 32px;
            max-height: 32px;
            flex-shrink: 0;
            display: flex;
            align-items: center;
            justify-content: center;
            overflow: hidden;
        }
        .card-header-icon {
            width: 100%;
            height: 100%;
            object-fit: contain;
            object-position: center;
            filter: brightness(0) saturate(100%);
            opacity: 0.8;
        }
        .card-header-title {
            margin: 0;
            font-size: 16px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: #111;
            flex: 1;
        }
        .card-header-subtitle {
            margin: 0 0 12px 0;
            font-size: 13px;
            font-weight: 500;
            color: #4b4b4b;
        }
        .card-main {
            flex: 1;
            padding: 22px 24px;
            display: flex;
            flex-direction: column;
        }
        .card-content {
            display: flex;
            flex-direction: column;
            gap: 10px;
        }
        .card-title {
            margin: 0;
            font-size: 14px;
            font-weight: 700;
            text-transform: uppercase;
            color: #111;
        }
        .card-athletes {
            margin: 0;
            font-size: 13px;
            font-weight: 600;
            color: #ba1b27;
        }
        .card-event {
            margin: 0;
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: #4b4b4b;
        }
        .card-scoreboard {
            border-radius: 12px;
            background: #f9f9fb;
            padding: 10px 14px;
            display: flex;
            flex-direction: column;
            gap: 10px;
        }
        .score-row {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 14px;
            flex-wrap: nowrap;
        }
        .score-row[data-role="primary"] { font-weight: 700; }
        .score-info {
            display: flex;
            align-items: center;
            gap: 12px;
            flex: 1;
            min-width: 0;
        }
        .flag-circle {
            width: 42px;
            height: 28px;
            border-radius: 6px;
            background: #ffffff;
            box-shadow: inset 0 0 0 1px rgba(0,0,0,0.08);
            display: flex;
            align-items: center;
            justify-content: center;
            overflow: hidden;
            flex-shrink: 0;
        }
        .flag-circle img {
            width: 100%;
            height: 100%;
            object-fit: cover;
        }
        .flag-emoji {
            font-size: 24px;
            line-height: 1;
        }
        .flag-placeholder {
            display: flex;
            align-items: center;
            justify-content: center;
            width: 42px;
            height: 28px;
            border-radius: 6px;
            background: #d3d3d3;
        }
        .score-meta { display: flex; flex-direction: column; gap: 2px; }
        .competitor-name { font-size: 12px; color: #1b1b1b; }
        .competitor-country {
            font-size: 10px;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: #7a7a7a;
        }
        .score-value {
            font-size: 15px;
            font-weight: 700;
            min-width: 40px;
            text-align: right;
            color: #0f172a;
            margin-left: auto;
            padding: 6px 14px;
            border-radius: 12px;
            background: #eef0f6;
            flex-shrink: 0;
            white-space: nowrap;
            font-variant-numeric: tabular-nums;
        }
        .card-result {
            margin: 0;
            font-size: 13px;
            line-height: 1.6;
            color: #333;
        }
        .result-badge {
            align-self: flex-start;
            padding: 3px 9px;
            border-radius: 999px;
            background: #ba1b27;
            color: #fff;
            font-size: 10px;
            text-transform: uppercase;
            letter-spacing: 0.1em;
        }
    </style>
</head>
<body>
    <div class="results-canvas">
        <section class="results-section">
            <header class="results-header">
                <div class="results-title-container">
                    <h2 class="results-title">${sectionTitle}</h2>
                </div>
                <div class="results-medal-tally">
                    ${goldCount} 🥇
                </div>
            </header>
            <div class="results-carousel" data-total-slides="${slides.length}">
                <div class="carousel-track" id="results-carousel-track">
                    ${slides.map((slide, slideIdx) => `
                    <div class="carousel-slide${slideIdx === 0 ? ' active' : ''}" data-slide-index="${slideIdx}">
                        <div class="results-grid">
                            ${slide.map(card => `
                            <article class="result-card" data-card-index="${card.index}">
                                <div class="card-header">
                                    <div class="card-header-title-row">
                                        ${card.sportIconUrl ? `<div class="card-header-icon-container"><img src="${card.sportIconUrl}" alt="${card.sport} icon" class="card-header-icon" /></div>` : ''}
                                        <h3 class="card-header-title">${card.sport}</h3>
                                    </div>
                                </div>
                                <div class="card-main">
                                    <div class="card-content">
                                        <p class="card-header-subtitle">${card.eventDetails}</p>
                                        <p class="card-athletes">${card.athletes}</p>
                                        <div class="card-scoreboard">
                                            ${card.competitors.map((competitor, idx) => `
                                            <div class="score-row" data-role="${idx === 0 ? 'primary' : 'opponent'}">
                                                <div class="score-info">
                                                    <div class="flag-circle">
                                                        ${competitor.flagImage ? `<img src="${competitor.flagImage}" alt="${competitor.country} flag" />` : competitor.flagIcon ? `<span class="flag-emoji" aria-hidden="true">${competitor.flagIcon}</span>` : `<span class="flag-placeholder"></span>`}
                                                    </div>
                                                    <div class="score-meta">
                                                        <span class="competitor-name">${competitor.name}</span>
                                                        <span class="competitor-country">${competitor.country}</span>
                                                    </div>
                                                </div>
                                                ${competitor.score ? `<span class="score-value">${competitor.score}</span>` : ''}
                                            </div>
                                            `).join('')}
                                        </div>
                                    </div>
                                </div>
                            </article>
                            `).join('')}
                        </div>
                    </div>
                    `).join('')}
                </div>
                <div class="carousel-dots" id="results-carousel-dots">
                    ${slides.map((_, idx) => `<button class="carousel-dot${idx === 0 ? ' active' : ''}" data-slide="${idx}"></button>`).join('')}
                </div>
            </div>
        </section>
    </div>
</body>
</html>`;
}

/**
 * Main function to generate highlights
 */
async function generateHighlights({ spreadsheetId, sheetName, date, sport }) {
  try {
    const sheetsClient = await getSheetsClient();
    
    const h2hMapping = await loadH2HSportsMapping(sheetsClient, spreadsheetId);
    
    const { data } = await loadData(sheetsClient, spreadsheetId, sheetName);
    
    let validRows = filterHighlightRows(data);
    
    let folderDate = date;
    if (!folderDate) {
      const today = new Date();
      folderDate = today.toISOString().split('T')[0];
    }
    
    if (date) {
      const normalizedInputDate = normalizeDate(date);
      
      validRows = validRows.filter(row => {
        const rowDate = (row[COLUMN_MAPPINGS.DATE_SGP] || '').trim();
        if (!rowDate) return false;
        
        const normalizedRowDate = normalizeDate(rowDate);
        return normalizedRowDate === normalizedInputDate;
      });
    }
    
    if (sport) {
      validRows = validRows.filter(row => {
        const rowSport = (row[COLUMN_MAPPINGS.SPORT] || '').trim();
        return rowSport.toLowerCase() === sport.toLowerCase();
      });
    }
    
    const highlights = validRows.map(row => formatHighlightData(row, h2hMapping));
    
    const groupKey = date || sport || 'All Highlights';
    
    const html = generateHTML(highlights, groupKey);
    
    const gcsBucketName = process.env.GCS_BUCKET_NAME || 'seag25-highlights';
    console.log(`Using GCS bucket: ${gcsBucketName}`);
    
    let gcsFiles = {
      html: null,
      screenshots: [],
    };
    
    // Only try to save to GCS if bucket name is configured
    if (gcsBucketName && gcsBucketName !== 'seag25-highlights') {
      try {
        const storageClient = getStorageClient();
        const timestamp = new Date().toISOString().replace(/[:.]/g, '-').split('T')[0] + '_' + 
                          new Date().toISOString().split('T')[1].split('.')[0].replace(/:/g, '-');
        const baseFileName = `highlights_${groupKey.replace(/[^a-zA-Z0-9]/g, '_')}_${timestamp}`;
        const htmlFileName = `${baseFileName}.html`;
        
        const gcsFolderPath = `highlights/${folderDate}`;
        const htmlGcsInfo = await saveHtmlToGCS(storageClient, gcsBucketName, gcsFolderPath, htmlFileName, html);
        gcsFiles.html = htmlGcsInfo;
        console.log(`Saved HTML to GCS: ${htmlGcsInfo.publicUrl}`);
        
        if (puppeteer && highlights.length > 0) {
          try {
            const screenshots = await generateScreenshotsToGCS(html, storageClient, gcsBucketName, gcsFolderPath, baseFileName);
            gcsFiles.screenshots = screenshots;
            console.log(`Generated ${screenshots.length} screenshot(s) to GCS`);
          } catch (screenshotError) {
            console.error('Error generating screenshots:', screenshotError.message);
          }
        }
      } catch (gcsError) {
        console.error('Error saving to GCS:', gcsError.message);
        // Continue anyway - return HTML even if GCS save fails
      }
    } else {
      console.log('Skipping GCS save (local test mode)');
    }
    
    return {
      html,
      highlightCount: highlights.length,
      groupKey,
      folderDate,
      gcsFiles,
    };
  } catch (error) {
    console.error('Error in generateHighlights:', error);
    throw error;
  }
}

/**
 * Generate screenshots from HTML and save to GCS
 */
async function generateScreenshotsToGCS(htmlContent, storageClient, bucketName, folderPath, baseFileName) {
  if (!puppeteer || !chromium) {
    console.log('Puppeteer/Chromium not available, skipping screenshots');
    return [];
  }
  
  try {
    let executablePath;
    let launchArgs;
    
    if (chromium) {
      executablePath = await chromium.executablePath();
      launchArgs = chromium.args;
    } else {
      executablePath = undefined;
      launchArgs = [
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--disable-dev-shm-usage',
        '--disable-gpu',
        '--single-process',
      ];
    }
    
    const browser = await puppeteer.launch({
      headless: true,
      args: launchArgs,
      executablePath: executablePath,
    });
    
    const page = await browser.newPage();
    await page.setViewport({ width: 1920, height: 1080, deviceScaleFactor: 2 });
    await page.emulateMediaType('screen');
    
    await page.setContent(htmlContent, { waitUntil: 'networkidle0' });
    
    await page.addStyleTag({ content: '.carousel-dots { display: none !important; }' });
    
    await new Promise(resolve => setTimeout(resolve, 500));
    
    const screenshotFiles = [];
    const canvas = await page.$('.results-canvas');
    
    if (!canvas) {
      console.log('Canvas not found, cannot generate screenshots');
      await browser.close();
      return [];
    }
    
    const slides = await page.$$('.results-carousel .carousel-slide');
    
    if (slides.length > 0) {
      for (let idx = 0; idx < slides.length; idx++) {
        await page.evaluate((index) => {
          const allSlides = Array.from(document.querySelectorAll('.results-carousel .carousel-slide'));
          allSlides.forEach((slide, i) => {
            slide.style.display = i === index ? 'block' : 'none';
            slide.classList.toggle('active', i === index);
          });
          window.scrollTo({ top: 0, left: 0, behavior: 'auto' });
        }, idx);
        
        await new Promise(resolve => setTimeout(resolve, 200));
        
        const screenshotBuffer = await canvas.screenshot({ type: 'png' });
        const screenshotFileName = `${baseFileName}_slide_${String(idx + 1).padStart(2, '0')}.png`;
        
        const screenshotGcsInfo = await saveImageToGCS(
          storageClient,
          bucketName,
          folderPath,
          screenshotFileName,
          screenshotBuffer
        );
        
        screenshotFiles.push(screenshotGcsInfo);
        console.log(`Saved screenshot to GCS: ${screenshotGcsInfo.publicUrl}`);
      }
    } else {
      await page.evaluate(() => {
        window.scrollTo(0, 0);
      });
      await new Promise(resolve => setTimeout(resolve, 200));
      
      const screenshotBuffer = await canvas.screenshot({ type: 'png' });
      const screenshotFileName = `${baseFileName}_slide_01.png`;
      
      const screenshotGcsInfo = await saveImageToGCS(
        storageClient,
        bucketName,
        folderPath,
        screenshotFileName,
        screenshotBuffer
      );
      
      screenshotFiles.push(screenshotGcsInfo);
      console.log(`Saved screenshot to GCS: ${screenshotGcsInfo.publicUrl}`);
    }
    
    await browser.close();
    return screenshotFiles;
  } catch (error) {
    console.error('Error in generateScreenshotsToGCS:', error);
    throw error;
  }
}

module.exports = { 
  generateHighlights,
  getStorageClient,
  saveHtmlToGCS,
  saveImageToGCS,
};

