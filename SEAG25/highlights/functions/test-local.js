/**
 * Test highlights generation locally
 */

const fs = require('fs').promises;
const path = require('path');

async function testLocal() {
  console.log('🧪 Testing highlights generation locally...\n');

  // Mock environment variables for local testing
  const credentialsPath = path.join(__dirname, '../../../AYG25/ayg-form-system/google_credentials.json');
  const credentials = JSON.parse(await fs.readFile(credentialsPath, 'utf8'));
  process.env.GOOGLE_CREDENTIALS_JSON = JSON.stringify(credentials);
  process.env.GCS_BUCKET_NAME = 'seag25-highlights-images'; // Dummy for local test

  const spreadsheetId = '15zXDQdkGeAN2AMMdrJ_qjkjReq_Y3mlU1-_7ciniyS4';
  const sheetName = 'Com Schedule - Test';
  const date = '2025-12-10'; // Date to test

  const outputDir = path.join(__dirname, '../test-output');
  await fs.mkdir(outputDir, { recursive: true });

  try {
    console.log('📊 Calling generateHighlights...');
    
    // Call generateHighlights directly - it will skip GCS in local test mode
    const generateHighlightsModule = require('./generateHighlights');
    const result = await generateHighlightsModule.generateHighlights({ spreadsheetId, sheetName, date });


    console.log(`\n✅ Generated ${result.highlightCount} highlights`);
    console.log(`📄 Group Key: ${result.groupKey}`);
    console.log(`📅 Folder Date: ${result.folderDate}`);

    if (result.highlightCount === 0) {
      console.warn(`\n⚠️  No highlights found. This could mean:
   - No gold medals in the test data
   - Date filter not matching
   - Missing required fields in test data`);
    }

    // Save HTML locally for viewing
    if (result.html) {
      const timestamp = new Date().toISOString().replace(/[:.]/g, '-').split('T')[0] + '_' + 
                        new Date().toISOString().split('T')[1].split('.')[0].replace(/:/g, '-');
      const htmlFileName = `highlights_${result.groupKey.replace(/[^a-zA-Z0-9]/g, '_')}_${timestamp}.html`;
      const htmlPath = path.join(outputDir, htmlFileName);
      await fs.writeFile(htmlPath, result.html);
      
      console.log(`\n📄 HTML saved to: ${htmlPath}`);
      console.log(`   Note: Flags and sports icons need to be in the same directory or use absolute paths`);
      console.log(`   For testing, you can symlink: ln -s ../flags test-output/flags && ln -s ../sports test-output/sports`);
    }

    if (result.gcsFiles && result.gcsFiles.html) {
      console.log(`\n📄 HTML also saved to GCS: ${result.gcsFiles.html.filePath}`);
    }

    if (result.gcsFiles && result.gcsFiles.screenshots && result.gcsFiles.screenshots.length > 0) {
      console.log(`\n📸 Generated ${result.gcsFiles.screenshots.length} screenshot(s):`);
      result.gcsFiles.screenshots.forEach((s, i) => {
        console.log(`   ${i + 1}. ${s.filePath}`);
      });
    } else {
      console.warn('\n⚠️  No screenshots generated (Puppeteer may not be working locally)');
    }


  } catch (error) {
    console.error('\n❌ Error in local test:', error);
    console.error(error.stack);
  } finally {
    console.log('\n✅ Test complete!\n');
  }
}

testLocal();

