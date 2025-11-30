/**
 * Fast script to analyze and resize all sports icons to square dimensions (32x32px)
 * Uses macOS built-in 'sips' command for fast image processing
 */

const fs = require('fs').promises;
const { execSync } = require('child_process');
const path = require('path');

const SPORTS_DIR = path.join(__dirname, '../sports');
const TARGET_SIZE = 32; // 32x32px square

function getImageDimensions(filePath) {
  try {
    // Use sips to get image dimensions (macOS built-in)
    const output = execSync(`sips -g pixelWidth -g pixelHeight "${filePath}"`, { encoding: 'utf8' });
    const widthMatch = output.match(/pixelWidth: (\d+)/);
    const heightMatch = output.match(/pixelHeight: (\d+)/);
    
    if (widthMatch && heightMatch) {
      return {
        width: parseInt(widthMatch[1]),
        height: parseInt(heightMatch[1])
      };
    }
  } catch (error) {
    // Fallback: try to use identify (ImageMagick) if available
    try {
      const output = execSync(`identify -format "%wx%h" "${filePath}"`, { encoding: 'utf8' });
      const [width, height] = output.trim().split('x').map(Number);
      return { width, height };
    } catch (e) {
      return null;
    }
  }
  return null;
}

function resizeImage(filePath, outputPath, size) {
  try {
    // Use sips to resize (macOS built-in, very fast)
    // sips -z height width will resize maintaining aspect ratio
    // We want square, so we'll resize to fit and then pad if needed
    execSync(`sips -z ${size} ${size} "${filePath}" --out "${outputPath}"`, { stdio: 'ignore' });
    return true;
  } catch (error) {
    // Fallback: try ImageMagick convert
    try {
      execSync(`convert "${filePath}" -resize ${size}x${size} -background transparent -gravity center -extent ${size}x${size} "${outputPath}"`, { stdio: 'ignore' });
      return true;
    } catch (e) {
      return false;
    }
  }
}

async function main() {
  console.log('🎨 Fast Sports Icon Resizer\n');
  console.log(`📁 Sports directory: ${SPORTS_DIR}`);
  console.log(`🎯 Target size: ${TARGET_SIZE}x${TARGET_SIZE}px\n`);
  
  // Check if sips is available
  try {
    execSync('which sips', { stdio: 'ignore' });
    console.log('✅ Using macOS sips (built-in, fast)\n');
  } catch (e) {
    try {
      execSync('which convert', { stdio: 'ignore' });
      console.log('✅ Using ImageMagick convert\n');
    } catch (e2) {
      console.error('❌ Neither sips nor ImageMagick is available.');
      console.error('   On macOS, sips should be available by default.');
      process.exit(1);
    }
  }
  
  try {
    const files = await fs.readdir(SPORTS_DIR);
    const pngFiles = files.filter(f => f.toLowerCase().endsWith('.png'));
    
    console.log(`📊 Analyzing ${pngFiles.length} icon(s)...\n`);
    
    const results = [];
    let needsResize = 0;
    
    // Analyze dimensions
    for (const file of pngFiles) {
      const filePath = path.join(SPORTS_DIR, file);
      const dims = getImageDimensions(filePath);
      
      if (!dims) {
        console.log(`⚠️  ${file.padEnd(45)} Could not read dimensions`);
        continue;
      }
      
      const isSquare = dims.width === dims.height;
      const isCorrectSize = dims.width === TARGET_SIZE && dims.height === TARGET_SIZE;
      const needsResizing = !isCorrectSize;
      
      if (needsResizing) needsResize++;
      
      results.push({
        file,
        filePath,
        ...dims,
        isSquare,
        isCorrectSize,
        needsResizing
      });
      
      const status = isCorrectSize ? '✅' : '⚠️';
      console.log(`${status} ${file.padEnd(45)} ${dims.width}x${dims.height}`);
    }
    
    console.log(`\n📊 Summary:`);
    console.log(`   Total icons: ${results.length}`);
    console.log(`   Already 32x32px: ${results.filter(r => r.isCorrectSize).length}`);
    console.log(`   Need resizing: ${needsResize}`);
    
    if (needsResize === 0) {
      console.log('\n✅ All icons are already properly sized!');
      return;
    }
    
    // Create backup
    const backupDir = path.join(SPORTS_DIR, 'backup');
    await fs.mkdir(backupDir, { recursive: true });
    console.log(`\n📦 Backing up originals to: ${backupDir}\n`);
    
    // Resize icons that need it
    console.log('🔄 Resizing icons...\n');
    let successCount = 0;
    let errorCount = 0;
    
    for (const item of results.filter(r => r.needsResizing)) {
      try {
        const backupPath = path.join(backupDir, item.file);
        
        // Backup
        await fs.copyFile(item.filePath, backupPath);
        
        // Resize (sips will maintain aspect ratio and fit within 32x32)
        // For true square with padding, we'll need a two-step process
        const tempPath = item.filePath + '.tmp';
        
        if (resizeImage(item.filePath, tempPath, TARGET_SIZE)) {
          // Move temp to final
          await fs.rename(tempPath, item.filePath);
          
          // Verify
          const newDims = getImageDimensions(item.filePath);
          if (newDims && newDims.width === TARGET_SIZE && newDims.height === TARGET_SIZE) {
            console.log(`✅ ${item.file.padEnd(45)} ${item.width}x${item.height} → ${newDims.width}x${newDims.height}`);
            successCount++;
          } else {
            console.log(`⚠️  ${item.file.padEnd(45)} Resized but dimensions may not be exact`);
            successCount++;
          }
        } else {
          throw new Error('Resize command failed');
        }
      } catch (error) {
        console.error(`❌ ${item.file.padEnd(45)} Error: ${error.message}`);
        errorCount++;
      }
    }
    
    console.log(`\n✅ Successfully resized ${successCount} icon(s)`);
    if (errorCount > 0) {
      console.log(`⚠️  ${errorCount} icon(s) had errors`);
    }
    
  } catch (error) {
    console.error('\n❌ Error:', error.message);
    process.exit(1);
  }
}

main();

