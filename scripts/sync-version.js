#!/usr/bin/env node
// package.json is the single source of truth for the app version. Gradle
// (android/app/build.gradle) and the React app (.env -> npm_package_version)
// read it by themselves; the Python backend can't (the packaged exe has no
// package.json), so this copies it into app/__init__.py.
//
// Runs automatically as npm's "version" lifecycle script:
//   npm version patch --no-git-tag-version   (or minor / major / 1.2.3)
// and can be run by hand: node scripts/sync-version.js
const fs = require('fs');
const path = require('path');

const root = path.join(__dirname, '..');
const { version } = JSON.parse(fs.readFileSync(path.join(root, 'package.json'), 'utf8'));
if (!/^\d+\.\d+\.\d+/.test(version)) {
  console.error(`Unsupported version "${version}" (expected MAJOR.MINOR.PATCH)`);
  process.exit(1);
}
const [major, minor, patch] = version.split('-')[0].split('.').map(Number);
if (minor > 99 || patch > 99) {
  console.error('minor and patch must stay under 100 (Android versionCode = major*10000 + minor*100 + patch)');
  process.exit(1);
}

const initPath = path.join(root, 'app', '__init__.py');
const source = fs.readFileSync(initPath, 'utf8');
const updated = source.replace(/^__version__ = ".*"/m, `__version__ = "${version}"`);
if (updated !== source) {
  fs.writeFileSync(initPath, updated);
  console.log(`app/__init__.py -> ${version}`);
}
console.log(`Version ${version}  (Android versionCode ${major * 10000 + minor * 100 + patch})`);
