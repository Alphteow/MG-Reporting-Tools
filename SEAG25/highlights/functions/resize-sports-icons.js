/**
 * Script to analyze and resize all sports icons to square dimensions (32x32px)
 * This ensures consistent sizing and prevents truncation in the card headers
 */

const fs = require('fs').promises;
const path = require('path');

// Try to use sharp (faster, but requires native dependencies)
// Fall back to jimp (pure JS, slower but more compatible)
let sharp = null;
let jimp = null;

try {
  sharp = require('sharp');
  console.log('✅ Using sharp for image processing');
} catch (e) {
  console.log('⚠️  sharp not available, trying jimp...');
  try {
    jimp = require('jimp');
    console.log('✅ Using jimp for image processing');
  } catch (e2) {
    console.error('❌ Neither sharp nor jimp is available. Please install one:');
    console.error('   npm install sharp');
    console.error('   OR');
    console.error('   npm install jimp');
    process.exit(1);
  }
}

const SPORTS_DIR = path.join(__dirname, '../../sports');
const TARGET_SIZE = 32; // 32x32px square

async function analyzeIconDimensions() {
  console.log('\n📊 Analyzing sports icon dimensions...\n');
  
  const files = await fs.readdir(SPORTS_DIR);
  const pngFiles = files.filter(f => f.toLowerCase().endsWith('.png'));
  
  const results = [];
  
  for (const file of pngFiles) {
    const filePath = path.join(SPORTS_DIR, file);
    
    try {
      let width, height;
      
      if (sharp) {
        const metadata = await sharp(filePath).metadata();
        width = metadata.width;
        height = metadata.height;
      } else if (jimp) {
        const image = await jimp.read(filePath);
        width = image.bitmap.width;
        height = image.bitmap.height;
      }
      
      const isSquare = width === height;
      const aspectRatio = (width / height).toFixed(2);
      
      results.push({
        file,
        width,
        height,
        isSquare,
        aspectRatio: parseFloat(aspectRatio),
        needsResize: !isSquare || width !== TARGET_SIZE || height !== TARGET_SIZE
      });
      
      const status = isSquare && width === TARGET_SIZE && height === TARGET_SIZE 
        ? '✅' 
        : '⚠️';
      console.log(`${status} ${file.padEnd(45)} ${width}x${height} (ratio: ${aspectRatio})`);
      
    } catch (error) {
      console.error(`❌ Error reading ${file}:`, error.message);
      results.push({
        file,
        error: error.message
      });
    }
  }
  
  return results;
}

async function resizeIcon(filePath, outputPath) {
  if (sharp) {
    // Use sharp: resize to fit 32x32, maintain aspect ratio, pad with transparent background
    await sharp(filePath)
      .resize(TARGET_SIZE, TARGET_SIZE, {
        fit: 'contain',
        background: { r: 0, g: 0, b: 0, alpha: 0 } // Transparent background
      })
      .toFile(outputPath);
  } else if (jimp) {
    // Use jimp: resize to fit 32x32, maintain aspect ratio, pad with transparent background
    const image = await jimp.read(filePath);
    
    // Calculate scaling to fit within 32x32 while maintaining aspect ratio
    const scale = Math.min(TARGET_SIZE / image.bitmap.width, TARGET_SIZE / image.bitmap.height);
    const newWidth = Math.round(image.bitmap.width * scale);
    const newHeight = Math.round(image.bitmap.height * scale);
    
    // Resize image
    image.resize(newWidth, newHeight);
    
    // Create a new 32x32 image with transparent background
    const squareImage = new jimp(TARGET_SIZE, TARGET_SIZE, 0x00000000); // Transparent
    
    // Center the resized image on the square canvas
    const x = Math.floor((TARGET_SIZE - newWidth) / 2);
    const y = Math.floor((TARGET_SIZE - newHeight) / 2);
    
    squareImage.composite(image, x, y);
    await squareImage.writeAsync(outputPath);
  }
}

async function resizeAllIcons(results) {
  console.log('\n🔄 Resizing icons to 32x32px...\n');
  
  const needsResize = results.filter(r => r.needsResize && !r.error);
  
  if (needsResize.length === 0) {
    console.log('✅ All icons are already 32x32px square!');
    return;
  }
  
  console.log(`Found ${needsResize.length} icon(s) that need resizing:\n`);
  
  // Create backup directory
  const backupDir = path.join(SPORTS_DIR, 'backup');
  await fs.mkdir(backupDir, { recursive: true });
  
  let successCount = 0;
  let errorCount = 0;
  
  for (const item of needsResize) {
    const filePath = path.join(SPORTS_DIR, item.file);
    const backupPath = path.join(backupDir, item.file);
    
    try {
      // Backup original
      await fs.copyFile(filePath, backupPath);
      
      // Resize
      await resizeIcon(filePath, filePath);
      
      // Verify new dimensions
      let newWidth, newHeight;
      if (sharp) {
        const metadata = await sharp(filePath).metadata();
        newWidth = metadata.width;
        newHeight = metadata.height;
      } else if (jimp) {
        const image = await jimp.read(filePath);
        newWidth = image.bitmap.width;
        newHeight = image.bitmap.height;
      }
      
      if (newWidth === TARGET_SIZE && newHeight === TARGET_SIZE) {
        console.log(`✅ ${item.file.padEnd(45)} ${item.width}x${item.height} → ${newWidth}x${newHeight}`);
        successCount++;
      } else {
        console.error(`⚠️  ${item.file.padEnd(45)} Expected 32x32, got ${newWidth}x${newHeight}`);
        errorCount++;
      }
      
    } catch (error) {
      console.error(`❌ Error resizing ${item.file}:`, error.message);
      // Restore from backup if resize failed
      try {
        await fs.copyFile(backupPath, filePath);
      } catch (restoreError) {
        console.error(`   Failed to restore backup:`, restoreError.message);
      }
      errorCount++;
    }
  }
  
  console.log(`\n✅ Successfully resized ${successCount} icon(s)`);
  if (errorCount > 0) {
    console.log(`⚠️  ${errorCount} icon(s) had errors`);
  }
  console.log(`\n📦 Original icons backed up to: ${backupDir}`);
}

async function main() {
  console.log('🎨 Sports Icon Resizer\n');
  console.log(`📁 Sports directory: ${SPORTS_DIR}`);
  console.log(`🎯 Target size: ${TARGET_SIZE}x${TARGET_SIZE}px\n`);
  
  try {
    // Analyze dimensions
    const results = await analyzeIconDimensions();
    
    // Summary
    const square = results.filter(r => r.isSquare && !r.error).length;
    const nonSquare = results.filter(r => !r.isSquare && !r.error).length;
    const correctSize = results.filter(r => r.width === TARGET_SIZE && r.height === TARGET_SIZE && !r.error).length;
    const needsResize = results.filter(r => r.needsResize && !r.error).length;
    
    console.log(`\n📊 Summary:`);
    console.log(`   Total icons: ${results.filter(r => !r.error).length}`);
    console.log(`   Square icons: ${square}`);
    console.log(`   Non-square icons: ${nonSquare}`);
    console.log(`   Already 32x32px: ${correctSize}`);
    console.log(`   Need resizing: ${needsResize}`);
    
    if (needsResize > 0) {
      console.log('\n⚠️  Some icons need to be resized to prevent truncation.');
      console.log('   Proceeding with resizing...\n');
      await resizeAllIcons(results);
    } else {
      console.log('\n✅ All icons are already properly sized!');
    }
    
  } catch (error) {
    console.error('\n❌ Error:', error);
    console.error(error.stack);
    process.exit(1);
  }
}

main();

