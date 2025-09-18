const fs = require('fs');
const path = require('path');

console.log('🧪 Testing Jarvis App Builder File Structure...\n');

// Test 1: Check if all required directories exist
const requiredDirs = [
    'templates/expo-template',
    'generator/src',
    'modules',
    'dashboard/src',
    'ci',
    'docs'
];

console.log('1. Checking directory structure...');
let allDirsExist = true;

requiredDirs.forEach(dir => {
    if (fs.existsSync(dir)) {
        console.log(`✅ ${dir} exists`);
    } else {
        console.log(`❌ ${dir} missing`);
        allDirsExist = false;
    }
});

// Test 2: Check if key files exist
const requiredFiles = [
    'templates/expo-template/package.json',
    'templates/expo-template/App.tsx',
    'generator/package.json',
    'generator/src/index.ts',
    'generator/src/generator.ts',
    'dashboard/package.json',
    'dashboard/src/index.ts',
    'modules/rizz-text-bot/module.json',
    'ci/github-actions.yml',
    'README.md'
];

console.log('\n2. Checking key files...');
let allFilesExist = true;

requiredFiles.forEach(file => {
    if (fs.existsSync(file)) {
        console.log(`✅ ${file} exists`);
    } else {
        console.log(`❌ ${file} missing`);
        allFilesExist = false;
    }
});

// Test 3: Check package.json files for required dependencies
console.log('\n3. Checking package.json dependencies...');

const checkPackageJson = (filePath, requiredDeps) => {
    if (!fs.existsSync(filePath)) {
        console.log(`❌ ${filePath} not found`);
        return false;
    }
    
    try {
        const pkg = JSON.parse(fs.readFileSync(filePath, 'utf8'));
        const deps = { ...pkg.dependencies, ...pkg.devDependencies };
        
        let allDepsFound = true;
        requiredDeps.forEach(dep => {
            if (deps[dep]) {
                console.log(`✅ ${filePath} has ${dep}`);
            } else {
                console.log(`❌ ${filePath} missing ${dep}`);
                allDepsFound = false;
            }
        });
        
        return allDepsFound;
    } catch (error) {
        console.log(`❌ ${filePath} invalid JSON: ${error.message}`);
        return false;
    }
};

const generatorDeps = ['express', 'cors', 'handlebars', 'fs-extra'];
const dashboardDeps = ['express', 'cors', 'axios'];

checkPackageJson('generator/package.json', generatorDeps);
checkPackageJson('dashboard/package.json', dashboardDeps);

// Test 4: Check module definitions
console.log('\n4. Checking module definitions...');
const moduleDirs = fs.readdirSync('modules').filter(item => 
    fs.statSync(path.join('modules', item)).isDirectory()
);

moduleDirs.forEach(moduleDir => {
    const moduleJson = path.join('modules', moduleDir, 'module.json');
    if (fs.existsSync(moduleJson)) {
        try {
            const module = JSON.parse(fs.readFileSync(moduleJson, 'utf8'));
            const requiredFields = ['id', 'name', 'inputs', 'outputs', 'api'];
            const hasAllFields = requiredFields.every(field => module[field]);
            
            if (hasAllFields) {
                console.log(`✅ ${moduleDir} module definition is valid`);
            } else {
                console.log(`❌ ${moduleDir} module definition missing required fields`);
            }
        } catch (error) {
            console.log(`❌ ${moduleDir} module.json invalid: ${error.message}`);
        }
    } else {
        console.log(`❌ ${moduleDir} missing module.json`);
    }
});

// Summary
console.log('\n📊 Summary:');
if (allDirsExist && allFilesExist) {
    console.log('🎉 All basic structure tests passed!');
    console.log('\n📱 Next steps:');
    console.log('   1. Install dependencies: npm install (in generator/ and dashboard/)');
    console.log('   2. Start services: run start-jarvis.bat or start-jarvis.sh');
    console.log('   3. Open http://localhost:3000 to use the dashboard');
} else {
    console.log('❌ Some tests failed. Please check the missing files/directories.');
}
