/**
 * Check which sports from the sheet don't have icons mapped
 */

const fs = require('fs');
const path = require('path');

// Load sport icon mapping
const mappingPath = path.join(__dirname, '../flags/sports/sports-icons-mapping.json');
const mapping = JSON.parse(fs.readFileSync(mappingPath, 'utf8'));

const mappedSports = new Set();
mapping.forEach(item => {
  mappedSports.add(item.sport.toLowerCase());
  // Add variations
  if (item.sport.toLowerCase() === 'batminton') {
    mappedSports.add('badminton');
  }
  if (item.sport.toLowerCase() === 'aquatic sports') {
    mappedSports.add('swimming');
    mappedSports.add('aquatics');
  }
  if (item.sport.toLowerCase() === 'flying discs') {
    mappedSports.add('flying disc');
  }
  if (item.sport.toLowerCase() === 'jui-jitsu') {
    mappedSports.add('ju-jitsu');
    mappedSports.add('jiu-jitsu');
  }
  if (item.sport.toLowerCase() === 'mixed martail arts') {
    mappedSports.add('mixed martial arts');
  }
  if (item.sport.toLowerCase() === 'esports') {
    mappedSports.add('e-sports');
  }
});

// Common SEAG25 sports to check
const seag25Sports = [
  'AIR SPORTS', 'AQUATICS', 'ARCHERY', 'ATHLETICS', 'BADMINTON',
  'BASEBALL', 'BASKETBALL', 'BILLIARDS', 'BOXING', 'CHESS', 'CRICKET',
  'CYCLING', 'E-SPORTS', 'FLOORBALL', 'FLYING DISC', 'FOOTBALL',
  'GOLF', 'GYMNASTICS', 'HANDBALL', 'HOCKEY', 'ICE HOCKEY',
  'JU-JITSU', 'JUDO', 'KARATE', 'KICKBOXING', 'MIXED MARTIAL ARTS',
  'MUAY', 'NETBALL', 'PENCAK SILAT', 'RUGBY', 'SAILING', 'SEPAK TAKRAW',
  'SHOOTING', 'SOFTBALL', 'SQUASH', 'TABLE TENNIS', 'TAEKWONDO',
  'TENNIS', 'TRADITIONAL BOAT RACE', 'TUG OF WAR', 'VOLLEYBALL', 'WEIGHTLIFTING'
];

console.log('Sport Icon Coverage Check:');
console.log('==========================\n');

const missing = [];
const found = [];

seag25Sports.forEach(sport => {
  const sportLower = sport.toLowerCase();
  let matched = false;
  
  // Check exact match
  if (mappedSports.has(sportLower)) {
    matched = true;
  } else {
    // Check partial matches
    for (const mapped of mappedSports) {
      if (sportLower.includes(mapped) || mapped.includes(sportLower)) {
        matched = true;
        break;
      }
    }
  }
  
  if (matched) {
    found.push(sport);
  } else {
    missing.push(sport);
  }
});

console.log(`✅ Sports with icons: ${found.length}`);
found.forEach(sport => console.log(`   ✓ ${sport}`));

console.log(`\n❌ Sports without icons: ${missing.length}`);
if (missing.length > 0) {
  missing.forEach(sport => console.log(`   ✗ ${sport}`));
} else {
  console.log('   (All sports have icons!)');
}

console.log(`\nTotal mapped icons: ${mappedSports.size}`);
console.log(`Total SEAG25 sports checked: ${seag25Sports.length}`);

