/**
 * Scrape sports icons from SEAG25 website
 * Saves icons to flags directory (reusing the flags folder structure)
 */

const https = require('https');
const fs = require('fs');
const path = require('path');
let puppeteer = null;
try {
  puppeteer = require('puppeteer');
} catch (e) {
  try {
    puppeteer = require('puppeteer-core');
  } catch (e2) {
    console.log('Puppeteer not available, will try direct download');
  }
}

const SPORTS_URL = 'https://www.seagames2025.org/sports';
const ICONS_DIR = path.join(__dirname, '../flags/sports');

// Ensure icons directory exists
if (!fs.existsSync(ICONS_DIR)) {
  fs.mkdirSync(ICONS_DIR, { recursive: true });
}

/**
 * Download a file from URL
 */
function downloadFile(url, filePath) {
  return new Promise((resolve, reject) => {
    const file = fs.createWriteStream(filePath);
    https.get(url, (response) => {
      if (response.statusCode === 200) {
        response.pipe(file);
        file.on('finish', () => {
          file.close();
          resolve(filePath);
        });
      } else if (response.statusCode === 301 || response.statusCode === 302) {
        file.close();
        fs.unlinkSync(filePath);
        downloadFile(response.headers.location, filePath).then(resolve).catch(reject);
      } else {
        file.close();
        fs.unlinkSync(filePath);
        reject(new Error(`Failed to download: ${response.statusCode}`));
      }
    }).on('error', (err) => {
      file.close();
      if (fs.existsSync(filePath)) {
        fs.unlinkSync(filePath);
      }
      reject(err);
    });
  });
}

/**
 * Scrape sports icons from SEAG25 website using Puppeteer
 */
async function scrapeSportsIcons() {
  try {
    console.log('Fetching sports page...');
    
    let iconUrls = [];
    
    if (puppeteer) {
      console.log('Using Puppeteer to scrape dynamic content...');
      const browser = await puppeteer.launch({ headless: true });
      const page = await browser.newPage();
      await page.goto(SPORTS_URL, { waitUntil: 'networkidle0' });
      
      // Wait a bit for dynamic content
      await new Promise(resolve => setTimeout(resolve, 2000));
      
      // Extract all icon URLs
      iconUrls = await page.evaluate(() => {
        const images = Array.from(document.querySelectorAll('img'));
        return images
          .map(img => img.src || img.getAttribute('src'))
          .filter(src => src && src.includes('SPORTS-') && src.includes('Icon_'))
          .filter((v, i, a) => a.indexOf(v) === i); // Remove duplicates
      });
      
      await browser.close();
    } else {
      console.log('Puppeteer not available, trying known sports...');
      // Fallback: try common sports
      const commonSports = [
        'Air Sports', 'Aquatics', 'Archery', 'Athletics', 'Badminton',
        'Baseball', 'Basketball', 'Billiards', 'Boxing', 'Chess', 'Cricket',
        'Cycling', 'E-Sports', 'Floorball', 'Flying Disc', 'Football',
        'Golf', 'Gymnastics', 'Handball', 'Hockey', 'Ice Hockey',
        'Jiu-Jitsu', 'Judo', 'Karate', 'Kickboxing', 'Mixed Martial Arts',
        'Muay', 'Netball', 'Pencak Silat', 'Rugby', 'Sailing', 'Sepak Takraw',
        'Shooting', 'Softball', 'Squash', 'Table Tennis', 'Taekwondo',
        'Tennis', 'Traditional Boat Race', 'Tug of War', 'Volleyball', 'Weightlifting'
      ];
      
      for (const sport of commonSports) {
        const sportUpper = sport.toUpperCase().replace(/\s+/g, '-');
        const iconName = encodeURIComponent(sport);
        const url = `https://storage.googleapis.com/seagames-2025.firebasestorage.app/content/SPORTS-${sportUpper}/Icon_${iconName}.png`;
        iconUrls.push(url);
      }
    }
    
    console.log(`Found ${iconUrls.length} sport icon URLs`);
    
    const downloaded = [];
    const failed = [];
    
    for (const src of iconUrls) {
      if (!src || !src.includes('Icon_')) {
        continue;
      }
      
      // Extract sport name from URL
      // URL pattern: .../SPORTS-{SPORT}/Icon_{Sport Name}.png
      const urlMatch = src.match(/SPORTS-([^/]+)\/Icon_([^.]+)\.(png|jpg|jpeg)/i);
      if (!urlMatch) {
        console.log(`  ⚠️  Skipping: ${src} (doesn't match pattern)`);
        continue;
      }
      
      const sportFolder = urlMatch[1];
      const sportName = decodeURIComponent(urlMatch[2]);
      const ext = urlMatch[3];
      
      // Create filename from sport name
      const fileName = `Icon_${sportName.replace(/\s+/g, '_')}.${ext}`;
      const filePath = path.join(ICONS_DIR, fileName);
      
      // Skip if already exists
      if (fs.existsSync(filePath)) {
        console.log(`  ⊙ Skipping (exists): ${sportName}`);
        downloaded.push({ sport: sportName, file: fileName, url: src });
        continue;
      }
      
      try {
        console.log(`Downloading: ${sportName} -> ${fileName}`);
        await downloadFile(src, filePath);
        downloaded.push({ sport: sportName, file: fileName, url: src });
        console.log(`  ✓ Saved: ${filePath}`);
      } catch (error) {
        console.error(`  ✗ Failed: ${sportName} - ${error.message}`);
        failed.push({ sport: sportName, error: error.message });
      }
    }
    
    console.log(`\n✅ Downloaded ${downloaded.length} icons`);
    if (failed.length > 0) {
      console.log(`\n❌ Failed ${failed.length} downloads:`);
      failed.forEach(f => console.log(`   - ${f.sport}: ${f.error}`));
    }
    
    // Create a mapping file
    const mapping = downloaded.map(d => ({
      sport: d.sport,
      fileName: d.file,
      url: d.url,
    }));
    
    const mappingPath = path.join(ICONS_DIR, 'sports-icons-mapping.json');
    fs.writeFileSync(mappingPath, JSON.stringify(mapping, null, 2));
    console.log(`\n📝 Saved mapping to: ${mappingPath}`);
    
  } catch (error) {
    console.error('Error scraping sports icons:', error);
    throw error;
  }
}

// Run if called directly
if (require.main === module) {
  scrapeSportsIcons()
    .then(() => {
      console.log('\n✅ Done!');
      process.exit(0);
    })
    .catch((error) => {
      console.error('\n❌ Error:', error);
      process.exit(1);
    });
}

module.exports = { scrapeSportsIcons };

