/**
 * Firebase Functions for SEAG25 Highlights Generator
 */

const functions = require('firebase-functions/v1');
const { generateHighlights } = require('./generateHighlights');

/**
 * HTTP endpoint for generating highlights
 */
exports.generateHighlightsHttpV2 = functions.https.onRequest(async (req, res) => {
  // Enable CORS
  res.set('Access-Control-Allow-Origin', '*');
  res.set('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.set('Access-Control-Allow-Headers', 'Content-Type');

  if (req.method === 'OPTIONS') {
    res.status(204).send('');
    return;
  }

  if (req.method !== 'POST') {
    res.status(405).json({ error: 'Method not allowed. Use POST.' });
    return;
  }

  try {
    const { spreadsheetId, sheetName, date, sport } = req.body;

    if (!spreadsheetId || !sheetName) {
      res.status(400).json({ 
        error: 'Missing required parameters: spreadsheetId and sheetName are required' 
      });
      return;
    }

    console.log(`Generating highlights for: ${spreadsheetId}, sheet: ${sheetName}, date: ${date || 'all'}`);

    const result = await generateHighlights({
      spreadsheetId,
      sheetName,
      date,
      sport,
    });

    res.status(200).json({
      success: true,
      highlightCount: result.highlightCount,
      groupKey: result.groupKey,
      folderDate: result.folderDate,
      gcsFiles: result.gcsFiles,
    });
  } catch (error) {
    console.error('Error in generateHighlightsHttpV2:', error);
    res.status(500).json({
      success: false,
      error: error.message || 'Internal server error',
    });
  }
});

