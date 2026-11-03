const fs = require('fs');
const content = fs.readFileSync('apps/mobile/src/i18n/translations.ts', 'utf8');
const lines = content.split('\n');
lines.forEach((l, idx) => {
  if (l.includes('saveProfileBtn') || l.includes('small_farmer')) {
    console.log(`${idx + 1}: ${l.trim()}`);
  }
});

